from datetime import datetime, timedelta

import pytest
from fastapi import status
from sqlalchemy import text

from app.api.auth import get_current_user
from app.main import app
from app.models.database import (
    KnowledgePublicationStatus,
    ApplicabilityDefault,
    ComplianceStatus,
    EditionStatus,
    EvidenceType,
    EvidenceStatus,
    Hospital,
    HospitalNABHRequirement,
    MaturityLevel,
    NABHChapter,
    NABHEdition,
    NABHEvidenceRequirement,
    NABHLegacyMigrationMap,
    NABHMeasurableElement, NABHRequirement,
    NABHObjective,
    NABHObjectiveElement,
    NABHStandard,
    Staff,
    UserRole,
)
from app.nabh.migration_bridge import migrate_hospital_legacy_nabh_state


@pytest.fixture(autouse=True)
def clean_db(db_session):
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.query(NABHLegacyMigrationMap).delete()
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHEvidenceRequirement).delete()
    db_session.query(NABHRequirement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.query(NABHObjective).delete()
    db_session.query(Staff).delete()
    db_session.query(Hospital).delete()
    db_session.commit()
    yield
    app.dependency_overrides.clear()


def setup_base_data(db_session):
    hospital = Hospital(id="hosp-task19", name="Task 19 Hospital", registration_number="TASK19")
    other_hospital = Hospital(id="hosp-other", name="Other Hospital", registration_number="OTHER19")
    staff = Staff(
        id="staff-task19",
        hospital_id=hospital.id,
        employee_id="EMP-T19",
        name="Task 19 Admin",
        role=UserRole.HOSPITAL_ADMIN,
        email="task19@example.com",
        is_active=True,
    )
    other_staff = Staff(
        id="staff-other",
        hospital_id=other_hospital.id,
        employee_id="EMP-OTHER19",
        name="Other Admin",
        role=UserRole.HOSPITAL_ADMIN,
        email="other19@example.com",
        is_active=True,
    )
    edition = NABHEdition(
        id="edition-task19",
        name="NABH 6th Edition",
        version="6.0",
        status=EditionStatus.ACTIVE,
        effective_date=datetime.utcnow(),
    )
    chapter = NABHChapter(
        id="chapter-fms-task19",
        edition_id=edition.id,
        code="FMS",
        canonical_code="FMS",
        title="Facility Management and Safety",
        display_order=1,
        official_standards_count=1,
        official_measurable_elements_count=3,
    )
    standard = NABHStandard(
        id="standard-fms-1-task19",
        edition_id=edition.id,
        chapter_id=chapter.id,
        code="1",
        canonical_code="FMS.1",
        title="Fire Safety",
        display_order=1,
    )
    objective = NABHObjectiveElement(
        id="objective-fms-1-a-task19",
        edition_id=edition.id,
        standard_id=standard.id,
        code="a",
        canonical_code="FMS.1.a",
        description="Fire safety objective.",
        display_order=1,
    )
    requirements = []
    for number in [1, 2, 3]:
        requirement = NABHRequirement(
            id=f"requirement-fms-1-a-{number}",
            edition_id=edition.id,
            standard_id=std.id,
            code=str(number,
        publication_status=KnowledgePublicationStatus.PUBLISHED,
        source_status="official_verified"),
            canonical_code=f"FMS-1.a.{number}",
            description=f"Fire safety requirement {number}.",
            applicability_default=ApplicabilityDefault.APPLICABLE,
            display_order=number,
        )
        requirements.append(requirement)
        db_session.add(requirement)
    db_session.add_all([hospital, other_hospital, staff, other_staff, edition, chapter, standard, objective])
    db_session.flush()
    for requirement in requirements:
        db_session.add(NABHEvidenceRequirement(
            requirement_id=requirement.id,
            evidence_code=f"{requirement.canonical_code}-EV-01",
            evidence_type=EvidenceType.LICENSE,
            description="Valid evidence definition.",
            is_mandatory=True,
            minimum_lookback_days=90,
        ))
    db_session.commit()
    return hospital, other_hospital, staff, other_staff, edition, requirements


def add_legacy_objective(
    db_session,
    hospital_id,
    code,
    *,
    maturity=MaturityLevel.IMPLEMENTED,
    remediation_owner=None,
    assessed_by="System Agent",
):
    legacy = NABHObjective(
        id=f"legacy-{code.lower().replace('.', '-').replace('-', '_')}",
        hospital_id=hospital_id,
        chapter_code=code.split("-")[0],
        objective_number=1,
        element_letter="a",
        standard_code=code,
        standard_name=f"Legacy {code}",
        maturity_level=maturity,
        remediation_deadline=datetime.utcnow() + timedelta(days=30),
        remediation_owner=remediation_owner,
        last_assessed=datetime.utcnow(),
        assessed_by=assessed_by,
    )
    db_session.add(legacy)
    db_session.commit()
    return legacy


def test_maps_legacy_objective_by_exact_measurable_element_code(db_session):
    hospital, _other_hospital, staff, _other_staff, _edition, requirements = setup_base_data(db_session)
    legacy = add_legacy_objective(
        db_session,
        hospital.id,
        "FMS.1.a.1",
        remediation_owner=staff.id,
        assessed_by=staff.id,
    )

    report = migrate_hospital_legacy_nabh_state(db_session, hospital.id)
    db_session.commit()

    assert report["legacy_records_seen"] == 1
    assert report["created_requirement_rows"] == 1
    state = db_session.query(HospitalNABHRequirement).filter_by(
        hospital_id=hospital.id,
        requirement_id=requirements[0].id,
    ).first()
    assert state is not None
    assert state.readiness_status == ComplianceStatus.COMPLIANT
    assert state.owner_id == staff.id
    assert state.last_reviewed_by == staff.id

    mapping = db_session.query(NABHLegacyMigrationMap).filter_by(legacy_objective_id=legacy.id).first()
    assert mapping.mapping_level == "measurable_element"
    assert mapping.mapping_status == "mapped"


def test_maps_legacy_objective_by_objective_element_code(db_session):
    hospital, *_rest = setup_base_data(db_session)
    add_legacy_objective(db_session, hospital.id, "FMS.1.a", maturity=MaturityLevel.DEFINED)

    report = migrate_hospital_legacy_nabh_state(db_session, hospital.id)
    db_session.commit()

    assert report["created_requirement_rows"] == 3
    assert "mapped to 3 requirements at objective_element level" in " ".join(report["warnings"])
    states = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hospital.id).all()
    assert len(states) == 3
    assert all(state.readiness_status == ComplianceStatus.PARTIALLY_COMPLIANT for state in states)


def test_maps_legacy_objective_by_standard_code(db_session):
    hospital, *_rest = setup_base_data(db_session)
    add_legacy_objective(db_session, hospital.id, "FMS.1", maturity=MaturityLevel.NON_EXISTENT)

    report = migrate_hospital_legacy_nabh_state(db_session, hospital.id)
    db_session.commit()

    assert report["created_requirement_rows"] == 3
    states = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hospital.id).all()
    assert len(states) == 3
    assert all(state.readiness_status == ComplianceStatus.NON_COMPLIANT for state in states)


def test_unmapped_legacy_objective_is_recorded_without_creating_state(db_session):
    hospital, *_rest = setup_base_data(db_session)
    legacy = add_legacy_objective(db_session, hospital.id, "ROM-99.z")

    report = migrate_hospital_legacy_nabh_state(db_session, hospital.id)
    db_session.commit()

    assert report["unmapped_legacy_records"] == 1
    assert report["created_requirement_rows"] == 0
    assert db_session.query(HospitalNABHRequirement).count() == 0
    mapping = db_session.query(NABHLegacyMigrationMap).filter_by(legacy_objective_id=legacy.id).first()
    assert mapping.mapping_status == "unmapped"
    assert mapping.new_requirement_id is None


def test_migration_preserves_existing_new_requirement_state(db_session):
    hospital, *_prefix, requirements = setup_base_data(db_session)
    add_legacy_objective(db_session, hospital.id, "FMS.1.a.1", maturity=MaturityLevel.IMPLEMENTED)
    existing = HospitalNABHRequirement(
        hospital_id=hospital.id,
        requirement_id=requirements[0].id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        readiness_status=ComplianceStatus.NON_COMPLIANT,
        maturity_level=MaturityLevel.NON_EXISTENT,
        evidence_status=EvidenceStatus.MISSING,
    )
    db_session.add(existing)
    db_session.commit()

    report = migrate_hospital_legacy_nabh_state(db_session, hospital.id)
    db_session.commit()

    assert report["skipped_existing_rows"] == 1
    refreshed = db_session.query(HospitalNABHRequirement).filter_by(id=existing.id).first()
    assert refreshed.readiness_status == ComplianceStatus.NON_COMPLIANT


def test_migration_is_idempotent(db_session):
    hospital, *_rest = setup_base_data(db_session)
    add_legacy_objective(db_session, hospital.id, "FMS.1.a.1")

    first = migrate_hospital_legacy_nabh_state(db_session, hospital.id)
    db_session.commit()
    second = migrate_hospital_legacy_nabh_state(db_session, hospital.id)
    db_session.commit()

    assert first["created_requirement_rows"] == 1
    assert second["created_requirement_rows"] == 0
    assert second["skipped_existing_rows"] == 1
    assert db_session.query(HospitalNABHRequirement).count() == 1
    assert db_session.query(NABHLegacyMigrationMap).count() == 1


def test_dry_run_reports_without_writing_rows(db_session):
    hospital, *_rest = setup_base_data(db_session)
    add_legacy_objective(db_session, hospital.id, "FMS.1.a.1")

    report = migrate_hospital_legacy_nabh_state(db_session, hospital.id, dry_run=True)

    assert report["dry_run"] is True
    assert report["created_requirement_rows"] == 1
    assert db_session.query(HospitalNABHRequirement).count() == 0
    assert db_session.query(NABHLegacyMigrationMap).count() == 0


def test_cross_hospital_review_staff_is_not_copied(db_session):
    hospital, _other_hospital, _staff, other_staff, _edition, _requirements = setup_base_data(db_session)
    add_legacy_objective(
        db_session,
        hospital.id,
        "FMS.1.a.1",
        assessed_by=other_staff.id,
        remediation_owner=other_staff.id,
    )

    report = migrate_hospital_legacy_nabh_state(db_session, hospital.id)
    db_session.commit()

    state = db_session.query(HospitalNABHRequirement).filter_by(hospital_id=hospital.id).first()
    assert state.owner_id is None
    assert state.last_reviewed_by is None
    assert "not active in this hospital" in " ".join(report["warnings"])


def test_migration_endpoint_returns_report(client, db_session):
    hospital, _other_hospital, staff, _other_staff, _edition, _requirements = setup_base_data(db_session)
    add_legacy_objective(db_session, hospital.id, "FMS.1.a.1")

    async def get_mock_user():
        return staff

    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.post(f"/api/nabh/migration/{hospital.id}/legacy-bridge?dry_run=true")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["legacy_records_seen"] == 1
    assert response.json()["created_requirement_rows"] == 1
    assert db_session.query(HospitalNABHRequirement).count() == 0
