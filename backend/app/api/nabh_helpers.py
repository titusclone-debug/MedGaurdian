"""Shared HTTP-layer helpers for NABH route modules."""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.database import Staff


def assert_staff_belongs_to_hospital(
    db: Session,
    staff_id: Optional[str],
    hospital_id: str,
    field_name: str,
) -> None:
    if staff_id is None:
        return

    staff = db.query(Staff).filter(
        Staff.id == staff_id,
        Staff.is_active == True,
    ).first()
    if not staff or staff.hospital_id != hospital_id:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must reference an active staff member in the same hospital.",
        )


def build_evidence_burden_summary(evidences: list) -> dict:
    mandatory_count = sum(1 for evidence in evidences if evidence.is_mandatory)
    optional_count = sum(1 for evidence in evidences if not evidence.is_mandatory)
    evidence_types = sorted({
        evidence.evidence_type.value
        if hasattr(evidence.evidence_type, "value")
        else str(evidence.evidence_type)
        for evidence in evidences
    })
    lookback_days = max([evidence.minimum_lookback_days for evidence in evidences] + [0])
    return {
        "mandatory_evidence_count": mandatory_count,
        "optional_evidence_count": optional_count,
        "evidence_types_required": evidence_types,
        "lookback_days_required": lookback_days,
    }
