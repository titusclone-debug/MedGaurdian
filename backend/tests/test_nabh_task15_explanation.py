import pytest
from datetime import datetime
from fastapi import status
from sqlalchemy import text

from app.api.auth import get_current_user
from app.main import app
from app.models.database import (
    KnowledgePublicationStatus,
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement, NABHRequirement, NABHObjective,
    Hospital, Staff, HospitalNABHRequirement, ComplianceRecord,
    EditionStatus, UserRole, ApplicabilityDefault, ComplianceStatus,
    MaturityLevel, EvidenceType, NABHEvidenceRequirement,
    NABHRequirementCitation, NABHSourceDocument, SeverityLevel,
    EvidenceStatus
)

@pytest.fixture(autouse=True)
def clean_db(db_session):
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHEvidenceRequirement).delete()
    db_session.query(NABHRequirementCitation).delete()
    db_session.query(NABHSourceDocument).delete()
    db_session.query(NABHRequirement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.query(Staff).delete()
    db_session.query(Hospital).delete()
    db_session.query(NABHObjective).delete()
    db_session.query(ComplianceRecord).delete()
    db_session.commit()
    yield

def create_setup_data(db_session, severity=SeverityLevel.MAJOR, default_owner_role="officer", me_desc="Possess NOC."):
    hosp = Hospital(id="test-hosp-15", name="Hospital 15", registration_number="REG-15")
    db_session.add(hosp)
    db_session.commit()

    staff = Staff(
        id="staff-15",
        hospital_id=hosp.id,
        employee_id="EMP-15",
        name="Staff 15 Owner",
        role=UserRole.HOSPITAL_ADMIN,
        email="owner15@hospital.com",
        is_active=True
    )
    db_session.add(staff)
    db_session.commit()

    ed = NABHEdition(
        id="ed-6.0-test15",
        name="NABH 6th Edition",
        version="6.0",
        status=EditionStatus.ACTIVE,
        effective_date=datetime.utcnow()
    )
    db_session.add(ed)
    db_session.commit()

    # Chapter
    chap = NABHChapter(
        id="chap-fms-test15",
        edition_id=ed.id,
        code="FMS",
        canonical_code="FMS",
        title="Facility Management and Safety",
        display_order=1,
        official_standards_count=1,
        official_measurable_elements_count=1
    )
    db_session.add(chap)
    db_session.commit()

    # Standard
    std = NABHStandard(
        id="std-fms-1-test15",
        edition_id=ed.id,
        chapter_id=chap.id,
        code="1",
        canonical_code="FMS.1",
        title="Standard FMS-1"
    )
    db_session.add(std)
    db_session.commit()

    # Objective
    obj = NABHObjectiveElement(
        id="obj-fms-1-a-test15",
        edition_id=ed.id,
        standard_id=std.id,
        code="a",
        canonical_code="FMS.1.a",
        description="Objective FMS-1.a",
        severity=severity
    )
    db_session.add(obj)
    db_session.commit()

    # Measurable Element
    me = NABHRequirement(
        id="me-fms-1-a-1-test15",
        edition_id=ed.id,
        standard_id=std.id,
        official_code="FMS 1.a.1",
        canonical_code="FMS.1.a.1",
        display_text=me_desc,
        applicability_default=ApplicabilityDefault.APPLICABLE,
        default_owner_role=default_owner_role,
        publication_status=KnowledgePublicationStatus.PUBLISHED,
        source_status="official_verified")
    db_session.add(me)
    db_session.commit()

    # Evidence Requirements
    ev = NABHEvidenceRequirement(
        id="ev-id-15",
        requirement_id=me.id,
        evidence_code="FMS.1.a.1.EV.01",
        evidence_type=EvidenceType.LICENSE,
        description="Fire safety license.",
        suggested_documentation="Original NOC certificate.",
        is_mandatory=True,
        evidence_frequency="yearly",
        minimum_lookback_days=365,
        default_owner_role="facility_director"
    )
    db_session.add(ev)
    db_session.commit()

    # Source Doc and Citation
    source_doc = NABHSourceDocument(
        id="doc-test15",
        edition_id=ed.id,
        title="Fire Guide Booklet",
        publisher="National Fire Board",
        edition_version="2026"
    )
    db_session.add(source_doc)
    db_session.commit()

    citation = NABHRequirementCitation(
        id="cit-test15",
        requirement_id=me.id,
        document_id=source_doc.id,
        section="Sec A",
        page_number="45",
        clause_text_summary="This fire guideline is critical.",
        effective_date=datetime(2026, 1, 1),
        file_path="/excerpts/fire_book.pdf"
    )
    db_session.add(citation)
    db_session.commit()

    return hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed


def test_explanation_cited_requirement_success(client, db_session):
    """Succeeds in explaining a cited requirement with evidence, summaries, and default owners."""
    hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed = create_setup_data(db_session)

    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["requirement_id"] == me.id
    assert res["requirement_code"] == me.canonical_code
    assert res["title"] == me.description
    
    # Plain Language formula check
    explanation = res["plain_language_explanation"]
    assert "This requirement asks the hospital to ensure: Possess NOC." in explanation
    assert "It belongs to FMS: Facility Management and Safety, under standard FMS-1: Standard FMS-1." in explanation
    assert "For survey readiness, the hospital must be able to show current, reviewable evidence." in explanation

    # Why-it-matters fallback check (since it is MAJOR severity by default)
    assert res["why_it_matters"] == "Surveyors use this to verify that the stated process is documented, assigned, and supported by evidence."

    # Evidence details
    assert len(res["required_evidence"]) == 1
    assert res["required_evidence"][0]["evidence_code"] == ev.evidence_code
    assert res["required_evidence"][0]["suggested_documentation"] == "Original NOC certificate."
    
    # Proof Burden Summary
    assert res["proof_burden_summary"]["mandatory_evidence_count"] == 1
    assert res["proof_burden_summary"]["optional_evidence_count"] == 0
    assert res["proof_burden_summary"]["evidence_types_required"] == ["license"]
    assert res["proof_burden_summary"]["lookback_days_required"] == 365

    # Citation details
    assert len(res["citations"]) == 1
    assert res["citations"][0]["document_title"] == "Fire Guide Booklet"
    assert res["citations"][0]["section"] == "Sec A"
    assert res["citations"][0]["file_path"] == "/excerpts/fire_book.pdf"

    # Default Owner (dominant role is facility_director from evidence)
    assert res["responsible_role"] == "facility_director"
    assert res["confidence"] == "source_cited"
    assert res["hospital_state"] is None
    assert len(res["limitations"]) == 0

    app.dependency_overrides.clear()


def test_explanation_critical_severity_why_it_matters(client, db_session):
    """Why-it-matters customizes for critical severity based on safety keywords."""
    # Seed a critical fire safety requirement
    hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed = create_setup_data(
        db_session, severity=SeverityLevel.CRITICAL, me_desc="Possess Fire NOC Certificate."
    )

    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()
    assert "critical for fire safety" in res["why_it_matters"]

    app.dependency_overrides.clear()


def test_explanation_missing_citation_degraded_response(client, db_session):
    """Returns a valid degraded response when citation is missing, without 500 error."""
    hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed = create_setup_data(db_session)
    
    # Delete the citation to simulate missing citation
    db_session.delete(citation)
    db_session.commit()

    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["plain_language_explanation"] is None
    assert res["why_it_matters"] is None
    assert res["confidence"] == "missing_citation"
    assert "No citation is available for this requirement." in res["limitations"]

    app.dependency_overrides.clear()


def test_explanation_hospital_specific_context(client, db_session):
    """Integrates hospital-specific state, Staff owner name/role details when hospital_id is provided."""
    hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed = create_setup_data(db_session)

    # Seed hospital specific requirement state
    hosp_req = HospitalNABHRequirement(
        hospital_id=hosp.id,
        requirement_id=me.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        applicability_reason="Mandatory NOC required.",
        readiness_status=ComplianceStatus.PARTIALLY_COMPLIANT,
        maturity_level=MaturityLevel.DEFINED,
        evidence_status=EvidenceStatus.DRAFT,
        owner_id=staff.id,
        due_date=datetime(2026, 12, 31)
    )
    db_session.add(hosp_req)
    db_session.commit()

    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    # Query with hospital_id
    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation?hospital_id={hosp.id}")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["hospital_state"] is not None
    assert res["hospital_state"]["applicability_status"] == "applicable"
    assert res["hospital_state"]["readiness_status"] == "partially_compliant"
    assert res["hospital_state"]["maturity_level"] == 2
    assert res["hospital_state"]["evidence_status"] == "draft"
    assert res["hospital_state"]["owner_id"] == staff.id
    
    # Staff details returned
    assert res["hospital_state"]["owner_name"] == staff.name
    assert res["hospital_state"]["owner_role"] == "hospital_admin"

    # Global responsible_role resolved as the assigned staff's role
    assert res["responsible_role"] == "hospital_admin"
    assert res["responsible_owner_id"] == staff.id
    assert res["responsible_owner_name"] == staff.name

    app.dependency_overrides.clear()


def test_explanation_uncomputed_hospital_state_limitation(client, db_session):
    """Appends limitation if hospital_id is provided but no state exists in database."""
    hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed = create_setup_data(db_session)

    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation?hospital_id={hosp.id}")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["hospital_state"] is None
    assert "Hospital-specific requirement state has not been computed yet." in res["limitations"]

    app.dependency_overrides.clear()


def test_explanation_multiple_evidence_roles(client, db_session):
    """Sets responsible_role to 'multiple' and returns all default_owner_role values if they differ."""
    hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed = create_setup_data(db_session)

    # Seed a second evidence requirement with different default role
    ev2 = NABHEvidenceRequirement(
        id="ev-id-15-second",
        requirement_id=me.id,
        evidence_code="FMS.1.a.1.EV.02",
        evidence_type=EvidenceType.PHOTO,
        description="Fire safety photo proof.",
        is_mandatory=False,
        evidence_frequency="yearly",
        minimum_lookback_days=180,
        default_owner_role="infection_control_officer"
    )
    db_session.add(ev2)
    db_session.commit()

    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["responsible_role"] == "multiple"
    assert set(res["responsible_roles"]) == {"facility_director", "infection_control_officer"}

    app.dependency_overrides.clear()


def test_explanation_retired_requirement_raises_404(client, db_session):
    """Raises 404 Not Found if the requested requirement is retired."""
    hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed = create_setup_data(db_session)
    
    # Retire the measurable element
    me.retired_at = datetime.utcnow()
    db_session.commit()

    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    app.dependency_overrides.clear()


def test_explanation_rbac_access_control(client, db_session):
    """Returns 403 Forbidden if a hospital staff attempts to query explanation with another hospital_id."""
    hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed = create_setup_data(db_session)

    # Seed another staff belonging to a different hospital
    hosp_other = Hospital(id="test-hosp-other", name="Other Hospital", registration_number="REG-OTHER")
    db_session.add(hosp_other)
    db_session.commit()

    staff_other = Staff(
        id="staff-other",
        hospital_id=hosp_other.id,
        employee_id="EMP-OTHER",
        name="Other Staff",
        role=UserRole.HOSPITAL_ADMIN,
        email="other@hospital.com",
        is_active=True
    )
    db_session.add(staff_other)
    db_session.commit()

    # Authenticate as staff_other (hospital "test-hosp-other")
    async def get_mock_user():
        return staff_other
    app.dependency_overrides[get_current_user] = get_mock_user

    # Query explanation requesting hospital_id of the first hospital ("test-hosp-15") -> 403
    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation?hospital_id={hosp.id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    app.dependency_overrides.clear()


def test_legacy_rows_ignored_in_explanation(client, db_session):
    """Legacy model rows do not interfere with explanation counts or data lookup."""
    hosp, staff, me, ev, citation, source_doc, obj, std, chap, ed = create_setup_data(db_session)

    # Seed legacy models
    legacy_rec = ComplianceRecord(
        id="legacy-rec-id-15",
        hospital_id=hosp.id,
        standard_code="FMS.1.a",
        standard_name="Legacy Standard",
        status=ComplianceStatus.COMPLIANT
    )
    db_session.add(legacy_rec)

    legacy_obj = NABHObjective(
        id="legacy-obj-id-15",
        hospital_id=hosp.id,
        chapter_code="FMS",
        objective_number=1,
        element_letter="a",
        standard_code="FMS.1.a",
        standard_name="Legacy Objective Standard",
        maturity_level=MaturityLevel.IMPLEMENTED
    )
    db_session.add(legacy_obj)
    db_session.commit()

    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()
    assert res["proof_burden_summary"]["mandatory_evidence_count"] == 1

    app.dependency_overrides.clear()
