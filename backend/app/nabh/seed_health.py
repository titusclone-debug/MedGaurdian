"""Service functions to verify the health of the NABH ontology database seed."""
import logging
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHRequirement, NABHEvidenceRequirement,
    NABHRequirementCitation, NABHSourceDocument, EditionStatus,
    KnowledgePublicationStatus,
)
from app.nabh.canonical import ensure_canonical_compatibility

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
        standards_count = 0
        requirements_count = 0
        official_verified_requirements_count = 0
        evidence_requirements_count = 0
        evidence_covered_requirements_count = 0
        citations_count = 0
        verified_citations_count = 0
        has_synthetic_codes = False
        has_official_source = False
        
        if edition_exists:
            ensure_canonical_compatibility(db, active_edition.id)
            has_synthetic_codes = db.query(NABHRequirement).filter(
                NABHRequirement.edition_id == active_edition.id,
                NABHRequirement.retired_at.is_(None),
                NABHRequirement.canonical_code.like('%-%')
            ).count() > 0
            has_official_source = db.query(NABHSourceDocument).filter(
                NABHSourceDocument.edition_id == active_edition.id,
                NABHSourceDocument.checksum == '0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A',
                NABHSourceDocument.retired_at.is_(None)
            ).count() > 0
            
            standards_count = db.query(NABHStandard).filter(
                NABHStandard.edition_id == active_edition.id,
                NABHStandard.retired_at.is_(None),
            ).count()
            requirements_count = db.query(NABHRequirement).filter(
                NABHRequirement.edition_id == active_edition.id,
                NABHRequirement.retired_at.is_(None),
                NABHRequirement.publication_status.in_([
                    KnowledgePublicationStatus.APPROVED,
                    KnowledgePublicationStatus.PUBLISHED,
                ]),
            ).count()
            official_verified_requirements_count = db.query(NABHRequirement).filter(
                NABHRequirement.edition_id == active_edition.id,
                NABHRequirement.retired_at.is_(None),
                NABHRequirement.publication_status.in_([
                    KnowledgePublicationStatus.APPROVED,
                    KnowledgePublicationStatus.PUBLISHED,
                ]),
                NABHRequirement.source_status == "official_verified",
            ).count()
            
            # Evidence requirements & citations
            me_ids = [row[0] for row in db.query(NABHRequirement.id).filter(
                NABHRequirement.edition_id == active_edition.id,
                NABHRequirement.retired_at.is_(None),
                NABHRequirement.publication_status.in_([
                    KnowledgePublicationStatus.APPROVED,
                    KnowledgePublicationStatus.PUBLISHED,
                ]),
            ).all()]
            
            if me_ids:
                evidence_requirements_count = db.query(NABHEvidenceRequirement).filter(
                    NABHEvidenceRequirement.requirement_id.in_(me_ids),
                    NABHEvidenceRequirement.retired_at.is_(None)
                ).count()
                evidence_covered_requirements_count = db.query(
                    func.count(func.distinct(NABHEvidenceRequirement.requirement_id))
                ).filter(
                    NABHEvidenceRequirement.requirement_id.in_(me_ids),
                    NABHEvidenceRequirement.retired_at.is_(None),
                ).scalar() or 0
                
                citations_count = db.query(
                    func.count(func.distinct(NABHRequirementCitation.requirement_id))
                ).join(
                    NABHSourceDocument,
                    NABHRequirementCitation.document_id == NABHSourceDocument.id,
                ).filter(
                    NABHRequirementCitation.requirement_id.in_(me_ids),
                    NABHRequirementCitation.retired_at.is_(None),
                    NABHSourceDocument.retired_at.is_(None),
                ).scalar() or 0
                verified_citations_count = db.query(
                    func.count(func.distinct(NABHRequirementCitation.requirement_id))
                ).join(
                    NABHSourceDocument,
                    NABHRequirementCitation.document_id == NABHSourceDocument.id,
                ).filter(
                    NABHRequirementCitation.requirement_id.in_(me_ids),
                    NABHRequirementCitation.retired_at.is_(None),
                    NABHRequirementCitation.human_verified.is_(True),
                    NABHSourceDocument.retired_at.is_(None),
                    NABHSourceDocument.verification_status.in_([
                        KnowledgePublicationStatus.APPROVED,
                        KnowledgePublicationStatus.PUBLISHED,
                    ]),
                ).scalar() or 0
                
        canonical_complete = (
            edition_exists and
            chapters_count == 10 and
            not missing_chapters and
            standards_count == 100 and
            requirements_count == 639 and
            official_verified_requirements_count == 639 and
            verified_citations_count == 639 and
            not has_synthetic_codes and
            has_official_source
        )
        partial_operational_seed = (
            requirements_count > 0 and
            evidence_requirements_count > 0 and
            citations_count > 0
        )
        is_healthy = (
            edition_exists and
            chapters_count == 10 and
            not missing_chapters and
            (canonical_complete or partial_operational_seed)
        )
        
        return {
            "is_healthy": is_healthy,
            "edition_exists": edition_exists,
            "chapters_count": chapters_count,
            "standards_count": standards_count,
            "requirements_count": requirements_count,
            "official_verified_requirements_count": official_verified_requirements_count,
            "objective_elements_count": requirements_count,
            "canonical_complete": canonical_complete,
            "partial_operational_seed": partial_operational_seed,
            "evidence_requirements_count": evidence_requirements_count,
            "evidence_covered_requirements_count": evidence_covered_requirements_count,
            "evidence_coverage_complete": (
                requirements_count > 0
                and evidence_covered_requirements_count == requirements_count
            ),
            "citations_count": citations_count,
            "verified_citations_count": verified_citations_count,
            "citation_coverage_complete": (
                requirements_count > 0
                and citations_count == requirements_count
            ),
            "verified_citation_coverage_complete": (
                requirements_count > 0
                and verified_citations_count == requirements_count
            ),
            "missing_chapters": missing_chapters
        }
    except Exception as e:
        logger.error(f"Failed to check NABH seed health: {e}", exc_info=True)
        return {
            "is_healthy": False,
            "edition_exists": False,
            "chapters_count": 0,
            "standards_count": 0,
            "requirements_count": 0,
            "official_verified_requirements_count": 0,
            "objective_elements_count": 0,
            "canonical_complete": False,
            "partial_operational_seed": False,
            "evidence_requirements_count": 0,
            "evidence_covered_requirements_count": 0,
            "evidence_coverage_complete": False,
            "citations_count": 0,
            "verified_citations_count": 0,
            "citation_coverage_complete": False,
            "verified_citation_coverage_complete": False,
            "missing_chapters": list(EXPECTED_CANONICAL_CHAPTERS)
        }
