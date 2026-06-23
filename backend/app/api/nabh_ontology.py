"""NABH 6th Edition Ontology Routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.api.auth import get_current_user, Staff
from app.api.nabh_helpers import build_evidence_burden_summary
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard, NABHRequirement,
    NABHRequirementCitation, NABHSourceDocument, NABHSourceAnomaly,
    NABHApplicabilityRule, NABHEvidenceRequirement,
    KnowledgePublicationStatus,
)
from app.nabh.citation_service import CitationService
from app.nabh.canonical import ensure_canonical_compatibility
from app.schemas.nabh import (
    NABHEditionSummary, NABHChapterSummary, NABHSourceDocumentSummary,
    NABHSourceAnomalySchema, NABHRequirementSummary, PaginatedRequirementSummary,
    NABHRuleSchema, NABHEvidenceRequirementSchema, NABHCitationSchema, NABHRequirementDetail,
    CitationResponse
)

router = APIRouter()

@router.get("/coverage")
async def get_ontology_coverage(db: Session = Depends(get_db)):
    """Return reconciled official totals and live canonical corpus coverage."""
    edition = db.query(NABHEdition).filter(
        NABHEdition.version == "6.0",
        NABHEdition.retired_at.is_(None),
    ).first()
    if not edition:
        return {
            "ontology_status": "partial_seed",
            "official_declared_total_standards": 0,
            "official_declared_total_elements": 0,
            "official_chapter_sum_standards": 0,
            "official_chapter_sum_elements": 0,
            "official_chapter_objective_elements_sum": 0,
            "official_category_breakdown_sum": 0,
            "official_standards_discrepancy": 0,
            "official_elements_discrepancy": 0,
            "has_source_inconsistency": False,
            "inconsistencies": [],
            "source_anomalies": [],
            "seeded_total_standards": 0,
            "seeded_total_elements": 0,
            "global_standards_coverage_percent": 0.0,
            "global_elements_coverage_percent": 0.0,
            "citation_complete": False,
            "chapters": []
        }

    ensure_canonical_compatibility(db, edition.id)
    official_chapter_codes = [
        "AAC", "COP", "MOM", "PRE", "IPC",
        "PSQ", "ROM", "FMS", "HRM", "IMS",
    ]
    chapters = db.query(NABHChapter).filter(
        NABHChapter.edition_id == edition.id,
        NABHChapter.canonical_code.in_(official_chapter_codes),
        NABHChapter.retired_at.is_(None),
    ).order_by(NABHChapter.display_order).all()

    standard_counts = dict(db.query(
        NABHStandard.chapter_id,
        func.count(NABHStandard.id),
    ).filter(
        NABHStandard.edition_id == edition.id,
        NABHStandard.retired_at.is_(None),
    ).group_by(NABHStandard.chapter_id).all())

    requirement_counts = dict(db.query(
        NABHStandard.chapter_id,
        func.count(NABHRequirement.id),
    ).join(
        NABHRequirement,
        NABHRequirement.standard_id == NABHStandard.id,
    ).filter(
        NABHRequirement.edition_id == edition.id,
        NABHRequirement.retired_at.is_(None),
        NABHRequirement.publication_status.in_([
            KnowledgePublicationStatus.APPROVED,
            KnowledgePublicationStatus.PUBLISHED,
        ]),
        NABHStandard.retired_at.is_(None),
    ).group_by(NABHStandard.chapter_id).all())

    citation_counts = dict(db.query(
        NABHStandard.chapter_id,
        func.count(func.distinct(NABHRequirementCitation.requirement_id)),
    ).join(
        NABHRequirement,
        NABHRequirementCitation.requirement_id == NABHRequirement.id,
    ).join(
        NABHStandard,
        NABHRequirement.standard_id == NABHStandard.id,
    ).join(
        NABHSourceDocument,
        NABHRequirementCitation.document_id == NABHSourceDocument.id,
    ).filter(
        NABHRequirement.edition_id == edition.id,
        NABHRequirement.retired_at.is_(None),
        NABHRequirementCitation.retired_at.is_(None),
        NABHSourceDocument.retired_at.is_(None),
    ).group_by(NABHStandard.chapter_id).all())

    chapter_stats = []
    total_seeded_standards = 0
    total_seeded_elements = 0
    for chap in chapters:
        seeded_standards_count = standard_counts.get(chap.id, 0)
        seeded_elements_count = requirement_counts.get(chap.id, 0)
        citation_count = citation_counts.get(chap.id, 0)
        uncited_count = max(seeded_elements_count - citation_count, 0)
        official_requirement_count = (
            chap.official_requirements_count
            if chap.official_requirements_count is not None
            else chap.official_measurable_elements_count
        )
        std_pct = (
            round((seeded_standards_count / chap.official_standards_count) * 100, 1)
            if chap.official_standards_count else 0.0
        )
        req_pct = (
            round((seeded_elements_count / official_requirement_count) * 100, 1)
            if official_requirement_count else 0.0
        )

        chapter_stats.append({
            "chapter_code": chap.canonical_code,
            "title": chap.title,
            "official_standards_count": chap.official_standards_count,
            "official_objective_elements_count": official_requirement_count,
            "core_count": chap.core_count,
            "commitment_count": chap.commitment_count,
            "achievement_count": chap.achievement_count,
            "excellence_count": chap.excellence_count,
            "seeded_standards_count": seeded_standards_count,
            "seeded_objective_elements_count": seeded_elements_count,
            "standards_coverage_percent": std_pct,
            "elements_coverage_percent": req_pct,
            "citation_count": citation_count,
            "uncited_seeded_elements_count": uncited_count,
            "is_fully_seeded": (
                seeded_standards_count == chap.official_standards_count
                and seeded_elements_count == official_requirement_count
                and uncited_count == 0
            ),
        })
        total_seeded_standards += seeded_standards_count
        total_seeded_elements += seeded_elements_count

    official_chapter_sum_standards = sum(
        chap.official_standards_count or 0 for chap in chapters
    )
    official_chapter_sum_elements = sum(
        chap.official_requirements_count
        if chap.official_requirements_count is not None
        else (chap.official_measurable_elements_count or 0)
        for chap in chapters
    )
    official_category_breakdown_sum = sum(
        (chapter.core_count or 0)
        + (chapter.commitment_count or 0)
        + (chapter.achievement_count or 0)
        + (chapter.excellence_count or 0)
        for chapter in chapters
    )
    anomalies = db.query(NABHSourceAnomaly).join(
        NABHSourceDocument,
        NABHSourceAnomaly.document_id == NABHSourceDocument.id,
    ).filter(
        NABHSourceDocument.edition_id == edition.id,
    ).order_by(NABHSourceAnomaly.anomaly_code).all()
    source_anomalies = [
        {
            "anomaly_code": anomaly.anomaly_code,
            "title": anomaly.title,
            "source_locator": anomaly.source_locator,
            "observed_value": anomaly.observed_value,
            "reconciled_value": anomaly.reconciled_value,
            "reconciliation_basis": anomaly.reconciliation_basis,
            "status": anomaly.status,
        }
        for anomaly in anomalies
    ]
    unresolved_anomalies = [
        anomaly for anomaly in source_anomalies
        if anomaly["status"] not in {"reconciled", "closed"}
    ]
    total_cited_requirements = sum(citation_counts.values())
    
    official_total_standards = official_chapter_sum_standards
    official_total_elements = official_chapter_sum_elements
    
    citation_complete = (
        official_total_elements > 0
        and total_seeded_elements == official_total_elements
        and total_cited_requirements == total_seeded_elements
    )
    canonical_complete = (
        len(chapters) > 0
        and official_total_standards > 0
        and total_seeded_standards == official_total_standards
        and total_seeded_elements == official_total_elements
        and official_category_breakdown_sum == official_total_elements
    )

    return {
        "ontology_status": "canonical_complete" if canonical_complete else "partial_seed",
        "official_declared_total_standards": official_total_standards,
        "official_declared_total_elements": official_total_elements,
        "official_chapter_sum_standards": official_chapter_sum_standards,
        "official_chapter_sum_elements": official_chapter_sum_elements,
        "official_chapter_objective_elements_sum": official_chapter_sum_elements,
        "official_category_breakdown_sum": official_category_breakdown_sum,
        "official_standards_discrepancy": official_total_standards - official_chapter_sum_standards,
        "official_elements_discrepancy": official_total_elements - official_chapter_sum_elements,
        "has_source_inconsistency": bool(unresolved_anomalies),
        "inconsistencies": unresolved_anomalies,
        "source_anomalies": source_anomalies,
        "seeded_total_standards": total_seeded_standards,
        "seeded_total_elements": total_seeded_elements,
        "global_standards_coverage_percent": round(
            (total_seeded_standards / official_total_standards) * 100 if official_total_standards else 0.0, 1
        ),
        "global_elements_coverage_percent": round(
            (total_seeded_elements / official_total_elements) * 100 if official_total_elements else 0.0, 1
        ),
        "citation_complete": citation_complete,
        "chapters": chapter_stats,
    }


@router.get("/editions", response_model=List[NABHEditionSummary])
async def get_ontology_editions(
    include_retired: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get the list of all standard editions, optionally including retired ones."""
    query = db.query(NABHEdition)
    if not include_retired:
        query = query.filter(NABHEdition.retired_at.is_(None))
    return query.all()


@router.get("/chapters", response_model=List[NABHChapterSummary])
async def get_ontology_chapters(
    edition_version: str = Query("6.0"),
    include_retired: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get the list of all chapters for a given edition version, optionally including retired ones."""
    edition = db.query(NABHEdition).filter(
        NABHEdition.version == edition_version,
        NABHEdition.retired_at.is_(None)
    ).first()
    if not edition:
        raise HTTPException(status_code=404, detail=f"Edition '{edition_version}' not found")
        
    query = db.query(NABHChapter).filter(NABHChapter.edition_id == edition.id)
    if not include_retired:
        query = query.filter(NABHChapter.retired_at.is_(None))
    return query.order_by(NABHChapter.display_order).all()


@router.get("/sources", response_model=List[NABHSourceDocumentSummary])
async def get_ontology_sources(
    edition_version: str = Query("6.0"),
    include_retired: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Return the governed source registry without protected source contents."""
    edition = db.query(NABHEdition).filter(
        NABHEdition.version == edition_version,
        NABHEdition.retired_at.is_(None),
    ).first()
    if not edition:
        raise HTTPException(
            status_code=404,
            detail=f"Edition '{edition_version}' not found",
        )

    query = db.query(NABHSourceDocument).filter(
        NABHSourceDocument.edition_id == edition.id,
    )
    if not include_retired:
        query = query.filter(NABHSourceDocument.retired_at.is_(None))
    documents = query.order_by(
        NABHSourceDocument.effective_date.desc(),
        NABHSourceDocument.title,
    ).all()

    document_ids = [document.id for document in documents]
    anomalies_by_document = {document_id: [] for document_id in document_ids}
    if document_ids:
        anomalies = db.query(NABHSourceAnomaly).filter(
            NABHSourceAnomaly.document_id.in_(document_ids),
        ).order_by(NABHSourceAnomaly.anomaly_code).all()
        for anomaly in anomalies:
            anomalies_by_document[anomaly.document_id].append(
                NABHSourceAnomalySchema.model_validate(anomaly)
            )

    return [
        NABHSourceDocumentSummary(
            id=document.id,
            title=document.title,
            publisher=document.publisher,
            edition_version=document.edition_version,
            checksum=document.checksum,
            file_size_bytes=document.file_size_bytes,
            pdf_page_count=document.pdf_page_count,
            printed_page_start=document.printed_page_start,
            printed_page_end=document.printed_page_end,
            isbn=document.isbn,
            document_type=document.document_type,
            programme=document.programme,
            authority_level=document.authority_level,
            rights_status=(
                document.rights_status.value
                if hasattr(document.rights_status, "value")
                else str(document.rights_status)
            ),
            may_store_full_text=document.may_store_full_text,
            may_display_full_text=document.may_display_full_text,
            may_create_embeddings=document.may_create_embeddings,
            verification_status=document.verification_status,
            verified_by=document.verified_by,
            verified_at=document.verified_at,
            approved_by=document.approved_by,
            approved_at=document.approved_at,
            effective_date=document.effective_date,
            anomalies=anomalies_by_document[document.id],
        )
        for document in documents
    ]


@router.get("/requirements", response_model=PaginatedRequirementSummary)
async def get_ontology_requirements(
    edition_version: str = Query("6.0"),
    chapter_code: Optional[str] = Query(None),
    standard_code: Optional[str] = Query(None),
    include_retired: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get canonical NABH Objective Element requirements with hierarchy context."""
    edition = db.query(NABHEdition).filter(
        NABHEdition.version == edition_version,
        NABHEdition.retired_at.is_(None),
    ).first()
    if not edition:
        raise HTTPException(
            status_code=404,
            detail=f"Edition '{edition_version}' not found",
        )
    ensure_canonical_compatibility(db, edition.id)

    query = db.query(
        NABHRequirement, NABHChapter, NABHStandard
    ).join(
        NABHStandard, NABHRequirement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        NABHRequirement.edition_id == edition.id,
    )
    
    if not include_retired:
        query = query.filter(
            NABHRequirement.retired_at.is_(None),
            NABHRequirement.publication_status.in_([
                KnowledgePublicationStatus.APPROVED,
                KnowledgePublicationStatus.PUBLISHED,
            ]),
            NABHStandard.retired_at.is_(None),
            NABHChapter.retired_at.is_(None)
        )
        
    if chapter_code:
        query = query.filter(NABHChapter.canonical_code == chapter_code)
    if standard_code:
        query = query.filter(NABHStandard.canonical_code == standard_code)
        
    total = query.count()
    results = query.order_by(
        NABHChapter.display_order,
        NABHStandard.display_order,
        NABHRequirement.display_order,
        NABHRequirement.canonical_code,
    ).offset(offset).limit(limit).all()
    
    items = [
        NABHRequirementSummary(
            id=requirement.id,
            code=requirement.official_code,
            canonical_code=requirement.canonical_code,
            description=requirement.display_text,
            applicability_default=requirement.applicability_default,
            chapter_code=chap.canonical_code,
            chapter_title=chap.title,
            standard_code=std.canonical_code,
            standard_title=std.title,
            objective_element_code=requirement.canonical_code,
            classification=requirement.classification,
            documentation_required=requirement.documentation_required,
            authority_level=requirement.authority_level,
            publication_status=requirement.publication_status,
            source_status=requirement.source_status,
        )
        for requirement, chap, std in results
    ]
    
    return PaginatedRequirementSummary(
        total=total,
        limit=limit,
        offset=offset,
        items=items
    )


@router.get("/requirements/{requirement_id}", response_model=NABHRequirementDetail)
async def get_ontology_requirement_detail(
    requirement_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get full details of a specific ontology requirement, including rules, evidence, and citations."""
    ensure_canonical_compatibility(db)
    result = db.query(
        NABHRequirement, NABHChapter, NABHStandard
    ).join(
        NABHStandard, NABHRequirement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        NABHRequirement.id == requirement_id,
        NABHRequirement.retired_at.is_(None),
        NABHRequirement.publication_status.in_([
            KnowledgePublicationStatus.APPROVED,
            KnowledgePublicationStatus.PUBLISHED,
        ]),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None)
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Requirement not found")
        
    requirement, chap, std = result
    
    rules = db.query(NABHApplicabilityRule).filter(
        NABHApplicabilityRule.requirement_id == requirement.id,
        NABHApplicabilityRule.retired_at.is_(None)
    ).all()
    
    evidences = db.query(NABHEvidenceRequirement).filter(
        NABHEvidenceRequirement.requirement_id == requirement.id,
        NABHEvidenceRequirement.retired_at.is_(None)
    ).all()
    
    citations = db.query(NABHRequirementCitation).filter(
        NABHRequirementCitation.requirement_id == requirement.id,
        NABHRequirementCitation.retired_at.is_(None)
    ).all()
    
    summary_data = build_evidence_burden_summary(evidences)
    return NABHRequirementDetail(
        id=requirement.id,
        code=requirement.official_code,
        canonical_code=requirement.canonical_code,
        description=requirement.display_text,
        applicability_default=requirement.applicability_default,
        chapter_code=chap.canonical_code,
        chapter_title=chap.title,
        standard_code=std.canonical_code,
        standard_title=std.title,
        objective_element_code=requirement.canonical_code,
        objective_element_description=requirement.display_text,
        classification=requirement.classification,
        documentation_required=requirement.documentation_required,
        authority_level=requirement.authority_level,
        publication_status=requirement.publication_status,
        source_status=requirement.source_status,
        applicability_rules=[NABHRuleSchema.model_validate(r) for r in rules],
        evidence_requirements=[NABHEvidenceRequirementSchema.model_validate(ev) for ev in evidences],
        citations=[NABHCitationSchema.model_validate(c) for c in citations],
        has_citation=len(citations) > 0,
        has_evidence_requirements=len(evidences) > 0,
        **summary_data
    )


@router.get("/citations/{citation_id}", response_model=CitationResponse)
async def get_ontology_citation(
    citation_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Retrieve detailed citation information by ID."""
    citation = CitationService.get_citation_by_id(db, citation_id)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found")
    return citation
