import pytest
from unittest.mock import MagicMock
from datetime import datetime

from app.compliance.service import LicenseService
from app.compliance.repository import LicenseRepository
from app.risk.service import RiskService
from app.risk.repository import RiskRepository
from app.nabh.service import ComplianceService
from app.nabh.repository import ComplianceRepository
from app.fcra.service import FCRAService
from app.fcra.repository import FCRARepository
from app.consent.service import ConsentService
from app.consent.repository import ConsentRepository

from app.models.database import (
    License, LicenseStatus, RiskAlert, RiskLevel,
    ComplianceRecord, ComplianceStatus, FundAccount, FundType,
    ConsentRecord, ConsentStatus, NABHObjective, SeverityLevel, MaturityLevel
)

def test_license_service_aggregation():
    """Verify LicenseService fetches and filters active status counts correctly."""
    db = MagicMock()
    licenses = [
        License(id="lic-1", license_name="Fire NOC", status=LicenseStatus.ACTIVE),
        License(id="lic-2", license_name="Pharmacy License", status=LicenseStatus.RENEWAL_IN_PROGRESS)
    ]
    
    original_get_all = LicenseRepository.get_all_for_hospital
    LicenseRepository.get_all_for_hospital = MagicMock(return_value=licenses)
    
    try:
        res = LicenseService.get_licenses(db, "hosp-1", status=LicenseStatus.ACTIVE)
        assert res["total_licenses"] == 1
        assert res["licenses"][0]["id"] == "lic-1"
    finally:
        LicenseRepository.get_all_for_hospital = original_get_all


def test_risk_service_acknowledgement():
    """Verify RiskService updates alert state upon acknowledgment."""
    db = MagicMock()
    alert = RiskAlert(id="alert-1", hospital_id="hosp-1", is_acknowledged=False)
    
    original_save = RiskRepository.save
    RiskRepository.save = MagicMock(return_value=alert)
    
    try:
        res = RiskService.acknowledge_alert(db, alert, "user-admin")
        assert res["status"] == "acknowledged"
        assert alert.is_acknowledged is True
        assert alert.acknowledged_by == "user-admin"
    finally:
        RiskRepository.save = original_save


def test_nabh_service_gap_analysis():
    """Verify ComplianceService aggregates non-compliant scores as critical compliance gaps."""
    db = MagicMock()
    records = [
        NABHObjective(
            standard_code="AAC-1.a",
            standard_name="Patient Access Services",
            chapter_code="ACC",
            severity=SeverityLevel.CRITICAL,
            maturity_level=MaturityLevel.AD_HOC,
            monitoring_indicator_rate=20.0,
            remediation_plan="Critical gap plan"
        ),
        NABHObjective(
            standard_code="AAC-2.a",
            standard_name="Assessment of Patients",
            chapter_code="ACC",
            severity=SeverityLevel.MAJOR,
            maturity_level=MaturityLevel.IMPLEMENTED,
            monitoring_indicator_rate=100.0
        )
    ]
    
    original_get_all = ComplianceRepository.get_all_for_hospital
    ComplianceRepository.get_all_for_hospital = MagicMock(return_value=records)
    
    try:
        res = ComplianceService.get_gap_analysis(db, "hosp-1")
        assert res["total_gaps"] == 1
        assert res["gaps"][0]["standard_code"] == "AAC-1.a"
        assert res["gaps"][0]["priority"] == "critical"
    finally:
        ComplianceRepository.get_all_for_hospital = original_get_all


def test_fcra_service_reconciliation():
    """Verify FCRAService computes closing balances and transaction compliance flags correctly."""
    db = MagicMock()
    accounts = [
        FundAccount(id="acc-1", account_name="FCRA Escrow", fund_type=FundType.FCRA_FOREIGN, current_balance=5000.0, is_fcra_designated=True)
    ]
    
    original_get_accounts = FCRARepository.get_accounts_for_hospital
    FCRARepository.get_accounts_for_hospital = MagicMock(return_value=accounts)
    
    original_get_txns = FCRARepository.get_transactions_in_range
    FCRARepository.get_transactions_in_range = MagicMock(return_value=[])
    
    try:
        res = FCRAService.get_compliance_report(db, "hosp-1", year=2026)
        assert res["summary"]["overall_compliance_rate"] == 100
        assert res["accounts"][0]["account_name"] == "FCRA Escrow"
    finally:
        FCRARepository.get_accounts_for_hospital = original_get_accounts
        FCRARepository.get_transactions_in_range = original_get_txns


def test_consent_service_withdrawal():
    """Verify ConsentService sets withdrawn properties on consent artefacts."""
    db = MagicMock()
    consent = ConsentRecord(id="consent-1", hospital_id="hosp-1", status=ConsentStatus.GRANTED)
    withdrawal = MagicMock()
    withdrawal.reason = "Patient request"
    
    original_save = ConsentRepository.save
    ConsentRepository.save = MagicMock(return_value=consent)
    
    try:
        res = ConsentService.withdraw_consent(db, consent, withdrawal)
        assert res["status"] == "withdrawn"
        assert consent.status == ConsentStatus.WITHDRAWN
        assert consent.withdrawal_reason == "Patient request"
    finally:
        ConsentRepository.save = original_save
