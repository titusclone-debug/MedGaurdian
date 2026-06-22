"""Dashboard API — The 'Risk Weather Forecast' overview."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user
from app.models.database import (
    Hospital, License, ComplianceRecord, BMWLog,
    ConsentRecord, RiskAlert, FundAccount, Staff,
    RiskLevel, ComplianceStatus, LicenseStatus, ConsentStatus
)
from app.models.database import Staff

router = APIRouter()


@router.get("/overview/{hospital_id}")
async def get_dashboard_overview(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    The 'Risk Weather Forecast' — a single-glance view of institutional health.
    Returns a heatmap-style risk assessment across all compliance domains.
    """
    assert_hospital_access(current_user, hospital_id)

    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    # === LICENSE HEALTH ===
    total_licenses = db.query(License).filter(License.hospital_id == hospital_id).count()
    expiring_soon = db.query(License).filter(
        and_(
            License.hospital_id == hospital_id,
            License.expiry_date <= datetime.utcnow() + timedelta(days=90),
            License.expiry_date > datetime.utcnow(),
            License.status != LicenseStatus.RENEWAL_IN_PROGRESS
        )
    ).count()
    expired_licenses = db.query(License).filter(
        and_(
            License.hospital_id == hospital_id,
            License.expiry_date < datetime.utcnow(),
            License.status != LicenseStatus.RENEWAL_IN_PROGRESS
        )
    ).count()
    
    # === NABH COMPLIANCE ===
    total_standards = db.query(ComplianceRecord).filter(
        ComplianceRecord.hospital_id == hospital_id
    ).count()
    compliant_standards = db.query(ComplianceRecord).filter(
        and_(
            ComplianceRecord.hospital_id == hospital_id,
            ComplianceRecord.status == ComplianceStatus.COMPLIANT
        )
    ).count()
    nabh_score = (compliant_standards / total_standards * 100) if total_standards > 0 else 0
    
    # === BMW COMPLIANCE (Last 30 days) ===
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    bmw_total = db.query(BMWLog).filter(
        and_(
            BMWLog.hospital_id == hospital_id,
            BMWLog.waste_date >= thirty_days_ago
        )
    ).count()
    bmw_properly_handled = db.query(BMWLog).filter(
        and_(
            BMWLog.hospital_id == hospital_id,
            BMWLog.waste_date >= thirty_days_ago,
            BMWLog.is_properly_segregated == True,
            BMWLog.is_properly_labeled == True,
            BMWLog.is_properly_stored == True
        )
    ).count()
    bmw_compliance_rate = (bmw_properly_handled / bmw_total * 100) if bmw_total > 0 else 100
    
    # === DPDP CONSENT ===
    total_consents = db.query(ConsentRecord).filter(
        ConsentRecord.hospital_id == hospital_id
    ).count()
    active_consents = db.query(ConsentRecord).filter(
        and_(
            ConsentRecord.hospital_id == hospital_id,
            ConsentRecord.status == ConsentStatus.GRANTED,
            ConsentRecord.expires_at > datetime.utcnow()
        )
    ).count()
    expired_consents = db.query(ConsentRecord).filter(
        and_(
            ConsentRecord.hospital_id == hospital_id,
            ConsentRecord.status == ConsentStatus.GRANTED,
            ConsentRecord.expires_at <= datetime.utcnow()
        )
    ).count()
    
    # === FCRA COMPLIANCE ===
    fcra_accounts = db.query(FundAccount).filter(
        and_(
            FundAccount.hospital_id == hospital_id,
            FundAccount.is_fcra_designated == True
        )
    ).count()
    fcra_compliant = db.query(FundAccount).filter(
        and_(
            FundAccount.hospital_id == hospital_id,
            FundAccount.is_fcra_designated == True,
            FundAccount.compliance_status == ComplianceStatus.COMPLIANT
        )
    ).count()
    
    # === RISK ALERTS ===
    active_alerts = db.query(RiskAlert).filter(
        and_(
            RiskAlert.hospital_id == hospital_id,
            RiskAlert.is_resolved == False
        )
    ).count()
    critical_alerts = db.query(RiskAlert).filter(
        and_(
            RiskAlert.hospital_id == hospital_id,
            RiskAlert.is_resolved == False,
            RiskAlert.severity == RiskLevel.CRITICAL
        )
    ).count()
    
    # === RISK SCORES (Domain-level) ===
    license_score = max(0, 100 - (expired_licenses * 20) - (expiring_soon * 5))
    fcra_score = (fcra_compliant / fcra_accounts * 100) if fcra_accounts > 0 else 100
    consent_score = (active_consents / total_consents * 100) if total_consents > 0 else 100
    staffing_score = 85  # Placeholder — computed from staffing ratios
    
    # Overall risk calculation
    from app.core.config import settings
    weights = settings.RISK_WEIGHTS
    overall_risk = (
        (100 - license_score) * weights["license_expiry"] +
        (100 - nabh_score) * weights["nabh_readiness"] +
        (100 - fcra_score) * weights["fcra_compliance"] +
        (100 - consent_score) * weights["dpdp_consent"] +
        (100 - bmw_compliance_rate) * weights["bmw_compliance"] +
        (100 - staffing_score) * weights["staffing_adequacy"]
    ) * 10
    
    # Risk level classification
    if overall_risk >= 80:
        risk_level = "critical"
        weather = "⛈️ Storm Warning"
    elif overall_risk >= 60:
        risk_level = "high"
        weather = "🌧️ Heavy Clouds"
    elif overall_risk >= 40:
        risk_level = "medium"
        weather = "⛅ Partly Cloudy"
    elif overall_risk >= 20:
        risk_level = "low"
        weather = "🌤️ Mostly Clear"
    else:
        risk_level = "minimal"
        weather = "☀️ Clear Skies"
    
    return {
        "risk_weather": {
            "overall_score": round(overall_risk, 1),
            "level": risk_level,
            "forecast": weather,
            "trend": "stable",  # TODO: compute from historical data
        },
        "domain_scores": {
            "licenses": {"score": round(license_score, 1), "status": "good" if license_score >= 80 else "warning" if license_score >= 60 else "critical"},
            "nabh": {"score": round(nabh_score, 1), "status": "good" if nabh_score >= 80 else "warning" if nabh_score >= 60 else "critical"},
            "fcra": {"score": round(fcra_score, 1), "status": "good" if fcra_score >= 80 else "warning" if fcra_score >= 60 else "critical"},
            "dpdp_consent": {"score": round(consent_score, 1), "status": "good" if consent_score >= 80 else "warning" if consent_score >= 60 else "critical"},
            "bmw": {"score": round(bmw_compliance_rate, 1), "status": "good" if bmw_compliance_rate >= 80 else "warning" if bmw_compliance_rate >= 60 else "critical"},
            "staffing": {"score": round(staffing_score, 1), "status": "good" if staffing_score >= 80 else "warning" if staffing_score >= 60 else "critical"},
        },
        "quick_stats": {
            "total_licenses": total_licenses,
            "expiring_soon": expiring_soon,
            "expired_licenses": expired_licenses,
            "nabh_readiness": f"{nabh_score:.0f}%",
            "bmw_compliance": f"{bmw_compliance_rate:.0f}%",
            "active_consents": active_consents,
            "expired_consents": expired_consents,
            "fcra_accounts": fcra_accounts,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
        },
        "alerts": {
            "total_active": active_alerts,
            "critical": critical_alerts,
        },
        "hospital": {
            "id": hospital.id,
            "name": hospital.name,
            "type": hospital.hospital_type,
            "bed_count": hospital.bed_count,
            "is_rural": hospital.is_rural,
            "onboarding_stage": hospital.onboarding_stage or "profile"
        }
    }


@router.get("/risk-heatmap/{hospital_id}")
async def get_risk_heatmap(
    hospital_id: str,
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Historical risk heatmap — shows risk evolution over time.
    Useful for identifying trends and seasonal patterns.
    """
    assert_hospital_access(current_user, hospital_id)
    # Generate daily risk snapshots for the requested period
    heatmap_data = []
    for i in range(days):
        date = datetime.utcnow() - timedelta(days=days - i - 1)
        
        # Alert count for that day
        alerts = db.query(RiskAlert).filter(
            and_(
                RiskAlert.hospital_id == hospital_id,
                func.date(RiskAlert.created_at) == date.date()
            )
        ).count()
        
        critical = db.query(RiskAlert).filter(
            and_(
                RiskAlert.hospital_id == hospital_id,
                func.date(RiskAlert.created_at) == date.date(),
                RiskAlert.severity == RiskLevel.CRITICAL
            )
        ).count()
        
        heatmap_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "alerts": alerts,
            "critical": critical,
            "risk_level": "critical" if critical > 0 else "high" if alerts > 3 else "medium" if alerts > 1 else "low",
        })
    
    return {
        "hospital_id": hospital_id,
        "period_days": days,
        "heatmap": heatmap_data
    }


@router.get("/action-items/{hospital_id}")
async def get_priority_actions(
    hospital_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Priority action items — what needs attention RIGHT NOW.
    Sorted by urgency, not just severity.
    """
    assert_hospital_access(current_user, hospital_id)
    from app.models.database import RiskAlert

    
    # Get unresolved alerts, sorted by severity and due date
    alerts = db.query(RiskAlert).filter(
        and_(
            RiskAlert.hospital_id == hospital_id,
            RiskAlert.is_resolved == False
        )
    ).order_by(
        RiskAlert.severity.desc(),
        RiskAlert.due_date.asc()
    ).limit(limit).all()
    
    # Also check for expiring licenses in next 30 days
    expiring = db.query(License).filter(
        and_(
            License.hospital_id == hospital_id,
            License.expiry_date <= datetime.utcnow() + timedelta(days=30),
            License.expiry_date > datetime.utcnow()
        )
    ).all()
    
    actions = []
    for alert in alerts:
        actions.append({
            "type": "alert",
            "id": alert.id,
            "title": alert.title,
            "severity": alert.severity.value,
            "domain": alert.alert_type,
            "due_date": alert.due_date.isoformat() if alert.due_date else None,
            "recommended_action": alert.recommended_action,
        })
    
    for lic in expiring:
        days_left = (lic.expiry_date - datetime.utcnow()).days
        actions.append({
            "type": "license_expiry",
            "id": lic.id,
            "title": f"License expiring: {lic.license_name}",
            "severity": "critical" if days_left <= 7 else "high" if days_left <= 30 else "medium",
            "domain": "license",
            "due_date": lic.expiry_date.isoformat(),
            "recommended_action": f"File renewal application for {lic.license_name} (expires in {days_left} days)",
        })
    
    # Sort by severity priority
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    actions.sort(key=lambda x: severity_order.get(x["severity"], 4))
    
    return {"actions": actions[:limit]}
