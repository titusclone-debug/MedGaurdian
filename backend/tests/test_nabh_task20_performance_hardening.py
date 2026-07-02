from datetime import datetime

from app.api.auth import get_current_user
from app.main import app
from app.models.database import (
    KnowledgePublicationStatus,
    ApplicabilityDefault,
    ComplianceStatus,
    EditionStatus,
    EvidenceStatus,
    EvidenceType,
    Hospital,
    HospitalNABHRequirement,
    HospitalRequirementEvidenceLink,
    HospitalAccreditationProfile,
    MaturityLevel,
    NABHChapter,
    NABHEdition,
    NABHEvidenceRequirement,
    NABHLegacyMigrationMap,
    NABHMeasurableElement, NABHRequirement,
    NABHObjective,
    NABHObjectiveElement,
    NABHRequirementCitation,
    NABHSourceDocument,
    NABHStandard,
    Staff,
    UserRole,
)


def _clean(db_session):
    db_session.query(NABHLegacyMigrationMap).delete()
    db_session.query(HospitalRequirementEvidenceLink).delete()
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHEvidenceRequirement).delete()
    db_session.query(NABHRequirementCitation).delete()
    db_session.query(NABHSourceDocument).delete()
    db_session.query(NABHRequirement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.query(NABHObjective).delete()
    db_session.query(HospitalAccreditationProfile).delete()
    db_session.query(Staff).delete()
    db_session.query(Hospital).delete()
    db_session.commit()


def _seed_bulk_evidence_fixture(db_session):
    hospital = Hospital(id="hosp-task20", name="Task 20 Hospital", registration_number="TASK20")
    staff = Staff(
        id="staff-task20",
        hospital_id=hospital.id,
        employee_id="TASK20",
        name="Task 20 Admin",
        role=UserRole.HOSPITAL_ADMIN,
        email="task20@example.com",
        is_active=True,
    )
    edition = NABHEdition(
        id="edition-task20",
        name="NABH 6th Edition",
        version="6.0",
        status=EditionStatus.ACTIVE,
        effective_date=datetime.utcnow(),
    )
    chapter = NABHChapter(
        id="chapter-fms-task20",
        edition_id=edition.id,
        code="FMS",
        canonical_code="FMS",
        title="Facility Management and Safety",
        display_order=1,
        official_standards_count=1,
        official_measurable_elements_count=3,
    )
    standard = NABHStandard(
        id="standard-fms-task20",
        edition_id=edition.id,
        chapter_id=chapter.id,
        code="FMS.1",
        canonical_code="FMS.1",
        title="Facility safety",
        display_order=1,
    )
    objective = NABHObjectiveElement(
        id="objective-fms-task20",
        edition_id=edition.id,
        standard_id=standard.id,
        code="FMS.1.a",
        canonical_code="FMS.1.a",
        description="Fire safety records are maintained.",
        display_order=1,
    )
    source = NABHSourceDocument(
        id="source-task20",
        edition_id=edition.id,
        title="NABH Reference Guide",
        publisher="NABH",
        edition_version="6.0",
    )
    db_session.add_all([hospital, staff, edition, chapter, standard, objective, source])
    db_session.flush()

    requirements = []
    states = []
    for index, applicability in enumerate(
        [
            ApplicabilityDefault.APPLICABLE,
            ApplicabilityDefault.MANUAL_REVIEW,
            ApplicabilityDefault.NOT_APPLICABLE,
        ],
        start=1,
    ):
        requirement = NABHRequirement(
            id=f"requirement-task20-{index}",
            edition_id=edition.id,
            standard_id=std.id,
            code=str(index,
        publication_status=KnowledgePublicationStatus.PUBLISHED,
        source_status="official_verified"),
            canonical_code=f"FMS-1.a.{index}",
            description=f"Requirement {index}",
            applicability_default=ApplicabilityDefault.APPLICABLE,
            default_owner_role="facility_director",
            display_order=index,
        )
        requirements.append(requirement)
        states.append(
            HospitalNABHRequirement(
                id=f"state-task20-{index}",
                hospital_id=hospital.id,
                requirement_id=requirement.id,
                applicability_status=applicability,
                applicability_reason="Task 20 scope fixture.",
                maturity_level=MaturityLevel.NON_EXISTENT,
                evidence_status=EvidenceStatus.MISSING,
                readiness_status=ComplianceStatus.UNDER_REVIEW,
                owner_id=staff.id if index == 1 else None,
            )
        )
        db_session.add(requirement)
        db_session.flush()
        db_session.add(
            NABHEvidenceRequirement(
                id=f"evidence-task20-{index}",
                requirement_id=requirement.id,
                evidence_code=f"FMS-1.a.{index}-EV-01",
                evidence_type=EvidenceType.LICENSE,
                description=f"Evidence for requirement {index}",
                suggested_documentation="Current certificate.",
                is_mandatory=True,
                minimum_lookback_days=365,
                default_owner_role="facility_director",
            )
        )
        db_session.add(
            NABHRequirementCitation(
                id=f"citation-task20-{index}",
                requirement_id=requirement.id,
                document_id=source.id,
                section="FMS",
                page_number=str(100 + index),
                clause_text_summary="Source-backed evidence requirement.",
            )
        )

    db_session.add_all(states)
    db_session.commit()
    return hospital, staff


def test_bulk_evidence_plan_returns_scoped_evidence_without_per_requirement_explanations(client, db_session):
    _clean(db_session)
    hospital, staff = _seed_bulk_evidence_fixture(db_session)

    def mock_user():
        return staff

    app.dependency_overrides[get_current_user] = mock_user
    try:
        response = client.get(f"/api/nabh/requirements/{hospital.id}/evidence-plan?limit=10")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_applicable_requirements"] == 2
    assert payload["returned_requirements"] == 2
    assert payload["evidence_item_count"] == 2
    assert [item["requirement_code"] for item in payload["items"]] == ["FMS.1.a.1", "FMS.1.a.2"]
    assert payload["items"][0]["responsible_owner_name"] == "Task 20 Admin"
    assert payload["items"][0]["confidence"] == "source_cited"
    assert payload["items"][0]["required_evidence"][0]["evidence_code"] == "FMS.1.a.1.EV.01"
