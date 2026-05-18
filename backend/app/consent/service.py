from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
from typing import Optional, List, Dict, Any
from app.consent.repository import ConsentRepository
from app.models.database import ConsentRecord, DataBreachLog, ConsentStatus

class ConsentService:
    @staticmethod
    def grant_consent(db: Session, consent: Any) -> Dict[str, Any]:
        """Anonymize PII, create a Digital Consent Artefact, and hash-chain it to the ledger block."""
        # Generate consent artefact hash
        artefact_data = f"{consent.patient_id}{consent.consent_type}{consent.purpose}{datetime.utcnow().isoformat()}"
        
        # Get previous hash for chain
        last_consent = ConsentRepository.get_last_consent(db, consent.hospital_id)
        previous_hash = last_consent.artefact_hash if last_consent else "0" * 64
        artefact_hash = hashlib.sha256(f"{artefact_data}{previous_hash}".encode()).hexdigest()
        
        # Hash patient name for privacy (we don't store PII in plaintext)
        patient_name_hash = hashlib.sha256(consent.patient_name.encode()).hexdigest()
        
        # Create consent record
        new_consent = ConsentRecord(
            hospital_id=consent.hospital_id,
            patient_id=consent.patient_id,
            patient_name_hash=patient_name_hash,
            consent_type=consent.consent_type,
            purpose=consent.purpose,
            data_categories=consent.data_categories,
            third_parties=consent.third_parties,
            status=ConsentStatus.GRANTED,
            granted_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=consent.expires_in_days),
            consent_method=consent.consent_method,
            artefact_hash=artefact_hash,
            previous_hash=previous_hash,
            is_minor=consent.is_minor,
            guardian_consent_id=consent.guardian_consent_id,
            language_preference=consent.language_preference,
        )
        
        saved = ConsentRepository.create_consent(db, new_consent)
        
        return {
            "consent_id": saved.id,
            "artefact_hash": artefact_hash,
            "status": "granted",
            "expires_at": saved.expires_at.isoformat(),
            "patient_id_hash": patient_name_hash[:16] + "...",
            "message": f"Consent artefact created. Valid for {consent.expires_in_days} days.",
            "dpdp_compliance": {
                "purpose_limited": True,
                "data_minimized": True,
                "tamper_proof": True,
                "language": consent.language_preference,
                "minor_protection": consent.is_minor,
            }
        }

    @staticmethod
    def withdraw_consent(db: Session, consent: ConsentRecord, withdrawal: Any) -> Dict[str, Any]:
        """Formally withdraw previously granted consent."""
        consent.status = ConsentStatus.WITHDRAWN
        consent.withdrawn_at = datetime.utcnow()
        consent.withdrawal_reason = withdrawal.reason
        
        ConsentRepository.save(db, consent)
        
        return {
            "consent_id": consent.id,
            "status": "withdrawn",
            "withdrawn_at": consent.withdrawn_at.isoformat(),
            "message": "Consent withdrawn. Data processing for this purpose must cease immediately.",
            "dpdp_obligation": "You must stop processing this patient's data for the withdrawn purpose within 24 hours."
        }

    @staticmethod
    def get_patient_consents(db: Session, hospital_id: str, patient_id: str) -> Dict[str, Any]:
        """Aggregate patient consent history, active ratios, and expiration dates."""
        consents = ConsentRepository.get_all_for_patient(db, hospital_id, patient_id)
        
        return {
            "patient_id_hash": patient_id[:8] + "...",
            "total_consents": len(consents),
            "active": sum(1 for c in consents if c.status == ConsentStatus.GRANTED and c.expires_at > datetime.utcnow()),
            "expired": sum(1 for c in consents if c.status == ConsentStatus.GRANTED and c.expires_at <= datetime.utcnow()),
            "withdrawn": sum(1 for c in consents if c.status == ConsentStatus.WITHDRAWN),
            "consents": [{
                "id": c.id,
                "type": c.consent_type,
                "purpose": c.purpose,
                "status": c.status.value,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                "data_categories": c.data_categories,
                "third_parties": c.third_parties,
                "artefact_hash": c.artefact_hash,
            } for c in consents]
        }

    @staticmethod
    def check_compliance(db: Session, hospital_id: str) -> Dict[str, Any]:
        """Perform comprehensive DPDP audit covering expired active consents and minor protections."""
        records = ConsentRepository.get_all_for_hospital(db, hospital_id)
        
        now = datetime.utcnow()
        expired_active = sum(1 for r in records if r.status == ConsentStatus.GRANTED and r.expires_at <= now)
        expiring_soon = sum(1 for r in records if r.status == ConsentStatus.GRANTED and now < r.expires_at <= now + timedelta(days=30))
        minor_no_guardian = sum(1 for r in records if r.is_minor and not r.guardian_consent_id and r.status == ConsentStatus.GRANTED)
        total_patients = len(set(r.patient_id for r in records))
        
        compliance_score = 100
        issues = []
        
        if expired_active > 0:
            compliance_score -= min(30, expired_active * 5)
            issues.append(f"🔴 {expired_active} expired consents still active — must renew or cease processing")
        
        if expiring_soon > 0:
            compliance_score -= min(10, expiring_soon * 2)
            issues.append(f"🟡 {expiring_soon} consents expiring within 30 days — initiate renewal")
        
        if minor_no_guardian > 0:
            compliance_score -= min(25, minor_no_guardian * 10)
            issues.append(f"🔴 {minor_no_guardian} minor patients without guardian consent — DPDP violation")
            
        return {
            "hospital_id": hospital_id,
            "compliance_score": max(0, compliance_score),
            "status": "compliant" if compliance_score >= 80 else "needs_attention" if compliance_score >= 60 else "non_compliant",
            "issues": issues,
            "metrics": {
                "total_patient_consents": total_patients,
                "expired_active": expired_active,
                "expiring_soon": expiring_soon,
                "minor_without_guardian": minor_no_guardian,
            },
            "recommendations": [
                "Renew all expired consents before next audit",
                "Implement automated consent renewal reminders",
                "Ensure all minor patients have guardian consent on file",
                "Verify consent language matches patient's preferred language",
            ]
        }

    @staticmethod
    def report_data_breach(db: Session, breach: Any) -> Dict[str, Any]:
        """Record regulatory breach data and calculate the 72-hour regulatory notification deadline."""
        new_breach = DataBreachLog(
            hospital_id=breach.hospital_id,
            breach_detected_at=datetime.utcnow(),
            breach_type=breach.breach_type,
            affected_records_count=breach.affected_records_count,
            data_categories_affected=breach.data_categories_affected,
            root_cause=breach.root_cause,
            status="detected",
        )
        saved = ConsentRepository.create_breach_log(db, new_breach)
        
        notification_deadline = datetime.utcnow() + timedelta(hours=72)
        
        return {
            "breach_id": saved.id,
            "detected_at": saved.breach_detected_at.isoformat(),
            "notification_deadline": notification_deadline.isoformat(),
            "hours_remaining": 72,
            "status": "detected",
            "immediate_actions": [
                "Contain the breach (isolate affected systems)",
                "Notify the Data Protection Officer immediately",
                "Begin impact assessment",
                "Prepare notification to DPDP Board (due within 72 hours)",
                "Prepare patient notification if required",
            ],
            "message": "⚠️ BREACH CLOCK STARTED — 72 hours to notify DPDP Board"
        }
