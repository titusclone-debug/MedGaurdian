import pytest
from datetime import datetime
from sqlalchemy import text

from app.models.database import (
    NABHEdition, EditionStatus, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement, NABHSourceDocument,
    NABHRequirementCitation, ApplicabilityDefault
)
from app.nabh.citation_service import CitationService

def test_citation_infrastructure_smoke(db_session):
    # Enable SQLite foreign keys for testing
    db_session.execute(text("PRAGMA foreign_keys=ON"))

    # 1. Seed base ontology
    edition = NABHEdition(
        id="ed-task5-smoke",
        name="NABH 6th Edition Task 5",
        version="6.0-T5",
        status=EditionStatus.ACTIVE,
        effective_date=datetime(2026, 1, 1)
    )
    db_session.add(edition)
    db_session.flush()

    chapter = NABHChapter(
        id="chap-task5-smoke",
        edition_id="ed-task5-smoke",
        code="IPC",
        canonical_code="IPC-6.0-T5",
        title="Infection Prevention and Control"
    )
    db_session.add(chapter)
    db_session.flush()

    standard = NABHStandard(
        id="std-task5-smoke",
        edition_id="ed-task5-smoke",
        chapter_id="chap-task5-smoke",
        code="IPC 1",
        canonical_code="IPC-1-6.0-T5",
        title="Infection Control Program"
    )
    db_session.add(standard)
    db_session.flush()

    obj_el = NABHObjectiveElement(
        id="obj-task5-smoke",
        edition_id="ed-task5-smoke",
        standard_id="std-task5-smoke",
        code="a",
        canonical_code="IPC-1.a-6.0-T5",
        description="The organization has an infection control committee."
    )
    db_session.add(obj_el)
    db_session.flush()

    meas_el = NABHMeasurableElement(
        id="meas-task5-smoke",
        edition_id="ed-task5-smoke",
        objective_element_id="obj-task5-smoke",
        code="1",
        canonical_code="IPC-1.a.1-6.0-T5",
        description="Infection control manual is updated.",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    # A second measurable element for empty state testing
    meas_el_empty = NABHMeasurableElement(
        id="meas-task5-empty",
        edition_id="ed-task5-smoke",
        objective_element_id="obj-task5-smoke",
        code="2",
        canonical_code="IPC-1.a.2-6.0-T5",
        description="Infection control committee meets regularly.",
        applicability_default=ApplicabilityDefault.APPLICABLE
    )
    db_session.add(meas_el)
    db_session.add(meas_el_empty)
    db_session.flush()

    # 2. Seed Source Document
    doc = NABHSourceDocument(
        id="doc-task5-smoke",
        edition_id="ed-task5-smoke",
        title="Official NABH 6th Edition Standards Manual",
        publisher="NABH Board",
        edition_version="6.0",
        file_path_or_url="/manuals/NABH_6th_Edition.pdf",
        effective_date=datetime(2026, 1, 1) # Document default effective date
    )
    db_session.add(doc)
    db_session.commit()

    # 3. Seed Citations
    # Citation A: Has override effective_date, page_number, file_path, and url
    citation_a = NABHRequirementCitation(
        id="cit-task5-a",
        measurable_element_id="meas-task5-smoke",
        document_id="doc-task5-smoke",
        section="Section 3.2",
        page_number="Page 89",
        clause_text_summary="Committee composition guidelines.",
        effective_date=datetime(2026, 3, 15), # Override date
        file_path="/excerpts/IPC_committee_excerpt.png", # Local excerpt snippet path
        url="https://nabh.co/standards/6th_edition/hic_3_2" # Web reference link
    )
    # Citation B: No override date (will fallback to doc.effective_date)
    citation_b = NABHRequirementCitation(
        id="cit-task5-b",
        measurable_element_id="meas-task5-smoke",
        document_id="doc-task5-smoke",
        section="Section 3.3",
        page_number="Page 90",
        clause_text_summary="Meeting frequencies.",
        effective_date=None, # Falls back
        file_path=None,
        url=None
    )
    db_session.add(citation_a)
    db_session.add(citation_b)
    db_session.commit()

    # 4. Verification: Happy Path & Overrides
    citations = CitationService.get_citations_for_measurable_element(db_session, "meas-task5-smoke")
    assert len(citations) == 2
    
    # Sort by ID to ensure test determinism
    citations.sort(key=lambda x: x["id"])
    cit_a = citations[0]
    cit_b = citations[1]
    
    # Assert Citation A values
    assert cit_a["id"] == "cit-task5-a"
    assert cit_a["section"] == "Section 3.2"
    assert cit_a["page_number"] == "Page 89"
    assert cit_a["clause_text_summary"] == "Committee composition guidelines."
    assert cit_a["file_path"] == "/excerpts/IPC_committee_excerpt.png"
    assert cit_a["url"] == "https://nabh.co/standards/6th_edition/hic_3_2"
    assert cit_a["effective_date_override"] == "2026-03-15"
    assert cit_a["resolved_effective_date"] == "2026-03-15" # Resolves to override
    
    # Assert Document details
    assert cit_a["document"]["title"] == "Official NABH 6th Edition Standards Manual"
    assert cit_a["document"]["effective_date"] == "2026-01-01"

    # Assert Full Ontology Context
    assert cit_a["ontology"]["chapter_code"] == "IPC"
    assert cit_a["ontology"]["chapter_title"] == "Infection Prevention and Control"
    assert cit_a["ontology"]["standard_code"] == "IPC-1-6.0-T5"
    assert cit_a["ontology"]["measurable_element_code"] == "IPC-1.a.1-6.0-T5"

    # Assert Citation B (date fallback)
    assert cit_b["id"] == "cit-task5-b"
    assert cit_b["effective_date_override"] is None
    assert cit_b["resolved_effective_date"] == "2026-01-01" # Falls back to doc effective date
    assert cit_b["file_path"] is None
    assert cit_b["url"] is None

    # 5. Verification: get_citation_by_id
    single_cit = CitationService.get_citation_by_id(db_session, "cit-task5-a")
    assert single_cit is not None
    assert single_cit["resolved_effective_date"] == "2026-03-15"
    
    non_existent = CitationService.get_citation_by_id(db_session, "cit-fake")
    assert non_existent is None

    # 6. Verification: format_citation_string
    formatted_str = CitationService.format_citation_string(cit_a)
    assert "[Citation]" in formatted_str
    assert "IPC-1.a.1-6.0-T5" in formatted_str
    assert "IPC" in formatted_str
    assert "Official NABH 6th Edition Standards Manual" in formatted_str
    assert "2026-03-15" in formatted_str # Verifies override date format
    assert "Section 3.2" in formatted_str
    assert "Page 89" in formatted_str
    assert "Committee composition guidelines." in formatted_str
    assert "/excerpts/IPC_committee_excerpt.png" in formatted_str

    # 7. Verification: Empty State Behavior
    empty_list = CitationService.get_citations_for_measurable_element(db_session, "meas-task5-empty")
    assert empty_list == []
