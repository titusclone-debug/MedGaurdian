"""BMW Sentinel — Bio-Medical Waste tracking and audit readiness."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role
from app.models.database import Hospital, BMWCategory, Staff, UserRole
from app.bmw.repository import BMWRepository
from app.bmw.service import BMWService, BMW_CATEGORY_INFO

router = APIRouter()


class BMWLogCreate(BaseModel):
    hospital_id: str
    category: str  # yellow, red, white, blue, black
    weight_kg: float
    source_department: str
    source_ward: Optional[str] = None
    treatment_method: Optional[str] = None
    treatment_operator: Optional[str] = None
    treatment_machine_id: Optional[str] = None
    treatment_temperature: Optional[float] = None
    treatment_duration_min: Optional[int] = None
    disposal_agency: Optional[str] = None
    disposal_manifest_number: Optional[str] = None
    disposal_vehicle_number: Optional[str] = None


class BMWVerification(BaseModel):
    is_properly_segregated: bool
    is_properly_labeled: bool
    is_properly_stored: bool
    compliance_notes: Optional[str] = None


@router.post("/log")
async def log_bmw_entry(
    entry: BMWLogCreate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER, UserRole.DOCTOR, UserRole.NURSE, UserRole.LAB_TECHNICIAN])),
):
    """Record a bio-medical waste entry with full chain-of-custody tracking."""
    assert_hospital_access(current_user, entry.hospital_id)

    # Validate category
    try:
        category = BMWCategory(entry.category.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid BMW category: {entry.category}. Must be one of: yellow, red, white, blue, black"
        )
    
    return BMWService.log_entry(db, entry, entry.hospital_id, category)


@router.post("/verify/{log_id}")
async def verify_bmw_entry(
    log_id: str,
    verification: BMWVerification,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """Verify a BMW entry — used during audit and spot checks."""
    log = BMWRepository.get_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="BMW log entry not found")
    assert_hospital_access(current_user, log.hospital_id)
    
    return BMWService.verify_entry(db, log, verification)


@router.get("/dashboard/{hospital_id}")
async def get_bmw_dashboard(
    hospital_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """BMW compliance dashboard — waste generation trends and compliance rates."""
    assert_hospital_access(current_user, hospital_id)
    
    return BMWService.get_dashboard(db, hospital_id, days)


@router.get("/audit-report/{hospital_id}")
async def generate_bmw_audit_report(
    hospital_id: str,
    month: int = Query(datetime.utcnow().month),
    year: int = Query(datetime.utcnow().year),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Generate monthly BMW audit report for CPCB/SPCB submission."""
    assert_hospital_access(current_user, hospital_id)
    
    return BMWService.generate_audit_report(db, hospital_id, month, year)
