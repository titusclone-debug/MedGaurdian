import pytest
from sqlalchemy import text
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement, NABHObjective,
    EditionStatus, ApplicabilityDefault, EvidenceType,
    NABHEvidenceRequirement, NABHRequirementCitation, NABHSourceDocument,
    NABHApplicabilityRule
)
from app.nabh.seeder import seed_versioned_ontology
from app.nabh.constants import VALID_EVIDENCE_TYPES

@pytest.fixture(autouse=True)
def clean_db(db_session):
    # Enable foreign keys
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.query(NABHRequirementCitation).delete()
    db_session.query(NABHSourceDocument).delete()
    db_session.query(NABHEvidenceRequirement).delete()
    db_session.query(NABHApplicabilityRule).delete()
    db_session.query(NABHMeasurableElement).delete()
    db_session.query(NABHObjectiveElement).delete()
    db_session.query(NABHStandard).delete()
    db_session.query(NABHChapter).delete()
    db_session.query(NABHEdition).delete()
    db_session.commit()
    yield

def test_nabh_ontology_seed_is_idempotent(db_session):
    # Run seeder the first time
    seed_versioned_ontology(db_session, "app/nabh/data", "6.0")

    # Capture initial counts
    edition_count = db_session.query(NABHEdition).count()
    chapter_count = db_session.query(NABHChapter).count()
    standard_count = db_session.query(NABHStandard).count()
    obj_count = db_session.query(NABHObjectiveElement).count()
    me_count = db_session.query(NABHMeasurableElement).count()
    rule_count = db_session.query(NABHApplicabilityRule).count()
    ev_count = db_session.query(NABHEvidenceRequirement).count()
    cit_count = db_session.query(NABHRequirementCitation).count()
    doc_count = db_session.query(NABHSourceDocument).count()

    assert edition_count > 0, "No editions seeded."
    assert chapter_count > 0, "No chapters seeded."
    assert me_count > 0, "No measurable elements seeded."

    # Run seeder a second time
    seed_versioned_ontology(db_session, "app/nabh/data", "6.0")

    # Assert counts remain identical
    assert db_session.query(NABHEdition).count() == edition_count
    assert db_session.query(NABHChapter).count() == chapter_count
    assert db_session.query(NABHStandard).count() == standard_count
    assert db_session.query(NABHObjectiveElement).count() == obj_count
    assert db_session.query(NABHMeasurableElement).count() == me_count
    assert db_session.query(NABHApplicabilityRule).count() == rule_count
    assert db_session.query(NABHEvidenceRequirement).count() == ev_count
    assert db_session.query(NABHRequirementCitation).count() == cit_count
    assert db_session.query(NABHSourceDocument).count() == doc_count

def test_active_edition_is_unique(db_session):
    seed_versioned_ontology(db_session, "app/nabh/data", "6.0")
    
    # Assert exactly one active edition with version 6.0 exists
    active_6_editions = db_session.query(NABHEdition).filter(
        NABHEdition.version == "6.0",
        NABHEdition.status == EditionStatus.ACTIVE,
        NABHEdition.retired_at.is_(None)
    ).all()
    assert len(active_6_editions) == 1, "There should be exactly one active 6.0 edition."
    
    active_edition = active_6_editions[0]
    
    # Assert active seeded requirements belong to the active edition chain
    active_requirements = db_session.query(NABHMeasurableElement).filter(
        NABHMeasurableElement.retired_at.is_(None)
    ).all()
    
    for me in active_requirements:
        assert me.edition_id == active_edition.id

def test_seeded_requirements_have_required_ontology_chain(db_session):
    seed_versioned_ontology(db_session, "app/nabh/data", "6.0")

    active_requirements = db_session.query(NABHMeasurableElement).filter(
        NABHMeasurableElement.retired_at.is_(None)
    ).all()

    for me in active_requirements:
        # Check chain exists and is not retired
        assert me.canonical_code is not None
        assert me.description is not None
        assert me.applicability_default in {ApplicabilityDefault.APPLICABLE, ApplicabilityDefault.NOT_APPLICABLE}

        oe = db_session.query(NABHObjectiveElement).filter_by(id=me.objective_element_id).first()
        assert oe is not None
        assert oe.retired_at is None
        assert oe.canonical_code is not None

        std = db_session.query(NABHStandard).filter_by(id=oe.standard_id).first()
        assert std is not None
        assert std.retired_at is None
        assert std.canonical_code is not None

        chap = db_session.query(NABHChapter).filter_by(id=std.chapter_id).first()
        assert chap is not None
        assert chap.retired_at is None
        assert chap.canonical_code is not None

        ed = db_session.query(NABHEdition).filter_by(id=chap.edition_id).first()
        assert ed is not None
        assert ed.retired_at is None
        assert ed.status == EditionStatus.ACTIVE

def test_seeded_requirement_codes_are_unique(db_session):
    seed_versioned_ontology(db_session, "app/nabh/data", "6.0")

    # No duplicate measurable element canonical codes
    me_codes = [me.canonical_code for me in db_session.query(NABHMeasurableElement).all()]
    assert len(me_codes) == len(set(me_codes)), "Duplicate measurable element canonical codes found."

    # No duplicate standard canonical codes
    std_codes = [std.canonical_code for std in db_session.query(NABHStandard).all()]
    assert len(std_codes) == len(set(std_codes)), "Duplicate standard canonical codes found."

    # No duplicate chapter canonical codes
    chap_codes = [chap.canonical_code for chap in db_session.query(NABHChapter).all()]
    assert len(chap_codes) == len(set(chap_codes)), "Duplicate chapter canonical codes found."

def test_every_active_seeded_requirement_has_citation(db_session):
    seed_versioned_ontology(db_session, "app/nabh/data", "6.0")

    active_requirements = db_session.query(NABHMeasurableElement).filter(
        NABHMeasurableElement.retired_at.is_(None)
    ).all()

    for me in active_requirements:
        citations = db_session.query(NABHRequirementCitation).filter(
            NABHRequirementCitation.measurable_element_id == me.id,
            NABHRequirementCitation.retired_at.is_(None)
        ).all()
        assert len(citations) >= 1, f"Requirement {me.canonical_code} lacks citations."

        for citation in citations:
            # Citation should connect to an active source document
            doc = db_session.query(NABHSourceDocument).filter_by(id=citation.document_id).first()
            assert doc is not None
            assert doc.retired_at is None

            # Citation should include at least one useful locator
            has_locator = any([
                citation.section,
                citation.page_number,
                citation.clause_text_summary,
                citation.file_path,
                citation.url
            ])
            assert has_locator, f"Citation for {me.canonical_code} has no locators."

def test_every_active_seeded_requirement_has_evidence_expectation(db_session):
    seed_versioned_ontology(db_session, "app/nabh/data", "6.0")

    active_requirements = db_session.query(NABHMeasurableElement).filter(
        NABHMeasurableElement.retired_at.is_(None)
    ).all()

    for me in active_requirements:
        evidence_reqs = db_session.query(NABHEvidenceRequirement).filter(
            NABHEvidenceRequirement.measurable_element_id == me.id,
            NABHEvidenceRequirement.retired_at.is_(None)
        ).all()
        assert len(evidence_reqs) >= 1, f"Requirement {me.canonical_code} lacks evidence expectations."

        for ev in evidence_reqs:
            assert ev.evidence_type is not None
            assert ev.description is not None
            assert ev.is_mandatory in {True, False}
            assert ev.minimum_lookback_days is not None
            assert ev.minimum_lookback_days >= 0
            
            # CONTRACT ENFORCEMENT: every active row in the production seed must have
            # suggested_documentation. If a future seed row omits it, this test will
            # correctly fail, acting as a regression guard. This is intentional.
            # Verified against nabh_6th_evidence_requirements.json (all 3 active rows include it).
            assert ev.suggested_documentation is not None, (
                f"Evidence row {ev.evidence_code} for {me.canonical_code} is missing "
                f"suggested_documentation. Add it to the seed file or explicitly mark the row "
                f"as not production-ready."
            )
            assert len(ev.suggested_documentation.strip()) > 0

def test_evidence_requirement_types_are_valid(db_session):
    seed_versioned_ontology(db_session, "app/nabh/data", "6.0")

    evidence_reqs = db_session.query(NABHEvidenceRequirement).all()
    for ev in evidence_reqs:
        # Check valid enum values
        assert ev.evidence_type.value in VALID_EVIDENCE_TYPES
        # No placeholders
        assert ev.evidence_type.value not in {"todo", "unknown", "tbd", ""}
        assert ev.description.lower() not in {"todo", "unknown", "tbd", ""}

def test_citations_do_not_point_to_retired_documents(db_session):
    seed_versioned_ontology(db_session, "app/nabh/data", "6.0")

    citations = db_session.query(NABHRequirementCitation).filter(
        NABHRequirementCitation.retired_at.is_(None)
    ).all()

    for citation in citations:
        doc = db_session.query(NABHSourceDocument).filter_by(id=citation.document_id).first()
        assert doc is not None
        assert doc.retired_at is None, f"Citation points to retired document {doc.title}"
