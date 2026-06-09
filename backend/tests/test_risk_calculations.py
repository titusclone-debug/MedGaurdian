from datetime import datetime, timedelta
from unittest.mock import patch

from app.models.database import Hospital, RiskAlert, RiskLevel
from app.risk.service import RiskService
from app.services.scheduler import _recalculate_risk_scores


def _create_hospital(db_session, hospital_id: str) -> Hospital:
    hospital = Hospital(
        id=hospital_id,
        name=f"Hospital {hospital_id}",
        registration_number=f"REG-{hospital_id}",
        hospital_type="trust",
    )
    db_session.add(hospital)
    db_session.commit()
    return hospital


def _seed_alert(
    db_session,
    hospital_id: str,
    severity: RiskLevel,
    created_at: datetime,
    alert_type: str = "compliance",
):
    alert = RiskAlert(
        hospital_id=hospital_id,
        alert_type=alert_type,
        severity=severity,
        title=f"{severity.value} alert",
        description="risk alert",
        is_resolved=False,
        created_at=created_at,
    )
    db_session.add(alert)
    db_session.commit()


def test_recalculate_risk_scores_sets_expected_score_and_level(db_session):
    hospital = _create_hospital(db_session, "risk-score-hosp-1")
    now = datetime.utcnow()

    for _ in range(2):
        _seed_alert(db_session, hospital.id, RiskLevel.CRITICAL, now)
    for _ in range(3):
        _seed_alert(db_session, hospital.id, RiskLevel.HIGH, now)

    with patch("app.core.database.SessionLocal", return_value=db_session), patch.object(
        db_session, "close", return_value=None
    ):
        _recalculate_risk_scores()
    updated_hospital = db_session.query(Hospital).filter(Hospital.id == hospital.id).first()
    assert updated_hospital is not None
    assert updated_hospital.overall_risk_score == 70
    assert updated_hospital.risk_level == RiskLevel.HIGH


def test_get_forecast_identifies_improving_trend(db_session):
    hospital = _create_hospital(db_session, "forecast-improving-hosp")
    now = datetime.utcnow()

    for i in range(5):
        _seed_alert(db_session, hospital.id, RiskLevel.HIGH, now - timedelta(days=12, hours=i))
    for i in range(2):
        _seed_alert(db_session, hospital.id, RiskLevel.HIGH, now - timedelta(days=2, hours=i))

    result = RiskService.get_forecast(db_session, hospital.id, days=14)
    assert result["trend"] == "improving"


def test_get_forecast_identifies_worsening_trend(db_session):
    hospital = _create_hospital(db_session, "forecast-worsening-hosp")
    now = datetime.utcnow()

    for i in range(2):
        _seed_alert(db_session, hospital.id, RiskLevel.HIGH, now - timedelta(days=12, hours=i))
    for i in range(6):
        _seed_alert(db_session, hospital.id, RiskLevel.HIGH, now - timedelta(days=2, hours=i))

    result = RiskService.get_forecast(db_session, hospital.id, days=14)
    assert result["trend"] == "worsening"


def test_get_forecast_identifies_stable_trend(db_session):
    hospital = _create_hospital(db_session, "forecast-stable-hosp")
    now = datetime.utcnow()

    for i in range(3):
        _seed_alert(db_session, hospital.id, RiskLevel.HIGH, now - timedelta(days=12, hours=i))
    for i in range(3):
        _seed_alert(db_session, hospital.id, RiskLevel.HIGH, now - timedelta(days=2, hours=i))

    result = RiskService.get_forecast(db_session, hospital.id, days=14)
    assert result["trend"] == "stable"
