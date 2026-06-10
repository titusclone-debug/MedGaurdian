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
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHMeasurableElement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.query(NABHObjective).delete()
    db_session.query(ComplianceRecord).delete()
    db_session.query(Staff).delete()
    db_session.query(Hospital).delete()
    db_session.commit()
    yield

def setup_base_data(db_session):
    hosp = Hospital(id="test-hosp-1", name="Hospital One", registration_number="REG-01")
    db_session.add(hosp)
    db_session.commit()

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
            display_order=1,
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

def test_legacy_nabh_objectives_do_not_affect_new_readiness(client, db_session):
    hosp, staff, ed = setup_base_data(db_session)
    async def get_current_user_override():
        return staff
    app.dependency_overrides[get_current_user] = get_current_user_override

    # Create active element and active hospital requirement (not ready)
    _, _, _, me1 = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.1")
    req1 = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.UNDER_REVIEW
    )
    db_session.add(req1)

    # Seed legacy NABHObjective row (fully compliant maturity)
    legacy_obj = NABHObjective(
        id="legacy-obj-id",
        hospital_id=hosp.id,
        chapter_code="FMS",
        objective_number=1,
        element_letter="a",
        standard_code="FMS-1.a",
        standard_name="Legacy Standard",
        maturity_level=MaturityLevel.IMPLEMENTED
    )
    db_session.add(legacy_obj)
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp.id}?edition_version=6.0")
    res = response.json()
    # Scored readiness should ignore the legacy compliant row (score stays 0%)
    assert res["denominator"] == 1
    assert res["ready_count"] == 0
    assert res["readiness_score_percent"] == 0.0

    app.dependency_overrides.clear()

def test_legacy_compliance_records_do_not_affect_new_readiness(client, db_session):
    hosp, staff, ed = setup_base_data(db_session)
    async def get_current_user_override():
        return staff
    app.dependency_overrides[get_current_user] = get_current_user_override

    # Create active requirement (not ready)
    _, _, _, me1 = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.1")
    req1 = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.UNDER_REVIEW
    )
    db_session.add(req1)

    # Seed legacy ComplianceRecord (marked compliant)
    legacy_record = ComplianceRecord(
        id="legacy-rec-id",
        hospital_id=hosp.id,
        standard_code="FMS-1.a",
        standard_name="Legacy Standard",
        status=ComplianceStatus.COMPLIANT
    )
    db_session.add(legacy_record)
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp.id}?edition_version=6.0")
    res = response.json()
    # Score should ignore the legacy record (remain 0.0%)
    assert res["readiness_score_percent"] == 0.0

    app.dependency_overrides.clear()

def test_new_requirement_state_is_source_of_truth(client, db_session):
    hosp, staff, ed = setup_base_data(db_session)
    async def get_current_user_override():
        return staff
    app.dependency_overrides[get_current_user] = get_current_user_override

    # Create active requirement (marked compliant / ready)
    _, _, _, me1 = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.1")
    req1 = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.COMPLIANT
    )
    db_session.add(req1)

    # Legacy objective with conflicting non-compliant state
    legacy_obj = NABHObjective(
        id="legacy-obj-id",
        hospital_id=hosp.id,
        chapter_code="FMS",
        objective_number=1,
        element_letter="a",
        standard_code="FMS-1.a",
        standard_name="Legacy Standard",
        maturity_level=MaturityLevel.NON_EXISTENT
    )
    db_session.add(legacy_obj)
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp.id}?edition_version=6.0")
    res = response.json()
    
    # Score should resolve from the new active state (100%)
    assert res["denominator"] == 1
    assert res["ready_count"] == 1
    assert res["readiness_score_percent"] == 100.0

    app.dependency_overrides.clear()

def test_legacy_compliant_does_not_override_new_state_non_compliant(client, db_session):
    """
    Explicit conflict case: legacy record claims COMPLIANT, new state says NON_COMPLIANT.
    The new HospitalNABHRequirement must win. Readiness score must stay 0%.
    """
    hosp, staff, ed = setup_base_data(db_session)
    async def get_current_user_override():
        return staff
    app.dependency_overrides[get_current_user] = get_current_user_override

    # New state explicitly says NON_COMPLIANT
    _, _, _, me1 = create_seeded_me(db_session, ed, "FMS", "FMS-1", "FMS-1.a", "FMS-1.a.1")
    req1 = HospitalNABHRequirement(
        hospital_id=hosp.id, requirement_id=me1.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.NON_COMPLIANT
    )
    db_session.add(req1)

    # Legacy record claims COMPLIANT for the same standard
    legacy_record = ComplianceRecord(
        id="legacy-conflict-id",
        hospital_id=hosp.id,
        standard_code="FMS-1.a",
        standard_name="Legacy Standard",
        status=ComplianceStatus.COMPLIANT
    )
    db_session.add(legacy_record)

    # Legacy objective also claims IMPLEMENTED (fully done)
    legacy_obj = NABHObjective(
        id="legacy-obj-conflict-id",
        hospital_id=hosp.id,
        chapter_code="FMS",
        objective_number=1,
        element_letter="a",
        standard_code="FMS-1.a",
        standard_name="Legacy Standard",
        maturity_level=MaturityLevel.IMPLEMENTED
    )
    db_session.add(legacy_obj)
    db_session.commit()

    response = client.get(f"/api/nabh/readiness/{hosp.id}?edition_version=6.0")
    res = response.json()

    # Despite both legacy records claiming compliance, the new non_compliant state must win
    assert res["denominator"] == 1
    assert res["ready_count"] == 0
    assert res["readiness_score_percent"] == 0.0

    app.dependency_overrides.clear()
