from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from app.models.database import ConsentRecord, DataBreachLog, Hospital

class ConsentRepository:
    @staticmethod
    def get_by_id(db: Session, consent_id: str) -> Optional[ConsentRecord]:
        """Fetch a specific consent record by UUID."""
        return db.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()

    @staticmethod
    def get_last_consent(db: Session, hospital_id: str) -> Optional[ConsentRecord]:
        """Fetch the single absolute most recent consent record for blockchain hashing."""
        return db.query(ConsentRecord).filter(
            ConsentRecord.hospital_id == hospital_id
        ).order_by(ConsentRecord.created_at.desc()).first()

    @staticmethod
    def get_all_for_patient(db: Session, hospital_id: str, patient_id: str) -> List[ConsentRecord]:
        """Fetch all consent records registered for a patient at a specific hospital."""
        return db.query(ConsentRecord).filter(
            and_(
                ConsentRecord.patient_id == patient_id,
                ConsentRecord.hospital_id == hospital_id
            )
        ).order_by(ConsentRecord.created_at.desc()).all()

    @staticmethod
    def get_all_for_hospital(db: Session, hospital_id: str) -> List[ConsentRecord]:
        """Fetch all consent records for a hospital (used in compliance calculation)."""
        return db.query(ConsentRecord).filter(
            ConsentRecord.hospital_id == hospital_id
        ).all()

    @staticmethod
    def create_consent(db: Session, record: ConsentRecord) -> ConsentRecord:
        """Persist a new patient consent record."""
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def create_breach_log(db: Session, log: DataBreachLog) -> DataBreachLog:
        """Persist a new regulatory data breach log."""
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def save(db: Session, record: ConsentRecord) -> ConsentRecord:
        """Commit updates to an existing consent record."""
        db.commit()
        db.refresh(record)
        return record
