import pytest
from datetime import datetime
from fastapi import status
from sqlalchemy import text
from app.api.auth import get_current_user
from app.main import app
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement, NABHObjective,
    Hospital, Staff, HospitalNABHRequirement,
    EditionStatus, UserRole, ApplicabilityDefault, ComplianceStatus
)

@pytest.fixture(autouse=True)
def clean_db(db_session):
    # Enable foreign keys
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHMeasurableElement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.query(Staff).delete()
    db_session.query(Hospital).delete()
    db_session.commit()
    yield

def setup_base_data(db_session):
    # Hospital
    hosp = Hospital(id="test-hosp-1", name="Hospital One", registration_number="REG-01")
    db_session.add(hosp)
    db_session.commit()

    # Staff / User
    staff = Staff(
        id="staff-h1",
        hospital_id=hosp.id,
        employee_id="EMP-H1",
        name="Hosp 1 Admin",
        role=UserRole.HOSPITAL_ADMIN,
        email="admin1@hosp1.com",
        is_active=True
    )
    db_session.add(staff)
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

    return hosp, staff, ed

def create_seeded_me(db_session, ed, chap_code, std_code, obj_code, me_code):
    chap = db_session.query(NABHChapter).filter_by(edition_id=ed.id, canonical_code=chap_code).first()
    if not chap:
        chap = NABHChapter(
            id=f"chap-{chap_code.lower()}",
            edition_id=ed.id,
            code=chap_code,
            canonical_code=chap_code,
            title=f"Chapter {chap_code}",
            display_order=1 if chap_code == "FMS" else 2,
            official_standards_count=1,
            official_measurable_elements_count=1
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
        id=f"me-{me_code.lower().replace('.', '-')}",
        edition_id=ed.id,
        objective_element_id=obj.id,
        code=me_code.split(".")[-1],
        canonical_code=me_code,
        description=f"Measurable {me_code}",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    db_session.add(me)
    db_session.commit()
    return chap, std, obj, me

def test_readiness_denominator_excludes_not_applicable(client, db_session):
    hosp, staff, ed = setup_base_data(db_session)
    async def get_current_user_override():
        return staff
    app.dependency_overrides[get_current_user] = get_current_user_override

    _, _, _, me1 = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.1")
    _, _, _, me2 = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.2")
    _, _, _, me3 = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.3")
    _, _, _, me4 = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.4")

    # 1. Scoped row 1: applicable + compliant (ready)
    req1 = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    # 2. Scoped row 2: conditional + non_compliant (in denominator)
    req2 = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me2.id,
        applicability_status=ApplicabilityDefault.CONDITIONAL,
        readiness_status=ComplianceStatus.NON_COMPLIANT
    )
    # 3. Scoped row 3: manual_review + under_review (in denominator)
    req3 = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me3.id,
        applicability_status=ApplicabilityDefault.MANUAL_REVIEW,
        readiness_status=ComplianceStatus.UNDER_REVIEW
    )
    # 4. Scoped row 4: not_applicable + compliant (EXCLUDED from denominator)
    req4 = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me4.id,
        applicability_status=ApplicabilityDefault.NOT_APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )

    db_session.add_all([req1, req2, req3, req4])
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp.id}?edition_version=6.0")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["total_state_rows"] == 4
    # Denominator includes: applicable (1) + conditional (1) + manual_review (1) = 3
    assert res["denominator"] == 3
    # Numerator ready count: only compliant req1 in denominator is ready. req4 is excluded.
    assert res["ready_count"] == 1
    # score = 1 / 3 * 100 = 33.3%
    assert round(res["readiness_score_percent"], 1) == 33.3
    
    app.dependency_overrides.clear()

def test_readiness_score_uses_new_requirement_state(client, db_session):
    hosp, staff, ed = setup_base_data(db_session)
    async def get_current_user_override():
        return staff
    app.dependency_overrides[get_current_user] = get_current_user_override

    _, _, _, me1 = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.1")

    # Mark requirement compliant (ready_count should be 1)
    req = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    db_session.add(req)
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp.id}?edition_version=6.0")
    res = response.json()
    assert res["denominator"] == 1
    assert res["ready_count"] == 1
    assert res["readiness_score_percent"] == 100.0

    app.dependency_overrides.clear()

def test_readiness_empty_scope_returns_not_ready_or_unscoped(client, db_session):
    hosp, staff, ed = setup_base_data(db_session)
    async def get_current_user_override():
        return staff
    app.dependency_overrides[get_current_user] = get_current_user_override

    # Clean scope (no requirement rows exist for this hospital)
    response = client.get(f"/api/nabh/readiness/{hosp.id}?edition_version=6.0")
    res = response.json()
    assert res["total_state_rows"] == 0
    assert res["denominator"] == 0
    assert res["ready_count"] == 0
    assert res["readiness_score_percent"] is None
    assert res["status"] == "not_scoped"

    app.dependency_overrides.clear()

def test_readiness_chapter_breakdown_matches_denominator_rules(client, db_session):
    hosp, staff, ed = setup_base_data(db_session)
    async def get_current_user_override():
        return staff
    app.dependency_overrides[get_current_user] = get_current_user_override

    # Create elements in two different chapters
    _, _, _, me_fms = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.1")
    _, _, _, me_mom = create_seeded_me(db_session, ed, "MOM", "MOM-1", "MOM-1.a", "MOM-1.a.1")

    # FMS requirement: applicable + compliant
    req_fms = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me_fms.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    # MOM requirement: not_applicable + compliant (excluded from denominator)
    req_mom = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me_mom.id,
        applicability_status=ApplicabilityDefault.NOT_APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    db_session.add_all([req_fms, req_mom])
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp.id}?edition_version=6.0")
    res = response.json()

    # Denominator global should equal sum of chapter denominators (1 + 0 = 1)
    assert res["denominator"] == 1
    assert len(res["chapters"]) == 2

    # Chapters sorted by display_order: FMS (1) then MOM (2)
    fms_chap = res["chapters"][0]
    assert fms_chap["chapter_code"] == "FMS"
    assert fms_chap["denominator"] == 1
    assert fms_chap["ready_count"] == 1
    assert fms_chap["readiness_score_percent"] == 100.0

    mom_chap = res["chapters"][1]
    assert mom_chap["chapter_code"] == "MOM"
    assert mom_chap["denominator"] == 0
    assert mom_chap["ready_count"] == 0
    assert mom_chap["readiness_score_percent"] is None
    assert mom_chap["status"] == "no_applicable_requirements"

    app.dependency_overrides.clear()
