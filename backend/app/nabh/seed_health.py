"""Service functions to verify the health of the NABH ontology database seed."""
import logging
from sqlalchemy.orm import Session
from app.models.database import (
    NABHEdition, NABHChapter,
    NABHMeasurableElement, NABHEvidenceRequirement,
    NABHRequirementCitation, EditionStatus
)

logger = logging.getLogger(__name__)

EXPECTED_CANONICAL_CHAPTERS = {
    "AAC", "COP", "MOM", "PRE", "IPC", "PSQ", "ROM", "FMS", "HRM", "IMS"
}

def check_nabh_seed_health(db: Session, target_version: str = "6.0") -> dict:
    """
    Evaluates database seed records for the versioned NABH ontology.
    Verifies that the target active edition exists, all 10 canonical chapters are present,
    and requirements/citations/evidence records are populated.
    """
    try:
        # Check active edition
        active_edition = db.query(NABHEdition).filter(
            NABHEdition.version == target_version,
            NABHEdition.status == EditionStatus.ACTIVE,
            NABHEdition.retired_at.is_(None)
        ).first()
        
        edition_exists = active_edition is not None
        
        # Check chapters
        chapters = []
        if edition_exists:
            chapters = db.query(NABHChapter).filter(
                NABHChapter.edition_id == active_edition.id,
                NABHChapter.retired_at.is_(None)
            ).all()
            
        found_chapters = {c.canonical_code for c in chapters}
        missing_chapters = sorted(list(EXPECTED_CANONICAL_CHAPTERS - found_chapters))
        chapters_count = len(chapters)
        
        # Check counts
        measurable_elements_count = 0
        evidence_requirements_count = 0
        citations_count = 0
        
        if edition_exists:
            # Measurable elements belonging to this edition
            measurable_elements_count = db.query(NABHMeasurableElement).filter(
                NABHMeasurableElement.edition_id == active_edition.id,
                NABHMeasurableElement.retired_at.is_(None)
            ).count()
            
            # Evidence requirements & citations
            me_ids = [row[0] for row in db.query(NABHMeasurableElement.id).filter(
                NABHMeasurableElement.edition_id == active_edition.id,
                NABHMeasurableElement.retired_at.is_(None)
            ).all()]
            
            if me_ids:
                evidence_requirements_count = db.query(NABHEvidenceRequirement).filter(
                    NABHEvidenceRequirement.measurable_element_id.in_(me_ids),
                    NABHEvidenceRequirement.retired_at.is_(None)
                ).count()
                
                citations_count = db.query(NABHRequirementCitation).filter(
                    NABHRequirementCitation.measurable_element_id.in_(me_ids),
                    NABHRequirementCitation.retired_at.is_(None)
                ).count()
                
        is_healthy = (
            edition_exists and
            chapters_count == 10 and
            not missing_chapters and
            measurable_elements_count > 0 and
            evidence_requirements_count > 0 and
            citations_count > 0
        )
        
        return {
            "is_healthy": is_healthy,
            "edition_exists": edition_exists,
            "chapters_count": chapters_count,
            "measurable_elements_count": measurable_elements_count,
            "evidence_requirements_count": evidence_requirements_count,
            "citations_count": citations_count,
            "missing_chapters": missing_chapters
        }
    except Exception as e:
        logger.error(f"Failed to check NABH seed health: {e}", exc_info=True)
        return {
            "is_healthy": False,
            "edition_exists": False,
            "chapters_count": 0,
            "measurable_elements_count": 0,
            "evidence_requirements_count": 0,
            "citations_count": 0,
            "missing_chapters": list(EXPECTED_CANONICAL_CHAPTERS)
        }
