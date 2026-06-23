from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.database import (
    NABHRequirementCitation, NABHSourceDocument, NABHRequirement,
    NABHStandard, NABHChapter
)
from app.nabh.canonical import ACTIVE_PUBLICATION_STATUSES, ensure_canonical_compatibility

def _map_citation_to_dict(citation: NABHRequirementCitation, doc: Optional[NABHSourceDocument],
                           requirement: NABHRequirement,
                           standard: NABHStandard, chapter: NABHChapter) -> Dict[str, Any]:
    """Helper to construct a fully populated citation dictionary."""
    doc_dict = None
    resolved_effective_date = None
    
    if doc:
        resolved_effective_date = citation.effective_date or doc.effective_date
        doc_dict = {
            "id": doc.id,
            "title": doc.title,
            "publisher": doc.publisher,
            "edition_version": doc.edition_version,
            "file_path_or_url": doc.file_path_or_url,
            "effective_date": doc.effective_date.strftime('%Y-%m-%d') if doc.effective_date else None
        }
    else:
        resolved_effective_date = citation.effective_date

    return {
        "id": citation.id,
        "requirement_id": citation.requirement_id,
        "measurable_element_id": citation.measurable_element_id,
        "document": doc_dict,
        "section": citation.section,
        "page_number": citation.page_number,
        "printed_page_number": citation.printed_page_number,
        "pdf_page_index": citation.pdf_page_index,
        "source_heading": citation.source_heading,
        "clause_text_summary": citation.clause_text_summary,
        "file_path": citation.file_path,
        "url": citation.url,
        "human_verified": citation.human_verified,
        "effective_date_override": citation.effective_date.strftime('%Y-%m-%d') if citation.effective_date else None,
        "resolved_effective_date": resolved_effective_date.strftime('%Y-%m-%d') if resolved_effective_date else None,
        "ontology": {
            "chapter_code": chapter.code,
            "chapter_title": chapter.title,
            "standard_code": standard.canonical_code,
            "standard_title": standard.title,
            "objective_element_code": requirement.canonical_code,
            "objective_element_description": requirement.display_text,
            "requirement_code": requirement.canonical_code,
            "requirement_description": requirement.display_text
        }
    }

class CitationService:
    @staticmethod
    def get_citations_for_measurable_element(db: Session, element_id: str) -> List[Dict[str, Any]]:
        """
        Deterministically fetch all citations for a given measurable element.
        Joins full ontology hierarchy context to populate the dictionary.
        """
        ensure_canonical_compatibility(db)
        results = db.query(
            NABHRequirementCitation, NABHSourceDocument, NABHRequirement,
            NABHStandard, NABHChapter
        ).outerjoin(
            NABHSourceDocument, NABHRequirementCitation.document_id == NABHSourceDocument.id
        ).join(
            NABHRequirement, NABHRequirementCitation.requirement_id == NABHRequirement.id
        ).join(
            NABHStandard, NABHRequirement.standard_id == NABHStandard.id
        ).join(
            NABHChapter, NABHStandard.chapter_id == NABHChapter.id
        ).filter(
            NABHRequirementCitation.requirement_id == element_id,
            NABHRequirementCitation.retired_at.is_(None),
            NABHRequirement.retired_at.is_(None),
            NABHRequirement.publication_status.in_(ACTIVE_PUBLICATION_STATUSES),
            NABHStandard.retired_at.is_(None),
            NABHChapter.retired_at.is_(None),
        ).all()
        
        return [
            _map_citation_to_dict(cit, doc, requirement, std, chap)
            for cit, doc, requirement, std, chap in results
        ]

    @staticmethod
    def get_citation_by_id(db: Session, citation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific citation record by ID, resolving full ontology details."""
        ensure_canonical_compatibility(db)
        result = db.query(
            NABHRequirementCitation, NABHSourceDocument, NABHRequirement,
            NABHStandard, NABHChapter
        ).outerjoin(
            NABHSourceDocument, NABHRequirementCitation.document_id == NABHSourceDocument.id
        ).join(
            NABHRequirement, NABHRequirementCitation.requirement_id == NABHRequirement.id
        ).join(
            NABHStandard, NABHRequirement.standard_id == NABHStandard.id
        ).join(
            NABHChapter, NABHStandard.chapter_id == NABHChapter.id
        ).filter(
            NABHRequirementCitation.id == citation_id,
            NABHRequirementCitation.retired_at.is_(None),
            NABHRequirement.retired_at.is_(None),
            NABHRequirement.publication_status.in_(ACTIVE_PUBLICATION_STATUSES),
            NABHStandard.retired_at.is_(None),
            NABHChapter.retired_at.is_(None),
        ).first()
        
        if not result:
            return None
            
        cit, doc, requirement, std, chap = result
        return _map_citation_to_dict(cit, doc, requirement, std, chap)

    @staticmethod
    def format_citation_string(citation: Dict[str, Any]) -> str:
        """
        Format a citation dictionary into a normalized string for logs,
        agent prompts, or UI displays.
        """
        ontology = citation.get("ontology", {})
        meas_code = ontology.get("requirement_code", "N/A")
        chap_code = ontology.get("chapter_code", "N/A")
        
        doc = citation.get("document") or {}
        doc_title = doc.get("title", "Unknown Source")
        doc_ver = doc.get("edition_version", "N/A")
        resolved_date = citation.get("resolved_effective_date") or "N/A"
        
        section = citation.get("section") or "N/A"
        page = citation.get("page_number") or "N/A"
        clause_summary = citation.get("clause_text_summary") or ""
        
        # Determine the best reference link / path for excerpt
        excerpt_path = citation.get("file_path") or citation.get("url") or doc.get("file_path_or_url") or "N/A"
        
        return (
            f"[Citation] Reference: {meas_code} ({chap_code}), "
            f"Source: {doc_title} (Ed: {doc_ver}, Effective: {resolved_date}), "
            f"Section: {section}, Page: {page}. "
            f"Summary: {clause_summary} (Excerpt: {excerpt_path})"
        )
