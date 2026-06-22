"""Deterministic source-cited requirement explanation route."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import assert_hospital_access, get_current_user
from app.core.database import get_db
from app.models.database import Staff
from app.nabh.explanation import build_requirement_explanation
from app.schemas.nabh import NABHRequirementExplanationResponse

router = APIRouter()


@router.get(
    "/ontology/requirements/{requirement_id}/explanation",
    response_model=NABHRequirementExplanationResponse,
)
async def get_requirement_explanation(
    requirement_id: str,
    hospital_id: Optional[str] = Query(None),
    edition_version: str = Query("6.0"),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Return deterministic, source-cited guidance for one requirement."""
    if hospital_id:
        assert_hospital_access(current_user, hospital_id)

    return build_requirement_explanation(
        db=db,
        requirement_id=requirement_id,
        hospital_id=hospital_id,
        edition_version=edition_version,
    )
