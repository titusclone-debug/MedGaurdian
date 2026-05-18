from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.database import License, Hospital

class LicenseRepository:
    @staticmethod
    def get_by_id(db: Session, license_id: str) -> Optional[License]:
        """Fetch a specific license by UUID."""
        return db.query(License).filter(License.id == license_id).first()

    @staticmethod
    def get_all_for_hospital(db: Session, hospital_id: str) -> List[License]:
        """Fetch all licenses registered for a hospital."""
        return db.query(License).filter(License.hospital_id == hospital_id).all()

    @staticmethod
    def create(db: Session, lic: License) -> License:
        """Persist a new license record."""
        db.add(lic)
        db.commit()
        db.refresh(lic)
        return lic

    @staticmethod
    def save(db: Session, lic: License) -> License:
        """Commit updates to an existing license record."""
        db.commit()
        db.refresh(lic)
        return lic

    @staticmethod
    def get_hospital_by_id(db: Session, hospital_id: str) -> Optional[Hospital]:
        """Fetch hospital details for license applications."""
        return db.query(Hospital).filter(Hospital.id == hospital_id).first()
