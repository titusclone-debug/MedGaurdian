from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from app.models.database import (
    ConsentRecord,
    ConsentStatus,
    Hospital,
    License,
    LicenseStatus,
    RiskAlert,
    RiskLevel,
)
from app.services.scheduler import _check_consent_expiry, _check_license_expiry


def _seed_hospital(db_session, hospital_id: str) -> Hospital:
    hospital = Hospital(
        id=hospital_id,
        name=f"Hospital {hospital_id}",
        registration_number=f"REG-{hospital_id}",
        hospital_type="trust",
    )
    db_session.add(hospital)
    db_session.commit()
    return hospital


def test_check_license_expiry_creates_critical_alert_and_is_idempotent(db_session):
    hospital = _seed_hospital(db_session, "sched-license-hosp")
    license_record = License(
        hospital_id=hospital.id,
        license_name="Fire NOC",
        license_number="NOC-001",
        issuing_authority="Fire Department",
        status=LicenseStatus.ACTIVE,
        expiry_date=datetime.utcnow() + timedelta(days=5),
    )
    db_session.add(license_record)
    db_session.commit()

    with patch("app.core.database.SessionLocal", return_value=db_session), patch.object(
        db_session, "close", return_value=None
    ):
        _check_license_expiry()

    alerts = db_session.query(RiskAlert).filter(RiskAlert.hospital_id == hospital.id).all()
    assert len(alerts) == 1
    assert alerts[0].severity == RiskLevel.CRITICAL
    assert alerts[0].alert_type == "license_expiry"

    with patch("app.core.database.SessionLocal", return_value=db_session), patch.object(
        db_session, "close", return_value=None
    ):
        _check_license_expiry()

    alerts_after_second_run = db_session.query(RiskAlert).filter(RiskAlert.hospital_id == hospital.id).all()
    assert len(alerts_after_second_run) == 1


def test_check_consent_expiry_marks_expired_records(db_session):
    hospital = _seed_hospital(db_session, "sched-consent-hosp")
    consent = ConsentRecord(
        hospital_id=hospital.id,
        patient_id="P-EXP-1",
        purpose="Treatment",
        status=ConsentStatus.GRANTED,
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    db_session.add(consent)
    db_session.commit()

    with patch("app.core.database.SessionLocal", return_value=db_session), patch.object(
        db_session, "close", return_value=None
    ):
        _check_consent_expiry()

    updated = db_session.query(ConsentRecord).filter(ConsentRecord.id == consent.id).first()
    assert updated is not None
    assert updated.status == ConsentStatus.EXPIRED


def test_check_license_expiry_handles_operational_error_and_rolls_back(db_session):
    hospital = _seed_hospital(db_session, "sched-error-hosp")
    license_record = License(
        hospital_id=hospital.id,
        license_name="Pollution Clearance",
        license_number="PCB-001",
        issuing_authority="Pollution Board",
        status=LicenseStatus.ACTIVE,
        expiry_date=datetime.utcnow() + timedelta(days=10),
    )
    db_session.add(license_record)
    db_session.commit()

    forced_error = OperationalError("COMMIT", {}, Exception("forced database failure"))

    with patch("app.core.database.SessionLocal", return_value=db_session), patch.object(
        db_session, "close", return_value=None
    ), patch.object(db_session, "rollback", wraps=db_session.rollback) as rollback_spy, patch.object(
        db_session, "commit", side_effect=forced_error
    ):
        _check_license_expiry()
        assert rollback_spy.called
