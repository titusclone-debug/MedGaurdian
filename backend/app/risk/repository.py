from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Optional, List
from app.models.database import RiskAlert

class RiskRepository:
    @staticmethod
    def get_by_id(db: Session, alert_id: str) -> Optional[RiskAlert]:
        """Fetch a specific risk alert by UUID."""
        return db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()

    @staticmethod
    def get_alerts(db: Session, hospital_id: str, resolved: bool) -> List[RiskAlert]:
        """Fetch all resolved or unresolved risk alerts for a hospital."""
        return db.query(RiskAlert).filter(
            and_(
                RiskAlert.hospital_id == hospital_id,
                RiskAlert.is_resolved == resolved
            )
        ).all()

    @staticmethod
    def get_alerts_since(db: Session, hospital_id: str, start_date: datetime) -> List[RiskAlert]:
        """Fetch all historical alerts since a start date for forecast analytics."""
        return db.query(RiskAlert).filter(
            and_(
                RiskAlert.hospital_id == hospital_id,
                RiskAlert.created_at >= start_date
            )
        ).all()

    @staticmethod
    def create(db: Session, alert: RiskAlert) -> RiskAlert:
        """Persist a new risk alert."""
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def save(db: Session, alert: RiskAlert) -> RiskAlert:
        """Commit updates to an existing risk alert."""
        db.commit()
        db.refresh(alert)
        return alert
