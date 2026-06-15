"""Admin API Endpoints for medguardian."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from app.core.database import get_db
from app.api.auth import require_role
from app.models.database import Staff, UserRole, Hospital, NABHObjective, MaturityLevel, SeverityLevel

router = APIRouter()

@router.get("/nabh-fleet-summary", response_model=List[Dict[str, Any]])
async def get_nabh_fleet_summary(
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """
    Returns a fleet compliance summary of all hospitals under management.
    Requires SUPER_ADMIN role.
    """
    hospitals = db.query(Hospital).all()
    
    fleet_summary = []
    for hospital in hospitals:
        objectives = db.query(NABHObjective).filter(NABHObjective.hospital_id == hospital.id).all()
        
        if not objectives:
            fleet_summary.append({
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "overall_maturity_avg": 0.0,
                "critical_gaps_count": 0,
                "last_assessed": None
            })
            continue
            
        total_maturity = sum(obj.maturity_level.value for obj in objectives if obj.maturity_level)
        overall_maturity_avg = round(total_maturity / len(objectives), 2)
        
        critical_gaps_count = sum(
            1 for obj in objectives 
            if obj.severity == SeverityLevel.CRITICAL and obj.maturity_level.value < MaturityLevel.IMPLEMENTED.value
        )
        
        last_assessed_dates = [obj.last_assessed for obj in objectives if obj.last_assessed]
        last_assessed = max(last_assessed_dates).isoformat() if last_assessed_dates else None
        
        fleet_summary.append({
            "hospital_id": hospital.id,
            "hospital_name": hospital.name,
            "overall_maturity_avg": overall_maturity_avg,
            "critical_gaps_count": critical_gaps_count,
            "last_assessed": last_assessed
        })
        
    return fleet_summary


@router.get("/db-inspection")
async def db_inspection(
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    import os
    from app.core.config import settings
    from app.models.database import (
        NABHEdition, NABHChapter, NABHStandard,
        NABHMeasurableElement, NABHEvidenceRequirement,
        NABHRequirementCitation
    )
    
    # Mask password in DATABASE_URL
    db_url = settings.DATABASE_URL
    masked_db_url = db_url
    if "@" in db_url:
        try:
            prefix, rest = db_url.split("@", 1)
            proto, credentials = prefix.split("://", 1)
            if ":" in credentials:
                user, _ = credentials.split(":", 1)
                masked_db_url = f"{proto}://{user}:***@{rest}"
        except Exception:
            masked_db_url = "invalid-or-masked-url"
            
    # Count of editions and chapters specifically for 6.0
    nabh_6_editions_count = db.query(NABHEdition).filter(NABHEdition.version == "6.0").count()
    nabh_6_chapters_count = db.query(NABHChapter).join(NABHEdition).filter(NABHEdition.version == "6.0").count()
    
    return {
        "database_url": masked_db_url,
        "is_render": "RENDER" in os.environ,
        "env_variables": {k: os.environ.get(k) for k in ["RENDER", "RENDER_SERVICE_ID", "RENDER_SERVICE_NAME"] if k in os.environ},
        "counts": {
            "editions": db.query(NABHEdition).count(),
            "chapters": db.query(NABHChapter).count(),
            "standards": db.query(NABHStandard).count(),
            "measurable_elements": db.query(NABHMeasurableElement).count(),
            "citations": db.query(NABHRequirementCitation).count(),
            "evidence_requirements": db.query(NABHEvidenceRequirement).count(),
        },
        "nabh_6_editions_count": nabh_6_editions_count,
        "nabh_6_chapters_count": nabh_6_chapters_count,
    }


@router.post("/seed-ontology")
async def seed_ontology(
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    from app.nabh.seeder import seed_versioned_ontology
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Admin triggered ontology seeding...")
    
    try:
        # Use official seeder
        seed_versioned_ontology(db, "app/nabh/data", "6.0")
        return {"status": "success", "message": "Ontology seeded successfully"}
    except Exception as e:
        logger.error(f"Error seeding ontology: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Seeding failed: {str(e)}"
        )
