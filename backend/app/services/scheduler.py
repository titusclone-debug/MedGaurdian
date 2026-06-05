"""Scheduler — Background tasks for regulatory monitoring and alerts."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler():
    """Start all scheduled background tasks."""
    if scheduler.running:
        logger.info("⏰ MedGuardian scheduler is already running")
        return
    
    
    # Regulatory ingestion — daily at 6 AM
    scheduler.add_job(
        _run_regulatory_ingestion,
        CronTrigger(hour=6, minute=0),
        id="regulatory_ingestion",
        name="Regulatory Ingestion Engine",
        replace_existing=True,
    )
    
    # License expiry check — daily at 8 AM
    scheduler.add_job(
        _check_license_expiry,
        CronTrigger(hour=8, minute=0),
        id="license_expiry_check",
        name="License Expiry Monitor",
        replace_existing=True,
    )
    
    # Consent expiry check — daily at 9 AM
    scheduler.add_job(
        _check_consent_expiry,
        CronTrigger(hour=9, minute=0),
        id="consent_expiry_check",
        name="Consent Expiry Monitor",
        replace_existing=True,
    )
    
    # Risk score recalculation — every 6 hours
    scheduler.add_job(
        _recalculate_risk_scores,
        IntervalTrigger(hours=6),
        id="risk_recalculation",
        name="Risk Score Recalculation",
        replace_existing=True,
    )
    
    # FCRA compliance check — weekly on Monday at 7 AM
    scheduler.add_job(
        _check_fcra_compliance,
        CronTrigger(day_of_week="mon", hour=7, minute=0),
        id="fcra_compliance_check",
        name="FCRA Compliance Check",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("⏰ MedGuardian scheduler started with 5 background tasks")


def _run_regulatory_ingestion():
    """Run the regulatory ingestion pipeline."""
    import asyncio
    from app.services.regulatory_ingestion import run_ingestion
    
    logger.info("📥 Running scheduled regulatory ingestion...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_ingestion())
        logger.info(f"📥 Ingestion complete: {result.get('new_updates', 0)} new updates")
    except Exception as e:
        logger.error(f"❌ Regulatory ingestion failed: {e}")
    finally:
        loop.close()


def _check_license_expiry():
    """Check for expiring licenses and create alerts."""
    from app.core.database import SessionLocal
    from app.models.database import License, RiskAlert, RiskLevel, LicenseStatus
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        # Find licenses expiring in 7, 30, 90 days (evaluate critical first)
        for days, severity in [(7, RiskLevel.CRITICAL), (30, RiskLevel.HIGH), (90, RiskLevel.MEDIUM)]:
            threshold = datetime.utcnow() + timedelta(days=days)
            
            expiring = db.query(License).filter(
                License.expiry_date <= threshold,
                License.expiry_date > datetime.utcnow(),
                License.status != LicenseStatus.RENEWAL_IN_PROGRESS
            ).all()
            
            for lic in expiring:
                # Check if alert already exists
                existing = db.query(RiskAlert).filter(
                    RiskAlert.title.contains(lic.license_name),
                    RiskAlert.alert_type == "license_expiry",
                    RiskAlert.is_resolved == False
                ).first()
                
                if not existing:
                    days_left = (lic.expiry_date - datetime.utcnow()).days
                    alert = RiskAlert(
                        hospital_id=lic.hospital_id,
                        alert_type="license_expiry",
                        severity=severity,
                        title=f"License expiring: {lic.license_name}",
                        description=f"{lic.license_name} (No: {lic.license_number}) expires in {days_left} days. Issued by {lic.issuing_authority}.",
                        recommended_action=f"File renewal application for {lic.license_name} immediately.",
                        risk_score=100 - days_left,
                        probability=1.0,
                        impact=8.0 if severity == RiskLevel.CRITICAL else 5.0,
                    )
                    db.add(alert)
            
            db.commit()
        
        logger.info("✅ License expiry check complete")
    except Exception as e:
        logger.error(f"❌ License expiry check failed: {e}")
        db.rollback()
    finally:
        db.close()


def _check_consent_expiry():
    """Check for expiring patient consents."""
    from app.core.database import SessionLocal
    from app.models.database import ConsentRecord, ConsentStatus
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        # Find consents expiring in 30 days
        threshold = datetime.utcnow() + timedelta(days=30)
        
        expiring = db.query(ConsentRecord).filter(
            ConsentRecord.status == ConsentStatus.GRANTED,
            ConsentRecord.expires_at <= threshold,
            ConsentRecord.expires_at > datetime.utcnow()
        ).count()
        
        if expiring > 0:
            logger.warning(f"⚠️ {expiring} patient consents expiring within 30 days")
        
        # Mark expired consents
        expired = db.query(ConsentRecord).filter(
            ConsentRecord.status == ConsentStatus.GRANTED,
            ConsentRecord.expires_at <= datetime.utcnow()
        ).all()
        
        for consent in expired:
            consent.status = ConsentStatus.EXPIRED
        
        db.commit()
        logger.info(f"✅ Consent check complete: {len(expired)} marked as expired")
    except Exception as e:
        logger.error(f"❌ Consent expiry check failed: {e}")
        db.rollback()
    finally:
        db.close()


def _recalculate_risk_scores():
    """Recalculate risk scores for all hospitals."""
    from app.core.database import SessionLocal
    from app.models.database import Hospital, RiskAlert, License, ComplianceRecord, RiskLevel
    from sqlalchemy import and_
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        hospitals = db.query(Hospital).all()
        
        for hospital in hospitals:
            # Count unresolved alerts by severity
            critical = db.query(RiskAlert).filter(
                and_(
                    RiskAlert.hospital_id == hospital.id,
                    RiskAlert.is_resolved == False,
                    RiskAlert.severity == RiskLevel.CRITICAL
                )
            ).count()
            
            high = db.query(RiskAlert).filter(
                and_(
                    RiskAlert.hospital_id == hospital.id,
                    RiskAlert.is_resolved == False,
                    RiskAlert.severity == RiskLevel.HIGH
                )
            ).count()
            
            # Simple risk score: critical = 20pts, high = 10pts
            risk_score = min(100, critical * 20 + high * 10)
            
            if risk_score >= 80:
                risk_level = RiskLevel.CRITICAL
            elif risk_score >= 60:
                risk_level = RiskLevel.HIGH
            elif risk_score >= 40:
                risk_level = RiskLevel.MEDIUM
            elif risk_score >= 20:
                risk_level = RiskLevel.LOW
            else:
                risk_level = RiskLevel.MINIMAL
            
            hospital.overall_risk_score = risk_score
            hospital.risk_level = risk_level
        
        db.commit()
        logger.info(f"✅ Risk scores recalculated for {len(hospitals)} hospitals")
    except Exception as e:
        logger.error(f"❌ Risk recalculation failed: {e}")
        db.rollback()
    finally:
        db.close()


def _check_fcra_compliance():
    """Weekly FCRA compliance check."""
    from app.core.database import SessionLocal
    from app.models.database import FundAccount, FundTransaction, Hospital, FundType, ComplianceStatus
    from sqlalchemy import and_
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        # Check for FCRA accounts without recent reconciliation
        threshold = datetime.utcnow() - timedelta(days=30)
        
        accounts = db.query(FundAccount).filter(
            FundAccount.is_fcra_designated == True
        ).all()
        
        for acc in accounts:
            if acc.last_reconciliation and acc.last_reconciliation < threshold:
                acc.compliance_status = ComplianceStatus.NON_COMPLIANT
            elif not acc.last_reconciliation:
                acc.compliance_status = ComplianceStatus.UNDER_REVIEW
        
        db.commit()
        logger.info(f"✅ FCRA compliance check complete for {len(accounts)} accounts")
    except Exception as e:
        logger.error(f"❌ FCRA compliance check failed: {e}")
        db.rollback()
    finally:
        db.close()
