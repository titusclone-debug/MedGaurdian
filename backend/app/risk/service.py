from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.risk.repository import RiskRepository
from app.models.database import RiskAlert, RiskLevel

class RiskService:
    @staticmethod
    def get_alerts(
        db: Session,
        hospital_id: str,
        severity: Optional[RiskLevel],
        resolved: bool,
        limit: int
    ) -> Dict[str, Any]:
        """Fetch filtered risk alerts and format them for UI rendering."""
        alerts = RiskRepository.get_alerts(db, hospital_id, resolved)
        
        # In-memory filter for severity and sort/limit to align repository reuse
        filtered_alerts = []
        for a in alerts:
            if severity and a.severity != severity:
                continue
            filtered_alerts.append(a)
            
        # Sort by severity descending, created_at descending
        filtered_alerts.sort(key=lambda x: (x.severity.value, x.created_at), reverse=True)
        paginated = filtered_alerts[:limit]
        
        return {
            "hospital_id": hospital_id,
            "total_alerts": len(paginated),
            "resolved": resolved,
            "alerts": [{
                "id": a.id,
                "type": a.alert_type,
                "severity": a.severity.value,
                "title": a.title,
                "description": a.description,
                "risk_score": a.risk_score,
                "probability": a.probability,
                "impact": a.impact,
                "recommended_action": a.recommended_action,
                "assigned_to": a.assigned_to,
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "is_acknowledged": a.is_acknowledged,
                "created_at": a.created_at.isoformat(),
                "escalation_level": a.escalation_level,
            } for a in paginated]
        }

    @staticmethod
    def create_alert(
        db: Session,
        alert: Any,
        risk_severity: RiskLevel,
        due_date: Optional[datetime]
    ) -> Dict[str, Any]:
        """Create and seed a new risk alert."""
        new_alert = RiskAlert(
            hospital_id=alert.hospital_id,
            alert_type=alert.alert_type,
            severity=risk_severity,
            title=alert.title,
            description=alert.description,
            recommended_action=alert.recommended_action,
            assigned_to=alert.assigned_to,
            due_date=due_date,
            risk_score=0.0,
        )
        saved = RiskRepository.create(db, new_alert)
        
        return {
            "id": saved.id,
            "severity": alert.severity,
            "message": f"Risk alert created: {alert.title}"
        }

    @staticmethod
    def acknowledge_alert(db: Session, alert: RiskAlert, user_id: str) -> Dict[str, Any]:
        """Mark an alert as acknowledged by a staff member."""
        alert.is_acknowledged = True
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()
        
        RiskRepository.save(db, alert)
        
        return {"id": alert.id, "status": "acknowledged", "message": "Alert acknowledged"}

    @staticmethod
    def resolve_alert(db: Session, alert: RiskAlert, resolution_notes: str) -> Dict[str, Any]:
        """Mark an alert as formally resolved."""
        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        alert.resolution_notes = resolution_notes
        
        RiskRepository.save(db, alert)
        
        return {"id": alert.id, "status": "resolved", "message": "Alert resolved"}

    @staticmethod
    def get_forecast(db: Session, hospital_id: str, days: int) -> Dict[str, Any]:
        """Compute predictive risk weather forecast trends based on historical alert frequency."""
        start_date = datetime.utcnow() - timedelta(days=days)
        alerts = RiskRepository.get_alerts_since(db, hospital_id, start_date)
        
        # Trend analysis
        weekly_counts = {}
        for alert in alerts:
            week = alert.created_at.isocalendar()[1]
            if week not in weekly_counts:
                weekly_counts[week] = {"total": 0, "critical": 0, "resolved": 0}
            weekly_counts[week]["total"] += 1
            if alert.severity == RiskLevel.CRITICAL:
                weekly_counts[week]["critical"] += 1
            if alert.is_resolved:
                weekly_counts[week]["resolved"] += 1
        
        weeks = sorted(weekly_counts.keys())
        if len(weeks) >= 2:
            recent = weekly_counts[weeks[-1]]["total"]
            previous = weekly_counts[weeks[-2]]["total"]
            trend = "improving" if recent < previous else "worsening" if recent > previous else "stable"
        else:
            trend = "insufficient_data"
        
        # Predicted risk areas
        type_counts = {}
        for alert in alerts:
            if alert.alert_type not in type_counts:
                type_counts[alert.alert_type] = 0
            type_counts[alert.alert_type] += 1
        
        top_risk_areas = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "hospital_id": hospital_id,
            "forecast_period_days": days,
            "trend": trend,
            "current_alerts": sum(1 for a in alerts if not a.is_resolved),
            "resolved_in_period": sum(1 for a in alerts if a.is_resolved),
            "top_risk_areas": [{"area": area, "alert_count": count} for area, count in top_risk_areas],
            "weekly_trend": [
                {"week": w, **data, "resolution_rate": round(data["resolved"] / data["total"] * 100, 1) if data["total"] > 0 else 100}
                for w, data in sorted(weekly_counts.items())
            ],
            "forecast": {
                "next_week_risk": "high" if trend == "worsening" else "medium" if trend == "stable" else "low",
                "recommendation": (
                    "Immediate attention required. Risk trend is worsening." if trend == "worsening" else
                    "Maintain current controls. Monitor closely." if trend == "stable" else
                    "Good progress. Continue current risk management practices."
                )
            }
        }
