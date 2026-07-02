from datetime import datetime

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
    Hospital,
    HospitalNABHRequirement,
    MaturityLevel,
    NABHChapter,
    NABHEdition,
    NABHEvidenceRequirement,
    NABHMeasurableElement, NABHRequirement,
    NABHObjectiveElement,
    NABHRequirementCitation,
    NABHSourceDocument,
    NABHStandard,
    Staff,
    UserRole,
)
from app.nabh.explanation import build_requirement_explanation
from app.nabh.quality import (
    NABHQualityError,
    assert_requirement_agent_retrievable,
    assert_requirement_has_evidence_definitions,
    validate_requirement_runtime_quality,
)


@pytest.fixture(autouse=True)
def clean_db(db_session):
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.query(HospitalNABHRequirement).delete()
    db_session.query(NABHRequirementCitation).delete()
    db_session.query(NABHSourceDocument).delete()
    db_session.query(NABHEvidenceRequirement).delete()
    db_session.query(NABHRequirement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.query(Staff).delete()
    db_session.query(Hospital).delete()
    db_session.commit()
    yield
    app.dependency_overrides.clear()


def create_requirement_graph(
    db_session,
    *,
    with_evidence=True,
    with_citation=True,
    citation_locator=True,
    retired_document=False,
    evidence_description="Fire NOC certificate.",
):
    hospital = Hospital(id="hosp-task18", name="Task 18 Hospital", registration_number="TASK18")
    staff = Staff(
        id="staff-task18",
        hospital_id=hospital.id,
        employee_id="EMP-T18",
        name="Task 18 Admin",
        role=UserRole.HOSPITAL_ADMIN,
        email="task18@example.com",
        is_active=True,
    )
    edition = NABHEdition(
        id="edition-task18",
        name="NABH 6th Edition",
        version="6.0",
        status=EditionStatus.ACTIVE,
        effective_date=datetime.utcnow(),
    )
    chapter = NABHChapter(
        id="chapter-task18",
        edition_id=edition.id,
        code="FMS",
        canonical_code="FMS",
        title="Facility Management and Safety",
        display_order=1,
        official_standards_count=1,
        official_measurable_elements_count=1,
    )
    standard = NABHStandard(
        id="standard-task18",
        edition_id=edition.id,
        chapter_id=chapter.id,
        code="1",
        canonical_code="FMS.1",
        title="Fire Safety",
    )
    objective = NABHObjectiveElement(
        id="objective-task18",
        edition_id=edition.id,
        standard_id=standard.id,
        code="a",
        canonical_code="FMS.1.a",
        description="Fire safety objective.",
    )
    requirement = NABHRequirement(
        id="requirement-task18",
        edition_id=edition.id,
        standard_id=standard.id,
        official_code="FMS 1.a.1",
        canonical_code="FMS 1 a 1",
        display_text="The hospital maintains a valid Fire NOC.",
        applicability_default=ApplicabilityDefault.APPLICABLE,
        publication_status=KnowledgePublicationStatus.PUBLISHED,
        source_status="official_verified"
    )

    db_session.add_all([hospital, staff, edition, chapter, standard, objective, requirement])
    db_session.flush()

    if with_evidence:
        db_session.add(
            NABHEvidenceRequirement(
                id="evidence-task18",
                requirement_id=requirement.id,
                evidence_code="FMS.1.a.1.EV.01",
                evidence_type=EvidenceType.LICENSE,
                description=evidence_description,
                suggested_documentation="Valid Fire NOC certificate.",
                is_mandatory=True,
                minimum_lookback_days=365,
            )
        )

    if with_citation:
        document = NABHSourceDocument(
            id="document-task18",
            edition_id=edition.id,
            title="NABH Reference Guide",
            publisher="NABH",
            edition_version="6.0",
            effective_date=datetime.utcnow(),
            retired_at=datetime.utcnow() if retired_document else None,
        )
        citation = NABHRequirementCitation(
            id="citation-task18",
            requirement_id=requirement.id,
            document_id=document.id,
            section="FMS",
            page_number="184" if citation_locator else None,
            clause_text_summary="Fire safety clearance is reviewable." if citation_locator else None,
            file_path="/citations/fms-fire-noc.png" if citation_locator else None,
        )
        if not citation_locator:
            citation.section = None
        db_session.add_all([document, citation])

    state = HospitalNABHRequirement(
        id="state-task18",
        hospital_id=hospital.id,
        requirement_id=requirement.id,
        applicability_status=ApplicabilityDefault.APPLICABLE,
        applicability_reason="Default applicability.",
        maturity_level=MaturityLevel.NON_EXISTENT,
        readiness_status=ComplianceStatus.UNDER_REVIEW,
    )
    db_session.add(state)
    db_session.commit()
    return hospital, staff, edition, chapter, standard, objective, requirement, state


def test_runtime_quality_rejects_missing_citation_for_agent_retrieval(db_session):
    *_prefix, requirement, _state = create_requirement_graph(db_session, with_citation=False)

    report = validate_requirement_runtime_quality(db_session, requirement.id)
    assert "missing active citation with active source document" in report.errors

    with pytest.raises(NABHQualityError, match="not agent-retrievable"):
        assert_requirement_agent_retrievable(db_session, requirement.id)


def test_admin_explanation_can_degrade_for_uncited_requirement(db_session):
    *_prefix, requirement, _state = create_requirement_graph(db_session, with_citation=False)

    explanation = build_requirement_explanation(
        db_session,
        requirement.id,
        hospital_id="hosp-task18",
        edition_version="6.0",
    )

    assert explanation["confidence"] == "missing_citation"
    assert "No citation is available for this requirement." in explanation["limitations"]


def test_runtime_quality_rejects_citation_without_locator(db_session):
    *_prefix, requirement, _state = create_requirement_graph(db_session, citation_locator=False)

    report = validate_requirement_runtime_quality(db_session, requirement.id)

    assert "missing citation locator" in report.errors


def test_runtime_quality_rejects_retired_source_document(db_session):
    *_prefix, requirement, _state = create_requirement_graph(db_session, retired_document=True)

    report = validate_requirement_runtime_quality(db_session, requirement.id)

    assert "missing active citation with active source document" in report.errors


def test_runtime_quality_rejects_retired_edition_chain_for_agent_retrieval(db_session):
    *_prefix, requirement, _state = create_requirement_graph(db_session)
    edition = db_session.query(NABHEdition).filter_by(id="edition-task18").first()
    edition.retired_at = datetime.utcnow()
    db_session.commit()

    with pytest.raises(NABHQualityError, match="retired ontology chain"):
        assert_requirement_agent_retrievable(db_session, requirement.id)


def test_runtime_quality_rejects_placeholder_evidence_description(db_session):
    *_prefix, requirement, _state = create_requirement_graph(
        db_session,
        evidence_description="TBD",
    )

    with pytest.raises(NABHQualityError, match="active evidence requirement definitions"):
        assert_requirement_has_evidence_definitions(db_session, requirement.id)


def test_partial_ontology_does_not_require_all_official_elements(db_session):
    *_prefix, requirement, _state = create_requirement_graph(db_session)
    chapter = db_session.query(NABHChapter).filter_by(id="chapter-task18").first()
    chapter.official_requirements_count = 639
    chapter.official_measurable_elements_count = 639
    db_session.commit()

    report = validate_requirement_runtime_quality(db_session, requirement.id)

    assert report.ok


def test_cannot_mark_requirement_compliant_without_evidence_definitions(client, db_session):
    hospital, staff, *_rest = create_requirement_graph(db_session, with_evidence=False)

    async def get_mock_user():
        return staff

    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.patch(
        f"/api/nabh/requirements/{hospital.id}/requirement-task18",
        json={"readiness_status": "compliant"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot be marked compliant" in response.json()["detail"]


def test_can_mark_requirement_compliant_when_evidence_definitions_exist(client, db_session):
    hospital, staff, *_rest = create_requirement_graph(db_session)

    async def get_mock_user():
        return staff

    app.dependency_overrides[get_current_user] = get_mock_user

    response = client.patch(
        f"/api/nabh/requirements/{hospital.id}/requirement-task18",
        json={"readiness_status": "compliant"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["readiness_status"] == "compliant"
