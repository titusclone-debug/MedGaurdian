import pytest
import io
import zipfile
import json
import csv
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from fastapi import status

from app.main import app
from app.api.auth import get_current_user
from app.models.database import (
    Base, Hospital, Staff, ConsentRecord, BMWLog, License,
    RiskAlert, UserRole, ConsentStatus, BMWCategory,
    LicenseStatus, ComplianceStatus, RiskLevel, MaturityLevel,
    NABHObjective, SeverityLevel
)
from app.nabh.agent import (
    UniversalSemanticStrategy, BMWComplianceStrategy,
    ConsentComplianceStrategy, FireSafetyComplianceStrategy,
    MedicationSafetyStrategy, SurgicalSafetyStrategy,
    AnesthesiaSafetyStrategy, BloodSafetyStrategy,
    HandHygieneStrategy, PatientIdentificationStrategy,
    IncidentCAPAStrategy, InspectorAgent, ConsultantAgent,
    TelemetryContext
)
from app.nabh.binder_exporter import generate_surveyor_binder


def _seed_base_data(db):
    """Seed base hospital, staff, and nabh objectives for tests."""
    hospital = Hospital(
        id="hospital-001",
        name="Test Memorial Hospital",
        registration_number="REG-001",
        nabh_edition="6th",
        bed_count=100
    )
    db.add(hospital)
    
    staff = Staff(
        id="staff-001",
        hospital_id="hospital-001",
        employee_id="EMP001",
        name="Compliance Officer",
        role=UserRole.COMPLIANCE_OFFICER,
        email="compliance@test.com",
        is_active=True
    )
    db.add(staff)
    
    # Seed a few target objectives
    objectives = [
        NABHObjective(
            id="obj-1", hospital_id="hospital-001", chapter_code="PC",
            objective_number=1, element_letter="a", standard_code="PC-1.a",
            standard_name="Patient rights and informed consent",
            severity=SeverityLevel.CRITICAL, maturity_level=MaturityLevel.NON_EXISTENT
        ),
        NABHObjective(
            id="obj-2", hospital_id="hospital-001", chapter_code="FMS",
            objective_number=2, element_letter="a", standard_code="FMS-2.a",
            standard_name="Bio-Medical Waste management",
            severity=SeverityLevel.CRITICAL, maturity_level=MaturityLevel.NON_EXISTENT
        ),
        NABHObjective(
            id="obj-3", hospital_id="hospital-001", chapter_code="FMS",
            objective_number=1, element_letter="a", standard_code="FMS-1.a",
            standard_name="Fire safety drills and NOC",
            severity=SeverityLevel.CRITICAL, maturity_level=MaturityLevel.NON_EXISTENT
        ),
        NABHObjective(
            id="obj-4", hospital_id="hospital-001", chapter_code="ACC",
            objective_number=1, element_letter="a", standard_code="AAC-1.a",
            standard_name="Admission protocols",
            severity=SeverityLevel.MAJOR, maturity_level=MaturityLevel.NON_EXISTENT
        )
    ]
    for obj in objectives:
        db.add(obj)
    db.commit()


def _get_test_context():
    """Create a TelemetryContext for validation checks."""
    return TelemetryContext(
        hospital_id="hospital-001",
        start_date=datetime.utcnow() - timedelta(days=7),
        end_date=datetime.utcnow(),
        thresholds={"weight_deviation_tolerance": 0.05},
        active_staff_roster=["staff-001"]
    )


# ============================================================
# RAG KEYWORD GATE & STALENESS TESTS
# ============================================================

@patch("app.nabh.agent.search_policies")
@patch("app.nabh.agent.search_regulations")
def test_rag_universal_strategy_keyword_gate_pass(mock_reg, mock_pol, db_session):
    _seed_base_data(db_session)
    
    # 1. Mock policy search results (containing all keywords: admission, criteria, protocol, policy)
    mock_pol.return_value = [{
        "content": "This is the St. Mary's patient admission SOP document. It outlines the admission criteria, registration protocol, and clinical triage policy. Approved by: Dr. Sarah Chen. Version 1.0. Date: 2026-01-01.",
        "metadata": {
            "standard_code": "AAC-1.a",
            "hospital_id": "hospital-001",
            "uploaded_at": datetime.utcnow().isoformat()
        }
    }]
    
    # 2. Mock regulations search results (giving distance 0.1 for 90% similarity)
    mock_reg.return_value = [{
        "content": "SOP for patient admission. Requires defined admission criteria...",
        "metadata": {"standard_code": "AAC-1.a"},
        "distance": 0.1,
        "id": "reg-aac-1a"
    }]
    
    strategy = UniversalSemanticStrategy(standard_code="AAC-1.a")
    res = strategy.validate(db_session, _get_test_context())
    
    assert res["maturity_level"] == MaturityLevel.DEFINED
    assert res["metrics"]["keyword_pass"] is True
    assert "PASSED" in res["remediation_plan"]


@patch("app.nabh.agent.search_policies")
@patch("app.nabh.agent.search_regulations")
def test_rag_universal_strategy_keyword_gate_fail(mock_reg, mock_pol, db_session):
    _seed_base_data(db_session)
    
    # Mock policy search results (lacking mandatory keywords for AAC-1.a)
    mock_pol.return_value = [{
        "content": "This is a completely unrelated clinical document outlining general hospital timings and patient visits. Version v1.0. Approved by: Admin. Date: 2026-01-01.",
        "metadata": {
            "standard_code": "AAC-1.a",
            "hospital_id": "hospital-001",
            "uploaded_at": datetime.utcnow().isoformat()
        }
    }]
    
    mock_reg.return_value = [{
        "content": "SOP for patient admission. Requires defined admission criteria...",
        "metadata": {"standard_code": "AAC-1.a"},
        "distance": 0.1,
        "id": "reg-aac-1a"
    }]
    
    strategy = UniversalSemanticStrategy(standard_code="AAC-1.a")
    res = strategy.validate(db_session, _get_test_context())
    
    assert res["maturity_level"] == MaturityLevel.AD_HOC
    assert res["metrics"]["keyword_pass"] is False
    assert "FAILED (Keyword Gate)" in res["remediation_plan"]


@patch("app.nabh.agent.search_policies")
@patch("app.nabh.agent.search_regulations")
def test_rag_universal_strategy_staleness_downgrade(mock_reg, mock_pol, db_session):
    _seed_base_data(db_session)
    
    # Mock stale policy older than 12 months
    stale_date = (datetime.utcnow() - timedelta(days=400)).isoformat()
    mock_pol.return_value = [{
        "content": "This is the St. Mary's patient admission SOP document. It outlines the admission criteria, registration protocol, and clinical triage policy. Approved by: Dr. Sarah Chen. Version 1.0. Date: 2024-01-01.",
        "metadata": {
            "standard_code": "AAC-1.a",
            "hospital_id": "hospital-001",
            "uploaded_at": stale_date
        }
    }]
    
    mock_reg.return_value = [{
        "content": "SOP for patient admission. Requires defined admission criteria...",
        "metadata": {"standard_code": "AAC-1.a"},
        "distance": 0.1,
        "id": "reg-aac-1a"
    }]
    
    strategy = UniversalSemanticStrategy(standard_code="AAC-1.a")
    res = strategy.validate(db_session, _get_test_context())
    
    assert res["maturity_level"] == MaturityLevel.AD_HOC  # Downgraded from Level 2 to Level 1
    assert res["metrics"]["is_stale"] is True
    assert "STALENESS WARNING" in res["remediation_plan"]


# ============================================================
# ZERO-TRUST TELEMETRY STRATEGY TESTS
# ============================================================

def test_bmw_compliance_strategy_scenarios(db_session):
    _seed_base_data(db_session)
    strategy = BMWComplianceStrategy()
    context = _get_test_context()
    
    # Scenario A: No logs
    res = strategy.validate(db_session, context)
    assert res["maturity_level"] == MaturityLevel.NON_EXISTENT
    assert "No Bio-Medical Waste logs" in res["remediation_plan"]
    
    # Scenario B: Logs exist, but temporal consistency fails (less than 6 log days in last week)
    log_date = datetime.utcnow() - timedelta(hours=1)
    bmw_log1 = BMWLog(
        hospital_id="hospital-001", waste_date=log_date, category=BMWCategory.YELLOW,
        weight_kg=10.0, is_properly_segregated=True, is_properly_labeled=True, is_properly_stored=True
    )
    db_session.add(bmw_log1)
    db_session.commit()
    
    res = strategy.validate(db_session, context)
    assert res["maturity_level"] == MaturityLevel.AD_HOC
    assert "BMW logging is inconsistent" in res["remediation_plan"]

    # Scenario C: 7 logs on 7 distinct days, but weight mismatch anomaly
    for i in range(1, 7):
        bmw = BMWLog(
            hospital_id="hospital-001", waste_date=log_date - timedelta(days=i), category=BMWCategory.YELLOW,
            weight_kg=10.0, is_properly_segregated=True, is_properly_labeled=True, is_properly_stored=True
        )
        db_session.add(bmw)
    db_session.commit()
    
    # Force weight mismatch (random mock generator inside validation logic is triggered)
    with patch("random.uniform", return_value=1.10):  # 10% deviation, exceeding threshold 0.05
        res = strategy.validate(db_session, context)
        assert res["maturity_level"] in [MaturityLevel.DEFINED, MaturityLevel.AD_HOC]
        assert "Zero-trust validation failed" in res["remediation_plan"]


def test_consent_compliance_strategy_scenarios(db_session):
    _seed_base_data(db_session)
    strategy = ConsentComplianceStrategy()
    context = _get_test_context()

    # Scenario A: No records
    res = strategy.validate(db_session, context)
    assert res["maturity_level"] == MaturityLevel.NON_EXISTENT

    # Scenario B: Unsigned consent records
    c1 = ConsentRecord(
        hospital_id="hospital-001", patient_id="pat-1", status=ConsentStatus.PENDING,
        purpose="General Treatment", created_at=datetime.utcnow() - timedelta(hours=1)
    )
    db_session.add(c1)
    db_session.commit()
    res = strategy.validate(db_session, context)
    assert res["maturity_level"] == MaturityLevel.AD_HOC  # lacks signatures

    # Scenario C: Cryptographically signed consent records
    c2 = ConsentRecord(
        hospital_id="hospital-001", patient_id="pat-2", status=ConsentStatus.GRANTED,
        purpose="General Treatment", digital_signature="0xabcdef1234567890",
        created_at=datetime.utcnow() - timedelta(hours=1)
    )
    db_session.add(c2)
    db_session.delete(c1)  # delete pending to make 100% compliant
    db_session.commit()
    res = strategy.validate(db_session, context)
    assert res["maturity_level"] == MaturityLevel.MEASURED
    assert "100% of consent records cryptographically sealed" in res["remediation_plan"]


def test_fire_safety_compliance_strategy_scenarios(db_session):
    _seed_base_data(db_session)
    strategy = FireSafetyComplianceStrategy()
    context = _get_test_context()

    # Scenario A: No NOC
    res = strategy.validate(db_session, context)
    assert res["maturity_level"] == MaturityLevel.NON_EXISTENT

    # Scenario B: Expired NOC
    lic = License(
        hospital_id="hospital-001", license_name="Fire NOC", license_type="fire",
        license_number="FS-123", issued_date=datetime.utcnow() - timedelta(days=400),
        expiry_date=datetime.utcnow() - timedelta(days=35), status=LicenseStatus.EXPIRED
    )
    db_session.add(lic)
    db_session.commit()
    res = strategy.validate(db_session, context)
    assert res["maturity_level"] == MaturityLevel.AD_HOC

    # Scenario C: Active NOC, expiring soon
    lic.status = LicenseStatus.ACTIVE
    lic.expiry_date = datetime.utcnow() + timedelta(days=20)
    db_session.commit()
    res = strategy.validate(db_session, context)
    assert res["maturity_level"] == MaturityLevel.DEFINED
    assert "expiring soon" in res["remediation_plan"]


# ============================================================
# SURVEYOR BINDER EXPORTER TESTS
# ============================================================

@patch("app.nabh.binder_exporter.fetch_policy_text")
def test_surveyor_binder_export(mock_fetch, db_session):
    _seed_base_data(db_session)
    mock_fetch.return_value = "# SOP Policy mock content"
    
    # Add mock licenses, consents, and waste logs to have a rich binder
    lic = License(
        hospital_id="hospital-001", license_name="Fire NOC", license_type="fire",
        license_number="FS-123", issued_date=datetime.utcnow() - timedelta(days=100),
        expiry_date=datetime.utcnow() + timedelta(days=200), status=LicenseStatus.ACTIVE
    )
    db_session.add(lic)
    
    c = ConsentRecord(
        hospital_id="hospital-001", patient_id="pat-1", patient_name="pat-1", status=ConsentStatus.GRANTED,
        purpose="General Treatment", digital_signature="0xabcdef1234567890",
        created_at=datetime.utcnow() - timedelta(hours=1)
    )
    db_session.add(c)
    
    bmw = BMWLog(
        hospital_id="hospital-001", waste_date=datetime.utcnow() - timedelta(hours=1), category=BMWCategory.YELLOW,
        weight_kg=5.2, is_properly_segregated=True, is_properly_labeled=True, is_properly_stored=True
    )
    db_session.add(bmw)
    
    db_session.commit()
    
    # Export
    zip_io = generate_surveyor_binder(db_session, "hospital-001")
    assert isinstance(zip_io, io.BytesIO)
    
    # Load ZIP structure
    with zipfile.ZipFile(zip_io, "r") as z:
        namelist = z.namelist()
        
        # Verify folder layouts
        assert "manifest.json" in namelist
        assert "Chapter_PC/policy.md" in namelist
        assert "Chapter_PC/telemetry.csv" in namelist
        assert "Chapter_PC/monitoring.json" in namelist
        assert "Chapter_PC/cqi.json" in namelist
        assert "Chapter_FMS/telemetry.csv" in namelist
        
        # Verify manifest JSON details
        manifest_content = z.read("manifest.json").decode("utf-8")
        manifest = json.loads(manifest_content)
        assert manifest["hospital_id"] == "hospital-001"
        assert manifest["nabh_edition"] == "6th"
        assert "Chapter_PC/policy.md" in manifest["files"]
        
        # Verify SHA-256 integrity check
        policy_content = z.read("Chapter_PC/policy.md")
        expected_hash = hashlib.sha256(policy_content).hexdigest()
        assert manifest["files"]["Chapter_PC/policy.md"] == expected_hash

        # Verify telemetry log parsing
        telemetry_content = z.read("Chapter_PC/telemetry.csv").decode("utf-8")
        csv_reader = csv.reader(io.StringIO(telemetry_content))
        rows = list(csv_reader)
        # Header + at least one consent row
        assert len(rows) > 1
        assert rows[1][0] == "PC-1.a"
        assert "pat-1" in rows[1][4]


# ============================================================
# API INTEGRATION TEST
# ============================================================

@patch("app.nabh.binder_exporter.fetch_policy_text")
def test_api_export_binder_endpoint(mock_fetch, client, db_session):
    _seed_base_data(db_session)
    mock_fetch.return_value = "# SOP Policy mock content"
    
    # Override current user mock
    async def mock_user():
        return Staff(
            id="staff-001",
            hospital_id="hospital-001",
            role=UserRole.COMPLIANCE_OFFICER,
            name="Test User",
            email="test@test.com",
            is_active=True
        )
    app.dependency_overrides[get_current_user] = mock_user

    # Request export-binder
    response = client.get("/api/nabh/agent/export-binder/hospital-001")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/zip"
    assert "attachment; filename=Surveyor_Binder_hospital-001.zip" in response.headers["content-disposition"]

    # Verify zip content
    zip_bytes = response.content
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        assert "manifest.json" in z.namelist()
        assert "Chapter_ACC/policy.md" in z.namelist()
        
    app.dependency_overrides.clear()
