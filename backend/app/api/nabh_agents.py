"""NABH 6th Edition Legacy Agent Routes (Quarantined)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user
from app.models.database import Staff

router = APIRouter()

QUARANTINE_MESSAGE = "Agent capabilities are temporarily disabled while MedGuardian transitions to the canonical 6th Edition Graph. Expected in Phase 4."

@router.get("/spot-check/{hospital_id}")
async def get_random_spot_checks(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Get randomized spot-check logs selected by the Inspector Agent."""
    assert_hospital_access(current_user, hospital_id)
    raise HTTPException(status_code=501, detail=QUARANTINE_MESSAGE)

@router.get("/sop/{hospital_id}/{standard_code}")
async def get_sop_template(
    hospital_id: str,
    standard_code: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Get dynamic, customized SOP template drafted by the Consultant Agent."""
    assert_hospital_access(current_user, hospital_id)
    raise HTTPException(status_code=501, detail=QUARANTINE_MESSAGE)

@router.get("/tracer/{hospital_id}/{patient_id}")
async def get_tracer_audit(
    hospital_id: str,
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Run a simulated patient tracer audit to map compliance end-to-end."""
    assert_hospital_access(current_user, hospital_id)
    raise HTTPException(status_code=501, detail=QUARANTINE_MESSAGE)

@router.get("/export-binder/{hospital_id}")
async def export_binder(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Generates and downloads the surveyor binder ZIP file containing all evidence."""
    assert_hospital_access(current_user, hospital_id)
    raise HTTPException(status_code=501, detail=QUARANTINE_MESSAGE)

@router.post("/assess/{hospital_id}")
async def trigger_agent_assessment(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Inspector Agent: Full autonomous audit of all 33 NABH standards."""
    assert_hospital_access(current_user, hospital_id)
    raise HTTPException(status_code=501, detail=QUARANTINE_MESSAGE)

@router.post("/generate-roadmap/{hospital_id}")
async def generate_roadmap(
    hospital_id: str,
    target_months: int = 16,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Consultant Agent: Generate a customized 16-month phased accreditation roadmap."""
    assert_hospital_access(current_user, hospital_id)
    raise HTTPException(status_code=501, detail=QUARANTINE_MESSAGE)

@router.get("/activity-feed/{hospital_id}")
async def get_activity_feed(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Live Agent Activity Feed: Returns the last 20 agent-generated events."""
    assert_hospital_access(current_user, hospital_id)
    raise HTTPException(status_code=501, detail=QUARANTINE_MESSAGE)

@router.get("/daily-brief/{hospital_id}")
async def get_daily_brief(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Daily Compliance Brief: Returns the top 3 priority actions for today."""
    assert_hospital_access(current_user, hospital_id)
    raise HTTPException(status_code=501, detail=QUARANTINE_MESSAGE)
