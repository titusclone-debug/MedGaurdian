from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Optional, List
from app.models.database import BMWLog

class BMWRepository:
    @staticmethod
    def create_entry(db: Session, log: BMWLog) -> BMWLog:
        """Persist a new BMW log entry."""
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def get_by_id(db: Session, log_id: str) -> Optional[BMWLog]:
        """Fetch a specific BMW entry by its UUID."""
        return db.query(BMWLog).filter(BMWLog.id == log_id).first()

    @staticmethod
    def get_logs_since(db: Session, hospital_id: str, start_date: datetime) -> List[BMWLog]:
        """Fetch all BMW entries for a hospital since a specified start date."""
        return db.query(BMWLog).filter(
            and_(
                BMWLog.hospital_id == hospital_id,
                BMWLog.waste_date >= start_date
            )
        ).order_by(BMWLog.waste_date.desc()).all()

    @staticmethod
    def save(db: Session, log: BMWLog) -> BMWLog:
        """Commit updates to an existing BMW record."""
        db.commit()
        db.refresh(log)
        return log
