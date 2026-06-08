"""NABH 6th Edition Compliance Tracker."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role
from app.models.database import (
    ComplianceRecord, Hospital, Staff, ComplianceStatus, UserRole,
    RiskAlert, NABHObjective, MaturityLevel, SeverityLevel
)
from app.nabh.repository import ComplianceRepository
from app.nabh.service import ComplianceService, NABH_STANDARDS, LEGACY_NABH_MODEL_NOTICE
from app.nabh.agent import InspectorAgent, ConsultantAgent, simulate_tracer_audit

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


@router.get("/agent/spot-check/{hospital_id}")
async def get_random_spot_checks(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Get randomized spot-check logs selected by the Inspector Agent.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)
    inspector = InspectorAgent()
    checks = inspector.select_random_spot_check_selector(db, hospital_id)
    if not checks:
        raise HTTPException(status_code=404, detail="No active logs found for spot check selection.")
    return checks


@router.get("/agent/sop/{hospital_id}/{standard_code}")
async def get_sop_template(
    hospital_id: str,
    standard_code: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Get dynamic, customized SOP template drafted by the Consultant Agent.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)
    consultant = ConsultantAgent()
    sop = consultant.generate_sop_template(db, hospital_id, standard_code)
    if "error" in sop:
        raise HTTPException(status_code=400, detail=sop["error"])
    return sop


@router.get("/agent/tracer/{hospital_id}/{patient_id}")
async def get_tracer_audit(
    hospital_id: str,
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Run a simulated patient tracer audit to map compliance end-to-end.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)
    return simulate_tracer_audit(db, hospital_id, patient_id)


@router.get("/agent/export-binder/{hospital_id}")
async def export_binder(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Generates and downloads the surveyor binder ZIP file containing all evidence.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)
    
    from app.nabh.binder_exporter import generate_surveyor_binder
    from fastapi.responses import StreamingResponse
    
    try:
        zip_io = generate_surveyor_binder(db, hospital_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate surveyor binder: {str(e)}")
        
    return StreamingResponse(
        zip_io,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=Surveyor_Binder_{hospital_id}.zip"}
    )


# ============================================================
# AGENTIC ENDPOINTS — Phase 3: Service as a Software
# ============================================================

@router.post("/agent/assess/{hospital_id}")
async def trigger_agent_assessment(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Inspector Agent: Full autonomous audit of all 33 NABH standards.
    Scans databases, cross-validates telemetry metrics, updates maturity levels,
    and auto-creates CAPA remediation tasks for every gap found.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)

    # Verify objectives exist; if not, seed them first
    obj_count = db.query(NABHObjective).filter(
        NABHObjective.hospital_id == hospital_id
    ).count()
    if obj_count == 0:
        from app.nabh.seeder import seed_nabh_objectives
        seed_nabh_objectives(db, hospital_id)

    # Run the Inspector Agent's full assessment
    inspector = InspectorAgent()
    gap_report = inspector.assess_current_state(db, hospital_id)

    # Auto-create CAPA tasks via the Consultant Agent
    consultant = ConsultantAgent()
    capa_result = consultant.generate_remediation_action_plan(db, hospital_id, gap_report)

    return {
        "assessment": gap_report,
        "remediation": capa_result,
        "agent": "Inspector + Consultant Dual-Agent Pipeline",
        "triggered_by": current_user.name
    }


@router.post("/agent/generate-roadmap/{hospital_id}")
async def generate_roadmap(
    hospital_id: str,
    target_months: int = 16,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Consultant Agent: Generate a customized 16-month phased accreditation roadmap.
    Buckets gaps by severity: CRITICAL (M1-4), MAJOR (M5-8), MINOR (M9-12), Pre-Survey (M13-16).
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)

    if target_months < 6 or target_months > 36:
        raise HTTPException(
            status_code=400,
            detail="Target months must be between 6 and 36."
        )

    consultant = ConsultantAgent()
    return consultant.generate_roadmap(db, hospital_id, target_months)


@router.get("/agent/activity-feed/{hospital_id}")
async def get_activity_feed(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Live Agent Activity Feed: Returns the last 20 agent-generated events.
    Powers the real-time activity timeline in the NABH dashboard showing
    Inspector and Consultant agent actions.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)

    events = db.query(RiskAlert).filter(
        RiskAlert.hospital_id == hospital_id,
        RiskAlert.alert_type == "nabh"
    ).order_by(RiskAlert.created_at.desc()).limit(20).all()

    # Also pull the last assessment timestamp from objectives
    last_assessed_obj = db.query(NABHObjective).filter(
        NABHObjective.hospital_id == hospital_id,
        NABHObjective.last_assessed.isnot(None)
    ).order_by(NABHObjective.last_assessed.desc()).first()

    return {
        "last_assessment": last_assessed_obj.last_assessed.isoformat() if last_assessed_obj and last_assessed_obj.last_assessed else None,
        "assessed_by": last_assessed_obj.assessed_by if last_assessed_obj else None,
        "feed_count": len(events),
        "feed": [{
            "id": e.id,
            "agent": "Consultant Agent" if "Gap" in (e.title or "") else "Inspector Agent",
            "action": e.description or e.title,
            "standard_code": (e.title or "").replace("NABH Gap: ", ""),
            "severity": e.severity.value if e.severity else "medium",
            "timestamp": e.created_at.isoformat() if e.created_at else None,
            "status": "resolved" if e.is_resolved else "active",
            "recommended_action": e.recommended_action
        } for e in events]
    }


@router.get("/agent/daily-brief/{hospital_id}")
async def get_daily_brief(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Daily Compliance Brief: Returns the top 3 priority actions for today.
    Sorted by severity (CRITICAL first) then lowest maturity level.
    Powers the 'Today's 3 Actions' panel — the admin's daily checklist.
    
    WARNING: LEGACY ENDPOINT
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    assert_hospital_access(current_user, hospital_id)

    # Get all objectives for this hospital
    all_objs = db.query(NABHObjective).filter(
        NABHObjective.hospital_id == hospital_id
    ).all()

    # Filter in Python to avoid SQLite enum string comparison issues
    gaps = [g for g in all_objs if g.maturity_level is not None and g.maturity_level.value < MaturityLevel.IMPLEMENTED.value]

    # Sort: critical first, then by lowest maturity
    severity_order = {SeverityLevel.CRITICAL: 0, SeverityLevel.MAJOR: 1, SeverityLevel.MINOR: 2}
    sorted_gaps = sorted(gaps, key=lambda g: (
        severity_order.get(g.severity, 3),
        g.maturity_level.value
    ))[:3]

    # Get overall stats for context
    total = len(all_objs)
    implemented = sum(1 for g in all_objs if g.maturity_level is not None and g.maturity_level.value >= MaturityLevel.IMPLEMENTED.value)

    return {
        "total_standards": total,
        "implemented_count": implemented,
        "gaps_remaining": total - implemented,
        "readiness_pct": round(implemented / max(1, total) * 100, 1),
        "daily_actions": [{
            "priority": i + 1,
            "standard_code": g.standard_code,
            "standard_name": g.standard_name,
            "chapter_code": g.chapter_code,
            "severity": g.severity.value,
            "maturity_level": g.maturity_level.value,
            "maturity_label": g.maturity_level.name.replace("_", " ").title(),
            "task": g.remediation_plan or f"Begin compliance evidence collection for {g.standard_code}: {g.standard_name}",
            "deadline": g.remediation_deadline.isoformat() if g.remediation_deadline else None
        } for i, g in enumerate(sorted_gaps)]
    }

