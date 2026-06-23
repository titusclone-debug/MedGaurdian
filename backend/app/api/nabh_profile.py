"""NABH 6th Edition Hospital Profile Routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role, Staff
from app.models.database import Hospital, UserRole
from app.nabh.applicability import ApplicabilityEngine
from app.schemas.nabh import (
    HospitalProfileResponse, HospitalProfileUpdate, ApplicabilityComputeResponse
)

router = APIRouter()

@router.get("/{hospital_id}", response_model=HospitalProfileResponse)
async def get_hospital_profile(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Retrieve hospital accreditation profile, returning a default draft shape if it does not exist in DB."""
    assert_hospital_access(current_user, hospital_id)
    
    # Verify hospital exists
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    from app.models.database import HospitalAccreditationProfile, ProfileStatus
    
    profile = db.query(HospitalAccreditationProfile).filter(
        HospitalAccreditationProfile.hospital_id == hospital_id,
        HospitalAccreditationProfile.retired_at.is_(None)
    ).first()
    
    if not profile:
        return HospitalProfileResponse(
            hospital_id=hospital_id,
            bed_count=0,
            profile_status=ProfileStatus.DRAFT,
            exists=False
        )
        
    services_offered = profile.services_offered or []
    specialty_services = profile.specialty_services or []
    scope_exclusions = profile.scope_exclusions or []
    
    return HospitalProfileResponse(
        id=profile.id,
        hospital_id=profile.hospital_id,
        bed_count=profile.bed_count,
        hospital_type=profile.hospital_type,
        profile_status=profile.profile_status,
        services_offered=services_offered,
        specialty_services=specialty_services,
        has_icu=profile.has_icu,
        has_operation_theatre=profile.has_operation_theatre,
        has_emergency=profile.has_emergency,
        has_pharmacy=profile.has_pharmacy,
        has_lab=profile.has_lab,
        has_blood_bank=profile.has_blood_bank,
        has_ambulance=profile.has_ambulance,
        has_maternity=profile.has_maternity,
        has_dialysis=profile.has_dialysis,
        has_imaging=profile.has_imaging,
        has_cssd=profile.has_cssd,
        scope_exclusions=scope_exclusions,
        annual_patient_volume=profile.annual_patient_volume,
        avg_monthly_opd=profile.avg_monthly_opd,
        last_scoped_at=profile.last_scoped_at,
        exists=True
    )


@router.put("/{hospital_id}", response_model=HospitalProfileResponse)
async def create_or_update_hospital_profile(
    hospital_id: str,
    update: HospitalProfileUpdate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER]))
):
    """Create or update a hospital accreditation profile."""
    assert_hospital_access(current_user, hospital_id)
    
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    from app.models.database import HospitalAccreditationProfile, ProfileStatus
    
    profile = db.query(HospitalAccreditationProfile).filter(
        HospitalAccreditationProfile.hospital_id == hospital_id,
        HospitalAccreditationProfile.retired_at.is_(None)
    ).first()
    
    if not profile:
        profile = HospitalAccreditationProfile(
            hospital_id=hospital_id,
            profile_status=ProfileStatus.DRAFT
        )
        db.add(profile)
        
    update_data = update.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(profile, key, val)
        
    db.commit()
    db.refresh(profile)
    
    services_offered = profile.services_offered or []
    specialty_services = profile.specialty_services or []
    scope_exclusions = profile.scope_exclusions or []
    
    return HospitalProfileResponse(
        id=profile.id,
        hospital_id=profile.hospital_id,
        bed_count=profile.bed_count,
        hospital_type=profile.hospital_type,
        profile_status=profile.profile_status,
        services_offered=services_offered,
        specialty_services=specialty_services,
        has_icu=profile.has_icu,
        has_operation_theatre=profile.has_operation_theatre,
        has_emergency=profile.has_emergency,
        has_pharmacy=profile.has_pharmacy,
        has_lab=profile.has_lab,
        has_blood_bank=profile.has_blood_bank,
        has_ambulance=profile.has_ambulance,
        has_maternity=profile.has_maternity,
        has_dialysis=profile.has_dialysis,
        has_imaging=profile.has_imaging,
        has_cssd=profile.has_cssd,
        scope_exclusions=scope_exclusions,
        annual_patient_volume=profile.annual_patient_volume,
        avg_monthly_opd=profile.avg_monthly_opd,
        last_scoped_at=profile.last_scoped_at,
        exists=True
    )


@router.post("/{hospital_id}/compute-applicability", response_model=ApplicabilityComputeResponse)
async def compute_hospital_applicability(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER]))
):
    """Computes/updates the hospital requirement scope based on its profile."""
    assert_hospital_access(current_user, hospital_id)
    
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    from app.models.database import HospitalAccreditationProfile
    
    profile = db.query(HospitalAccreditationProfile).filter(
        HospitalAccreditationProfile.hospital_id == hospital_id,
        HospitalAccreditationProfile.retired_at.is_(None)
    ).first()
    
    res = ApplicabilityEngine.compute_applicability(db, hospital_id)
    db.commit()
    
    warnings = []
    if not profile:
        warnings.append("Hospital accreditation profile is missing.")
        
    return ApplicabilityComputeResponse(
        total_requirements_evaluated=res["total_requirements_evaluated"],
        status_counts=res["status_counts"],
        created_rows_count=res["created_rows_count"],
        updated_rows_count=res["updated_rows_count"],
        unchanged_rows_count=res["unchanged_rows_count"],
        warnings=warnings
    )
