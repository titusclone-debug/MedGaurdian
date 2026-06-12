"""Deterministic bridge from legacy NABHObjective rows to v6 requirement state."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.database import (
    ApplicabilityDefault,
    ComplianceStatus,
    EditionStatus,
    EvidenceStatus,
    Hospital,
    HospitalNABHRequirement,
    MaturityLevel,
    NABHChapter,
    NABHEdition,
    NABHLegacyMigrationMap,
    NABHMeasurableElement,
    NABHObjective,
    NABHObjectiveElement,
    NABHStandard,
    Staff,
)
from app.nabh.quality import NABHQualityError, assert_requirement_has_evidence_definitions


@dataclass
class MappingTarget:
    mapping_level: str
    requirement: NABHMeasurableElement


@dataclass
class MigrationReport:
    hospital_id: str
    edition_version: str
    dry_run: bool
    legacy_records_seen: int = 0
    mapped_legacy_records: int = 0
    unmapped_legacy_records: int = 0
    created_requirement_rows: int = 0
    updated_requirement_rows: int = 0
    skipped_existing_rows: int = 0
    conflicts: int = 0
    warnings: list[str] = field(default_factory=list)
    unmapped: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "hospital_id": self.hospital_id,
            "edition_version": self.edition_version,
            "dry_run": self.dry_run,
            "legacy_records_seen": self.legacy_records_seen,
            "mapped_legacy_records": self.mapped_legacy_records,
            "unmapped_legacy_records": self.unmapped_legacy_records,
            "created_requirement_rows": self.created_requirement_rows,
            "updated_requirement_rows": self.updated_requirement_rows,
            "skipped_existing_rows": self.skipped_existing_rows,
            "conflicts": self.conflicts,
            "warnings": self.warnings,
            "unmapped": self.unmapped,
        }


def _clean_code(value: Optional[str]) -> str:
    return (value or "").strip()


def _find_active_edition(db: Session, edition_version: str) -> Optional[NABHEdition]:
    return db.query(NABHEdition).filter(
        NABHEdition.version == edition_version,
        NABHEdition.status == EditionStatus.ACTIVE,
        NABHEdition.retired_at.is_(None),
    ).first()


def _active_requirement_query(db: Session, edition: NABHEdition):
    return db.query(NABHMeasurableElement).join(
        NABHObjectiveElement,
        NABHMeasurableElement.objective_element_id == NABHObjectiveElement.id,
    ).join(
        NABHStandard,
        NABHObjectiveElement.standard_id == NABHStandard.id,
    ).join(
        NABHChapter,
        NABHStandard.chapter_id == NABHChapter.id,
    ).filter(
        NABHMeasurableElement.edition_id == edition.id,
        NABHMeasurableElement.retired_at.is_(None),
        NABHObjectiveElement.retired_at.is_(None),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None),
    )


def _resolve_mapping_targets(db: Session, edition: NABHEdition, legacy_code: str) -> list[MappingTarget]:
    code = _clean_code(legacy_code)
    if not code:
        return []

    exact_requirement = _active_requirement_query(db, edition).filter(
        NABHMeasurableElement.canonical_code == code,
    ).first()
    if exact_requirement:
        return [MappingTarget("measurable_element", exact_requirement)]

    objective = db.query(NABHObjectiveElement).join(
        NABHStandard,
        NABHObjectiveElement.standard_id == NABHStandard.id,
    ).join(
        NABHChapter,
        NABHStandard.chapter_id == NABHChapter.id,
    ).filter(
        NABHObjectiveElement.edition_id == edition.id,
        NABHObjectiveElement.canonical_code == code,
        NABHObjectiveElement.retired_at.is_(None),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None),
    ).first()
    if objective:
        rows = _active_requirement_query(db, edition).filter(
            NABHMeasurableElement.objective_element_id == objective.id,
        ).order_by(NABHMeasurableElement.display_order).all()
        return [MappingTarget("objective_element", row) for row in rows]

    standard = db.query(NABHStandard).join(
        NABHChapter,
        NABHStandard.chapter_id == NABHChapter.id,
    ).filter(
        NABHStandard.edition_id == edition.id,
        NABHStandard.canonical_code == code,
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None),
    ).first()
    if standard:
        rows = _active_requirement_query(db, edition).filter(
            NABHObjectiveElement.standard_id == standard.id,
        ).order_by(
            NABHObjectiveElement.display_order,
            NABHMeasurableElement.display_order,
        ).all()
        return [MappingTarget("standard", row) for row in rows]

    return []


def _translate_maturity(maturity: Optional[MaturityLevel]) -> tuple[MaturityLevel, ComplianceStatus, EvidenceStatus]:
    if maturity in {MaturityLevel.IMPLEMENTED, MaturityLevel.MEASURED, MaturityLevel.OPTIMIZED}:
        return maturity, ComplianceStatus.COMPLIANT, EvidenceStatus.PENDING_VERIFICATION
    if maturity == MaturityLevel.DEFINED:
        return maturity, ComplianceStatus.PARTIALLY_COMPLIANT, EvidenceStatus.DRAFT
    if maturity in {MaturityLevel.NON_EXISTENT, MaturityLevel.AD_HOC}:
        return maturity, ComplianceStatus.NON_COMPLIANT, EvidenceStatus.MISSING
    return MaturityLevel.NON_EXISTENT, ComplianceStatus.UNDER_REVIEW, EvidenceStatus.MISSING


def _staff_in_hospital(db: Session, staff_id: Optional[str], hospital_id: str) -> Optional[Staff]:
    if not staff_id:
        return None
    return db.query(Staff).filter(
        Staff.id == staff_id,
        Staff.hospital_id == hospital_id,
        Staff.is_active == True,
    ).first()


def _record_mapping(
    db: Session,
    *,
    dry_run: bool,
    hospital_id: str,
    legacy: NABHObjective,
    new_requirement_id: Optional[str],
    mapping_level: str,
    mapping_status: str,
    reason: str,
) -> None:
    if dry_run:
        return

    existing = db.query(NABHLegacyMigrationMap).filter(
        NABHLegacyMigrationMap.legacy_objective_id == legacy.id,
        NABHLegacyMigrationMap.new_requirement_id == new_requirement_id,
        NABHLegacyMigrationMap.mapping_level == mapping_level,
    ).first()
    if existing:
        existing.mapping_status = mapping_status
        existing.reason = reason
        existing.migrated_at = datetime.utcnow()
        return

    db.add(NABHLegacyMigrationMap(
        hospital_id=hospital_id,
        legacy_objective_id=legacy.id,
        legacy_standard_code=legacy.standard_code,
        new_requirement_id=new_requirement_id,
        mapping_level=mapping_level,
        mapping_status=mapping_status,
        reason=reason,
        migrated_at=datetime.utcnow(),
    ))


def _build_new_state(
    db: Session,
    *,
    legacy: NABHObjective,
    target: MappingTarget,
    hospital_id: str,
    report: MigrationReport,
) -> HospitalNABHRequirement:
    maturity, readiness, evidence_status = _translate_maturity(legacy.maturity_level)
    if readiness == ComplianceStatus.COMPLIANT:
        try:
            assert_requirement_has_evidence_definitions(db, target.requirement.id)
        except NABHQualityError:
            readiness = ComplianceStatus.UNDER_REVIEW
            evidence_status = EvidenceStatus.MISSING
            report.warnings.append(
                f"Legacy objective {legacy.id} was compliant, but {target.requirement.canonical_code} "
                "was downgraded to under_review because evidence definitions are missing."
            )

    owner_id = None
    if _staff_in_hospital(db, legacy.remediation_owner, hospital_id):
        owner_id = legacy.remediation_owner
    elif legacy.remediation_owner:
        report.warnings.append(
            f"Legacy objective {legacy.id} remediation_owner was ignored because it is not active in this hospital."
        )

    reviewer_id = None
    if _staff_in_hospital(db, legacy.assessed_by, hospital_id):
        reviewer_id = legacy.assessed_by
    elif legacy.assessed_by and legacy.assessed_by != "System Agent":
        report.warnings.append(
            f"Legacy objective {legacy.id} assessed_by was not copied because it is not an active same-hospital staff id."
        )

    return HospitalNABHRequirement(
        hospital_id=hospital_id,
        requirement_id=target.requirement.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        applicability_reason=f"Migrated from legacy NABH objective {legacy.standard_code} at {target.mapping_level} level.",
        maturity_level=maturity,
        evidence_status=evidence_status,
        owner_id=owner_id,
        due_date=legacy.remediation_deadline,
        last_reviewed_at=legacy.last_assessed,
        last_reviewed_by=reviewer_id,
        readiness_status=readiness,
    )


def migrate_hospital_legacy_nabh_state(
    db: Session,
    hospital_id: str,
    edition_version: str = "6.0",
    dry_run: bool = False,
) -> dict:
    """Map legacy NABHObjective records into new requirement state where safe."""
    report = MigrationReport(
        hospital_id=hospital_id,
        edition_version=edition_version,
        dry_run=dry_run,
    )

    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise ValueError(f"Hospital '{hospital_id}' not found.")

    edition = _find_active_edition(db, edition_version)
    if not edition:
        raise ValueError(f"Active NABH edition '{edition_version}' not found.")

    legacy_rows = db.query(NABHObjective).filter(
        NABHObjective.hospital_id == hospital_id,
    ).order_by(NABHObjective.standard_code).all()
    report.legacy_records_seen = len(legacy_rows)

    for legacy in legacy_rows:
        targets = _resolve_mapping_targets(db, edition, legacy.standard_code)
        if not targets:
            report.unmapped_legacy_records += 1
            reason = "No active v6 standard, objective element, or measurable element matched legacy standard_code."
            report.unmapped.append({
                "legacy_objective_id": legacy.id,
                "legacy_standard_code": legacy.standard_code,
                "reason": reason,
            })
            _record_mapping(
                db,
                dry_run=dry_run,
                hospital_id=hospital_id,
                legacy=legacy,
                new_requirement_id=None,
                mapping_level="unmapped",
                mapping_status="unmapped",
                reason=reason,
            )
            continue

        report.mapped_legacy_records += 1
        if len(targets) > 1:
            report.warnings.append(
                f"Legacy objective {legacy.id} ({legacy.standard_code}) mapped to "
                f"{len(targets)} requirements at {targets[0].mapping_level} level."
            )

        for target in targets:
            existing = db.query(HospitalNABHRequirement).filter(
                HospitalNABHRequirement.hospital_id == hospital_id,
                HospitalNABHRequirement.requirement_id == target.requirement.id,
                HospitalNABHRequirement.retired_at.is_(None),
            ).first()

            if existing:
                report.skipped_existing_rows += 1
                _record_mapping(
                    db,
                    dry_run=dry_run,
                    hospital_id=hospital_id,
                    legacy=legacy,
                    new_requirement_id=target.requirement.id,
                    mapping_level=target.mapping_level,
                    mapping_status="skipped_existing",
                    reason="Existing new requirement state preserved.",
                )
                continue

            if not dry_run:
                db.add(_build_new_state(
                    db,
                    legacy=legacy,
                    target=target,
                    hospital_id=hospital_id,
                    report=report,
                ))
            report.created_requirement_rows += 1
            _record_mapping(
                db,
                dry_run=dry_run,
                hospital_id=hospital_id,
                legacy=legacy,
                new_requirement_id=target.requirement.id,
                mapping_level=target.mapping_level,
                mapping_status="mapped",
                reason="Created new requirement state from legacy objective.",
            )

    if not dry_run:
        db.flush()
    return report.to_dict()


def migrate_all_hospitals_legacy_nabh_state(
    db: Session,
    edition_version: str = "6.0",
    dry_run: bool = False,
) -> list[dict]:
    hospital_ids = [
        row[0]
        for row in db.query(NABHObjective.hospital_id).distinct().all()
    ]
    return [
        migrate_hospital_legacy_nabh_state(db, hospital_id, edition_version, dry_run)
        for hospital_id in hospital_ids
    ]
