from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.compliance.repository import LicenseRepository
from app.models.database import License, LicenseStatus

class LicenseService:
    @staticmethod
    def get_licenses(db: Session, hospital_id: str, status: Optional[LicenseStatus] = None) -> Dict[str, Any]:
        """Fetch and aggregate license statuses and compile days-to-expiry priorities."""
        licenses = LicenseRepository.get_all_for_hospital(db, hospital_id)
        
        result = []
        for lic in licenses:
            # Filter by status if specified
            if status and lic.status != status:
                continue
                
            days_to_expiry = None
            if lic.expiry_date:
                days_to_expiry = (lic.expiry_date - datetime.utcnow()).days
            
            result.append({
                "id": lic.id,
                "name": lic.license_name,
                "number": lic.license_number,
                "authority": lic.issuing_authority,
                "type": lic.license_type,
                "issued_date": lic.issued_date.isoformat() if lic.issued_date else None,
                "expiry_date": lic.expiry_date.isoformat() if lic.expiry_date else None,
                "days_to_expiry": days_to_expiry,
                "status": lic.status.value,
                "reminder_days": lic.renewal_reminder_days,
                "renewal_filed": lic.renewal_application_filed,
                "conditions": lic.conditions,
                "urgency": (
                    "expired" if days_to_expiry is not None and days_to_expiry < 0 else
                    "critical" if days_to_expiry is not None and days_to_expiry <= 7 else
                    "high" if days_to_expiry is not None and days_to_expiry <= 30 else
                    "medium" if days_to_expiry is not None and days_to_expiry <= 90 else
                    "low" if days_to_expiry is not None else
                    "none"
                )
            })
            
        expired = sum(1 for r in result if r["urgency"] == "expired")
        critical = sum(1 for r in result if r["urgency"] == "critical")
        high = sum(1 for r in result if r["urgency"] == "high")
        
        return {
            "hospital_id": hospital_id,
            "total_licenses": len(result),
            "summary": {
                "expired": expired,
                "critical": critical,
                "high": high,
                "ok": len(result) - expired - critical - high,
            },
            "licenses": result
        }

    @staticmethod
    def create_license(
        db: Session,
        license_data: Any,
        issued_date: datetime,
        expiry_date: Optional[datetime]
    ) -> Dict[str, Any]:
        """Instantiate and register a new license."""
        new_license = License(
            hospital_id=license_data.hospital_id,
            license_name=license_data.license_name,
            license_number=license_data.license_number,
            issuing_authority=license_data.issuing_authority,
            license_type=license_data.license_type,
            issued_date=issued_date,
            expiry_date=expiry_date,
            renewal_reminder_days=license_data.renewal_reminder_days,
            conditions=license_data.conditions,
            status=LicenseStatus.ACTIVE,
        )
        saved = LicenseRepository.create(db, new_license)
        
        return {
            "id": saved.id,
            "message": f"License '{license_data.license_name}' registered successfully",
            "status": "active"
        }

    @staticmethod
    def file_renewal(db: Session, lic: License) -> Dict[str, Any]:
        """File a formal license renewal transaction."""
        lic.status = LicenseStatus.RENEWAL_IN_PROGRESS
        lic.renewal_application_filed = True
        lic.renewal_application_date = datetime.utcnow()
        
        LicenseRepository.save(db, lic)
        
        return {
            "id": lic.id,
            "status": "renewal_in_progress",
            "message": f"Renewal filed for '{lic.license_name}'. Monitor progress."
        }

    @staticmethod
    def draft_license_renewal(db: Session, lic: License) -> Dict[str, Any]:
        """Generate a complete pre-formatted licensing authority renewal draft letter."""
        hospital = LicenseRepository.get_hospital_by_id(db, lic.hospital_id)
        
        draft = f"""
To
The Licensing Authority
{lic.issuing_authority}

Subject: Application for Renewal of {lic.license_name}
License No: {lic.license_number}

Respected Sir/Madam,

I am writing on behalf of {hospital.name if hospital else 'our institution'}, located at {hospital.address if hospital else 'N/A'}, to respectfully request the renewal of the above-referenced license.

License Details:
- License Name: {lic.license_name}
- License Number: {lic.license_number}
- Date of Issue: {lic.issued_date.strftime('%d-%m-%Y') if lic.issued_date else 'N/A'}
- Date of Expiry: {lic.expiry_date.strftime('%d-%m-%Y') if lic.expiry_date else 'N/A'}

The institution has maintained full compliance with all conditions attached to the license during its validity period. We have not been subject to any adverse findings, penalties, or enforcement actions.

We request your good office to kindly renew the license for the ensuing period.

Thanking you,

Yours faithfully,
[Authorized Signatory]
{hospital.name if hospital else 'Institution Name'}
"""
        
        return {
            "license_id": lic.id,
            "license_name": lic.license_name,
            "draft": draft.strip(),
            "message": "Review and customize this draft before submission."
        }
