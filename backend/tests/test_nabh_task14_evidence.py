import os
import json
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
    MaturityLevel, EvidenceType, NABHEvidenceRequirement,
    NABHRequirementCitation, NABHSourceDocument
)
from app.nabh.validator import validate_ontology_seeds, ValidationError

# ---------------------------------------------------------------------------
# Fixtures & Helpers for Validator Tests
# ---------------------------------------------------------------------------

def _write_mock_seeds(tmp_path, *, chapters=None, requirements=None, evidence=None, rules=None, citations=None, citation_envelope=True, citation_complete=False):
    """Write mock ontology seed files to the tmp_path directory."""
    if chapters is None:
        chapters = [{
            "code": "FMS",
            "title": "Facility Management and Safety",
            "description": "FMS chapter",
            "display_order": 1,
            "official_standards_count": 1,
            "official_measurable_elements_count": 1,
            "is_fully_seeded": True
        }]
    
    if requirements is None:
        requirements = [{
            "chapter_code": "FMS",
            "edition_version": "6.0",
            "standards": [{
                "code": "FMS-1",
                "title": "Standard 1",
                "description": "Standard 1 desc",
                "display_order": 1,
                "objective_elements": [{
                    "code": "FMS-1.a",
                    "description": "Objective element a",
                    "severity": "major",
                    "display_order": 1,
                    "measurable_elements": [{
                        "code": "FMS-1.a.1",
                        "description": "Measurable element 1",
                        "applicability_default": "applicable",
                        "scoring_weight": 1.0,
                        "risk_weight": 1.0,
                        "default_owner_role": "officer",
                        "display_order": 1
                    }]
                }]
            }]
        }]

    if evidence is None:
        evidence = [{
            "measurable_element_code": "FMS-1.a.1",
            "edition_version": "6.0",
            "evidence_code": "FMS-1.a.1-EV-01",
            "evidence_type": "sop",
            "description": "SOP description",
            "is_mandatory": True,
            "evidence_frequency": "yearly",
            "minimum_lookback_days": 180,
            "default_owner_role": "officer"
        }]

    if rules is None:
        rules = []

    # Write chapters, requirements, evidence, and rules
    for filename, data in [
        ("nabh_6th_chapters.json", chapters),
        ("nabh_6th_requirements.json", requirements),
        ("nabh_6th_evidence_requirements.json", data if (data := evidence) is not None else []),
        ("nabh_6th_applicability_rules.json", rules),
    ]:
        with open(os.path.join(str(tmp_path), filename), "w", encoding="utf-8") as f:
            json.dump(data, f)

    # Write citations if provided
    if citations is not None:
        if citation_envelope:
            payload = {
                "_meta": {
                    "citation_complete": citation_complete,
                    "description": "Mock citations for test"
                },
                "citations": citations
            }
        else:
            payload = citations
        with open(os.path.join(str(tmp_path), "nabh_6th_citations.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f)


# ---------------------------------------------------------------------------
# Validator Unit Tests (Temp Directory Seeds)
# ---------------------------------------------------------------------------

def test_validator_fails_on_no_evidence(tmp_path):
    """Validator fails if a seeded measurable element has zero evidence requirements."""
    _write_mock_seeds(tmp_path, evidence=[])
    with pytest.raises(ValidationError, match="does not have any evidence requirements"):
        validate_ontology_seeds(str(tmp_path), allow_missing_citations=True)


def test_validator_fails_on_no_mandatory_evidence(tmp_path):
    """Validator fails if evidence exists but none are marked mandatory (is_mandatory is False)."""
    evidence = [{
        "measurable_element_code": "FMS-1.a.1",
        "edition_version": "6.0",
        "evidence_code": "FMS-1.a.1-EV-01",
        "evidence_type": "sop",
        "description": "Optional SOP",
        "is_mandatory": False,
        "evidence_frequency": "yearly",
        "minimum_lookback_days": 180,
        "default_owner_role": "officer"
    }]
    _write_mock_seeds(tmp_path, evidence=evidence)
    with pytest.raises(ValidationError, match="does not have any mandatory evidence requirement"):
        validate_ontology_seeds(str(tmp_path), allow_missing_citations=True)


def test_validator_fails_on_invalid_evidence_type(tmp_path):
    """Validator fails if evidence_type is not in VALID_EVIDENCE_TYPES."""
    evidence = [{
        "measurable_element_code": "FMS-1.a.1",
        "edition_version": "6.0",
        "evidence_code": "FMS-1.a.1-EV-01",
        "evidence_type": "invalid_type_here",
        "description": "SOP",
        "is_mandatory": True,
        "evidence_frequency": "yearly",
        "minimum_lookback_days": 180,
        "default_owner_role": "officer"
    }]
    _write_mock_seeds(tmp_path, evidence=evidence)
    with pytest.raises(ValidationError, match="Invalid evidence type"):
        validate_ontology_seeds(str(tmp_path), allow_missing_citations=True)


def test_validator_fails_on_duplicate_evidence_code(tmp_path):
    """Validator fails if the same evidence_code is defined twice for the same measurable element."""
    evidence = [
        {
            "measurable_element_code": "FMS-1.a.1",
            "edition_version": "6.0",
            "evidence_code": "FMS-1.a.1-EV-01",
            "evidence_type": "sop",
            "description": "SOP 1",
            "is_mandatory": True,
            "evidence_frequency": "yearly",
            "minimum_lookback_days": 180,
            "default_owner_role": "officer"
        },
        {
            "measurable_element_code": "FMS-1.a.1",
            "edition_version": "6.0",
            "evidence_code": "FMS-1.a.1-EV-01", # Duplicate evidence_code
            "evidence_type": "register",
            "description": "Register 1",
            "is_mandatory": False,
            "evidence_frequency": "yearly",
            "minimum_lookback_days": 180,
            "default_owner_role": "officer"
        }
    ]
    _write_mock_seeds(tmp_path, evidence=evidence)
    with pytest.raises(ValidationError, match="Duplicate evidence code"):
        validate_ontology_seeds(str(tmp_path), allow_missing_citations=True)


def test_validator_fails_on_invalid_frequency(tmp_path):
    """Validator fails if evidence_frequency is not one of VALID_EVIDENCE_FREQUENCIES."""
    evidence = [{
        "measurable_element_code": "FMS-1.a.1",
        "edition_version": "6.0",
        "evidence_code": "FMS-1.a.1-EV-01",
        "evidence_type": "sop",
        "description": "SOP",
        "is_mandatory": True,
        "evidence_frequency": "hourly_not_supported",
        "minimum_lookback_days": 180,
        "default_owner_role": "officer"
    }]
    _write_mock_seeds(tmp_path, evidence=evidence)
    with pytest.raises(ValidationError, match="Invalid evidence frequency"):
        validate_ontology_seeds(str(tmp_path), allow_missing_citations=True)


def test_validator_fails_on_negative_lookback_days(tmp_path):
    """Validator fails if minimum_lookback_days is negative."""
    evidence = [{
        "measurable_element_code": "FMS-1.a.1",
        "edition_version": "6.0",
        "evidence_code": "FMS-1.a.1-EV-01",
        "evidence_type": "sop",
        "description": "SOP",
        "is_mandatory": True,
        "evidence_frequency": "yearly",
        "minimum_lookback_days": -5,
        "default_owner_role": "officer"
    }]
    _write_mock_seeds(tmp_path, evidence=evidence)
    with pytest.raises(ValidationError, match="Invalid minimum_lookback_days"):
        validate_ontology_seeds(str(tmp_path), allow_missing_citations=True)


def test_validator_fails_on_production_missing_citation(tmp_path):
    """Validator fails in production (allow_missing_citations=False) if a requirement has no citations."""
    # Seed with citations file empty or missing that element
    _write_mock_seeds(tmp_path, citations=[])
    with pytest.raises(ValidationError, match="does not have any citations"):
        validate_ontology_seeds(str(tmp_path), allow_missing_citations=False)


def test_validator_passes_on_partial_citation_complete(tmp_path):
    """Validator passes in production if every element has a citation, even if citation_complete=false."""
    citations = [{
        "measurable_element_code": "FMS-1.a.1",
        "edition_version": "6.0",
        "document_title": "Fire NOC Guide",
        "document_publisher": "Local Government",
        "document_version": "1.0",
        "section": "Sec 1",
        "page_number": "10",
        "clause_text_summary": "Fire clearance summary.",
        "effective_date": "2026-01-01",
        "file_path": "/excerpts/fire_clearance.pdf",
        "url": None
    }]
    # citation_complete=False in _meta
    _write_mock_seeds(tmp_path, citations=citations, citation_complete=False)
    result = validate_ontology_seeds(str(tmp_path), allow_missing_citations=False)
    assert len(result["citations"]) == 1
    assert result["citation_meta"]["citation_complete"] is False


# ---------------------------------------------------------------------------
# API & Database Integration Tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_db(db_session):
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHEvidenceRequirement).delete()
    db_session.query(NABHRequirementCitation).delete()
    db_session.query(NABHSourceDocument).delete()
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


def create_base_test_data(db_session):
    hosp = Hospital(id="test-hosp-14", name="Hospital 14", registration_number="REG-14")
    db_session.add(hosp)
    db_session.commit()

    staff = Staff(
        id="staff-14",
        hospital_id=hosp.id,
        employee_id="EMP-14",
        name="Hospital 14 Admin",
        role=UserRole.HOSPITAL_ADMIN,
        email="admin14@hospital.com",
        is_active=True
    )
    db_session.add(staff)
    db_session.commit()

    ed = NABHEdition(
        id="ed-6.0-test",
        name="NABH 6th Edition",
        version="6.0",
        status=EditionStatus.ACTIVE,
        effective_date=datetime.utcnow()
    )
    db_session.add(ed)
    db_session.commit()

    # Chapter
    chap = NABHChapter(
        id="chap-fms-test",
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
        id="std-fms-1-test",
        edition_id=ed.id,
        chapter_id=chap.id,
        code="1",
        canonical_code="FMS-1",
        title="Standard FMS-1"
    )
    db_session.add(std)
    db_session.commit()

    # Objective
    obj = NABHObjectiveElement(
        id="obj-fms-1-a-test",
        edition_id=ed.id,
        standard_id=std.id,
        code="a",
        canonical_code="FMS-1.a",
        description="Objective FMS-1.a"
    )
    db_session.add(obj)
    db_session.commit()

    # Measurable Element
    me = NABHMeasurableElement(
        id="me-fms-1-a-1-test",
        edition_id=ed.id,
        objective_element_id=obj.id,
        code="1",
        canonical_code="FMS-1.a.1",
        description="Measurable FMS-1.a.1",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    db_session.add(me)
    db_session.commit()

    # Evidence Requirements: 1 mandatory, 1 optional
    ev_mand = NABHEvidenceRequirement(
        id="ev-mand-id",
        measurable_element_id=me.id,
        evidence_code="FMS-1.a.1-EV-01",
        evidence_type=EvidenceType.SOP,
        description="Mandatory SOP for Fire NOC",
        suggested_documentation="Original NOC certificate.",
        is_mandatory=True,
        evidence_frequency="yearly",
        minimum_lookback_days=365,
        default_owner_role="facility_director"
    )
    ev_opt = NABHEvidenceRequirement(
        id="ev-opt-id",
        measurable_element_id=me.id,
        evidence_code="FMS-1.a.1-EV-02",
        evidence_type=EvidenceType.TRAINING_RECORD,
        description="Optional staff training logs",
        suggested_documentation="Sign-in sheets for fire drills.",
        is_mandatory=False,
        evidence_frequency="quarterly",
        minimum_lookback_days=90,
        default_owner_role="safety_officer"
    )
    db_session.add_all([ev_mand, ev_opt])
    db_session.commit()

    # Citation
    source_doc = NABHSourceDocument(
        id="doc-test",
        edition_id=ed.id,
        title="Fire safety laws",
        publisher="National Fire Authority",
        edition_version="2026"
    )
    db_session.add(source_doc)
    db_session.commit()

    citation = NABHRequirementCitation(
        id="cit-test",
        measurable_element_id=me.id,
        document_id=source_doc.id,
        section="Section 5",
        page_number="12",
        clause_text_summary="All hospitals must have a valid NOC.",
        effective_date=datetime(2026, 1, 1),
        file_path="/excerpts/fire_noc_req.pdf"
    )
    db_session.add(citation)
    db_session.commit()

    # Hospital state record
    hosp_req = HospitalNABHRequirement(
        hospital_id=hosp.id,
        requirement_id=me.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.NON_COMPLIANT
    )
    db_session.add(hosp_req)
    db_session.commit()

    return hosp, staff, me, ev_mand, ev_opt, citation


def test_ontology_requirement_detail_endpoint(client, db_session):
    """Ontology requirement detail API returns evidence requirements with suggested_documentation and proof burden summary."""
    hosp, staff, me, ev_mand, ev_opt, citation = create_base_test_data(db_session)
    
    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/ontology/requirements/{me.id}")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    # Check that basic information is populated
    assert res["id"] == me.id
    assert res["canonical_code"] == me.canonical_code
    assert res["code"] == me.code
    assert res["has_citation"] is True
    assert res["has_evidence_requirements"] is True

    # Check Proof Burden Summary fields
    assert res["mandatory_evidence_count"] == 1
    assert res["optional_evidence_count"] == 1
    # evidence_types_required must contain sop and training_record
    assert set(res["evidence_types_required"]) == {"sop", "training_record"}
    # lookback_days_required must be max of 365 and 90, which is 365
    assert res["lookback_days_required"] == 365

    # Check evidence requirements list and suggested_documentation
    evidence_list = res["evidence_requirements"]
    assert len(evidence_list) == 2
    
    mand_res = next(e for e in evidence_list if e["id"] == ev_mand.id)
    assert mand_res["evidence_code"] == "FMS-1.a.1-EV-01"
    assert mand_res["evidence_type"] == "sop"
    assert mand_res["is_mandatory"] is True
    assert mand_res["suggested_documentation"] == "Original NOC certificate."
    assert mand_res["evidence_frequency"] == "yearly"
    assert mand_res["minimum_lookback_days"] == 365
    assert mand_res["default_owner_role"] == "facility_director"

    opt_res = next(e for e in evidence_list if e["id"] == ev_opt.id)
    assert opt_res["evidence_code"] == "FMS-1.a.1-EV-02"
    assert opt_res["evidence_type"] == "training_record"
    assert opt_res["is_mandatory"] is False
    assert opt_res["suggested_documentation"] == "Sign-in sheets for fire drills."
    assert opt_res["evidence_frequency"] == "quarterly"
    assert opt_res["minimum_lookback_days"] == 90
    assert opt_res["default_owner_role"] == "safety_officer"

    app.dependency_overrides.clear()


def test_hospital_requirement_detail_endpoint(client, db_session):
    """Hospital requirement detail API returns ontology requirement with suggested_documentation and proof burden summary."""
    hosp, staff, me, ev_mand, ev_opt, citation = create_base_test_data(db_session)
    
    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.get(f"/api/nabh/requirements/{hosp.id}/{me.id}")
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["hospital_id"] == hosp.id
    assert res["requirement_id"] == me.id
    assert res["applicability_status"] == "applicable"
    assert res["readiness_status"] == "non_compliant"

    # Check ontology requirement detail nested inside
    ont_detail = res["ontology_requirement"]
    assert ont_detail["id"] == me.id
    assert ont_detail["mandatory_evidence_count"] == 1
    assert ont_detail["optional_evidence_count"] == 1
    assert set(ont_detail["evidence_types_required"]) == {"sop", "training_record"}
    assert ont_detail["lookback_days_required"] == 365

    # Check nested evidence requirements
    evs = ont_detail["evidence_requirements"]
    assert len(evs) == 2
    mand_ev = next(e for e in evs if e["id"] == ev_mand.id)
    assert mand_ev["suggested_documentation"] == "Original NOC certificate."
    assert mand_ev["evidence_frequency"] == "yearly"

    app.dependency_overrides.clear()


def test_patch_hospital_requirement_endpoint(client, db_session):
    """PATCH hospital requirement API updates fields and returns nested ontology detail with proof burden summary."""
    hosp, staff, me, ev_mand, ev_opt, citation = create_base_test_data(db_session)
    
    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    patch_payload = {
        "readiness_status": "compliant",
        "maturity_level": 3,
        "evidence_status": "verified"
    }

    response = client.patch(f"/api/nabh/requirements/{hosp.id}/{me.id}", json=patch_payload)
    assert response.status_code == status.HTTP_200_OK
    res = response.json()

    assert res["readiness_status"] == "compliant"
    assert res["maturity_level"] == 3
    assert res["evidence_status"] == "verified"

    # Check Proof Burden Summary fields are present on the returned ontology requirement
    ont_detail = res["ontology_requirement"]
    assert ont_detail["mandatory_evidence_count"] == 1
    assert ont_detail["optional_evidence_count"] == 1
    assert set(ont_detail["evidence_types_required"]) == {"sop", "training_record"}
    assert ont_detail["lookback_days_required"] == 365

    app.dependency_overrides.clear()


def test_legacy_rows_ignored_in_detail(client, db_session):
    """Legacy models (ComplianceRecord, NABHObjective) do not affect detail API endpoints."""
    hosp, staff, me, ev_mand, ev_opt, citation = create_base_test_data(db_session)

    # Seed legacy ComplianceRecord
    legacy_rec = ComplianceRecord(
        id="legacy-rec-id-14",
        hospital_id=hosp.id,
        standard_code="FMS-1.a",
        standard_name="Legacy Standard",
        status=ComplianceStatus.COMPLIANT
    )
    db_session.add(legacy_rec)

    # Seed legacy NABHObjective
    legacy_obj = NABHObjective(
        id="legacy-obj-id-14",
        hospital_id=hosp.id,
        chapter_code="FMS",
        objective_number=1,
        element_letter="a",
        standard_code="FMS-1.a",
        standard_name="Legacy Standard Name",
        maturity_level=MaturityLevel.IMPLEMENTED
    )
    db_session.add(legacy_obj)
    db_session.commit()

    async def get_mock_user():
        return staff
    app.dependency_overrides[get_current_user] = get_mock_user

    # Query requirement detail, should work fine and ignore legacy tables
    response = client.get(f"/api/nabh/ontology/requirements/{me.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["mandatory_evidence_count"] == 1

    response = client.get(f"/api/nabh/requirements/{hosp.id}/{me.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["ontology_requirement"]["mandatory_evidence_count"] == 1

    app.dependency_overrides.clear()
