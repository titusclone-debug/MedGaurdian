from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from app.models.database import NABHObjective

# WARNING: LEGACY REPOSITORY
# Do not build new features on this model; use the upcoming versioned ontology models.
class ComplianceRepository:
    @staticmethod
    def get_by_standard_code(db: Session, hospital_id: str, code: str) -> Optional[NABHObjective]:
        """Fetch a specific compliance assessment record by standard code."""
        return db.query(NABHObjective).filter(
            and_(
                NABHObjective.hospital_id == hospital_id,
                NABHObjective.standard_code == code
            )
        ).first()

    @staticmethod
    def get_all_for_hospital(db: Session, hospital_id: str) -> List[NABHObjective]:
        """Fetch all assessment records registered for a hospital."""
        return db.query(NABHObjective).filter(
            NABHObjective.hospital_id == hospital_id
        ).all()

    @staticmethod
    def create(db: Session, record: NABHObjective) -> NABHObjective:
        """Persist a new compliance record."""
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def save(db: Session, record: NABHObjective) -> NABHObjective:
        """Commit updates to an existing compliance record."""
        db.commit()
        db.refresh(record)
        return record
