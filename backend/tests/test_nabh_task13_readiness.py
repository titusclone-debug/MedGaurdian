import pytest
from datetime import datetime
from fastapi import status
from sqlalchemy import text

from app.api.auth import get_current_user
from app.main import app
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement, NABHObjective,
    Hospital, Staff, HospitalNABHRequirement, ComplianceRecord,
    EditionStatus, UserRole, ApplicabilityDefault, ComplianceStatus,
    MaturityLevel
)

@pytest.fixture(autouse=True)
def clean_db(db_session):
    # Enable foreign keys
    db_session.execute(text("PRAGMA foreign_keys=ON"))

    # Clean tables
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHMeasurableElement).delete()
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

def create_base_data(db_session):
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

    return hosp1, hosp2, staff_h1, staff_h2, super_admin, ed

def seed_chapter_std_obj_me(db_session, ed, chap_code, std_code, obj_code, me_code, me_id=None, app_def=ApplicabilityDefault.APPLICABLE):
    chap = db_session.query(NABHChapter).filter_by(edition_id=ed.id, canonical_code=chap_code).first()
    if not chap:
        chap = NABHChapter(
            id=f"chap-{chap_code.lower()}",
            edition_id=ed.id,
            code=chap_code,
            canonical_code=chap_code,
            title=f"Chapter {chap_code}",
            display_order=1 if chap_code == "FMS" else 2,
            official_standards_count=2,
            official_measurable_elements_count=5
        )
        db_session.add(chap)
        db_session.commit()

    std = db_session.query(NABHStandard).filter_by(edition_id=ed.id, canonical_code=std_code).first()
    if not std:
        std = NABHStandard(
            id=f"std-{std_code.lower()}",
            edition_id=ed.id,
            chapter_id=chap.id,
            code=std_code.split("-")[-1],
            canonical_code=std_code,
            title=f"Standard {std_code}"
        )
        db_session.add(std)
        db_session.commit()

    obj = db_session.query(NABHObjectiveElement).filter_by(edition_id=ed.id, canonical_code=obj_code).first()
    if not obj:
        obj = NABHObjectiveElement(
            id=f"obj-{obj_code.lower()}",
            edition_id=ed.id,
            standard_id=std.id,
            code=obj_code.split(".")[-1],
            canonical_code=obj_code,
            description=f"Objective {obj_code}"
        )
        db_session.add(obj)
        db_session.commit()

    me = NABHMeasurableElement(
        id=me_id or f"me-{me_code.lower()}",
        edition_id=ed.id,
        objective_element_id=obj.id,
        code=me_code.split(".")[-1],
        canonical_code=me_code,
        description=f"Measurable {me_code}",
        applicability_default=app_def
    )
    db_session.add(me)
    db_session.commit()
    return chap, std, obj, me

def test_no_state_rows(client, db_session):
    hosp1, _, staff_h1, _, _, ed = create_base_data(db_session)
    async def get_h1_user():
        return staff_h1
    app.dependency_overrides[get_current_user] = get_h1_user

    # No state rows exist for hospital 1
    response = client.get(f"/api/nabh/readiness/{hosp1.id}?edition_version=6.0")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()
    assert res["hospital_id"] == hosp1.id
    assert res["edition_version"] == "6.0"
    assert res["status"] == "not_scoped"
    assert res["total_state_rows"] == 0
    assert res["denominator"] == 0
    assert res["ready_count"] == 0
    assert res["readiness_score_percent"] is None
    assert res["calculated_at"] is not None
    assert res["generated_at"] is not None
    
    app.dependency_overrides.clear()

def test_denominator_and_numerator_calculation(client, db_session):
    hosp1, _, staff_h1, _, _, ed = create_base_data(db_session)
    async def get_h1_user():
        return staff_h1
    app.dependency_overrides[get_current_user] = get_h1_user

    # Seed 5 requirements in MOM chapter
    _, _, _, me1 = seed_chapter_std_obj_me(db_session, ed, "MOM", "MOM-1", "MOM-1.a", "MOM-1.a.1")
    _, _, _, me2 = seed_chapter_std_obj_me(db_session, ed, "MOM", "MOM-1", "MOM-1.a", "MOM-1.a.2")
    _, _, _, me3 = seed_chapter_std_obj_me(db_session, ed, "MOM", "MOM-1", "MOM-1.a", "MOM-1.a.3")
    _, _, _, me4 = seed_chapter_std_obj_me(db_session, ed, "MOM", "MOM-1", "MOM-1.a", "MOM-1.a.4")
    _, _, _, me5 = seed_chapter_std_obj_me(db_session, ed, "MOM", "MOM-1", "MOM-1.a", "MOM-1.a.5")

    # 1. State row 1: applicable + compliant
    req1 = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    # 2. State row 2: applicable + under_review (not compliant)
    req2 = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me2.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.UNDER_REVIEW
    )
    # 3. State row 3: conditional + non_compliant
    req3 = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me3.id,
        applicability_status=ApplicabilityDefault.CONDITIONAL,
        readiness_status=ComplianceStatus.NON_COMPLIANT
    )
    # 4. State row 4: manual_review + partially_compliant
    req4 = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me4.id,
        applicability_status=ApplicabilityDefault.MANUAL_REVIEW,
        readiness_status=ComplianceStatus.PARTIALLY_COMPLIANT
    )
    # 5. State row 5 (User Addendum): not_applicable + compliant (MUST be excluded from both numerator & denominator)
    req5 = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me5.id,
        applicability_status=ApplicabilityDefault.NOT_APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )

    db_session.add_all([req1, req2, req3, req4, req5])
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp1.id}?edition_version=6.0")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["total_state_rows"] == 5
    # Denominator includes: applicable (2) + conditional (1) + manual_review (1) = 4
    assert res["denominator"] == 4
    # Numerator ready count: only compliant in denominator.
    # req1 is compliant. req5 is compliant but not_applicable (excluded).
    assert res["ready_count"] == 1
    # score = 1 / 4 * 100 = 25.0%
    assert res["readiness_score_percent"] == 25.0
    assert res["status"] == "in_progress"
    
    assert res["applicable_count"] == 2
    assert res["conditional_count"] == 1
    assert res["manual_review_count"] == 1
    assert res["not_applicable_count"] == 1
    
    # 2 compliant rows (req1 and req5)
    assert res["compliant_count"] == 2
    assert res["under_review_count"] == 1
    assert res["non_compliant_count"] == 1
    assert res["partially_compliant_count"] == 1

    app.dependency_overrides.clear()

def test_score_mutations_and_all_not_applicable(client, db_session):
    hosp1, _, staff_h1, _, _, ed = create_base_data(db_session)
    async def get_h1_user():
        return staff_h1
    app.dependency_overrides[get_current_user] = get_h1_user

    _, _, _, me1 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.1")
    _, _, _, me2 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.2")

    req1 = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.UNDER_REVIEW
    )
    req2 = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me2.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    db_session.add_all([req1, req2])
    db_session.commit()

    # Initial state: 2 applicable. denominator = 2. ready = 1 (req2). score = 50.0
    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    assert response.json()["readiness_score_percent"] == 50.0
    assert response.json()["denominator"] == 2
    assert response.json()["ready_count"] == 1

    # Mutation 1: Score Mutation By Applicability
    # Change req1 (under_review) to not_applicable. Denominator becomes 1, score should be 1/1 * 100 = 100.0, status = "ready"
    req1.applicability_status = ApplicabilityDefault.NOT_APPLICABLE
    db_session.commit()
    
    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    res = response.json()
    assert res["denominator"] == 1
    assert res["ready_count"] == 1
    assert res["readiness_score_percent"] == 100.0
    assert res["status"] == "ready"

    # Mutation 2: Score Mutation By Readiness
    # Change req1 back to applicable, and make it compliant as well. Both compliant. score = 100.0
    req1.applicability_status = ApplicabilityDefault.APPLICABLE
    req1.readiness_status = ComplianceStatus.COMPLIANT
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    res = response.json()
    assert res["denominator"] == 2
    assert res["ready_count"] == 2
    assert res["readiness_score_percent"] == 100.0
    assert res["status"] == "ready"

    # Mutation 3: All Not Applicable
    # Change both to not_applicable. denominator = 0, status = "no_applicable_requirements", score = null
    req1.applicability_status = ApplicabilityDefault.NOT_APPLICABLE
    req2.applicability_status = ApplicabilityDefault.NOT_APPLICABLE
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    res = response.json()
    assert res["denominator"] == 0
    assert res["ready_count"] == 0
    assert res["readiness_score_percent"] is None
    assert res["status"] == "no_applicable_requirements"

    app.dependency_overrides.clear()

def test_per_chapter_breakdown(client, db_session):
    hosp1, _, staff_h1, _, _, ed = create_base_data(db_session)
    async def get_h1_user():
        return staff_h1
    app.dependency_overrides[get_current_user] = get_h1_user

    # Chapter FMS
    _, _, _, me_fms = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.1")
    # Chapter MOM
    _, _, _, me_mom = seed_chapter_std_obj_me(db_session, ed, "MOM", "MOM-1", "MOM-1.a", "MOM-1.a.1")

    req_fms = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me_fms.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    req_mom = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me_mom.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.UNDER_REVIEW
    )
    db_session.add_all([req_fms, req_mom])
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    res = response.json()
    
    assert len(res["chapters"]) == 2
    
    # Chapters are sorted by display_order. FMS display_order=1, MOM display_order=2.
    fms_chap = res["chapters"][0]
    assert fms_chap["chapter_code"] == "FMS"
    assert fms_chap["total_state_rows"] == 1
    assert fms_chap["denominator"] == 1
    assert fms_chap["ready_count"] == 1
    assert fms_chap["readiness_score_percent"] == 100.0
    assert fms_chap["status"] == "ready"

    mom_chap = res["chapters"][1]
    assert mom_chap["chapter_code"] == "MOM"
    assert mom_chap["total_state_rows"] == 1
    assert mom_chap["denominator"] == 1
    assert mom_chap["ready_count"] == 0
    assert mom_chap["readiness_score_percent"] == 0.0
    assert mom_chap["status"] == "in_progress"

    app.dependency_overrides.clear()

def test_retired_rows_excluded(client, db_session):
    hosp1, _, staff_h1, _, _, ed = create_base_data(db_session)
    async def get_h1_user():
        return staff_h1
    app.dependency_overrides[get_current_user] = get_h1_user

    # Seed 6 requirements in FMS
    _, _, _, me1 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.1")
    _, _, _, me2 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.2")
    _, _, _, me3 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.3")
    _, _, _, me4 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.4")
    _, _, _, me5 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.5")
    _, _, _, me6 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.6")

    req1 = HospitalNABHRequirement(hospital_id=hosp1.id, requirement_id=me1.id, applicability_status=ApplicabilityDefault.APPLICABLE, readiness_status=ComplianceStatus.COMPLIANT)
    req2 = HospitalNABHRequirement(hospital_id=hosp1.id, requirement_id=me2.id, applicability_status=ApplicabilityDefault.APPLICABLE, readiness_status=ComplianceStatus.COMPLIANT)
    req3 = HospitalNABHRequirement(hospital_id=hosp1.id, requirement_id=me3.id, applicability_status=ApplicabilityDefault.APPLICABLE, readiness_status=ComplianceStatus.COMPLIANT)
    req4 = HospitalNABHRequirement(hospital_id=hosp1.id, requirement_id=me4.id, applicability_status=ApplicabilityDefault.APPLICABLE, readiness_status=ComplianceStatus.COMPLIANT)
    req5 = HospitalNABHRequirement(hospital_id=hosp1.id, requirement_id=me5.id, applicability_status=ApplicabilityDefault.APPLICABLE, readiness_status=ComplianceStatus.COMPLIANT)
    req6 = HospitalNABHRequirement(hospital_id=hosp1.id, requirement_id=me6.id, applicability_status=ApplicabilityDefault.APPLICABLE, readiness_status=ComplianceStatus.COMPLIANT)

    db_session.add_all([req1, req2, req3, req4, req5, req6])
    db_session.commit()

    # Now retire each layer selectively
    
    # 1. Retire HospitalNABHRequirement (req1)
    req1.retired_at = datetime.utcnow()
    # 2. Retire NABHMeasurableElement (me2)
    me2.retired_at = datetime.utcnow()
    
    # 3. Retire NABHObjectiveElement containing me3
    # Let's find standard & objective element for me3
    obj_me3 = db_session.query(NABHObjectiveElement).filter_by(id=me3.objective_element_id).first()
    obj_me3.retired_at = datetime.utcnow()
    
    # 4. Retire NABHStandard containing me4
    std_me4 = db_session.query(NABHStandard).filter_by(id=obj_me3.standard_id).first()
    # Wait, me4 shares standard with me3? Let's check. Yes, seed_chapter_std_obj_me created FMS-1 standard.
    # Since standard is shared, standard retire will affect me1, me2, me3, me4, me5, me6.
    # To keep them separate, let's create a new standard, objective, measurable element for me4, me5, me6 to retire them individually.
    db_session.commit()

    # Let's seed fresh separate ones:
    # me4 under standard FMS-2
    _, _, _, me_fresh_4 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.2", "FMS.2.a", "FMS.2.a.1")
    req4.requirement_id = me_fresh_4.id
    # me5 under standard FMS-3
    _, std5, _, me_fresh_5 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.3", "FMS.3.a", "FMS.3.a.1")
    req5.requirement_id = me_fresh_5.id
    # me6 under chapter MOM
    _, _, _, me_fresh_6 = seed_chapter_std_obj_me(db_session, ed, "MOM", "MOM-1", "MOM-1.a", "MOM-1.a.1")
    req6.requirement_id = me_fresh_6.id
    
    db_session.commit()

    # Let's retire standard of me4 (FMS-2)
    std4 = db_session.query(NABHStandard).filter_by(canonical_code="FMS.2").first()
    std4.retired_at = datetime.utcnow()

    # Let's retire chapter of me6 (MOM)
    chap_mom = db_session.query(NABHChapter).filter_by(canonical_code="MOM").first()
    chap_mom.retired_at = datetime.utcnow()

    db_session.commit()

    # So out of req1-req6:
    # req1 is retired -> excluded.
    # req2 has retired measurable element -> excluded.
    # req3 standard has retired objective element -> excluded.
    # req4 has retired standard FMS-2 -> excluded.
    # req6 has retired chapter MOM -> excluded.
    # Only req5 should remain active! (HospitalOne, FMS-3, FMS-3.a.1, not retired)
    
    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    res = response.json()

    assert res["total_state_rows"] == 1
    assert res["denominator"] == 1
    assert res["ready_count"] == 1
    assert res["readiness_score_percent"] == 100.0

    app.dependency_overrides.clear()

def test_legacy_rows_ignored(client, db_session):
    hosp1, _, staff_h1, _, _, ed = create_base_data(db_session)
    async def get_h1_user():
        return staff_h1
    app.dependency_overrides[get_current_user] = get_h1_user

    # Seed 1 active 6.0 requirement
    _, _, _, me1 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.1")
    req1 = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    db_session.add(req1)

    # Seed legacy NABHObjective row
    legacy_obj = NABHObjective(
        id="legacy-obj-id",
        hospital_id=hosp1.id,
        chapter_code="FMS",
        objective_number=1,
        element_letter="a",
        standard_code="FMS.1.a",
        standard_name="Legacy Standard",
        maturity_level=MaturityLevel.IMPLEMENTED
    )
    db_session.add(legacy_obj)

    # Seed legacy ComplianceRecord row
    legacy_record = ComplianceRecord(
        id="legacy-rec-id",
        hospital_id=hosp1.id,
        standard_code="FMS.1.a",
        standard_name="Legacy Standard",
        status=ComplianceStatus.COMPLIANT
    )
    db_session.add(legacy_record)
    db_session.commit()

    # Calculate readiness. Score should only count the 6.0 requirement.
    # Score should be 100% since req1 is compliant.
    # If legacy rows were counted, counts or results would differ.
    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    res = response.json()
    assert res["total_state_rows"] == 1
    assert res["ready_count"] == 1
    assert res["readiness_score_percent"] == 100.0

    app.dependency_overrides.clear()

def test_api_access_control(client, db_session):
    hosp1, hosp2, staff_h1, staff_h2, super_admin, ed = create_base_data(db_session)

    # Seed 1 requirement
    _, _, _, me1 = seed_chapter_std_obj_me(db_session, ed, "FMS", "FMS.1", "FMS.1.a", "FMS.1.a.1")
    req1 = HospitalNABHRequirement(
        hospital_id=hosp1.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    db_session.add(req1)
    db_session.commit()

    # Scenario 1: Own hospital allowed (Hosp 1 admin querying Hosp 1)
    async def get_h1_user():
        return staff_h1
    app.dependency_overrides[get_current_user] = get_h1_user

    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    assert response.status_code == status.HTTP_200_OK

    # Scenario 2: Cross-hospital forbidden (Hosp 2 user querying Hosp 1)
    async def get_h2_user():
        return staff_h2
    app.dependency_overrides[get_current_user] = get_h2_user

    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Scenario 3: Super admin allowed (Super admin querying Hosp 1)
    async def get_super_user():
        return super_admin
    app.dependency_overrides[get_current_user] = get_super_user

    response = client.get(f"/api/nabh/readiness/{hosp1.id}")
    assert response.status_code == status.HTTP_200_OK

    app.dependency_overrides.clear()

def test_missing_hospital_and_edition(client, db_session):
    hosp1, _, staff_h1, _, super_admin, ed = create_base_data(db_session)
    async def get_super_user():
        return super_admin
    app.dependency_overrides[get_current_user] = get_super_user

    # Missing hospital (queried by super_admin so access control passes, then hospital existence check returns 404)
    response = client.get(f"/api/nabh/readiness/non_existent_hosp_id?edition_version=6.0")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Hospital" in response.json()["detail"]

    # Switch override back to staff_h1 for own hospital edition query
    async def get_h1_user():
        return staff_h1
    app.dependency_overrides[get_current_user] = get_h1_user

    # Missing edition version
    response = client.get(f"/api/nabh/readiness/{hosp1.id}?edition_version=9.9")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Edition" in response.json()["detail"]

    app.dependency_overrides.clear()
