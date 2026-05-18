"""Risk Intelligence — The 'Weather Forecast' for institutional risk."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role
from app.models.database import RiskAlert, Hospital, Staff, RiskLevel, UserRole
from app.risk.repository import RiskRepository
from app.risk.service import RiskService

router = APIRouter()


class AlertCreate(BaseModel):
    hospital_id: str
    alert_type: str
    severity: str
    title: str
    description: str
    recommended_action: str
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


@router.get("/alerts/{hospital_id}")
async def get_risk_alerts(
    hospital_id: str,
    severity: Optional[str] = None,
    resolved: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Get risk alerts with filtering."""
    assert_hospital_access(current_user, hospital_id)

    risk_severity = None
    if severity:
        try:
            risk_severity = RiskLevel(severity.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid risk severity: '{severity}'. Must be one of: critical, high, medium, low, minimal"
            )
            
    return RiskService.get_alerts(db, hospital_id, risk_severity, resolved, limit)


@router.post("/alerts")
async def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """Create a new risk alert."""
    assert_hospital_access(current_user, alert.hospital_id)

    try:
        risk_severity = RiskLevel(alert.severity.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid risk severity: '{alert.severity}'. Must be one of: critical, high, medium, low, minimal"
        )

    due_date = None
    if alert.due_date:
        try:
            due_date = datetime.fromisoformat(alert.due_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid due_date format: '{alert.due_date}'. Must be in ISO 8601 format (YYYY-MM-DD)."
            )

    return RiskService.create_alert(db, alert, risk_severity, due_date)


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """Acknowledge a risk alert."""
    alert = RiskRepository.get_by_id(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    assert_hospital_access(current_user, alert.hospital_id)
    
    return RiskService.acknowledge_alert(db, alert, current_user.id)


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolution_notes: str = Query(...),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """Resolve a risk alert."""
    alert = RiskRepository.get_by_id(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    assert_hospital_access(current_user, alert.hospital_id)
    
    return RiskService.resolve_alert(db, alert, resolution_notes)


@router.get("/forecast/{hospital_id}")
async def get_risk_forecast(
    hospital_id: str,
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Risk Weather Forecast — predictive risk intelligence."""
    # SECURITY FIX: Restored assert_hospital_access from docstring comment into active code!
    assert_hospital_access(current_user, hospital_id)
    
    return RiskService.get_forecast(db, hospital_id, days)
