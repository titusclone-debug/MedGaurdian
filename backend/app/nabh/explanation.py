from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHRequirement,
    NABHEvidenceRequirement, NABHRequirementCitation,
    NABHSourceDocument, HospitalNABHRequirement, Staff,
    EditionStatus
)
from app.nabh.canonical import ACTIVE_PUBLICATION_STATUSES, ensure_canonical_compatibility
from app.nabh.quality import citation_has_locator

def build_requirement_explanation(
    db: Session,
    requirement_id: str,
    hospital_id: Optional[str] = None,
    edition_version: str = "6.0"
) -> Dict[str, Any]:
    """
    Builds a deterministic explanation for a NABH requirement.
    Raises HTTPException(404) if requirement or active edition is missing/retired.
    """
    # 1. Verify Edition
    edition = db.query(NABHEdition).filter(
        NABHEdition.version == edition_version,
        NABHEdition.status == EditionStatus.ACTIVE,
        NABHEdition.retired_at.is_(None)
    ).first()
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active NABH edition version '{edition_version}' not found."
        )

    # 2. Query Requirement and all parent ontology layers (excluding retired)
    ensure_canonical_compatibility(db, edition.id)
    result = db.query(
        NABHRequirement, NABHStandard, NABHChapter
    ).join(
        NABHStandard, NABHRequirement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        NABHRequirement.id == requirement_id,
        NABHRequirement.edition_id == edition.id,
        NABHRequirement.retired_at.is_(None),
        NABHRequirement.publication_status.in_(ACTIVE_PUBLICATION_STATUSES),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None)
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active requirement with ID '{requirement_id}' not found."
        )

    requirement, std, chapter = result

    # 3. Retrieve Evidence Requirements (non-retired)
    evidences = db.query(NABHEvidenceRequirement).filter(
        NABHEvidenceRequirement.requirement_id == requirement.id,
        NABHEvidenceRequirement.retired_at.is_(None)
    ).all()

    # 4. Retrieve Citations (non-retired)
    citations_data = db.query(
        NABHRequirementCitation, NABHSourceDocument
    ).join(
        NABHSourceDocument, NABHRequirementCitation.document_id == NABHSourceDocument.id
    ).filter(
        NABHRequirementCitation.requirement_id == requirement.id,
        NABHRequirementCitation.retired_at.is_(None),
        NABHSourceDocument.retired_at.is_(None)
    ).all()
    citations_data = [
        (citation, document)
        for citation, document in citations_data
        if citation_has_locator(citation)
    ]

    # 5. Retrieve Hospital Requirement State if hospital_id is provided
    hospital_req = None
    if hospital_id:
        hospital_req = db.query(HospitalNABHRequirement).filter(
            HospitalNABHRequirement.hospital_id == hospital_id,
            HospitalNABHRequirement.canonical_requirement_id == requirement.id,
            HospitalNABHRequirement.retired_at.is_(None)
        ).first()

    # 6. Explanation Logic & Citations Check
    plain_language_explanation = None
    why_it_matters = None
    confidence = "missing_citation"
    limitations = []

    if not citations_data:
        limitations.append("No citation is available for this requirement.")
    else:
        confidence = "source_cited"
        plain_language_explanation = (
            f"This requirement asks the hospital to ensure: {requirement.display_text}. "
            f"It belongs to {chapter.code}: {chapter.title}, under standard {std.canonical_code}: {std.title}. "
            f"For survey readiness, the hospital must be able to show current, reviewable evidence."
        )

        why_it_matters = (
            "Surveyors use this objective element to verify that the stated process "
            "is implemented and supported by appropriate evidence."
        )

    # 7. Evidence Requirements mapping
    required_evidence = []
    for ev in evidences:
        required_evidence.append({
            "evidence_code": ev.evidence_code,
            "evidence_type": ev.evidence_type.value if hasattr(ev.evidence_type, "value") else str(ev.evidence_type),
            "description": ev.description,
            "suggested_documentation": ev.suggested_documentation,
            "is_mandatory": ev.is_mandatory,
            "evidence_frequency": ev.evidence_frequency,
            "minimum_lookback_days": ev.minimum_lookback_days,
            "default_owner_role": ev.default_owner_role
        })

    proof_burden_summary = {
        "mandatory_evidence_count": sum(1 for ev in evidences if ev.is_mandatory),
        "optional_evidence_count": sum(1 for ev in evidences if not ev.is_mandatory),
        "evidence_types_required": list(set(
            ev.evidence_type.value if hasattr(ev.evidence_type, "value") else str(ev.evidence_type)
            for ev in evidences
        )),
        "lookback_days_required": max([ev.minimum_lookback_days for ev in evidences] + [0])
    }

    # 8. Responsible Role Resolution
    evidence_roles = sorted(list({ev.default_owner_role for ev in evidences if ev.default_owner_role and ev.default_owner_role.strip()}))
    
    responsible_role = "quality_officer"
    responsible_roles = []
    responsible_owner_id = None
    responsible_owner_name = None

    staff_owner = None
    if hospital_req and hospital_req.owner_id and hospital_id:
        staff_owner = db.query(Staff).filter(
            Staff.id == hospital_req.owner_id,
            Staff.hospital_id == hospital_id,
            Staff.is_active == True
        ).first()

    if staff_owner:
        responsible_role = staff_owner.role.value if hasattr(staff_owner.role, "value") else str(staff_owner.role)
        responsible_owner_id = staff_owner.id
        responsible_owner_name = staff_owner.name
    elif hospital_req and hospital_req.owner_id:
        # owner_id exists but is not a Staff ID (e.g. role string)
        responsible_role = hospital_req.owner_id
    elif len(evidence_roles) == 1:
        responsible_role = evidence_roles[0]
    elif len(evidence_roles) > 1:
        responsible_role = "multiple"
        responsible_roles = evidence_roles
    elif requirement.default_owner_role:
        responsible_role = requirement.default_owner_role

    # 9. Applicability formatting
    applicability = {
        "status": requirement.applicability_default.value if hasattr(requirement.applicability_default, "value") else str(requirement.applicability_default),
        "reason": "Default applicability for this requirement."
    }

    # 10. Citations mapping
    citations = []
    for cit, doc in citations_data:
        citations.append({
            "document_title": doc.title,
            "publisher": doc.publisher,
            "edition_version": doc.edition_version,
            "section": cit.section,
            "page_number": cit.page_number,
            "clause_text_summary": cit.clause_text_summary,
            "effective_date": cit.effective_date,
            "file_path": cit.file_path,
            "url": cit.url
        })

    # 11. Hospital State context
    hospital_state = None
    if hospital_id:
        if hospital_req:
            # Look up owner if not done
            if not staff_owner and hospital_req.owner_id and hospital_id:
                staff_owner = db.query(Staff).filter(
                    Staff.id == hospital_req.owner_id,
                    Staff.hospital_id == hospital_id,
                    Staff.is_active == True
                ).first()

            hospital_state = {
                "applicability_status": hospital_req.applicability_status.value if hasattr(hospital_req.applicability_status, "value") else str(hospital_req.applicability_status),
                "applicability_reason": hospital_req.applicability_reason,
                "readiness_status": hospital_req.readiness_status.value if hasattr(hospital_req.readiness_status, "value") else str(hospital_req.readiness_status),
                "maturity_level": hospital_req.maturity_level.value if hasattr(hospital_req.maturity_level, "value") else hospital_req.maturity_level,
                "evidence_status": hospital_req.evidence_status.value if (hospital_req.evidence_status and hasattr(hospital_req.evidence_status, "value")) else (str(hospital_req.evidence_status) if hospital_req.evidence_status else None),
                "due_date": hospital_req.due_date,
                "owner_id": hospital_req.owner_id,
                "owner_name": staff_owner.name if staff_owner else None,
                "owner_role": (staff_owner.role.value if hasattr(staff_owner.role, "value") else str(staff_owner.role)) if staff_owner else None
            }
        else:
            limitations.append("Hospital-specific requirement state has not been computed yet.")

    return {
        "requirement_id": requirement.id,
        "requirement_code": requirement.canonical_code,
        "title": requirement.display_text,
        "plain_language_explanation": plain_language_explanation,
        "why_it_matters": why_it_matters,
        "required_evidence": required_evidence,
        "proof_burden_summary": proof_burden_summary,
        "responsible_role": responsible_role,
        "responsible_roles": responsible_roles,
        "responsible_owner_id": responsible_owner_id,
        "responsible_owner_name": responsible_owner_name,
        "applicability": applicability,
        "citations": citations,
        "confidence": confidence,
        "hospital_state": hospital_state,
        "limitations": limitations
    }
