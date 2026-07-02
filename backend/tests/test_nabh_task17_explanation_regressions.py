import pytest
from datetime import datetime
from fastapi import status
from sqlalchemy import text
from app.api.auth import get_current_user
from app.main import app
from app.models.database import (
    KnowledgePublicationStatus,
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement, NABHRequirement, Hospital, Staff,
    HospitalNABHRequirement, EditionStatus, UserRole, ApplicabilityDefault,
    ComplianceStatus, MaturityLevel, EvidenceType, NABHEvidenceRequirement,
    NABHRequirementCitation, NABHSourceDocument, SeverityLevel, EvidenceStatus
)

@pytest.fixture(autouse=True)
def clean_db(db_session):
    # Enable foreign keys
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
    db_session.commit()
    yield

def setup_base_data(db_session, severity=SeverityLevel.MAJOR, default_owner_role="officer", me_desc="Possess Fire NOC."):
    # Hospital A
    hosp_a = Hospital(id="test-hosp-a", name="Hospital A", registration_number="REG-A")
    db_session.add(hosp_a)
    db_session.commit()

    # Staff A
    staff_a = Staff(
        id="staff-a",
        hospital_id=hosp_a.id,
        employee_id="EMP-A",
        name="Staff A",
        role=UserRole.HOSPITAL_ADMIN,
        email="admina@hospitala.com",
        is_active=True
    )
    db_session.add(staff_a)
    db_session.commit()

    # Active Edition 6.0
    ed = NABHEdition(
        id="ed-6.0",
        name="NABH 6th Edition",
        version="6.0",
        status=EditionStatus.ACTIVE,
        effective_date=datetime.utcnow()
    )
    db_session.add(ed)
    db_session.commit()

    # Chapter
    chap = NABHChapter(
        id="chap-fms",
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
        id="std-fms-1",
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
        id="obj-fms-1-a",
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
        id="me-fms-1-a-1",
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
        id="ev-fms-1",
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
        id="doc-fms",
        edition_id=ed.id,
        title="Fire Guide Booklet",
        publisher="National Fire Board",
        edition_version="2026"
    )
    db_session.add(source_doc)
    db_session.commit()

    citation = NABHRequirementCitation(
        id="cit-fms",
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

    return hosp_a, staff_a, me, ev, citation, source_doc, obj, std, chap, ed

def test_requirement_explanation_returns_source_cited_plain_language_response(client, db_session):
    hosp_a, staff_a, me, ev, citation, source_doc, obj, std, chap, ed = setup_base_data(db_session)

    async def get_mock_user():
        return staff_a
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["requirement_id"] == me.id
    assert res["requirement_code"] == me.canonical_code
    assert res["title"] == me.description
    assert res["confidence"] == "source_cited"
    assert "This requirement asks the hospital to ensure" in res["plain_language_explanation"]
    assert "Surveyors use this to verify" in res["why_it_matters"]
    assert len(res["citations"]) == 1
    assert len(res["required_evidence"]) == 1
    assert res["proof_burden_summary"]["mandatory_evidence_count"] == 1

    app.dependency_overrides.clear()

def test_explanation_missing_citation_is_explicit(client, db_session):
    hosp_a, staff_a, me, ev, citation, source_doc, obj, std, chap, ed = setup_base_data(db_session)

    # Delete the citation to simulate missing citation
    db_session.delete(citation)
    db_session.commit()

    async def get_mock_user():
        return staff_a
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["plain_language_explanation"] is None
    assert res["why_it_matters"] is None
    assert res["confidence"] == "missing_citation"
    assert "No citation is available for this requirement." in res["limitations"]

    app.dependency_overrides.clear()

def test_explanation_uses_hospital_state_when_hospital_id_provided(client, db_session):
    hosp_a, staff_a, me, ev, citation, source_doc, obj, std, chap, ed = setup_base_data(db_session)

    h_req = HospitalNABHRequirement(
        hospital_id=hosp_a.id,
        requirement_id=me.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        applicability_reason="Rule-matched.",
        readiness_status=ComplianceStatus.PARTIALLY_COMPLIANT,
        maturity_level=MaturityLevel.DEFINED,
        evidence_status=EvidenceStatus.DRAFT,
        owner_id=staff_a.id,
        due_date=datetime(2026, 12, 31)
    )
    db_session.add(h_req)
    db_session.commit()

    async def get_mock_user():
        return staff_a
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation?hospital_id={hosp_a.id}")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["hospital_state"] is not None
    assert res["hospital_state"]["applicability_status"] == "applicable"
    assert res["hospital_state"]["readiness_status"] == "partially_compliant"
    assert res["hospital_state"]["owner_id"] == staff_a.id
    assert res["hospital_state"]["owner_name"] == staff_a.name
    assert res["hospital_state"]["owner_role"] == "hospital_admin"

    app.dependency_overrides.clear()

def test_explanation_for_cross_hospital_request_is_forbidden(client, db_session):
    hosp_a, staff_a, me, ev, citation, source_doc, obj, std, chap, ed = setup_base_data(db_session)

    # Seed Hospital B and Staff B
    hosp_b = Hospital(id="test-hosp-b", name="Hospital B", registration_number="REG-B")
    db_session.add(hosp_b)
    db_session.commit()

    staff_b = Staff(
        id="staff-b",
        hospital_id=hosp_b.id,
        employee_id="EMP-B",
        name="Staff B",
        role=UserRole.HOSPITAL_ADMIN,
        email="adminb@hospitalb.com",
        is_active=True
    )
    db_session.add(staff_b)
    db_session.commit()

    # Authenticate as Staff B (from Hospital B)
    async def get_mock_user():
        return staff_b
    app.dependency_overrides[get_current_user] = get_mock_user

    # Request explanation of ME belonging to Hospital A -> 403
    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation?hospital_id={hosp_a.id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    app.dependency_overrides.clear()

def test_explanation_staff_owner_lookup_is_safe(client, db_session):
    hosp_a, staff_a, me, ev, citation, source_doc, obj, std, chap, ed = setup_base_data(db_session)

    # Seed Hospital B and Staff B
    hosp_b = Hospital(id="test-hosp-b", name="Hospital B", registration_number="REG-B")
    db_session.add(hosp_b)
    db_session.commit()

    staff_b = Staff(
        id="staff-b",
        hospital_id=hosp_b.id,
        employee_id="EMP-B",
        name="Staff B Owner",
        role=UserRole.COMPLIANCE_OFFICER,
        email="ownerb@hospitalb.com",
        is_active=True
    )
    db_session.add(staff_b)
    db_session.commit()

    # Hospital requirement for Hospital A, but pointing to staff_b of Hospital B (cross-hospital owner configuration)
    h_req = HospitalNABHRequirement(
        hospital_id=hosp_a.id,
        requirement_id=me.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.PARTIALLY_COMPLIANT,
        owner_id=staff_b.id # invalid cross-hospital owner mapping
    )
    db_session.add(h_req)
    db_session.commit()

    async def get_mock_user():
        return staff_a
    app.dependency_overrides[get_current_user] = get_mock_user

    # Query explanation. The system should not expose staff_b's details since it belongs to Hospital B
    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation?hospital_id={hosp_a.id}")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    # The owner name and role should resolve to None (safety fallback), and the global role falls back to the default
    assert res["hospital_state"]["owner_name"] is None
    assert res["hospital_state"]["owner_role"] is None
    assert res["responsible_owner_name"] is None

    app.dependency_overrides.clear()

def test_explanation_uses_active_edition_only(client, db_session):
    hosp_a, staff_a, me, ev, citation, source_doc, obj, std, chap, ed = setup_base_data(db_session)

    # Retire the edition
    ed.retired_at = datetime.utcnow()
    db_session.commit()

    async def get_mock_user():
        return staff_a
    app.dependency_overrides[get_current_user] = get_mock_user

    # Query explanation -> 404 since edition is retired
    response = client.get(f"/api/nabh/ontology/requirements/{me.id}/explanation")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    app.dependency_overrides.clear()
