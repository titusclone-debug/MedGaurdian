import pytest
from datetime import datetime
from sqlalchemy import text
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement, NABHApplicabilityRule,
    Hospital, HospitalAccreditationProfile, HospitalNABHRequirement,
    ApplicabilityDefault, MaturityLevel, EvidenceStatus, ComplianceStatus,
    NABHObjective, EditionStatus, ProfileStatus
)
from app.nabh.applicability import ApplicabilityEngine, evaluate_rule_json

def test_applicability_engine_smoke(db_session):
    # Enable foreign keys for SQLite
    db_session.execute(text("PRAGMA foreign_keys=ON"))

    # Clean existing data to isolate the test environment
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHApplicabilityRule).delete()
    db_session.query(NABHMeasurableElement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.query(HospitalAccreditationProfile).delete()
    db_session.query(Hospital).delete()
    db_session.query(NABHObjective).delete()
    db_session.commit()

    # 1. Setup Active Edition (6.0)
    edition = NABHEdition(
        id="test-ed-6",
        version="6.0",
        name="NABH 6.0 Edition",
        status=EditionStatus.ACTIVE,
        effective_date=datetime.utcnow()
    )
    db_session.add(edition)
    db_session.commit()

    # 2. Setup Chapters (e.g. FMS)
    chapter = NABHChapter(
        id="test-chap-fms",
        edition_id=edition.id,
        code="FMS",
        canonical_code="FMS",
        title="Facility Management and Safety",
        display_order=8,
        official_standards_count=7,
        official_measurable_elements_count=43
    )
    db_session.add(chapter)
    db_session.commit()

    # 3. Setup Standard and Objective Element
    standard = NABHStandard(
        id="test-std-fms-1",
        edition_id=edition.id,
        chapter_id=chapter.id,
        code="FMS.1",
        canonical_code="FMS.1",
        title="Fire safety program"
    )
    db_session.add(standard)
    db_session.commit()

    obj_element = NABHObjectiveElement(
        id="test-obj-fms-1.a",
        edition_id=edition.id,
        standard_id=standard.id,
        code="FMS.1.a",
        canonical_code="FMS.1.a",
        description="Verify fire clearance NOC"
    )
    db_session.add(obj_element)
    db_session.commit()

    # 4. Setup Measurable Elements
    # E1: Element with default applicability only (no rules)
    e1 = NABHMeasurableElement(
        id="test-me-fms-1.a.1",
        edition_id=edition.id,
        objective_element_id=obj_element.id,
        code="FMS.1.a.1",
        canonical_code="FMS.1.a.1",
        description="Check validity of NOC",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    # E2: Element with an 'eq' operator rule
    e2 = NABHMeasurableElement(
        id="test-me-fms-1.a.2",
        edition_id=edition.id,
        objective_element_id=obj_element.id,
        code="FMS.1.a.2",
        canonical_code="FMS.1.a.2",
        description="Check OT safety protocols",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    # E3: Element with 'in' operator rules and multiple rule precedence
    e3 = NABHMeasurableElement(
        id="test-me-fms-1.a.3",
        edition_id=edition.id,
        objective_element_id=obj_element.id,
        code="FMS.1.a.3",
        canonical_code="FMS.1.a.3",
        description="Check ICU clinical guidelines",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    # E4: Element with numeric comparison rule
    e4 = NABHMeasurableElement(
        id="test-me-fms-1.a.4",
        edition_id=edition.id,
        objective_element_id=obj_element.id,
        code="FMS.1.a.4",
        canonical_code="FMS.1.a.4",
        description="Check specific rules for beds threshold",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )

    db_session.add_all([e1, e2, e3, e4])
    db_session.commit()

    # 5. Setup Rules
    # Rule for E2: not applicable if has_operation_theatre == False
    r2 = NABHApplicabilityRule(
        id="test-rule-e2",
        measurable_element_id=e2.id,
        rule_code="RULE-FMS-E2",
        description="Requirement is not applicable if hospital does not have an operating theatre.",
        action_if_true="not_applicable",
        action_if_false="applicable",
        rule_json={"field": "has_operation_theatre", "operator": "eq", "value": False}
    )
    # Rules for E3 (Precedence test):
    # Rule 3A: conditional if services_offered contains "cardiology" (intersects/in list check)
    r3a = NABHApplicabilityRule(
        id="test-rule-e3a",
        measurable_element_id=e3.id,
        rule_code="RULE-FMS-E3A",
        description="ICU safety conditional if cardiology is offered.",
        action_if_true="conditional",
        action_if_false="applicable",
        rule_json={"field": "services_offered", "operator": "in", "value": ["cardiology"]}
    )
    # Rule 3B: not_applicable if has_icu == False (this should beat conditional due to precedence)
    r3b = NABHApplicabilityRule(
        id="test-rule-e3b",
        measurable_element_id=e3.id,
        rule_code="RULE-FMS-E3B",
        description="ICU safety not applicable if no ICU exists.",
        action_if_true="not_applicable",
        action_if_false="applicable",
        rule_json={"field": "has_icu", "operator": "eq", "value": False}
    )
    # Rule for E4: conditional if bed_count >= 50
    r4 = NABHApplicabilityRule(
        id="test-rule-e4",
        measurable_element_id=e4.id,
        rule_code="RULE-FMS-E4",
        description="High bed count safety standards apply conditionally if bed count is 50 or more.",
        action_if_true="conditional",
        action_if_false="applicable",
        rule_json={"field": "bed_count", "operator": "gte", "value": 50}
    )

    db_session.add_all([r2, r3a, r3b, r4])
    db_session.commit()

    # 6. Setup Hospital and Accreditation Profile
    hosp = Hospital(id="test-hosp-1", name="Test Hospital")
    db_session.add(hosp)
    db_session.commit()

    profile = HospitalAccreditationProfile(
        id="test-prof-1",
        hospital_id=hosp.id,
        bed_count=30,
        has_icu=False,
        has_operation_theatre=False,
        services_offered=["cardiology", "general_medicine"],
        profile_status=ProfileStatus.COMPLETE
    )
    db_session.add(profile)
    db_session.commit()

    # ==========================================
    # TEST: Missing Profile Field behavior
    # ==========================================
    r_null = NABHApplicabilityRule(
        id="test-rule-null",
        measurable_element_id=e1.id,
        rule_code="RULE-FMS-NULL",
        description="Test null field rule",
        action_if_true="conditional",
        action_if_false="applicable",
        rule_json={"field": "annual_patient_volume", "operator": "gt", "value": 1000}
    )
    db_session.add(r_null)
    db_session.commit()

    # Run engine
    res = ApplicabilityEngine.compute_applicability(db_session, hosp.id)

    # Verify return schema
    assert res["total_requirements_evaluated"] == 4
    assert res["created_rows_count"] == 4
    assert res["updated_rows_count"] == 0
    assert res["unchanged_rows_count"] == 0

    results_by_code = {r["requirement_code"]: r for r in res["results"]}

    # ME 1 (E1) -> Rule on null field ('annual_patient_volume' is None in profile) -> resolves to manual_review
    assert results_by_code["FMS.1.a.1"]["applicability_status"] == "manual_review"
    assert "missing or incomplete" in results_by_code["FMS.1.a.1"]["applicability_reason"]

    # ME 2 (E2) -> has_operation_theatre is False -> evaluates true -> not_applicable
    assert results_by_code["FMS.1.a.2"]["applicability_status"] == "not_applicable"
    assert "operating theatre" in results_by_code["FMS.1.a.2"]["applicability_reason"]

    # ME 3 (E3) -> Rule 3A evaluates True (cardiology in services_offered) -> conditional
    #              Rule 3B evaluates True (has_icu == False) -> not_applicable
    # Precedence: not_applicable beats conditional -> winning_status must be not_applicable
    assert results_by_code["FMS.1.a.3"]["applicability_status"] == "not_applicable"

    # ME 4 (E4) -> bed_count is 30 -> rule 30 >= 50 evaluates False -> action_if_false is 'applicable'
    assert results_by_code["FMS.1.a.4"]["applicability_status"] == "applicable"
    assert "High bed count safety standards" in results_by_code["FMS.1.a.4"]["applicability_reason"]
    assert "applying applicable" in results_by_code["FMS.1.a.4"]["applicability_reason"]

    # Clean up the null rule to test clean rerun
    db_session.delete(r_null)
    db_session.commit()

    # ==========================================
    # TEST: Rerun/Recompute & Progress Preservation
    # ==========================================
    # Manually simulate progress attributes on E2
    db_session.execute(text(
        "UPDATE hospital_nabh_requirements "
        "SET maturity_level = 'IMPLEMENTED', evidence_status = 'VERIFIED', due_date = '2026-12-31 00:00:00' "
        "WHERE requirement_id = 'test-me-fms-1.a.2'"
    ))
    db_session.commit()

    # Re-run engine
    res2 = ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    assert res2["total_requirements_evaluated"] == 4
    # FMS-1.a.1 had rule deleted, now falls back to Default (applicable). It gets updated.
    assert res2["updated_rows_count"] == 1
    assert res2["unchanged_rows_count"] == 3

    # Verify FMS-1.a.2 state preserved progress
    req_e2 = db_session.query(HospitalNABHRequirement).filter(
        HospitalNABHRequirement.requirement_id == e2.id
    ).first()
    assert req_e2.applicability_status == ApplicabilityDefault.NOT_APPLICABLE
    assert req_e2.maturity_level == MaturityLevel.IMPLEMENTED
    assert req_e2.evidence_status == EvidenceStatus.VERIFIED
    assert req_e2.due_date.year == 2026

    # ==========================================
    # TEST: Operator 'in' checks
    # ==========================================
    # A. Scalar in list: field is hospital_type ("eye"), rule value is ["eye", "dental"]
    profile.hospital_type = "eye"
    db_session.add(profile)
    db_session.commit()
    r_op_in_1 = evaluate_rule_json(profile, {"field": "hospital_type", "operator": "in", "value": ["eye", "dental"]})
    assert r_op_in_1["matched"] is True

    # B. List contains scalar: field is services_offered (["cardiology"]), rule value is "cardiology"
    r_op_in_2 = evaluate_rule_json(profile, {"field": "services_offered", "operator": "in", "value": "cardiology"})
    assert r_op_in_2["matched"] is True

    # C. List intersects list: field is services_offered, rule value is ["cardiology", "pediatrics"]
    r_op_in_3 = evaluate_rule_json(profile, {"field": "services_offered", "operator": "in", "value": ["cardiology", "pediatrics"]})
    assert r_op_in_3["matched"] is True

    # ==========================================
    # TEST: Numeric Type Checking
    # ==========================================
    # Test that non-numeric comparison values resolve to manual_review
    r_num_err = evaluate_rule_json(profile, {"field": "bed_count", "operator": "gt", "value": "fifty"})
    assert r_num_err["status_override"] == ApplicabilityDefault.MANUAL_REVIEW
    assert "Non-numeric values" in r_num_err["reason"]

    # ==========================================
    # TEST: Missing Profile Behavior
    # ==========================================
    hosp_no_prof = Hospital(id="test-hosp-no-profile", name="No Profile Hospital")
    db_session.add(hosp_no_prof)
    db_session.commit()

    res_no_prof = ApplicabilityEngine.compute_applicability(db_session, hosp_no_prof.id)
    assert res_no_prof["total_requirements_evaluated"] == 4
    for r in res_no_prof["results"]:
        assert r["applicability_status"] == "manual_review"
        assert "profile is missing" in r["applicability_reason"]

    # ==========================================
    # TEST: No Legacy Dependency
    # ==========================================
    # Create a legacy NABHObjective row
    legacy_obj = NABHObjective(
        id="legacy-1",
        hospital_id=hosp.id,
        chapter_code="HIC",
        objective_number=1,
        element_letter="a",
        standard_code="HIC 1",
        standard_name="Legacy Standard"
    )
    db_session.add(legacy_obj)
    db_session.commit()

    # Running applicability should NOT query or update the legacy table
    # We verify that its attributes remain completely unmodified
    ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    refreshed_legacy = db_session.query(NABHObjective).filter(NABHObjective.id == "legacy-1").first()
    assert refreshed_legacy.maturity_level == MaturityLevel.NON_EXISTENT

    # ==========================================
    # TEST: Retired Parent Requirements Excluded
    # ==========================================
    retired_standard = NABHStandard(
        id="test-std-fms-retired",
        edition_id=edition.id,
        chapter_id=chapter.id,
        code="FMS.99",
        canonical_code="FMS.99",
        title="Retired standard",
        retired_at=datetime.utcnow()
    )
    db_session.add(retired_standard)
    db_session.commit()

    retired_obj = NABHObjectiveElement(
        id="test-obj-fms-retired.a",
        edition_id=edition.id,
        standard_id=retired_standard.id,
        code="FMS.99.a",
        canonical_code="FMS.99.a",
        description="Retired objective element"
    )
    db_session.add(retired_obj)
    db_session.commit()

    retired_child = NABHMeasurableElement(
        id="test-me-fms-retired.a.1",
        edition_id=edition.id,
        objective_element_id=retired_obj.id,
        code="FMS.99.a.1",
        canonical_code="FMS.99.a.1",
        description="Child under retired standard",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    db_session.add(retired_child)
    db_session.commit()

    retired_objective = NABHObjectiveElement(
        id="test-obj-fms-active-standard-retired-objective",
        edition_id=edition.id,
        standard_id=standard.id,
        code="FMS.1.z",
        canonical_code="FMS.1.z",
        description="Retired objective under active standard",
        retired_at=datetime.utcnow()
    )
    db_session.add(retired_objective)
    db_session.commit()

    retired_objective_child = NABHMeasurableElement(
        id="test-me-fms-active-standard-retired-objective.1",
        edition_id=edition.id,
        objective_element_id=retired_objective.id,
        code="FMS.1.z.1",
        canonical_code="FMS.1.z.1",
        description="Child under retired objective element",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    db_session.add(retired_objective_child)
    db_session.commit()

    res_retired_parent = ApplicabilityEngine.compute_applicability(db_session, hosp.id)
    assert res_retired_parent["total_requirements_evaluated"] == 4
    retired_state = db_session.query(HospitalNABHRequirement).filter(
        HospitalNABHRequirement.requirement_id == retired_child.id
    ).first()
    assert retired_state is None
    retired_objective_state = db_session.query(HospitalNABHRequirement).filter(
        HospitalNABHRequirement.requirement_id == retired_objective_child.id
    ).first()
    assert retired_objective_state is None
