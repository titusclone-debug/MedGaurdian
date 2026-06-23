"""NABH 6th Edition Compliance Tracker."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role
from app.api.nabh_helpers import (
    assert_staff_belongs_to_hospital,
    build_evidence_burden_summary,
)
from app.api import nabh_evidence, nabh_explanation, nabh_operations, nabh_ontology, nabh_profile, nabh_requirements, nabh_agents
from app.models.database import (
    ComplianceRecord, Hospital, Staff, ComplianceStatus, UserRole,
    RiskAlert, NABHObjective, MaturityLevel, SeverityLevel,
    NABHEdition, NABHChapter, NABHStandard, NABHRequirement,
    NABHRequirementCitation, NABHSourceDocument, NABHSourceAnomaly,
    NABHApplicabilityRule, NABHEvidenceRequirement,
    HospitalNABHRequirement, HospitalRequirementEvidenceLink,
    EvidenceStatus, ApplicabilityDefault, KnowledgePublicationStatus,
)
from app.nabh.repository import ComplianceRepository
from app.nabh.service import ComplianceService, NABH_STANDARDS, LEGACY_NABH_MODEL_NOTICE
from app.nabh.agent import InspectorAgent, ConsultantAgent, simulate_tracer_audit
from app.nabh.citation_service import CitationService
from app.nabh.applicability import ApplicabilityEngine
from app.nabh.canonical import ensure_canonical_compatibility
from app.nabh.quality import NABHQualityError, assert_compliant_status_allowed

from app.schemas.nabh import (
    NABHEditionSummary, NABHChapterSummary, NABHSourceDocumentSummary,
    NABHSourceAnomalySchema, NABHRequirementSummary, PaginatedRequirementSummary,
    NABHRuleSchema, NABHEvidenceRequirementSchema, NABHCitationSchema, NABHRequirementDetail,
    CitationResponse, HospitalProfileResponse, HospitalProfileUpdate, ApplicabilityComputeResponse,
    HospitalRequirementSummary as SchemaHospitalRequirementSummary,
    PaginatedHospitalRequirementSummary, HospitalRequirementDetail as SchemaHospitalRequirementDetail,
    HospitalRequirementPatch, HospitalRequirementEvidenceLinkSchema
)

router = APIRouter()



class ComplianceUpdate(BaseModel):
    standard_code: str
    status: str  # compliant, non_compliant, partially_compliant, under_review
    current_score: float = 0.0
    evidence_description: Optional[str] = None
    remediation_plan: Optional[str] = None
    remediation_deadline: Optional[str] = None


@router.get("/standards")
async def get_nabh_standards():
    """
    Get the complete NABH 6th Edition standards reference.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    return {
        "edition": "6th",
        "effective_date": "2025-01-01",
        "total_chapters": sum(len(s["chapters"]) for s in NABH_STANDARDS.values()),
        "standards": NABH_STANDARDS
    }


@router.get("/compliance/{hospital_id}")
async def get_compliance_status(
    hospital_id: str,
    chapter: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Get NABH compliance status with optional filters.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)

    compliance_status = None
    if status:
        try:
            compliance_status = ComplianceStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid compliance status: '{status}'. Must be one of: compliant, non_compliant, partially_compliant, under_review, not_applicable"
            )
            
    return ComplianceService.get_compliance_status(db, hospital_id, chapter, compliance_status)


@router.post("/update/{hospital_id}")
async def update_compliance(
    hospital_id: str,
    update: ComplianceUpdate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """
    Update compliance status for a specific NABH standard.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)

    try:
        compliance_status = ComplianceStatus(update.status.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid compliance status: '{update.status}'. Must be one of: compliant, non_compliant, partially_compliant, under_review, not_applicable"
        )

    remediation_deadline = None
    if update.remediation_deadline:
        try:
            remediation_deadline = datetime.fromisoformat(update.remediation_deadline)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid remediation_deadline format: '{update.remediation_deadline}'. Must be in ISO 8601 format (YYYY-MM-DD)."
            )

    return ComplianceService.update_compliance(db, hospital_id, update, compliance_status, remediation_deadline)


@router.get("/gap-analysis/{hospital_id}")
async def get_gap_analysis(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Gap analysis — identifies what's missing for NABH accreditation.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)
    return ComplianceService.get_gap_analysis(db, hospital_id)












