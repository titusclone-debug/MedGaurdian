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
    RiskAlert, NABHObjective, MaturityLevel, SeverityLevel,
    NABHEdition, NABHChapter, NABHStandard, NABHObjectiveElement,
    NABHMeasurableElement, NABHRequirementCitation, NABHSourceDocument,
    EvidenceStatus, ApplicabilityDefault
)
from app.nabh.repository import ComplianceRepository
from app.nabh.service import ComplianceService, NABH_STANDARDS, LEGACY_NABH_MODEL_NOTICE
from app.nabh.agent import InspectorAgent, ConsultantAgent, simulate_tracer_audit
from app.nabh.citation_service import CitationService
from app.nabh.applicability import ApplicabilityEngine
from app.nabh.readiness import calculate_hospital_readiness

from app.schemas.nabh import (
    NABHEditionSummary, NABHChapterSummary, NABHRequirementSummary, PaginatedRequirementSummary,
    NABHRuleSchema, NABHEvidenceRequirementSchema, NABHCitationSchema, NABHRequirementDetail,
    CitationResponse, HospitalProfileResponse, HospitalProfileUpdate, ApplicabilityComputeResponse,
    HospitalRequirementSummary as SchemaHospitalRequirementSummary,
    PaginatedHospitalRequirementSummary, HospitalRequirementDetail as SchemaHospitalRequirementDetail,
    HospitalRequirementPatch, HospitalRequirementEvidenceLinkSchema, HospitalReadinessResponse
)

router = APIRouter()


def _assert_staff_belongs_to_hospital(db: Session, staff_id: Optional[str], hospital_id: str, field_name: str) -> None:
    """Validate staff references used on hospital-scoped requirement state."""
    if staff_id is None:
        return

    staff = db.query(Staff).filter(
        Staff.id == staff_id,
        Staff.is_active == True
    ).first()
    if not staff or staff.hospital_id != hospital_id:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must reference an active staff member in the same hospital."
        )


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


@router.get("/ontology/coverage")
async def get_ontology_coverage(db: Session = Depends(get_db)):
    """
    Get the official reference ontology coverage statistics for NABH 6th Edition.
    """
    import os
    import json
    
    # 1. Read citation complete status from nabh_6th_citations.json
    api_dir = os.path.dirname(os.path.abspath(__file__))
    citations_path = os.path.abspath(os.path.join(api_dir, "..", "nabh", "data", "nabh_6th_citations.json"))
    
    citation_complete = False
    if os.path.exists(citations_path):
        try:
            with open(citations_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                if isinstance(raw_data, dict):
                    citation_complete = raw_data.get("_meta", {}).get("citation_complete", False)
        except Exception:
            pass

    # 2. Get the active edition (6.0)
    edition = db.query(NABHEdition).filter(NABHEdition.version == "6.0").first()
    if not edition:
        return {
            "ontology_status": "partial_seed",
            "official_declared_total_standards": 100,
            "official_declared_total_elements": 639,
            "official_chapter_sum_standards": 100,
            "official_chapter_sum_elements": 638,
            "official_chapter_objective_elements_sum": 638,
            "official_category_breakdown_sum": 639,
            "official_standards_discrepancy": 0,
            "official_elements_discrepancy": 1,
            "has_source_inconsistency": True,
            "inconsistencies": [
                {
                    "chapter_code": "COP",
                    "objective_elements_count": 135,
                    "category_breakdown_sum": 136,
                    "difference": 1,
                    "note": "Official summary table appears internally inconsistent. COP objective elements count is listed as 135, but its category breakdown sum is 136."
                }
            ],
            "seeded_total_standards": 0,
            "seeded_total_elements": 0,
            "global_standards_coverage_percent": 0.0,
            "global_elements_coverage_percent": 0.0,
            "citation_complete": citation_complete,
            "chapters": []
        }

    # 3. Query all official 6th edition chapters from nabh_chapters
    # Exclude HIC from calculations if it exists, matching only the official 10 canonical codes
    official_chapter_codes = ["AAC", "COP", "MOM", "PRE", "IPC", "PSQ", "ROM", "FMS", "HRM", "IMS"]
    
    chapters = db.query(NABHChapter).filter(
        NABHChapter.edition_id == edition.id,
        NABHChapter.canonical_code.in_(official_chapter_codes)
    ).order_by(NABHChapter.display_order).all()

    chapter_stats = []
    total_seeded_standards = 0
    total_seeded_elements = 0
    
    for chap in chapters:
        # Seeded standards count for this chapter
        seeded_standards_count = db.query(NABHStandard).filter(
            NABHStandard.chapter_id == chap.id
        ).count()
        
        # Seeded measurable elements (represented as objective elements) count for this chapter
        seeded_elements = db.query(NABHMeasurableElement).join(NABHObjectiveElement).join(NABHStandard).filter(
            NABHStandard.chapter_id == chap.id
        ).all()
        seeded_elements_count = len(seeded_elements)
        seeded_element_ids = [el.id for el in seeded_elements]

        # Citation count for seeded elements in this chapter
        citation_count = 0
        if seeded_element_ids:
            citation_count = db.query(NABHRequirementCitation).filter(
                NABHRequirementCitation.measurable_element_id.in_(seeded_element_ids),
                NABHRequirementCitation.retired_at.is_(None)
            ).count()
            
        # Uncited seeded elements count
        uncited_count = 0
        for el in seeded_elements:
            has_citation = db.query(NABHRequirementCitation).filter(
                NABHRequirementCitation.measurable_element_id == el.id,
                NABHRequirementCitation.retired_at.is_(None)
            ).first() is not None
            if not has_citation:
                uncited_count += 1
                
        # Coverage percentages
        std_pct = round((seeded_standards_count / chap.official_standards_count) * 100, 1) if chap.official_standards_count else 0.0
        meas_pct = round((seeded_elements_count / chap.official_measurable_elements_count) * 100, 1) if chap.official_measurable_elements_count else 0.0

        chapter_stats.append({
            "chapter_code": chap.canonical_code,
            "title": chap.title,
            "official_standards_count": chap.official_standards_count,
            "official_objective_elements_count": chap.official_measurable_elements_count,
            "core_count": chap.core_count,
            "commitment_count": chap.commitment_count,
            "achievement_count": chap.achievement_count,
            "excellence_count": chap.excellence_count,
            "seeded_standards_count": seeded_standards_count,
            "seeded_objective_elements_count": seeded_elements_count,
            "standards_coverage_percent": std_pct,
            "elements_coverage_percent": meas_pct,
            "citation_count": citation_count,
            "uncited_seeded_elements_count": uncited_count,
            "is_fully_seeded": chap.is_fully_seeded
        })
        
        total_seeded_standards += seeded_standards_count
        total_seeded_elements += seeded_elements_count

    # Global calculations
    global_std_pct = round((total_seeded_standards / 100) * 100, 1)
    global_elem_pct = round((total_seeded_elements / 639) * 100, 1)

    official_chapter_sum_standards = sum(chap.official_standards_count for chap in chapters)
    official_chapter_sum_elements = sum(chap.official_measurable_elements_count for chap in chapters)

    official_category_breakdown_sum = sum(
        (c.core_count or 0) + (c.commitment_count or 0) + (c.achievement_count or 0) + (c.excellence_count or 0)
        for c in chapters
    )

    inconsistencies = []
    for chap in chapters:
        cat_sum = (chap.core_count or 0) + (chap.commitment_count or 0) + (chap.achievement_count or 0) + (chap.excellence_count or 0)
        if chap.official_measurable_elements_count is not None and cat_sum > 0 and chap.official_measurable_elements_count != cat_sum:
            diff = cat_sum - chap.official_measurable_elements_count
            inconsistencies.append({
                "chapter_code": chap.canonical_code,
                "objective_elements_count": chap.official_measurable_elements_count,
                "category_breakdown_sum": cat_sum,
                "difference": abs(diff),
                "note": f"Official summary table appears internally inconsistent. {chap.canonical_code} objective elements count is listed as {chap.official_measurable_elements_count}, but its category breakdown sum is {cat_sum}."
            })
    has_source_inconsistency = len(inconsistencies) > 0

    return {
        "ontology_status": "partial_seed",
        "official_declared_total_standards": 100,
        "official_declared_total_elements": 639,
        "official_chapter_sum_standards": official_chapter_sum_standards,
        "official_chapter_sum_elements": official_chapter_sum_elements,
        "official_chapter_objective_elements_sum": official_chapter_sum_elements,
        "official_category_breakdown_sum": official_category_breakdown_sum,
        "official_standards_discrepancy": 100 - official_chapter_sum_standards,
        "official_elements_discrepancy": 639 - official_chapter_sum_elements,
        "has_source_inconsistency": has_source_inconsistency,
        "inconsistencies": inconsistencies,
        "seeded_total_standards": total_seeded_standards,
        "seeded_total_elements": total_seeded_elements,
        "global_standards_coverage_percent": global_std_pct,
        "global_elements_coverage_percent": global_elem_pct,
        "citation_complete": citation_complete,
        "chapters": chapter_stats
    }


# ============================================================
# NEW NABH ONTOLOGY & COMPLIANCE APIs (Tasks 10-12)
# ============================================================

@router.get("/ontology/editions", response_model=List[NABHEditionSummary])
async def get_ontology_editions(
    include_retired: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get the list of all standard editions, optionally including retired ones."""
    query = db.query(NABHEdition)
    if not include_retired:
        query = query.filter(NABHEdition.retired_at.is_(None))
    return query.all()


@router.get("/ontology/chapters", response_model=List[NABHChapterSummary])
async def get_ontology_chapters(
    edition_version: str = Query("6.0"),
    include_retired: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get the list of all chapters for a given edition version, optionally including retired ones."""
    edition = db.query(NABHEdition).filter(
        NABHEdition.version == edition_version,
        NABHEdition.retired_at.is_(None)
    ).first()
    if not edition:
        raise HTTPException(status_code=404, detail=f"Edition '{edition_version}' not found")
        
    query = db.query(NABHChapter).filter(NABHChapter.edition_id == edition.id)
    if not include_retired:
        query = query.filter(NABHChapter.retired_at.is_(None))
    return query.order_by(NABHChapter.display_order).all()


@router.get("/ontology/requirements", response_model=PaginatedRequirementSummary)
async def get_ontology_requirements(
    edition_version: str = Query("6.0"),
    chapter_code: Optional[str] = Query(None),
    standard_code: Optional[str] = Query(None),
    include_retired: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get a paginated, filtered list of all requirements (measurable elements) with hierarchy context."""
    query = db.query(
        NABHMeasurableElement, NABHChapter, NABHStandard, NABHObjectiveElement
    ).join(
        NABHObjectiveElement, NABHMeasurableElement.objective_element_id == NABHObjectiveElement.id
    ).join(
        NABHStandard, NABHObjectiveElement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).join(
        NABHEdition, NABHChapter.edition_id == NABHEdition.id
    ).filter(
        NABHEdition.version == edition_version
    )
    
    if not include_retired:
        query = query.filter(
            NABHMeasurableElement.retired_at.is_(None),
            NABHObjectiveElement.retired_at.is_(None),
            NABHStandard.retired_at.is_(None),
            NABHChapter.retired_at.is_(None)
        )
        
    if chapter_code:
        query = query.filter(NABHChapter.canonical_code == chapter_code)
    if standard_code:
        query = query.filter(NABHStandard.canonical_code == standard_code)
        
    total = query.count()
    results = query.order_by(
        NABHChapter.display_order,
        NABHStandard.display_order,
        NABHObjectiveElement.display_order,
        NABHMeasurableElement.display_order
    ).offset(offset).limit(limit).all()
    
    items = [
        NABHRequirementSummary(
            id=el.id,
            code=el.code,
            canonical_code=el.canonical_code,
            description=el.description,
            applicability_default=el.applicability_default,
            chapter_code=chap.canonical_code,
            chapter_title=chap.title,
            standard_code=std.canonical_code,
            standard_title=std.title,
            objective_element_code=obj.canonical_code
        )
        for el, chap, std, obj in results
    ]
    
    return PaginatedRequirementSummary(
        total=total,
        limit=limit,
        offset=offset,
        items=items
    )


@router.get("/ontology/requirements/{requirement_id}", response_model=NABHRequirementDetail)
async def get_ontology_requirement_detail(
    requirement_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get full details of a specific ontology requirement, including rules, evidence, and citations."""
    result = db.query(
        NABHMeasurableElement, NABHChapter, NABHStandard, NABHObjectiveElement
    ).join(
        NABHObjectiveElement, NABHMeasurableElement.objective_element_id == NABHObjectiveElement.id
    ).join(
        NABHStandard, NABHObjectiveElement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        NABHMeasurableElement.id == requirement_id,
        NABHMeasurableElement.retired_at.is_(None),
        NABHObjectiveElement.retired_at.is_(None),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None)
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Requirement not found")
        
    el, chap, std, obj = result
    
    from app.models.database import NABHApplicabilityRule, NABHEvidenceRequirement, NABHRequirementCitation
    
    rules = db.query(NABHApplicabilityRule).filter(
        NABHApplicabilityRule.measurable_element_id == el.id,
        NABHApplicabilityRule.retired_at.is_(None)
    ).all()
    
    evidences = db.query(NABHEvidenceRequirement).filter(
        NABHEvidenceRequirement.measurable_element_id == el.id,
        NABHEvidenceRequirement.retired_at.is_(None)
    ).all()
    
    citations = db.query(NABHRequirementCitation).filter(
        NABHRequirementCitation.measurable_element_id == el.id,
        NABHRequirementCitation.retired_at.is_(None)
    ).all()
    
    return NABHRequirementDetail(
        id=el.id,
        code=el.code,
        canonical_code=el.canonical_code,
        description=el.description,
        applicability_default=el.applicability_default,
        chapter_code=chap.canonical_code,
        chapter_title=chap.title,
        standard_code=std.canonical_code,
        standard_title=std.title,
        objective_element_code=obj.canonical_code,
        objective_element_description=obj.description,
        applicability_rules=[NABHRuleSchema.model_validate(r) for r in rules],
        evidence_requirements=[NABHEvidenceRequirementSchema.model_validate(ev) for ev in evidences],
        citations=[NABHCitationSchema.model_validate(c) for c in citations],
        has_citation=len(citations) > 0,
        has_evidence_requirements=len(evidences) > 0
    )


@router.get("/ontology/citations/{citation_id}", response_model=CitationResponse)
async def get_ontology_citation(
    citation_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Retrieve detailed citation information by ID."""
    citation = CitationService.get_citation_by_id(db, citation_id)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found")
    return citation


@router.get("/profile/{hospital_id}", response_model=HospitalProfileResponse)
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


@router.put("/profile/{hospital_id}", response_model=HospitalProfileResponse)
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


@router.post("/profile/{hospital_id}/compute-applicability", response_model=ApplicabilityComputeResponse)
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


@router.get("/requirements/{hospital_id}", response_model=PaginatedHospitalRequirementSummary)
async def get_hospital_requirements(
    hospital_id: str,
    chapter_code: Optional[str] = Query(None),
    applicability_status: Optional[ApplicabilityDefault] = Query(None),
    evidence_status: Optional[EvidenceStatus] = Query(None),
    readiness_status: Optional[ComplianceStatus] = Query(None),
    owner_id: Optional[str] = Query(None),
    include_retired: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Retrieve paginated, filtered hospital requirement progress states with ontology reference information."""
    assert_hospital_access(current_user, hospital_id)
    
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    from app.models.database import HospitalNABHRequirement
    
    query = db.query(
        HospitalNABHRequirement, NABHMeasurableElement, NABHChapter, NABHStandard, NABHObjectiveElement
    ).join(
        NABHMeasurableElement, HospitalNABHRequirement.requirement_id == NABHMeasurableElement.id
    ).join(
        NABHObjectiveElement, NABHMeasurableElement.objective_element_id == NABHObjectiveElement.id
    ).join(
        NABHStandard, NABHObjectiveElement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        HospitalNABHRequirement.hospital_id == hospital_id
    )
    
    if not include_retired:
        query = query.filter(
            HospitalNABHRequirement.retired_at.is_(None),
            NABHMeasurableElement.retired_at.is_(None),
            NABHObjectiveElement.retired_at.is_(None),
            NABHStandard.retired_at.is_(None),
            NABHChapter.retired_at.is_(None)
        )
        
    if chapter_code:
        query = query.filter(NABHChapter.canonical_code == chapter_code)
    if applicability_status:
        query = query.filter(HospitalNABHRequirement.applicability_status == applicability_status)
    if evidence_status:
        query = query.filter(HospitalNABHRequirement.evidence_status == evidence_status)
    if readiness_status:
        query = query.filter(HospitalNABHRequirement.readiness_status == readiness_status)
    if owner_id:
        query = query.filter(HospitalNABHRequirement.owner_id == owner_id)
        
    total = query.count()
    results = query.order_by(
        NABHChapter.display_order,
        NABHStandard.display_order,
        NABHObjectiveElement.display_order,
        NABHMeasurableElement.display_order
    ).offset(offset).limit(limit).all()
    
    items = [
        SchemaHospitalRequirementSummary(
            id=req.id,
            hospital_id=req.hospital_id,
            requirement_id=req.requirement_id,
            applicability_status=req.applicability_status,
            applicability_reason=req.applicability_reason,
            maturity_level=req.maturity_level,
            evidence_status=req.evidence_status,
            owner_id=req.owner_id,
            due_date=req.due_date,
            last_reviewed_at=req.last_reviewed_at,
            last_reviewed_by=req.last_reviewed_by,
            readiness_status=req.readiness_status,
            requirement_code=el.canonical_code,
            requirement_description=el.description,
            chapter_code=chap.canonical_code,
            standard_code=std.canonical_code,
            objective_element_code=obj.canonical_code
        )
        for req, el, chap, std, obj in results
    ]
    
    return PaginatedHospitalRequirementSummary(
        total=total,
        limit=limit,
        offset=offset,
        items=items
    )


@router.get("/requirements/{hospital_id}/{requirement_id}", response_model=SchemaHospitalRequirementDetail)
async def get_hospital_requirement_detail(
    hospital_id: str,
    requirement_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Retrieve detailed state of a specific hospital requirement."""
    assert_hospital_access(current_user, hospital_id)
    
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    from app.models.database import HospitalNABHRequirement
    
    result = db.query(
        HospitalNABHRequirement, NABHMeasurableElement, NABHChapter, NABHStandard, NABHObjectiveElement
    ).join(
        NABHMeasurableElement, HospitalNABHRequirement.requirement_id == NABHMeasurableElement.id
    ).join(
        NABHObjectiveElement, NABHMeasurableElement.objective_element_id == NABHObjectiveElement.id
    ).join(
        NABHStandard, NABHObjectiveElement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        HospitalNABHRequirement.hospital_id == hospital_id,
        HospitalNABHRequirement.requirement_id == requirement_id,
        HospitalNABHRequirement.retired_at.is_(None),
        NABHMeasurableElement.retired_at.is_(None),
        NABHObjectiveElement.retired_at.is_(None),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None)
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Hospital requirement state not found")
        
    req, el, chap, std, obj = result
    
    from app.models.database import (
        NABHApplicabilityRule, NABHEvidenceRequirement, NABHRequirementCitation,
        HospitalRequirementEvidenceLink
    )
    
    rules = db.query(NABHApplicabilityRule).filter(
        NABHApplicabilityRule.measurable_element_id == el.id,
        NABHApplicabilityRule.retired_at.is_(None)
    ).all()
    
    evidences = db.query(NABHEvidenceRequirement).filter(
        NABHEvidenceRequirement.measurable_element_id == el.id,
        NABHEvidenceRequirement.retired_at.is_(None)
    ).all()
    
    citations = db.query(NABHRequirementCitation).filter(
        NABHRequirementCitation.measurable_element_id == el.id,
        NABHRequirementCitation.retired_at.is_(None)
    ).all()
    
    links = db.query(HospitalRequirementEvidenceLink).filter(
        HospitalRequirementEvidenceLink.hospital_requirement_id == req.id,
        HospitalRequirementEvidenceLink.retired_at.is_(None)
    ).all()
    
    ont_detail = NABHRequirementDetail(
        id=el.id,
        code=el.code,
        canonical_code=el.canonical_code,
        description=el.description,
        applicability_default=el.applicability_default,
        chapter_code=chap.canonical_code,
        chapter_title=chap.title,
        standard_code=std.canonical_code,
        standard_title=std.title,
        objective_element_code=obj.canonical_code,
        objective_element_description=obj.description,
        applicability_rules=[NABHRuleSchema.model_validate(r) for r in rules],
        evidence_requirements=[NABHEvidenceRequirementSchema.model_validate(ev) for ev in evidences],
        citations=[NABHCitationSchema.model_validate(c) for c in citations],
        has_citation=len(citations) > 0,
        has_evidence_requirements=len(evidences) > 0
    )
    
    return SchemaHospitalRequirementDetail(
        id=req.id,
        hospital_id=req.hospital_id,
        requirement_id=req.requirement_id,
        applicability_status=req.applicability_status,
        applicability_reason=req.applicability_reason,
        maturity_level=req.maturity_level,
        evidence_status=req.evidence_status,
        owner_id=req.owner_id,
        due_date=req.due_date,
        last_reviewed_at=req.last_reviewed_at,
        last_reviewed_by=req.last_reviewed_by,
        readiness_status=req.readiness_status,
        ontology_requirement=ont_detail,
        evidence_links=[HospitalRequirementEvidenceLinkSchema.model_validate(l) for l in links]
    )


@router.patch("/requirements/{hospital_id}/{requirement_id}", response_model=SchemaHospitalRequirementDetail)
async def patch_hospital_requirement(
    hospital_id: str,
    requirement_id: str,
    patch: HospitalRequirementPatch,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER]))
):
    """Patch standard progress fields for a hospital's requirement state."""
    assert_hospital_access(current_user, hospital_id)
    
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    from app.models.database import HospitalNABHRequirement
    
    req_result = db.query(
        HospitalNABHRequirement
    ).join(
        NABHMeasurableElement, HospitalNABHRequirement.requirement_id == NABHMeasurableElement.id
    ).join(
        NABHObjectiveElement, NABHMeasurableElement.objective_element_id == NABHObjectiveElement.id
    ).join(
        NABHStandard, NABHObjectiveElement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        HospitalNABHRequirement.hospital_id == hospital_id,
        HospitalNABHRequirement.requirement_id == requirement_id,
        HospitalNABHRequirement.retired_at.is_(None),
        NABHMeasurableElement.retired_at.is_(None),
        NABHObjectiveElement.retired_at.is_(None),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None)
    ).first()
    
    if not req_result:
        raise HTTPException(status_code=404, detail="Hospital requirement state not found")

    req = req_result
        
    patch_data = patch.model_dump(exclude_unset=True)
    _assert_staff_belongs_to_hospital(db, patch_data.get("owner_id"), hospital_id, "owner_id")
    _assert_staff_belongs_to_hospital(db, patch_data.get("last_reviewed_by"), hospital_id, "last_reviewed_by")
    for key, val in patch_data.items():
        setattr(req, key, val)
        
    db.commit()
    
    # Reload details to return the full response schema
    result = db.query(
        HospitalNABHRequirement, NABHMeasurableElement, NABHChapter, NABHStandard, NABHObjectiveElement
    ).join(
        NABHMeasurableElement, HospitalNABHRequirement.requirement_id == NABHMeasurableElement.id
    ).join(
        NABHObjectiveElement, NABHMeasurableElement.objective_element_id == NABHObjectiveElement.id
    ).join(
        NABHStandard, NABHObjectiveElement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        HospitalNABHRequirement.hospital_id == hospital_id,
        HospitalNABHRequirement.requirement_id == requirement_id,
        HospitalNABHRequirement.retired_at.is_(None),
        NABHMeasurableElement.retired_at.is_(None),
        NABHObjectiveElement.retired_at.is_(None),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None)
    ).first()
    
    req, el, chap, std, obj = result
    
    from app.models.database import (
        NABHApplicabilityRule, NABHEvidenceRequirement, NABHRequirementCitation,
        HospitalRequirementEvidenceLink
    )
    
    rules = db.query(NABHApplicabilityRule).filter(
        NABHApplicabilityRule.measurable_element_id == el.id,
        NABHApplicabilityRule.retired_at.is_(None)
    ).all()
    
    evidences = db.query(NABHEvidenceRequirement).filter(
        NABHEvidenceRequirement.measurable_element_id == el.id,
        NABHEvidenceRequirement.retired_at.is_(None)
    ).all()
    
    citations = db.query(NABHRequirementCitation).filter(
        NABHRequirementCitation.measurable_element_id == el.id,
        NABHRequirementCitation.retired_at.is_(None)
    ).all()
    
    links = db.query(HospitalRequirementEvidenceLink).filter(
        HospitalRequirementEvidenceLink.hospital_requirement_id == req.id,
        HospitalRequirementEvidenceLink.retired_at.is_(None)
    ).all()
    
    ont_detail = NABHRequirementDetail(
        id=el.id,
        code=el.code,
        canonical_code=el.canonical_code,
        description=el.description,
        applicability_default=el.applicability_default,
        chapter_code=chap.canonical_code,
        chapter_title=chap.title,
        standard_code=std.canonical_code,
        standard_title=std.title,
        objective_element_code=obj.canonical_code,
        objective_element_description=obj.description,
        applicability_rules=[NABHRuleSchema.model_validate(r) for r in rules],
        evidence_requirements=[NABHEvidenceRequirementSchema.model_validate(ev) for ev in evidences],
        citations=[NABHCitationSchema.model_validate(c) for c in citations],
        has_citation=len(citations) > 0,
        has_evidence_requirements=len(evidences) > 0
    )
    
    return SchemaHospitalRequirementDetail(
        id=req.id,
        hospital_id=req.hospital_id,
        requirement_id=req.requirement_id,
        applicability_status=req.applicability_status,
        applicability_reason=req.applicability_reason,
        maturity_level=req.maturity_level,
        evidence_status=req.evidence_status,
        owner_id=req.owner_id,
        due_date=req.due_date,
        last_reviewed_at=req.last_reviewed_at,
        last_reviewed_by=req.last_reviewed_by,
        readiness_status=req.readiness_status,
        ontology_requirement=ont_detail,
        evidence_links=[HospitalRequirementEvidenceLinkSchema.model_validate(l) for l in links]
    )


@router.get("/readiness/{hospital_id}", response_model=HospitalReadinessResponse)
async def get_hospital_readiness(
    hospital_id: str,
    edition_version: str = Query("6.0"),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """
    Get the new ontology/applicability-based readiness score and per-chapter breakdown.
    """
    assert_hospital_access(current_user, hospital_id)
    return calculate_hospital_readiness(db, hospital_id, edition_version)


