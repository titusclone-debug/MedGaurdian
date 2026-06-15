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

