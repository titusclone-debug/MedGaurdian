"""Bulk hospital evidence-plan route."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import assert_hospital_access, get_current_user
from app.core.database import get_db
from app.models.database import Staff
from app.nabh.evidence_plan import build_hospital_evidence_plan
from app.schemas.nabh import NABHEvidencePlanResponse

router = APIRouter()


@router.get("/requirements/{hospital_id}/evidence-plan", response_model=NABHEvidencePlanResponse)
async def get_hospital_evidence_plan(
    hospital_id: str,
    edition_version: str = Query("6.0"),
    limit: int = Query(100, ge=1, le=250),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Return a paged bulk evidence plan for hospital-scoped requirements."""
    assert_hospital_access(current_user, hospital_id)
    return build_hospital_evidence_plan(
        db=db,
        hospital_id=hospital_id,
        edition_version=edition_version,
        limit=limit,
        offset=offset,
    )
