"""License Tracker — Every license, registration, and accreditation."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role
from app.models.database import License, Hospital, LicenseStatus, Staff, UserRole
from app.compliance.repository import LicenseRepository
from app.compliance.service import LicenseService

router = APIRouter()


class LicenseCreate(BaseModel):
    hospital_id: str
    license_name: str
    license_number: str
    issuing_authority: str
    license_type: str
    issued_date: str
    expiry_date: Optional[str] = None
    renewal_reminder_days: int = 90
    conditions: Optional[List[str]] = None


@router.get("/{hospital_id}")
async def get_licenses(
    hospital_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Get all licenses for a hospital with expiry tracking."""
    assert_hospital_access(current_user, hospital_id)

    license_status = None
    if status:
        try:
            license_status = LicenseStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid license status: {status}. Must be one of: active, expiring_soon, expired, renewal_in_progress, suspended"
            )
            
    return LicenseService.get_licenses(db, hospital_id, license_status)


@router.post("/")
async def create_license(
    license_data: LicenseCreate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """Register a new license or accreditation."""
    assert_hospital_access(current_user, license_data.hospital_id)

    try:
        issued_date = datetime.fromisoformat(license_data.issued_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid issued_date format: '{license_data.issued_date}'. Must be in ISO 8601 format (YYYY-MM-DD)."
        )

    expiry_date = None
    if license_data.expiry_date:
        try:
            expiry_date = datetime.fromisoformat(license_data.expiry_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid expiry_date format: '{license_data.expiry_date}'. Must be in ISO 8601 format (YYYY-MM-DD)."
            )

    return LicenseService.create_license(db, license_data, issued_date, expiry_date)


@router.post("/renewal/{license_id}")
async def file_renewal(
    license_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """Mark a license as renewal-in-progress."""
    lic = LicenseRepository.get_by_id(db, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    assert_hospital_access(current_user, lic.hospital_id)
    
    return LicenseService.file_renewal(db, lic)


@router.get("/renewal-draft/{license_id}")
async def draft_license_renewal(
    license_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER, UserRole.ACCOUNTANT])),
):
    """Auto-draft a license renewal application (Bureaucracy Engine)."""
    lic = LicenseRepository.get_by_id(db, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    assert_hospital_access(current_user, lic.hospital_id)
    
    return LicenseService.draft_license_renewal(db, lic)
