import pytest
import io
import zipfile
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from fastapi import status
from app.main import app
from app.api.auth import get_current_user
from app.models.database import (
    Hospital, Staff, RiskAlert, UserRole,
    MaturityLevel, NABHObjective, SeverityLevel, RiskLevel
)
from app.nabh.seeder import seed_nabh_objectives

def _seed_base_hospital(db, hospital_id="hospital-001", name="Test Memorial Hospital"):
    hospital = Hospital(
        id=hospital_id,
        name=name,
        registration_number="REG-" + hospital_id[-3:],
        nabh_edition="6th",
        bed_count=100
    )
    db.add(hospital)
    db.commit()
    return hospital

def _mock_compliance_officer_user(hospital_id="hospital-001"):
    return Staff(
        id="staff-officer",
        hospital_id=hospital_id,
        role=UserRole.COMPLIANCE_OFFICER,
        name="Test Compliance Officer",
        email="compliance@test.com",
        is_active=True
    )

def _mock_super_admin_user():
    return Staff(
        id="staff-admin",
        hospital_id="hospital-001",
        role=UserRole.SUPER_ADMIN,
        name="Super Admin",
        email="admin@test.com",
        is_active=True
    )

@patch("app.nabh.agent.search_policies")
@patch("app.nabh.agent.search_regulations")
def test_seed_and_assess_pipeline(mock_reg, mock_policy, db_session, client):
    """Test seeding and running full assessment via Agent API."""
    mock_reg.return_value = []
    mock_policy.return_value = []
    
    _seed_base_hospital(db_session, "hospital-001")
    
    app.dependency_overrides[get_current_user] = lambda: _mock_compliance_officer_user("hospital-001")
    
    # Trigger assessment endpoint
    response = client.post("/api/nabh/agent/assess/hospital-001")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "assessment" in data
    assert "remediation" in data
    assert data["assessment"]["gaps_count"] > 0
    
    # Check that objectives were seeded in DB
    obj_count = db_session.query(NABHObjective).filter(
        NABHObjective.hospital_id == "hospital-001"
    ).count()
    assert obj_count == 33  # 6th edition standard count
    
    app.dependency_overrides.clear()

def test_roadmap_phase_bucketing(db_session):
    """Test ConsultantAgent's roadmap generation buckets gaps correctly by severity."""
    from app.nabh.agent import ConsultantAgent
    
    _seed_base_hospital(db_session, "hospital-001")
    
    # Add a few manual objectives with different severities and non-existent maturity
    db_session.add_all([
        NABHObjective(
            hospital_id="hospital-001",
            chapter_code="ACC",
            objective_number=1,
            element_letter="a",
            standard_code="ACC-1.a",
            standard_name="Access protocols",
            severity=SeverityLevel.CRITICAL,
            maturity_level=MaturityLevel.NON_EXISTENT
        ),
        NABHObjective(
            hospital_id="hospital-001",
            chapter_code="PC",
            objective_number=1,
            element_letter="a",
            standard_code="PC-1.a",
            standard_name="Patient protocols",
            severity=SeverityLevel.MAJOR,
            maturity_level=MaturityLevel.NON_EXISTENT
        ),
        NABHObjective(
            hospital_id="hospital-001",
            chapter_code="FMS",
            objective_number=1,
            element_letter="a",
            standard_code="FMS.1.a",
            standard_name="Fire drills",
            severity=SeverityLevel.MINOR,
            maturity_level=MaturityLevel.NON_EXISTENT
        )
    ])
    db_session.commit()
    
    agent = ConsultantAgent()
    roadmap_data = agent.generate_roadmap(db_session, "hospital-001", target_months=16)
    
    assert roadmap_data["hospital_id"] == "hospital-001"
    assert roadmap_data["total_gaps"] == 3
    
    roadmap = roadmap_data["roadmap"]
    # Verify critical goes to Phase 1, major to Phase 2, minor to Phase 3
    assert len(roadmap["Phase 1 - Foundation"]["standards"]) == 1
    assert roadmap["Phase 1 - Foundation"]["standards"][0]["code"] == "ACC-1.a"
    
    assert len(roadmap["Phase 2 - Remediation"]["standards"]) == 1
    assert roadmap["Phase 2 - Remediation"]["standards"][0]["code"] == "PC-1.a"
    
    assert len(roadmap["Phase 3 - Monitoring"]["standards"]) == 1
    assert roadmap["Phase 3 - Monitoring"]["standards"][0]["code"] == "FMS.1.a"

def test_daily_brief_top3(db_session, client):
    """Test daily-brief endpoint returns exactly top 3 gaps sorted by severity/maturity."""
    _seed_base_hospital(db_session, "hospital-001")
    
    # Add 5 gaps of different severities and maturities
    db_session.add_all([
        NABHObjective(
            hospital_id="hospital-001",
            chapter_code="ACC",
            objective_number=1,
            element_letter="a",
            standard_code="ACC-1.a",
            standard_name="Critical 1",
            severity=SeverityLevel.CRITICAL,
            maturity_level=MaturityLevel.NON_EXISTENT
        ),
        NABHObjective(
            hospital_id="hospital-001",
            chapter_code="ACC",
            objective_number=2,
            element_letter="a",
            standard_code="ACC-2.a",
            standard_name="Critical 2",
            severity=SeverityLevel.CRITICAL,
            maturity_level=MaturityLevel.AD_HOC
        ),
        NABHObjective(
            hospital_id="hospital-001",
            chapter_code="PC",
            objective_number=1,
            element_letter="a",
            standard_code="PC-1.a",
            standard_name="Major 1",
            severity=SeverityLevel.MAJOR,
            maturity_level=MaturityLevel.NON_EXISTENT
        ),
        NABHObjective(
            hospital_id="hospital-001",
            chapter_code="FMS",
            objective_number=1,
            element_letter="a",
            standard_code="FMS.1.a",
            standard_name="Minor 1",
            severity=SeverityLevel.MINOR,
            maturity_level=MaturityLevel.NON_EXISTENT
        ),
        NABHObjective(
            hospital_id="hospital-001",
            chapter_code="QMS",
            objective_number=1,
            element_letter="a",
            standard_code="QMS-1.a",
            standard_name="Compliant",
            severity=SeverityLevel.CRITICAL,
            maturity_level=MaturityLevel.IMPLEMENTED  # Implemented should not show up as a gap
        )
    ])
    db_session.commit()
    
    app.dependency_overrides[get_current_user] = lambda: _mock_compliance_officer_user("hospital-001")
    
    response = client.get("/api/nabh/agent/daily-brief/hospital-001")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "daily_actions" in data
    actions = data["daily_actions"]
    
    # Must return top 3 gaps
    assert len(actions) == 3
    # Sorted by severity (Critical first)
    assert actions[0]["standard_code"] == "ACC-1.a" # Critical non-existent
    assert actions[1]["standard_code"] == "ACC-2.a" # Critical ad-hoc
    assert actions[2]["standard_code"] == "PC-1.a"  # Major non-existent
    
    app.dependency_overrides.clear()

def test_activity_feed_format(db_session, client):
    """Test activity-feed returns correct layout from RiskAlert entries."""
    _seed_base_hospital(db_session, "hospital-001")
    
    # Seed a couple of RiskAlerts with alert_type="nabh"
    db_session.add_all([
        RiskAlert(
            id="alert-1",
            hospital_id="hospital-001",
            alert_type="nabh",
            title="NABH Gap: FMS-2.a",
            description="Bio-Medical Waste weight discrepancy",
            severity=RiskLevel.CRITICAL,
            is_resolved=False,
            created_at=datetime.utcnow() - timedelta(minutes=5)
        ),
        RiskAlert(
            id="alert-2",
            hospital_id="hospital-001",
            alert_type="nabh",
            title="NABH Gap: PC-1.a",
            description="Patient identification protocol violation",
            severity=RiskLevel.HIGH,
            is_resolved=True,
            created_at=datetime.utcnow() - timedelta(minutes=15)
        )
    ])
    db_session.commit()
    
    app.dependency_overrides[get_current_user] = lambda: _mock_compliance_officer_user("hospital-001")
    
    response = client.get("/api/nabh/agent/activity-feed/hospital-001")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "feed" in data
    feed = data["feed"]
    assert len(feed) == 2
    
    assert feed[0]["standard_code"] == "FMS.2.a"
    assert feed[0]["severity"] == "critical"
    assert feed[0]["status"] == "active"
    
    assert feed[1]["standard_code"] == "PC-1.a"
    assert feed[1]["severity"] == "high"
    assert feed[1]["status"] == "resolved"
    
    app.dependency_overrides.clear()

@patch("app.nabh.agent.search_policies")
@patch("app.nabh.agent.search_regulations")
def test_sop_endpoint_200(mock_reg, mock_policy, db_session, client):
    """Test the SOP drafting endpoint succeeds and returns drafted content."""
    mock_reg.return_value = [{"title": "Regulation mock"}]
    mock_policy.return_value = [{"title": "Policy mock"}]
    
    _seed_base_hospital(db_session, "hospital-001")
    # Seed the 33 objectives for the hospital
    seed_nabh_objectives(db_session, "hospital-001")
    
    app.dependency_overrides[get_current_user] = lambda: _mock_compliance_officer_user("hospital-001")
    
    response = client.get("/api/nabh/agent/sop/hospital-001/FMS-1.a")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["standard_code"] == "FMS.1.a"
    assert "customized_content" in data
    assert len(data["customized_content"]) > 0
    
    app.dependency_overrides.clear()

def test_export_binder_zip(db_session, client):
    """Test that binder exporter returns a valid zip file with manifest.json."""
    _seed_base_hospital(db_session, "hospital-001")
    
    app.dependency_overrides[get_current_user] = lambda: _mock_compliance_officer_user("hospital-001")
    
    response = client.get("/api/nabh/agent/export-binder/hospital-001")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/zip"
    
    # Verify zip format and contents
    zip_bytes = response.content
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        namelist = z.namelist()
        assert "manifest.json" in namelist
        assert any("policy.md" in name for name in namelist)
        
    app.dependency_overrides.clear()

def test_fleet_summary_endpoint(db_session, client):
    """Test that SUPER_ADMIN can request nabh fleet summary of all hospitals."""
    # Seed two hospitals
    _seed_base_hospital(db_session, "hospital-001", "Hospital Alpha")
    _seed_base_hospital(db_session, "hospital-002", "Hospital Beta")
    
    # Seed one objective with critical gap for hospital-001
    db_session.add(NABHObjective(
        hospital_id="hospital-001",
        chapter_code="ACC",
        objective_number=1,
        element_letter="a",
        standard_code="ACC-1.a",
        standard_name="Access protocols",
        severity=SeverityLevel.CRITICAL,
        maturity_level=MaturityLevel.NON_EXISTENT
    ))
    # Seed one objective with implemented level for hospital-002 (so no critical gaps)
    db_session.add(NABHObjective(
        hospital_id="hospital-002",
        chapter_code="ACC",
        objective_number=1,
        element_letter="a",
        standard_code="ACC-1.a",
        standard_name="Access protocols",
        severity=SeverityLevel.CRITICAL,
        maturity_level=MaturityLevel.IMPLEMENTED
    ))
    db_session.commit()
    
    app.dependency_overrides[get_current_user] = _mock_super_admin_user
    
    response = client.get("/api/admin/nabh-fleet-summary")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert len(data) == 2
    
    h1 = next(item for item in data if item["hospital_id"] == "hospital-001")
    h2 = next(item for item in data if item["hospital_id"] == "hospital-002")
    
    assert h1["hospital_name"] == "Hospital Alpha"
    assert h1["critical_gaps_count"] == 1
    assert h1["overall_maturity_avg"] == 0.0
    
    assert h2["hospital_name"] == "Hospital Beta"
    assert h2["critical_gaps_count"] == 0
    assert h2["overall_maturity_avg"] == 3.0
    
    app.dependency_overrides.clear()
