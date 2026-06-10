import pytest
from datetime import datetime
from sqlalchemy import text
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement,
    Hospital, Staff, HospitalNABHRequirement,
    EditionStatus, UserRole, ApplicabilityDefault, ComplianceStatus,
    MaturityLevel, HospitalAccreditationProfile, NABHApplicabilityRule,
    ProfileStatus
)
from app.nabh.applicability import ApplicabilityEngine

@pytest.fixture(autouse=True)
def clean_db(db_session):
    # Enable foreign keys
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHApplicabilityRule).delete()
    db_session.query(NABHMeasurableElement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.query(HospitalAccreditationProfile).delete()
    db_session.query(Staff).delete()
    db_session.query(Hospital).delete()
    db_session.commit()
    yield

def setup_base_data(db_session):
    # Hospital
    hosp = Hospital(id="hosp-1", name="Test Hospital", registration_number="REG-01")
    db_session.add(hosp)
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

    # Create official Chapter FMS
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

    # Standard FMS-1
    std = NABHStandard(
        id="std-fms-1",
        edition_id=ed.id,
        chapter_id=chap.id,
        code="1",
        canonical_code="FMS-1",
        title="Standard 1"
    )
    db_session.add(std)
    db_session.commit()

    # Objective Element FMS-1.a
    obj = NABHObjectiveElement(
        id="obj-fms-1.a",
        edition_id=ed.id,
        standard_id=std.id,
        code="a",
        canonical_code="FMS-1.a",
        description="Objective a"
    )
    db_session.add(obj)
    db_session.commit()

    return hosp, ed, chap, std, obj

def create_me(db_session, ed, obj, code, app_def=ApplicabilityDefault.APPLICABLE):
    me = NABHMeasurableElement(
        id=f"me-{code.lower().replace('.', '-')}",
        edition_id=ed.id,
        objective_element_id=obj.id,
        code=code.split(".")[-1],
        canonical_code=code,
        description=f"Measurable {code}",
        applicability_default=app_def
    )
    db_session.add(me)
    db_session.commit()
    return me

def test_applicability_defaults_create_state_rows(db_session):
    hosp, ed, chap, std, obj = setup_base_data(db_session)
    me = create_me(db_session, ed, obj, "FMS-1.a.1", ApplicabilityDefault.APPLICABLE)

    # Compute with no profile saved first (should fall back to manual review with reason)
    res = ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    assert res["total_requirements_evaluated"] == 1
    assert res["created_rows_count"] == 1
    
    req_state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    assert req_state is not None
    assert req_state.applicability_status == ApplicabilityDefault.MANUAL_REVIEW
    assert "profile is missing" in req_state.applicability_reason

    # Clean requirements and try with a saved default profile
    db_session.delete(req_state)
    db_session.commit()

    profile = HospitalAccreditationProfile(
        hospital_id=hosp.id,
        bed_count=10,
        has_emergency=True,
        profile_status=ProfileStatus.COMPLETE
    )
    db_session.add(profile)
    db_session.commit()

    res = ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    assert res["created_rows_count"] == 1

    req_state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    assert req_state.applicability_status == ApplicabilityDefault.APPLICABLE
    assert "Default applicability" in req_state.applicability_reason

def test_applicability_rule_boolean_match(db_session):
    hosp, ed, chap, std, obj = setup_base_data(db_session)
    me = create_me(db_session, ed, obj, "FMS-1.a.1", ApplicabilityDefault.APPLICABLE)

    # Rule: applies (applicable) if has_blood_bank == true, else not_applicable
    rule = NABHApplicabilityRule(
        id="rule-blood-bank",
        measurable_element_id=me.id,
        rule_code="R-BLOOD-BANK",
        description="Requires blood bank",
        rule_json={
            "field": "has_blood_bank",
            "operator": "eq",
            "value": True
        },
        action_if_true="applicable",
        action_if_false="not_applicable"
    )
    db_session.add(rule)
    
    # Profile with has_blood_bank = False
    profile = HospitalAccreditationProfile(
        hospital_id=hosp.id,
        has_blood_bank=False,
        profile_status=ProfileStatus.COMPLETE
    )
    db_session.add(profile)
    db_session.commit()

    ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    req_state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    assert req_state.applicability_status == ApplicabilityDefault.NOT_APPLICABLE
    assert "Rule did not match" in req_state.applicability_reason

    # Clean requirement row, update profile to has_blood_bank = True
    db_session.delete(req_state)
    profile.has_blood_bank = True
    db_session.commit()

    ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    req_state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    assert req_state.applicability_status == ApplicabilityDefault.APPLICABLE
    assert req_state.applicability_reason == "Requires blood bank"

def test_applicability_rule_list_match(db_session):
    hosp, ed, chap, std, obj = setup_base_data(db_session)
    me = create_me(db_session, ed, obj, "FMS-1.a.1", ApplicabilityDefault.APPLICABLE)

    # Rule: applies (applicable) if services_offered contains "ICU"
    rule = NABHApplicabilityRule(
        id="rule-list-match",
        measurable_element_id=me.id,
        rule_code="R-ICU-SERVICE",
        description="Requires ICU services offered",
        rule_json={
            "field": "services_offered",
            "operator": "in",
            "value": "ICU"
        },
        action_if_true="applicable",
        action_if_false="not_applicable"
    )
    db_session.add(rule)

    profile = HospitalAccreditationProfile(
        hospital_id=hosp.id,
        services_offered=["OPD", "IPD"],
        profile_status=ProfileStatus.COMPLETE
    )
    db_session.add(profile)
    db_session.commit()

    ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    req_state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    assert req_state.applicability_status == ApplicabilityDefault.NOT_APPLICABLE

    # Add "ICU" to services offered
    db_session.delete(req_state)
    profile.services_offered = ["OPD", "IPD", "ICU"]
    db_session.commit()

    ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    req_state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    assert req_state.applicability_status == ApplicabilityDefault.APPLICABLE

def test_applicability_manual_review_when_rule_cannot_be_resolved(db_session):
    hosp, ed, chap, std, obj = setup_base_data(db_session)
    me = create_me(db_session, ed, obj, "FMS-1.a.1", ApplicabilityDefault.APPLICABLE)

    # 1. Unknown profile field
    rule_invalid_field = NABHApplicabilityRule(
        id="rule-invalid-field",
        measurable_element_id=me.id,
        rule_code="R-INVALID-FIELD",
        rule_json={
            "field": "non_existent_field",
            "operator": "eq",
            "value": True
        },
        action_if_true="applicable",
        action_if_false="not_applicable"
    )
    db_session.add(rule_invalid_field)
    
    profile = HospitalAccreditationProfile(
        hospital_id=hosp.id,
        profile_status=ProfileStatus.COMPLETE
    )
    db_session.add(profile)
    db_session.commit()

    ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    req_state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    assert req_state.applicability_status == ApplicabilityDefault.MANUAL_REVIEW
    assert "Unknown or non-whitelisted profile field" in req_state.applicability_reason

    # Clean up and try:
    # 2. Non-numeric value in numeric operator gt
    db_session.delete(req_state)
    db_session.delete(rule_invalid_field)
    
    rule_non_numeric = NABHApplicabilityRule(
        id="rule-non-numeric",
        measurable_element_id=me.id,
        rule_code="R-NON-NUMERIC",
        rule_json={
            "field": "bed_count",
            "operator": "gt",
            "value": "ten_beds_string" # string value is invalid for gt
        },
        action_if_true="applicable",
        action_if_false="not_applicable"
    )
    db_session.add(rule_non_numeric)
    db_session.commit()

    ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    req_state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    assert req_state.applicability_status == ApplicabilityDefault.MANUAL_REVIEW
    assert "Non-numeric values in numeric comparison" in req_state.applicability_reason

def test_compute_applicability_is_idempotent(db_session):
    hosp, ed, chap, std, obj = setup_base_data(db_session)
    create_me(db_session, ed, obj, "FMS-1.a.1", ApplicabilityDefault.APPLICABLE)

    profile = HospitalAccreditationProfile(
        hospital_id=hosp.id,
        profile_status=ProfileStatus.COMPLETE
    )
    db_session.add(profile)
    db_session.commit()

    # First run
    res_1 = ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    assert res_1["created_rows_count"] == 1
    assert res_1["updated_rows_count"] == 0
    assert res_1["unchanged_rows_count"] == 0

    # Second run
    res_2 = ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    assert res_2["created_rows_count"] == 0
    assert res_2["updated_rows_count"] == 0
    assert res_2["unchanged_rows_count"] == 1

def test_recompute_updates_existing_rows_without_losing_user_fields(db_session):
    hosp, ed, chap, std, obj = setup_base_data(db_session)
    me = create_me(db_session, ed, obj, "FMS-1.a.1", ApplicabilityDefault.APPLICABLE)

    rule = NABHApplicabilityRule(
        id="rule-blood-bank",
        measurable_element_id=me.id,
        rule_code="R-BLOOD-BANK",
        rule_json={
            "field": "has_blood_bank",
            "operator": "eq",
            "value": True
        },
        action_if_true="applicable",
        action_if_false="not_applicable"
    )
    db_session.add(rule)

    profile = HospitalAccreditationProfile(
        hospital_id=hosp.id,
        has_blood_bank=True,
        profile_status=ProfileStatus.COMPLETE
    )
    db_session.add(profile)
    db_session.commit()

    ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    req_state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    
    # Create valid staff record to satisfy foreign key constraint on owner_id
    staff = Staff(
        id="staff-001",
        hospital_id=hosp.id,
        employee_id="EMP-001",
        name="Test Owner",
        role=UserRole.HOSPITAL_ADMIN,
        email="testowner@hosp.com",
        is_active=True
    )
    db_session.add(staff)
    db_session.commit()

    # User marks progress fields
    req_state.owner_id = "staff-001"
    req_state.due_date = datetime.strptime("2026-12-31", "%Y-%m-%d")
    req_state.readiness_status = ComplianceStatus.COMPLIANT
    db_session.commit()

    # Profile changes -> blood bank is false -> applicability transitions to not_applicable
    profile.has_blood_bank = False
    db_session.commit()

    ApplicabilityEngine.compute_applicability(db_session, hosp.id)

    # Query requirement row
    req_state_after = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hosp.id, requirement_id=me.id).first()
    assert req_state_after.applicability_status == ApplicabilityDefault.NOT_APPLICABLE
    
    # Assert user compliance tracking fields are preserved
    assert req_state_after.owner_id == "staff-001"
    assert req_state_after.due_date.strftime("%Y-%m-%d") == "2026-12-31"
    assert req_state_after.readiness_status == ComplianceStatus.COMPLIANT
