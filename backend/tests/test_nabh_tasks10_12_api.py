import pytest
from datetime import datetime
from fastapi import status
from sqlalchemy import text

from app.api.auth import get_current_user
from app.main import app
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement, NABHRequirementCitation,
    NABHEvidenceRequirement, Hospital, Staff, HospitalAccreditationProfile,
    HospitalNABHRequirement, HospitalRequirementEvidenceLink,
    EditionStatus, ProfileStatus, UserRole, ApplicabilityDefault,
    MaturityLevel, EvidenceStatus, ComplianceStatus, EvidenceType,
    NABHObjective
)

@pytest.fixture(autouse=True)
def clean_db(db_session):
    # Enable foreign keys
    db_session.execute(text("PRAGMA foreign_keys=ON"))

    # Clean tables
    db_session.query(HospitalRequirementEvidenceLink).delete()
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHRequirementCitation).delete()
    db_session.query(NABHEvidenceRequirement).delete()
    db_session.query(NABHMeasurableElement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.query(HospitalAccreditationProfile).delete()
    db_session.query(Staff).delete()
    db_session.query(Hospital).delete()
    db_session.query(NABHObjective).delete()
    db_session.commit()
    yield

def test_nabh_tasks10_12_api_suite(client, db_session):
    # 1. Setup Test Data
    # Base Hospitals
    hosp1 = Hospital(id="test-hosp-1", name="Hospital One", registration_number="REG-01")
    hosp2 = Hospital(id="test-hosp-2", name="Hospital Two", registration_number="REG-02")
    db_session.add_all([hosp1, hosp2])
    db_session.commit()

    # Staff / Users
    staff_h1 = Staff(
        id="staff-h1",
        hospital_id=hosp1.id,
        employee_id="EMP-H1",
        name="Hosp 1 Admin",
        role=UserRole.HOSPITAL_ADMIN,
        email="admin1@hosp1.com",
        is_active=True
    )
    staff_h2 = Staff(
        id="staff-h2",
        hospital_id=hosp2.id,
        employee_id="EMP-H2",
        name="Hosp 2 User",
        role=UserRole.COMPLIANCE_OFFICER,
        email="user2@hosp2.com",
        is_active=True
    )
    super_admin = Staff(
        id="staff-super",
        hospital_id=hosp1.id,
        employee_id="EMP-SUP",
        name="Super Admin User",
        role=UserRole.SUPER_ADMIN,
        email="super@system.com",
        is_active=True
    )
    db_session.add_all([staff_h1, staff_h2, super_admin])
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
        official_standards_count=2,
        official_measurable_elements_count=5
    )
    db_session.add(chap)
    db_session.commit()

    # Standard
    std = NABHStandard(
        id="std-fms-1",
        edition_id=ed.id,
        chapter_id=chap.id,
        code="FMS-1",
        canonical_code="FMS-1",
        title="Fire Safety Standard"
    )
    db_session.add(std)
    db_session.commit()

    # Objective Element
    obj = NABHObjectiveElement(
        id="obj-fms-1.a",
        edition_id=ed.id,
        standard_id=std.id,
        code="a",
        canonical_code="FMS-1.a",
        description="Verify fire clearance and NOC requirements."
    )
    db_session.add(obj)
    db_session.commit()

    # Measurable Elements (Requirements)
    me1 = NABHMeasurableElement(
        id="me-fms-1.a.1",
        edition_id=ed.id,
        objective_element_id=obj.id,
        code="1",
        canonical_code="FMS-1.a.1",
        description="Check validity of NOC clearance.",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    me2 = NABHMeasurableElement(
        id="me-fms-1.a.2",
        edition_id=ed.id,
        objective_element_id=obj.id,
        code="2",
        canonical_code="FMS-1.a.2",
        description="Verify fire drills conducted.",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    db_session.add_all([me1, me2])
    db_session.commit()

    # Citation & Evidence for ME 1
    cit1 = NABHRequirementCitation(
        id="cit-fms-1.a.1",
        measurable_element_id=me1.id,
        document_id=None,
        section="Clause 5.2",
        clause_text_summary="Fire NOC must be renewed annually."
    )
    ev1 = NABHEvidenceRequirement(
        id="ev-fms-1.a.1",
        measurable_element_id=me1.id,
        evidence_type=EvidenceType.LICENSE,
        description="Annual Fire NOC Document",
        is_mandatory=True
    )
    db_session.add_all([cit1, ev1])
    db_session.commit()

    # Setup standard default dependency override to staff_h1 (Hosp 1)
    async def get_h1_user_override():
        return staff_h1
    
    app.dependency_overrides[get_current_user] = get_h1_user_override

    # ============================================================
    # TASK 10: ONTOLOGY APIs TESTS
    # ============================================================
    
    # A. GET /api/nabh/ontology/editions
    response = client.get("/api/nabh/ontology/editions")
    assert response.status_code == status.HTTP_200_OK
    editions = response.json()
    assert len(editions) == 1
    assert editions[0]["version"] == "6.0"

    # B. GET /api/nabh/ontology/chapters
    response = client.get("/api/nabh/ontology/chapters?edition_version=6.0")
    assert response.status_code == status.HTTP_200_OK
    chapters = response.json()
    assert len(chapters) == 1
    assert chapters[0]["code"] == "FMS"

    # GET /api/nabh/ontology/chapters for invalid version
    response = client.get("/api/nabh/ontology/chapters?edition_version=99.0")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # C. GET /api/nabh/ontology/requirements
    response = client.get("/api/nabh/ontology/requirements?edition_version=6.0")
    assert response.status_code == status.HTTP_200_OK
    res_req = response.json()
    assert res_req["total"] == 2
    assert len(res_req["items"]) == 2
    assert res_req["items"][0]["canonical_code"] == "FMS-1.a.1"
    assert res_req["items"][0]["chapter_code"] == "FMS"

    # D. GET /api/nabh/ontology/requirements/{requirement_id}
    response = client.get(f"/api/nabh/ontology/requirements/{me1.id}")
    assert response.status_code == status.HTTP_200_OK
    detail = response.json()
    assert detail["canonical_code"] == "FMS-1.a.1"
    assert detail["has_citation"] is True
    assert detail["has_evidence_requirements"] is True
    assert len(detail["citations"]) == 1
    assert len(detail["evidence_requirements"]) == 1
    assert detail["citations"][0]["section"] == "Clause 5.2"

    # Invalid ID detail
    response = client.get("/api/nabh/ontology/requirements/missing-id")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # E. GET /api/nabh/ontology/citations/{citation_id}
    # Standard CitationService retrieves details based on database tables. We mock or test it:
    response = client.get(f"/api/nabh/ontology/citations/{cit1.id}")
    # Since CitationService expects NABHSourceDocument to join (as an outer join/join), let's see.
    # Note: CitationService get_citation_by_id has joins on:
    # NABHSourceDocument (outer), NABHMeasurableElement, NABHObjectiveElement, NABHStandard, NABHChapter.
    # We did insert them all, but did not seed a source document with ID 'doc-ref-1'.
    # Because of outerjoin it should still work fine!
    assert response.status_code == status.HTTP_200_OK
    cit_detail = response.json()
    assert cit_detail["id"] == cit1.id
    assert cit_detail["section"] == "Clause 5.2"
    
    # Missing citation
    response = client.get("/api/nabh/ontology/citations/missing-cit")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # ============================================================
    # TASK 11: HOSPITAL PROFILE APIs TESTS
    # ============================================================
    
    # A. GET /api/nabh/profile/{hospital_id} (missing profile -> default shape)
    response = client.get(f"/api/nabh/profile/{hosp1.id}")
    assert response.status_code == status.HTTP_200_OK
    profile_data = response.json()
    assert profile_data["exists"] is False
    assert profile_data["profile_status"] == "draft"
    assert profile_data["bed_count"] == 0

    # B. PUT /api/nabh/profile/{hospital_id} (create profile)
    payload = {
        "bed_count": 80,
        "hospital_type": "Eye Specialty",
        "profile_status": "complete",
        "services_offered": ["ophthalmology", "general_surgery"],
        "has_operation_theatre": True,
        "has_icu": False
    }
    response = client.put(f"/api/nabh/profile/{hosp1.id}", json=payload)
    assert response.status_code == status.HTTP_200_OK
    profile_data = response.json()
    assert profile_data["exists"] is True
    assert profile_data["bed_count"] == 80
    assert profile_data["has_operation_theatre"] is True
    assert profile_data["has_icu"] is False
    assert "ophthalmology" in profile_data["services_offered"]

    # Try putting extra fields (ConfigDict extra="forbid" verification)
    response = client.put(f"/api/nabh/profile/{hosp1.id}", json={**payload, "invalid_field": "error"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Negative profile volume/capacity values should be rejected
    response = client.put(f"/api/nabh/profile/{hosp1.id}", json={"bed_count": -1})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response = client.put(f"/api/nabh/profile/{hosp1.id}", json={"annual_patient_volume": -10})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # GET profile now that it exists
    response = client.get(f"/api/nabh/profile/{hosp1.id}")
    assert response.status_code == status.HTTP_200_OK
    profile_data = response.json()
    assert profile_data["exists"] is True
    assert profile_data["bed_count"] == 80

    # C. POST /api/nabh/profile/{hospital_id}/compute-applicability
    response = client.post(f"/api/nabh/profile/{hosp1.id}/compute-applicability")
    assert response.status_code == status.HTTP_200_OK
    comp_res = response.json()
    assert comp_res["total_requirements_evaluated"] == 2
    assert comp_res["created_rows_count"] == 2
    assert comp_res["updated_rows_count"] == 0

    # Idempotency: second run should not duplicate
    response = client.post(f"/api/nabh/profile/{hosp1.id}/compute-applicability")
    assert response.status_code == status.HTTP_200_OK
    comp_res = response.json()
    assert comp_res["created_rows_count"] == 0
    assert comp_res["unchanged_rows_count"] == 2

    # Verify rows exist in DB
    db_reqs = db_session.query(HospitalNABHRequirement).filter(HospitalNABHRequirement.hospital_id == hosp1.id).all()
    assert len(db_reqs) == 2

    # ============================================================
    # TASK 12: REQUIREMENT-STATE APIs TESTS
    # ============================================================
    
    # A. GET /api/nabh/requirements/{hospital_id}
    response = client.get(f"/api/nabh/requirements/{hosp1.id}")
    assert response.status_code == status.HTTP_200_OK
    req_list = response.json()
    assert req_list["total"] == 2
    assert len(req_list["items"]) == 2
    assert req_list["items"][0]["requirement_code"] == "FMS-1.a.1"
    assert req_list["items"][0]["maturity_level"] == 0 # default starting value: MaturityLevel.NON_EXISTENT

    # Filter by chapter
    response = client.get(f"/api/nabh/requirements/{hosp1.id}?chapter_code=FMS")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total"] == 2

    response = client.get(f"/api/nabh/requirements/{hosp1.id}?chapter_code=AAC")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total"] == 0

    # B. GET /api/nabh/requirements/{hospital_id}/{requirement_id}
    response = client.get(f"/api/nabh/requirements/{hosp1.id}/{me1.id}")
    assert response.status_code == status.HTTP_200_OK
    req_detail = response.json()
    assert req_detail["requirement_id"] == me1.id
    assert req_detail["applicability_status"] == "applicable"
    assert req_detail["ontology_requirement"]["canonical_code"] == "FMS-1.a.1"

    # Try state details of non-existent requirement for Hosp 1
    response = client.get(f"/api/nabh/requirements/{hosp1.id}/missing-req-id")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # C. PATCH /api/nabh/requirements/{hospital_id}/{requirement_id}
    patch_payload = {
        "maturity_level": 3, # IMPLEMENTED
        "evidence_status": "verified",
        "readiness_status": "compliant"
    }
    response = client.patch(f"/api/nabh/requirements/{hosp1.id}/{me1.id}", json=patch_payload)
    assert response.status_code == status.HTTP_200_OK
    patched_detail = response.json()
    assert patched_detail["maturity_level"] == 3
    assert patched_detail["evidence_status"] == "verified"
    assert patched_detail["readiness_status"] == "compliant"

    # Verify DB update
    req_db = db_session.query(HospitalNABHRequirement).filter(
        HospitalNABHRequirement.hospital_id == hosp1.id,
        HospitalNABHRequirement.requirement_id == me1.id
    ).first()
    assert req_db.maturity_level == MaturityLevel.IMPLEMENTED

    # Try patching forbidden field or extra field
    response = client.patch(f"/api/nabh/requirements/{hosp1.id}/{me1.id}", json={"applicability_status": "not_applicable"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    response = client.patch(f"/api/nabh/requirements/{hosp1.id}/{me1.id}", json={"non_existent_field": "error"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Owner/reviewer references must stay inside the same hospital tenant
    response = client.patch(f"/api/nabh/requirements/{hosp1.id}/{me1.id}", json={"owner_id": staff_h2.id})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response = client.patch(f"/api/nabh/requirements/{hosp1.id}/{me1.id}", json={"last_reviewed_by": staff_h2.id})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    response = client.patch(f"/api/nabh/requirements/{hosp1.id}/{me1.id}", json={"owner_id": staff_h1.id})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["owner_id"] == staff_h1.id

    # ============================================================
    # ACCESS CONTROL (RBAC) TESTS
    # ============================================================
    
    # Switch authenticated user override to staff_h2 (who belongs to test-hosp-2)
    async def get_h2_user_override():
        return staff_h2
    
    app.dependency_overrides[get_current_user] = get_h2_user_override

    # Querying Hosp 1's profile from Hosp 2 user should return 403 Forbidden
    response = client.get(f"/api/nabh/profile/{hosp1.id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Querying Hosp 1's requirements from Hosp 2 user should return 403
    response = client.get(f"/api/nabh/requirements/{hosp1.id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Querying Hosp 2's requirements detail (non-computed state) from Hosp 2 user should return 404 Not Found
    response = client.get(f"/api/nabh/requirements/{hosp2.id}/{me1.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Switch authenticated user override to super_admin (who has access to everything)
    async def get_super_user_override():
        return super_admin
    
    app.dependency_overrides[get_current_user] = get_super_user_override

    # Super Admin querying Hosp 1's profile should succeed
    response = client.get(f"/api/nabh/profile/{hosp1.id}")
    assert response.status_code == status.HTTP_200_OK

    # ============================================================
    # LEGACY STABILITY CHECK
    # ============================================================
    # Seed a legacy row
    legacy_obj = NABHObjective(
        id="legacy-api-1",
        hospital_id=hosp1.id,
        chapter_code="HIC",
        objective_number=1,
        element_letter="a",
        standard_code="HIC 1",
        standard_name="Legacy Standard"
    )
    db_session.add(legacy_obj)
    db_session.commit()

    # Querying requirements lists should NOT contain or be affected by this legacy row
    response = client.get(f"/api/nabh/requirements/{hosp1.id}")
    assert response.status_code == status.HTTP_200_OK
    req_list_data = response.json()
    assert req_list_data["total"] == 2
    for item in req_list_data["items"]:
        assert item["chapter_code"] != "HIC"
        assert item["requirement_code"] != "HIC 1"

    # Retired ontology requirements should not be accessible through state detail/patch APIs
    me2.retired_at = datetime.utcnow()
    db_session.add(me2)
    db_session.commit()

    response = client.get(f"/api/nabh/ontology/requirements/{me2.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = client.get(f"/api/nabh/requirements/{hosp1.id}/{me2.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = client.patch(f"/api/nabh/requirements/{hosp1.id}/{me2.id}", json={"evidence_status": "verified"})
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Clean up overrides
    app.dependency_overrides.pop(get_current_user, None)
