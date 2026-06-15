from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import (
    ApplicabilityDefault,
    EditionStatus,
    Hospital,
    HospitalNABHRequirement,
    NABHChapter,
    NABHEdition,
    NABHEvidenceRequirement,
    NABHMeasurableElement,
    NABHObjectiveElement,
    NABHRequirementCitation,
    NABHSourceDocument,
    NABHStandard,
    Staff,
)
from app.nabh.quality import citation_has_locator


OFFICIAL_CHAPTER_CODES = ["AAC", "COP", "MOM", "PRE", "IPC", "PSQ", "ROM", "FMS", "HRM", "IMS"]
SCOPED_APPLICABILITY_STATUSES = [
    ApplicabilityDefault.APPLICABLE,
    ApplicabilityDefault.CONDITIONAL,
    ApplicabilityDefault.MANUAL_REVIEW,
]


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _proof_burden_summary(evidences: List[NABHEvidenceRequirement]) -> Dict[str, Any]:
    return {
        "mandatory_evidence_count": sum(1 for evidence in evidences if evidence.is_mandatory),
        "optional_evidence_count": sum(1 for evidence in evidences if not evidence.is_mandatory),
        "evidence_types_required": sorted({
            _enum_value(evidence.evidence_type)
            for evidence in evidences
            if evidence.evidence_type is not None
        }),
        "lookback_days_required": max([evidence.minimum_lookback_days for evidence in evidences] + [0]),
    }


def _resolve_responsible_role(
    hospital_req: HospitalNABHRequirement,
    requirement: NABHMeasurableElement,
    evidences: List[NABHEvidenceRequirement],
    staff_by_id: Dict[str, Staff],
) -> Dict[str, Optional[str]]:
    if hospital_req.owner_id:
        staff_owner = staff_by_id.get(hospital_req.owner_id)
        if staff_owner:
            return {
                "responsible_role": _enum_value(staff_owner.role),
                "responsible_owner_id": staff_owner.id,
                "responsible_owner_name": staff_owner.name,
            }
        return {
            "responsible_role": hospital_req.owner_id,
            "responsible_owner_id": hospital_req.owner_id,
            "responsible_owner_name": None,
        }

    evidence_roles = sorted({
        evidence.default_owner_role
        for evidence in evidences
        if evidence.default_owner_role and evidence.default_owner_role.strip()
    })
    if len(evidence_roles) == 1:
        responsible_role = evidence_roles[0]
    elif len(evidence_roles) > 1:
        responsible_role = "multiple"
    elif requirement.default_owner_role:
        responsible_role = requirement.default_owner_role
    else:
        responsible_role = "quality_officer"

    return {
        "responsible_role": responsible_role,
        "responsible_owner_id": None,
        "responsible_owner_name": None,
    }


def build_hospital_evidence_plan(
    db: Session,
    hospital_id: str,
    edition_version: str = "6.0",
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Return a bulk evidence plan for hospital-scoped requirements.

    This is intentionally lighter than the full explanation endpoint. It exists
    to avoid one HTTP request and several database queries per requirement when
    the frontend needs an aggregated "Evidence Needed" view.
    """
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital with ID '{hospital_id}' does not exist.",
        )

    edition = db.query(NABHEdition).filter(
        NABHEdition.version == edition_version,
        NABHEdition.status == EditionStatus.ACTIVE,
        NABHEdition.retired_at.is_(None),
    ).first()
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active NABH edition version '{edition_version}' not found.",
        )

    base_query = db.query(
        HospitalNABHRequirement,
        NABHMeasurableElement,
        NABHObjectiveElement,
        NABHStandard,
        NABHChapter,
    ).join(
        NABHMeasurableElement,
        HospitalNABHRequirement.requirement_id == NABHMeasurableElement.id,
    ).join(
        NABHObjectiveElement,
        NABHMeasurableElement.objective_element_id == NABHObjectiveElement.id,
    ).join(
        NABHStandard,
        NABHObjectiveElement.standard_id == NABHStandard.id,
    ).join(
        NABHChapter,
        NABHStandard.chapter_id == NABHChapter.id,
    ).filter(
        HospitalNABHRequirement.hospital_id == hospital_id,
        HospitalNABHRequirement.applicability_status.in_(SCOPED_APPLICABILITY_STATUSES),
        HospitalNABHRequirement.retired_at.is_(None),
        NABHMeasurableElement.edition_id == edition.id,
        NABHMeasurableElement.retired_at.is_(None),
        NABHObjectiveElement.retired_at.is_(None),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None),
        NABHChapter.canonical_code.in_(OFFICIAL_CHAPTER_CODES),
    )

    total_requirements = base_query.count()
    rows = base_query.order_by(
        NABHChapter.display_order,
        NABHStandard.display_order,
        NABHObjectiveElement.display_order,
        NABHMeasurableElement.display_order,
    ).offset(offset).limit(limit).all()

    requirement_ids = [row.NABHMeasurableElement.id for row in rows]
    evidences_by_requirement: Dict[str, List[NABHEvidenceRequirement]] = defaultdict(list)
    active_citation_counts: Dict[str, int] = defaultdict(int)

    if requirement_ids:
        evidences = db.query(NABHEvidenceRequirement).filter(
            NABHEvidenceRequirement.measurable_element_id.in_(requirement_ids),
            NABHEvidenceRequirement.retired_at.is_(None),
        ).order_by(
            NABHEvidenceRequirement.evidence_code,
            NABHEvidenceRequirement.id,
        ).all()
        for evidence in evidences:
            evidences_by_requirement[evidence.measurable_element_id].append(evidence)

        citation_rows = db.query(
            NABHRequirementCitation,
            NABHSourceDocument,
        ).join(
            NABHSourceDocument,
            NABHRequirementCitation.document_id == NABHSourceDocument.id,
        ).filter(
            NABHRequirementCitation.measurable_element_id.in_(requirement_ids),
            NABHRequirementCitation.retired_at.is_(None),
            NABHSourceDocument.retired_at.is_(None),
        ).all()
        for citation, _document in citation_rows:
            if citation_has_locator(citation):
                active_citation_counts[citation.measurable_element_id] += 1

    owner_ids = {
        row.HospitalNABHRequirement.owner_id
        for row in rows
        if row.HospitalNABHRequirement.owner_id
    }
    staff_by_id: Dict[str, Staff] = {}
    if owner_ids:
        staff_records = db.query(Staff).filter(
            Staff.id.in_(owner_ids),
            Staff.hospital_id == hospital_id,
            Staff.is_active == True,
        ).all()
        staff_by_id = {staff.id: staff for staff in staff_records}

    items = []
    evidence_item_count = 0
    for hospital_req, requirement, _objective, standard, chapter in rows:
        requirement_evidences = evidences_by_requirement.get(requirement.id, [])
        evidence_item_count += len(requirement_evidences)
        responsibility = _resolve_responsible_role(
            hospital_req,
            requirement,
            requirement_evidences,
            staff_by_id,
        )
        citation_count = active_citation_counts.get(requirement.id, 0)
        limitations = []
        if citation_count == 0:
            limitations.append("No active citation with locator is available for this requirement.")
        if not requirement_evidences:
            limitations.append("No active evidence requirement is available for this requirement.")

        items.append({
            "requirement_id": requirement.id,
            "requirement_code": requirement.canonical_code,
            "title": requirement.description,
            "chapter_code": chapter.canonical_code,
            "standard_code": standard.canonical_code,
            "applicability_status": _enum_value(hospital_req.applicability_status),
            "readiness_status": _enum_value(hospital_req.readiness_status),
            "evidence_status": _enum_value(hospital_req.evidence_status),
            "responsible_role": responsibility["responsible_role"],
            "responsible_owner_id": responsibility["responsible_owner_id"],
            "responsible_owner_name": responsibility["responsible_owner_name"],
            "confidence": "source_cited" if citation_count > 0 else "missing_citation",
            "citation_count": citation_count,
            "required_evidence": [
                {
                    "evidence_code": evidence.evidence_code,
                    "evidence_type": _enum_value(evidence.evidence_type),
                    "description": evidence.description,
                    "suggested_documentation": evidence.suggested_documentation,
                    "is_mandatory": evidence.is_mandatory,
                    "evidence_frequency": evidence.evidence_frequency,
                    "minimum_lookback_days": evidence.minimum_lookback_days,
                    "default_owner_role": evidence.default_owner_role,
                }
                for evidence in requirement_evidences
            ],
            "proof_burden_summary": _proof_burden_summary(requirement_evidences),
            "limitations": limitations,
        })

    return {
        "hospital_id": hospital_id,
        "edition_version": edition_version,
        "total_applicable_requirements": total_requirements,
        "returned_requirements": len(items),
        "evidence_item_count": evidence_item_count,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
