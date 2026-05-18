from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from app.models.database import ComplianceRecord

class ComplianceRepository:
    @staticmethod
    def get_by_standard_code(db: Session, hospital_id: str, code: str) -> Optional[ComplianceRecord]:
        """Fetch a specific compliance assessment record by standard code."""
        return db.query(ComplianceRecord).filter(
            and_(
                ComplianceRecord.hospital_id == hospital_id,
                ComplianceRecord.standard_code == code
            )
        ).first()

    @staticmethod
    def get_all_for_hospital(db: Session, hospital_id: str) -> List[ComplianceRecord]:
        """Fetch all assessment records registered for a hospital."""
        return db.query(ComplianceRecord).filter(
            ComplianceRecord.hospital_id == hospital_id
        ).all()

    @staticmethod
    def create(db: Session, record: ComplianceRecord) -> ComplianceRecord:
        """Persist a new compliance record."""
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def save(db: Session, record: ComplianceRecord) -> ComplianceRecord:
        """Commit updates to an existing compliance record."""
        db.commit()
        db.refresh(record)
        return record
