"""Runtime quality guardrails for NABH v6 ontology usage.

The JSON seed validator checks source-file structure before database writes.
This module checks persisted database entities before they are used for
production-facing, agent-facing, or compliant-status workflows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.database import (
    ApplicabilityDefault,
    ComplianceStatus,
    EditionStatus,
    NABHChapter,
    NABHEdition,
    NABHEvidenceRequirement,
    NABHRequirement,
    NABHRequirementCitation,
    NABHSourceDocument,
    NABHStandard,
    KnowledgePublicationStatus,
)
from app.nabh.canonical import ACTIVE_PUBLICATION_STATUSES, ensure_canonical_compatibility


PLACEHOLDER_VALUES = {"", "tbd", "todo", "placeholder", "unknown", "n/a"}


class NABHQualityError(ValueError):
    """Raised when a NABH requirement fails runtime quality checks."""


@dataclass
class RequirementQualityReport:
    requirement_id: str
    requirement_code: str
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _has_text(value: Optional[str]) -> bool:
    if value is None:
        return False
    return bool(str(value).strip())


def _is_placeholder(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in PLACEHOLDER_VALUES


def _add_required_text_error(errors: list[str], label: str, value: Optional[str]) -> None:
    if not _has_text(value):
        errors.append(f"missing {label}")
    elif _is_placeholder(value):
        errors.append(f"{label} contains placeholder value")


def _active_requirement_chain(db: Session, requirement_id: str):
    ensure_canonical_compatibility(db)
    return db.query(
        NABHRequirement,
        NABHStandard,
        NABHChapter,
        NABHEdition,
    ).join(
        NABHStandard,
        NABHRequirement.standard_id == NABHStandard.id,
    ).join(
        NABHChapter,
        NABHStandard.chapter_id == NABHChapter.id,
    ).join(
        NABHEdition,
        NABHChapter.edition_id == NABHEdition.id,
    ).filter(
        NABHRequirement.id == requirement_id,
        NABHRequirement.retired_at.is_(None),
        NABHRequirement.publication_status.in_(ACTIVE_PUBLICATION_STATUSES),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None),
        NABHEdition.retired_at.is_(None),
    ).first()


def _active_evidence_requirements(db: Session, requirement_id: str) -> list[NABHEvidenceRequirement]:
    return db.query(NABHEvidenceRequirement).filter(
        NABHEvidenceRequirement.requirement_id == requirement_id,
        NABHEvidenceRequirement.retired_at.is_(None),
    ).all()


def _active_citations_with_documents(db: Session, requirement_id: str):
    return db.query(NABHRequirementCitation, NABHSourceDocument).join(
        NABHSourceDocument,
        NABHRequirementCitation.document_id == NABHSourceDocument.id,
    ).filter(
        NABHRequirementCitation.requirement_id == requirement_id,
        NABHRequirementCitation.retired_at.is_(None),
        NABHSourceDocument.retired_at.is_(None),
    ).all()


def citation_has_locator(citation: NABHRequirementCitation) -> bool:
    return any(
        _has_text(value)
        for value in (
            citation.section,
            citation.page_number,
            citation.clause_text_summary,
            citation.file_path,
            citation.url,
        )
    )


def validate_requirement_runtime_quality(
    db: Session,
    requirement_id: str,
    *,
    require_citation: bool = True,
    require_evidence: bool = True,
    require_active_edition: bool = True,
) -> RequirementQualityReport:
    """Validate persisted requirement quality without requiring full ontology coverage.

    This checks only the requested active/seeded requirement. It deliberately does
    not require all official NABH v6 elements to be present.
    """
    chain = _active_requirement_chain(db, requirement_id)
    if not chain:
        return RequirementQualityReport(
            requirement_id=requirement_id,
            requirement_code=requirement_id,
            errors=["requirement is missing or has a retired ontology chain"],
        )

    requirement, standard, chapter, edition = chain
    report = RequirementQualityReport(
        requirement_id=requirement.id,
        requirement_code=requirement.canonical_code or requirement.id,
    )
    errors = report.errors

    if require_active_edition and edition.status != EditionStatus.ACTIVE:
        errors.append("edition is not active")

    _add_required_text_error(errors, "chapter code", chapter.canonical_code)
    _add_required_text_error(errors, "chapter title", chapter.title)
    _add_required_text_error(errors, "standard code", standard.canonical_code)
    _add_required_text_error(errors, "standard title", standard.title)
    _add_required_text_error(errors, "requirement code", requirement.canonical_code)
    _add_required_text_error(errors, "requirement description", requirement.display_text)

    if requirement.applicability_default is None:
        errors.append("missing applicability default")
    elif _enum_value(requirement.applicability_default) not in {item.value for item in ApplicabilityDefault}:
        errors.append("invalid applicability default")

    if require_evidence:
        evidence_rows = _active_evidence_requirements(db, requirement.id)
        if not evidence_rows:
            errors.append("missing active evidence requirement")
        for evidence in evidence_rows:
            if evidence.evidence_type is None:
                errors.append("missing evidence type")
            _add_required_text_error(errors, "evidence description", evidence.description)
            if evidence.is_mandatory is None:
                errors.append("missing evidence mandatory flag")
            if evidence.minimum_lookback_days is None or evidence.minimum_lookback_days < 0:
                errors.append("invalid evidence lookback days")

    if require_citation:
        citation_rows = _active_citations_with_documents(db, requirement.id)
        if not citation_rows:
            errors.append("missing active citation with active source document")
        elif not any(citation_has_locator(citation) for citation, _document in citation_rows):
            errors.append("missing citation locator")
        if requirement.source_status == "official_verified":
            verified_citations = [
                (citation, document)
                for citation, document in citation_rows
                if citation.human_verified
                and document.verification_status in {
                    KnowledgePublicationStatus.APPROVED,
                    KnowledgePublicationStatus.PUBLISHED,
                }
            ]
            if not verified_citations:
                errors.append(
                    "official requirement lacks a human-verified citation "
                    "to an approved source document"
                )

    return report


def assert_requirement_agent_retrievable(db: Session, requirement_id: str) -> RequirementQualityReport:
    """Require source-cited runtime quality before authoritative agent use."""
    report = validate_requirement_runtime_quality(
        db,
        requirement_id,
        require_citation=True,
        require_evidence=False,
        require_active_edition=True,
    )
    if not report.ok:
        raise NABHQualityError(
            f"Requirement {report.requirement_code} is not agent-retrievable: "
            + "; ".join(report.errors)
        )
    return report


def assert_requirement_has_evidence_definitions(db: Session, requirement_id: str) -> None:
    """Require active evidence definitions before compliant status is allowed."""
    chain_report = validate_requirement_runtime_quality(
        db,
        requirement_id,
        require_citation=False,
        require_evidence=False,
        require_active_edition=True,
    )
    if not chain_report.ok:
        raise NABHQualityError(
            "Requirement cannot be marked compliant because its active ontology "
            "chain is incomplete: " + "; ".join(chain_report.errors)
        )

    evidence_rows = _active_evidence_requirements(db, requirement_id)
    valid_rows = [
        evidence
        for evidence in evidence_rows
        if evidence.evidence_type is not None
        and _has_text(evidence.description)
        and not _is_placeholder(evidence.description)
        and evidence.is_mandatory is not None
        and evidence.minimum_lookback_days is not None
        and evidence.minimum_lookback_days >= 0
    ]
    if not valid_rows:
        raise NABHQualityError(
            "Requirement cannot be marked compliant until active evidence "
            "requirement definitions exist."
        )


def assert_compliant_status_allowed(
    db: Session,
    requirement_id: str,
    readiness_status: Optional[ComplianceStatus],
) -> None:
    if readiness_status == ComplianceStatus.COMPLIANT or readiness_status == ComplianceStatus.COMPLIANT.value:
        assert_requirement_has_evidence_definitions(db, requirement_id)


def assert_seeded_requirements_runtime_quality(
    db: Session,
    requirement_ids: Iterable[str],
) -> list[RequirementQualityReport]:
    """Validate seeded DB rows after upsert and raise with all quality failures."""
    reports = [
        validate_requirement_runtime_quality(db, requirement_id)
        for requirement_id in sorted(set(requirement_ids))
    ]
    failures = [report for report in reports if not report.ok]
    if failures:
        details = []
        for report in failures:
            details.extend(
                f"{report.requirement_code}: {error}"
                for error in report.errors
            )
        raise NABHQualityError(
            "NABH runtime quality validation failed:\n- " + "\n- ".join(details)
        )
    return reports
