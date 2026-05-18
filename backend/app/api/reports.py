"""Reports & Export — Generate compliance reports for auditors."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import io

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user
from app.models.database import Staff

router = APIRouter()


@router.get("/compliance-summary/{hospital_id}")
async def generate_compliance_summary(
    hospital_id: str,
    format: str = Query("json", pattern="^(json|pdf|csv)$"),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Generate a comprehensive compliance summary report."""
    assert_hospital_access(current_user, hospital_id)

    from app.models.database import (
        Hospital, License, ComplianceRecord, BMWLog,
        ConsentRecord, RiskAlert, FundAccount
    )
    from sqlalchemy import and_
    
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    report = {
        "report_type": "Comprehensive Compliance Summary",
        "generated_at": datetime.utcnow().isoformat(),
        "hospital": {
            "name": hospital.name,
            "type": hospital.hospital_type,
            "bed_count": hospital.bed_count,
            "state": hospital.state,
            "district": hospital.district,
            "fcra_number": hospital.fcra_number,
            "nabh_id": hospital.nabh_accreditation_id,
        },
        "sections": {}
    }
    
    # License Summary
    licenses = db.query(License).filter(License.hospital_id == hospital_id).all()
    report["sections"]["licenses"] = {
        "total": len(licenses),
        "active": sum(1 for l in licenses if l.status.value == "active"),
        "expiring_soon": sum(1 for l in licenses if l.status.value == "expiring_soon"),
        "expired": sum(1 for l in licenses if l.status.value == "expired"),
    }
    
    # NABH Summary
    compliance = db.query(ComplianceRecord).filter(ComplianceRecord.hospital_id == hospital_id).all()
    report["sections"]["nabh_compliance"] = {
        "total_standards": len(compliance),
        "compliant": sum(1 for c in compliance if c.status.value == "compliant"),
        "non_compliant": sum(1 for c in compliance if c.status.value == "non_compliant"),
        "partially_compliant": sum(1 for c in compliance if c.status.value == "partially_compliant"),
    }
    
    # BMW Summary
    from sqlalchemy import func
    bmw_count = db.query(func.count(BMWLog.id)).filter(BMWLog.hospital_id == hospital_id).scalar()
    report["sections"]["bmw"] = {
        "total_entries": bmw_count,
        "status": "audit_ready" if bmw_count > 0 else "no_data"
    }
    
    # Consent Summary
    consent_count = db.query(func.count(ConsentRecord.id)).filter(ConsentRecord.hospital_id == hospital_id).scalar()
    report["sections"]["dpdp_consent"] = {
        "total_consents": consent_count,
        "status": "active" if consent_count > 0 else "no_data"
    }
    
    # FCRA Summary
    fcra_accounts = db.query(FundAccount).filter(
        and_(FundAccount.hospital_id == hospital_id, FundAccount.is_fcra_designated == True)
    ).count()
    report["sections"]["fcra"] = {
        "designated_accounts": fcra_accounts,
        "status": "compliant" if fcra_accounts > 0 else "needs_review"
    }
    
    # Risk Summary
    active_alerts = db.query(RiskAlert).filter(
        and_(RiskAlert.hospital_id == hospital_id, RiskAlert.is_resolved == False)
    ).count()
    report["sections"]["risk"] = {
        "active_alerts": active_alerts,
        "status": "critical" if active_alerts > 10 else "attention" if active_alerts > 5 else "managed"
    }
    
    if format == "json":
        return report
    elif format == "csv":
        # Flatten to CSV
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Section", "Metric", "Value"])
        for section, data in report["sections"].items():
            for key, value in data.items():
                writer.writerow([section, key, value])
        
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=compliance_report_{hospital_id}.csv"}
        )
    else:
        return report  # PDF generation would use reportlab


@router.get("/audit-trail/{hospital_id}")
async def get_audit_trail(
    hospital_id: str,
    days: int = Query(30, ge=1, le=365),
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Get audit trail for compliance verification."""
    assert_hospital_access(current_user, hospital_id)

    from app.models.database import AuditLog
    from datetime import timedelta
    
    query = db.query(AuditLog).filter(
        AuditLog.timestamp >= datetime.utcnow() - timedelta(days=days)
    )
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    logs = query.order_by(AuditLog.timestamp.desc()).limit(1000).all()
    
    return {
        "hospital_id": hospital_id,
        "period_days": days,
        "total_entries": len(logs),
        "entries": [{
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "hash": log.entry_hash,
        } for log in logs]
    }
