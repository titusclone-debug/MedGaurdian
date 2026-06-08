import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

from app.models.database import (
    Hospital, Staff, UserRole, NABHEdition, EditionStatus,
    NABHChapter, NABHStandard, NABHObjectiveElement, NABHMeasurableElement,
    NABHEvidenceRequirement, ApplicabilityDefault, EvidenceType,
    EvidenceStatus, VerificationStatus, HospitalNABHRequirement,
    HospitalRequirementEvidenceLink, ComplianceStatus, MaturityLevel
)

def test_hospital_requirement_and_evidence_smoke(db_session):
    # Enable foreign keys for SQLite in-memory DB connection
    db_session.execute(text("PRAGMA foreign_keys=ON"))

    # 1. Seed base references
    hospital = Hospital(
        id="hosp-task4-smoke",
        name="Task 4 Smoke Hospital",
        registration_number="REG-T4",
        nabh_edition="6th",
        bed_count=50
    )
    db_session.add(hospital)
    
    staff_owner = Staff(
        id="staff-owner",
        hospital_id="hosp-task4-smoke",
        employee_id="EMP-T4-O",
        name="Owner Staff",
        role=UserRole.COMPLIANCE_OFFICER,
        email="owner@task4.com",
        is_active=True
    )
    staff_reviewer = Staff(
        id="staff-reviewer",
        hospital_id="hosp-task4-smoke",
        employee_id="EMP-T4-R",
        name="Reviewer Staff",
        role=UserRole.COMPLIANCE_OFFICER,
        email="reviewer@task4.com",
        is_active=True
    )
    db_session.add(staff_owner)
    db_session.add(staff_reviewer)

    edition = NABHEdition(
        id="edition-6",
        name="NABH 6th Edition",
        version="6.0",
        status=EditionStatus.ACTIVE,
        effective_date=datetime.utcnow()
    )
    db_session.add(edition)
    db_session.flush()

    chapter = NABHChapter(
        id="chap-acc",
        edition_id="edition-6",
        code="ACC",
        canonical_code="ACC-6.0",
        title="Access, Assessment and Care of Patients"
    )
    db_session.add(chapter)
    db_session.flush()

    standard = NABHStandard(
        id="std-aac1",
        edition_id="edition-6",
        chapter_id="chap-acc",
        code="AAC 1",
        canonical_code="AAC-1-6.0",
        title="Admission Criteria"
    )
    db_session.add(standard)
    db_session.flush()

    obj_el = NABHObjectiveElement(
        id="obj-el-1a",
        edition_id="edition-6",
        standard_id="std-aac1",
        code="a",
        canonical_code="AAC-1.a-6.0",
        description="The organization has a documented admission registration protocol."
    )
    db_session.add(obj_el)
    db_session.flush()

    meas_el = NABHMeasurableElement(
        id="meas-el-1a1",
        edition_id="edition-6",
        objective_element_id="obj-el-1a",
        code="1",
        canonical_code="AAC-1.a.1-6.0",
        description="Documented registration process.",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    db_session.add(meas_el)
    db_session.flush()

    ev_req = NABHEvidenceRequirement(
        id="ev-req-sop",
        measurable_element_id="meas-el-1a1",
        evidence_type=EvidenceType.SOP,
        description="Standard Operating Procedure for Patient Registration",
        is_mandatory=True,
        minimum_lookback_days=180
    )
    db_session.add(ev_req)
    db_session.commit()

    # 2. Insert HospitalNABHRequirement (State)
    hosp_req = HospitalNABHRequirement(
        id="hosp-req-state",
        hospital_id="hosp-task4-smoke",
        requirement_id="meas-el-1a1",
        applicability_status=ApplicabilityDefault.APPLICABLE,
        maturity_level=MaturityLevel.DEFINED,
        evidence_status=EvidenceStatus.DRAFT,
        owner_id="staff-owner",
        last_reviewed_by="staff-reviewer",
        readiness_status=ComplianceStatus.UNDER_REVIEW
    )
    db_session.add(hosp_req)
    db_session.commit()

    # 3. Insert HospitalRequirementEvidenceLink
    ev_link = HospitalRequirementEvidenceLink(
        id="ev-link-pdf",
        hospital_requirement_id="hosp-req-state",
        evidence_requirement_id="ev-req-sop",
        document_name="Admission_SOP_v2.pdf",
        file_path_or_url="/uploads/Admission_SOP_v2.pdf",
        verification_status=VerificationStatus.PENDING,
        uploaded_by="staff-owner"
    )
    db_session.add(ev_link)
    db_session.commit()

    # 4. Verify relationships from both directions
    # Hospital -> HospitalNABHRequirement
    assert len(hospital.nabh_requirements) == 1
    assert hospital.nabh_requirements[0].id == "hosp-req-state"
    # HospitalNABHRequirement -> Hospital
    assert hosp_req.hospital.id == "hosp-task4-smoke"

    # NABHMeasurableElement -> HospitalNABHRequirement
    assert len(meas_el.hospital_states) == 1
    assert meas_el.hospital_states[0].id == "hosp-req-state"
    # HospitalNABHRequirement -> NABHMeasurableElement
    assert hosp_req.measurable_element.id == "meas-el-1a1"

    # HospitalNABHRequirement -> HospitalRequirementEvidenceLink
    assert len(hosp_req.evidence_links) == 1
    assert hosp_req.evidence_links[0].id == "ev-link-pdf"
    # HospitalRequirementEvidenceLink -> HospitalNABHRequirement
    assert ev_link.hospital_requirement.id == "hosp-req-state"

    # NABHEvidenceRequirement -> HospitalRequirementEvidenceLink
    assert len(ev_req.evidence_links) == 1
    assert ev_req.evidence_links[0].id == "ev-link-pdf"
    # HospitalRequirementEvidenceLink -> NABHEvidenceRequirement
    assert ev_link.evidence_requirement.id == "ev-req-sop"

    # Staff relations
    assert hosp_req.owner.id == "staff-owner"
    assert hosp_req.reviewer.id == "staff-reviewer"
    assert ev_link.uploader.id == "staff-owner"
    assert ev_link.verifier is None

    # 5. Verify Uniqueness Constraints
    # hospital_id + requirement_id uniqueness on HospitalNABHRequirement
    duplicate_req = HospitalNABHRequirement(
        id="hosp-req-duplicate",
        hospital_id="hosp-task4-smoke",
        requirement_id="meas-el-1a1"
    )
    db_session.add(duplicate_req)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # hospital_requirement_id + evidence_requirement_id uniqueness on HospitalRequirementEvidenceLink
    duplicate_link = HospitalRequirementEvidenceLink(
        id="ev-link-duplicate",
        hospital_requirement_id="hosp-req-state",
        evidence_requirement_id="ev-req-sop",
        document_name="Duplicate.pdf",
        file_path_or_url="/uploads/Duplicate.pdf"
    )
    db_session.add(duplicate_link)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 6. Verify ON DELETE SET NULL for staff deletions
    db_session.delete(staff_owner)
    db_session.commit()
    db_session.refresh(hosp_req)
    db_session.refresh(ev_link)
    assert hosp_req.owner_id is None
    assert hosp_req.owner is None
    assert ev_link.uploaded_by is None
    assert ev_link.uploader is None

    # 7. Verify CASCADE DELETE on Hospital deletion
    db_session.delete(staff_reviewer)
    db_session.delete(hospital)
    db_session.commit()
    # Check that requirement state and evidence link are cascade deleted
    assert db_session.get(HospitalNABHRequirement, "hosp-req-state") is None
    assert db_session.get(HospitalRequirementEvidenceLink, "ev-link-pdf") is None
