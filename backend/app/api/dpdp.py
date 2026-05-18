"""DPDP Consent Manager — Patient data protection and consent management."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role
from app.models.database import ConsentRecord, DataBreachLog, Hospital, ConsentStatus, Staff, UserRole
from app.consent.repository import ConsentRepository
from app.consent.service import ConsentService

router = APIRouter()


class ConsentCreate(BaseModel):
    hospital_id: str
    patient_id: str
    patient_name: str
    consent_type: str  # treatment, data_sharing, research, billing
    purpose: str
    data_categories: List[str]
    third_parties: Optional[List[str]] = None
    consent_method: str  # digital_signature, otp, verbal_witness, thumbprint
    is_minor: bool = False
    guardian_consent_id: Optional[str] = None
    language_preference: str = "en"
    expires_in_days: int = 365


class ConsentWithdraw(BaseModel):
    reason: str


class BreachReport(BaseModel):
    hospital_id: str
    breach_type: str
    affected_records_count: int
    data_categories_affected: List[str]
    root_cause: str


@router.post("/grant")
async def grant_consent(
    consent: ConsentCreate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER, UserRole.DOCTOR, UserRole.NURSE])),
):
    """
    Create a Digital Consent Artefact — blockchain-timestamped per DPDP 2026.
    Every patient interaction gets a tamper-proof consent record.
    """
    assert_hospital_access(current_user, consent.hospital_id)

    if consent.expires_in_days <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Consent validity days must be greater than zero: {consent.expires_in_days}"
        )

    return ConsentService.grant_consent(db, consent)


@router.post("/withdraw/{consent_id}")
async def withdraw_consent(
    consent_id: str,
    withdrawal: ConsentWithdraw,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER, UserRole.DOCTOR, UserRole.NURSE])),
):
    """Withdraw previously granted consent. DPDP mandates this must be as easy as granting."""
    consent = ConsentRepository.get_by_id(db, consent_id)
    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found")
    assert_hospital_access(current_user, consent.hospital_id)
    
    if consent.status != ConsentStatus.GRANTED:
        raise HTTPException(status_code=400, detail=f"Cannot withdraw consent in status: {consent.status.value}")
    
    return ConsentService.withdraw_consent(db, consent, withdrawal)


@router.get("/patient/{patient_id}")
async def get_patient_consents(
    patient_id: str,
    hospital_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Get all consent records for a patient — the 'Consent Dashboard'."""
    assert_hospital_access(current_user, hospital_id)

    return ConsentService.get_patient_consents(db, hospital_id, patient_id)


@router.get("/compliance-check/{hospital_id}")
async def check_dpdp_compliance(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """DPDP compliance audit — checks for gaps in consent management."""
    assert_hospital_access(current_user, hospital_id)

    return ConsentService.check_compliance(db, hospital_id)


@router.post("/breach/report")
async def report_data_breach(
    breach: BreachReport,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """
    Report a data breach — DPDP mandates 72-hour notification.
    This endpoint starts the clock.
    """
    assert_hospital_access(current_user, breach.hospital_id)

    if breach.affected_records_count < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Affected records count cannot be negative: {breach.affected_records_count}"
        )

    return ConsentService.report_data_breach(db, breach)


@router.get("/list/{hospital_id}")
async def list_consents(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """List all consent records for the hospital."""
    assert_hospital_access(current_user, hospital_id)
    records = ConsentRepository.get_all_for_hospital(db, hospital_id)
    return {
        "consents": [{
            "id": r.id,
            "patient_id": r.patient_id,
            "type": r.consent_type,
            "purpose": r.purpose,
            "status": r.status.value,
            "granted_at": r.granted_at.strftime("%Y-%m-%d") if r.granted_at else None,
            "expires_at": r.expires_at.strftime("%Y-%m-%d") if r.expires_at else None,
            "is_minor": r.is_minor,
            "guardian_consent_id": r.guardian_consent_id,
            "artefact_hash": r.artefact_hash,
            "withdrawal_reason": r.withdrawal_reason
        } for r in records]
    }

