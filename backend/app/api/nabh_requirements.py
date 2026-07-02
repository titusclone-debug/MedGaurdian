"""NABH 6th Edition Hospital Requirement Routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role, Staff
from app.api.nabh_helpers import (
    assert_staff_belongs_to_hospital,
    build_evidence_burden_summary,
)
from app.models.database import (
    Hospital, UserRole,
    HospitalNABHRequirement, NABHRequirement, NABHChapter, NABHStandard,
    NABHRequirementCitation, NABHSourceDocument, NABHApplicabilityRule, NABHEvidenceRequirement,
    HospitalRequirementEvidenceLink, EvidenceStatus, ApplicabilityDefault,
    ComplianceStatus, KnowledgePublicationStatus
)
from app.nabh.canonical import ensure_canonical_compatibility, resolve_canonical_requirement_id
from app.nabh.public_text import redact_source_heading, requirement_public_text
from app.nabh.quality import assert_compliant_status_allowed, NABHQualityError
from app.schemas.nabh import (
    PaginatedHospitalRequirementSummary,
    HospitalRequirementDetail as SchemaHospitalRequirementDetail,
    HospitalRequirementSummary as SchemaHospitalRequirementSummary,
    HospitalRequirementPatch,
    HospitalRequirementEvidenceLinkSchema,
    NABHRequirementDetail,
    NABHRuleSchema,
    NABHEvidenceRequirementSchema,
    NABHCitationSchema
)

router = APIRouter()

@router.get("/{hospital_id}", response_model=PaginatedHospitalRequirementSummary)
async def get_hospital_requirements(
    hospital_id: str,
    chapter_code: Optional[str] = Query(None),
    applicability_status: Optional[ApplicabilityDefault] = Query(None),
    evidence_status: Optional[EvidenceStatus] = Query(None),
    readiness_status: Optional[ComplianceStatus] = Query(None),
    owner_id: Optional[str] = Query(None),
    include_retired: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Retrieve paginated, filtered hospital requirement progress states with ontology reference information."""
    assert_hospital_access(current_user, hospital_id)
    
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")

    ensure_canonical_compatibility(db)
    query = db.query(
        HospitalNABHRequirement, NABHRequirement, NABHChapter, NABHStandard
    ).join(
        NABHRequirement,
        HospitalNABHRequirement.canonical_requirement_id == NABHRequirement.id,
    ).join(
        NABHStandard, NABHRequirement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        HospitalNABHRequirement.hospital_id == hospital_id
    )
    
    if not include_retired:
        query = query.filter(
            HospitalNABHRequirement.retired_at.is_(None),
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
    if applicability_status:
        query = query.filter(HospitalNABHRequirement.applicability_status == applicability_status)
    if evidence_status:
        query = query.filter(HospitalNABHRequirement.evidence_status == evidence_status)
    if readiness_status:
        query = query.filter(HospitalNABHRequirement.readiness_status == readiness_status)
    if owner_id:
        query = query.filter(HospitalNABHRequirement.owner_id == owner_id)
        
    total = query.count()
    results = query.order_by(
        NABHChapter.display_order,
        NABHStandard.display_order,
        NABHRequirement.display_order,
        NABHRequirement.canonical_code,
    ).offset(offset).limit(limit).all()
    
    items = [
        SchemaHospitalRequirementSummary(
            id=req.id,
            hospital_id=req.hospital_id,
            requirement_id=req.canonical_requirement_id,
            applicability_status=req.applicability_status,
            applicability_reason=req.applicability_reason,
            maturity_level=req.maturity_level,
            evidence_status=req.evidence_status,
            owner_id=req.owner_id,
            due_date=req.due_date,
            last_reviewed_at=req.last_reviewed_at,
            last_reviewed_by=req.last_reviewed_by,
            readiness_status=req.readiness_status,
            requirement_code=requirement.canonical_code,
            requirement_description=requirement_public_text(requirement),
            chapter_code=chap.canonical_code,
            standard_code=std.canonical_code,
            objective_element_code=requirement.canonical_code,
        )
        for req, requirement, chap, std in results
    ]
    
    return PaginatedHospitalRequirementSummary(
        total=total,
        limit=limit,
        offset=offset,
        items=items
    )


@router.get("/{hospital_id}/{requirement_id}", response_model=SchemaHospitalRequirementDetail)
async def get_hospital_requirement_detail(
    hospital_id: str,
    requirement_id: str,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Retrieve detailed state of a specific hospital requirement."""
    assert_hospital_access(current_user, hospital_id)
    
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    ensure_canonical_compatibility(db)
    
    canonical_id, is_legacy = resolve_canonical_requirement_id(db, requirement_id)
    if is_legacy:
        response.headers["Warning"] = '299 - "Legacy NABH requirement ID used. Please migrate to canonical IDs."'
        
    result = db.query(
        HospitalNABHRequirement, NABHRequirement, NABHChapter, NABHStandard
    ).join(
        NABHRequirement,
        HospitalNABHRequirement.canonical_requirement_id == NABHRequirement.id,
    ).join(
        NABHStandard, NABHRequirement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        HospitalNABHRequirement.hospital_id == hospital_id,
        HospitalNABHRequirement.canonical_requirement_id == canonical_id,
        HospitalNABHRequirement.retired_at.is_(None),
        NABHRequirement.retired_at.is_(None),
        NABHRequirement.publication_status.in_([
            KnowledgePublicationStatus.APPROVED,
            KnowledgePublicationStatus.PUBLISHED,
        ]),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None)
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Hospital requirement state not found")
        
    req, requirement, chap, std = result
    
    rules = db.query(NABHApplicabilityRule).filter(
        NABHApplicabilityRule.requirement_id == requirement.id,
        NABHApplicabilityRule.retired_at.is_(None)
    ).all()
    
    evidences = db.query(NABHEvidenceRequirement).filter(
        NABHEvidenceRequirement.requirement_id == requirement.id,
        NABHEvidenceRequirement.retired_at.is_(None)
    ).all()
    
    citations = db.query(NABHRequirementCitation, NABHSourceDocument).outerjoin(
        NABHSourceDocument, NABHRequirementCitation.document_id == NABHSourceDocument.id
    ).filter(
        NABHRequirementCitation.requirement_id == requirement.id,
        NABHRequirementCitation.retired_at.is_(None)
    ).all()
    citation_schemas = [
        NABHCitationSchema(
            id=citation.id,
            requirement_id=citation.requirement_id,
            measurable_element_id=citation.measurable_element_id,
            document_id=citation.document_id,
            section=citation.section,
            page_number=citation.page_number,
            printed_page_number=citation.printed_page_number,
            pdf_page_index=citation.pdf_page_index,
            source_heading=redact_source_heading(document, citation.source_heading),
            clause_text_summary=citation.clause_text_summary if document and document.may_display_full_text else None,
            file_path=citation.file_path if document and document.may_display_full_text else None,
            url=citation.url if document and document.may_display_full_text else None,
            human_verified=citation.human_verified,
        )
        for citation, document in citations
    ]
    
    links = db.query(HospitalRequirementEvidenceLink).filter(
        HospitalRequirementEvidenceLink.hospital_requirement_id == req.id,
        HospitalRequirementEvidenceLink.retired_at.is_(None)
    ).all()
    
    summary_data = build_evidence_burden_summary(evidences)
    ont_detail = NABHRequirementDetail(
        id=requirement.id,
        code=requirement.official_code,
        canonical_code=requirement.canonical_code,
        description=requirement_public_text(requirement),
        applicability_default=requirement.applicability_default,
        chapter_code=chap.canonical_code,
        chapter_title=chap.title,
        standard_code=std.canonical_code,
        standard_title=std.title,
        objective_element_code=requirement.canonical_code,
        objective_element_description=requirement_public_text(requirement),
        classification=requirement.classification,
        documentation_required=requirement.documentation_required,
        authority_level=requirement.authority_level,
        publication_status=requirement.publication_status,
        source_status=requirement.source_status,
        applicability_rules=[NABHRuleSchema.model_validate(r) for r in rules],
        evidence_requirements=[NABHEvidenceRequirementSchema.model_validate(ev) for ev in evidences],
        citations=citation_schemas,
        has_citation=len(citation_schemas) > 0,
        has_evidence_requirements=len(evidences) > 0,
        **summary_data
    )
    
    return SchemaHospitalRequirementDetail(
        id=req.id,
        hospital_id=req.hospital_id,
        requirement_id=req.canonical_requirement_id,
        applicability_status=req.applicability_status,
        applicability_reason=req.applicability_reason,
        maturity_level=req.maturity_level,
        evidence_status=req.evidence_status,
        owner_id=req.owner_id,
        due_date=req.due_date,
        last_reviewed_at=req.last_reviewed_at,
        last_reviewed_by=req.last_reviewed_by,
        readiness_status=req.readiness_status,
        ontology_requirement=ont_detail,
        evidence_links=[HospitalRequirementEvidenceLinkSchema.model_validate(l) for l in links]
    )


@router.patch("/{hospital_id}/{requirement_id}", response_model=SchemaHospitalRequirementDetail)
async def patch_hospital_requirement(
    hospital_id: str,
    requirement_id: str,
    patch: HospitalRequirementPatch,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER]))
):
    """Patch standard progress fields for a hospital's requirement state."""
    assert_hospital_access(current_user, hospital_id)
    
    hosp = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    ensure_canonical_compatibility(db)
    
    canonical_id, is_legacy = resolve_canonical_requirement_id(db, requirement_id)
    if is_legacy:
        response.headers["Warning"] = '299 - "Legacy NABH requirement ID used. Please migrate to canonical IDs."'

    result = db.query(
        HospitalNABHRequirement, NABHRequirement, NABHChapter, NABHStandard
    ).join(
        NABHRequirement,
        HospitalNABHRequirement.canonical_requirement_id == NABHRequirement.id,
    ).join(
        NABHStandard, NABHRequirement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).filter(
        HospitalNABHRequirement.hospital_id == hospital_id,
        HospitalNABHRequirement.canonical_requirement_id == canonical_id,
        HospitalNABHRequirement.retired_at.is_(None),
        NABHRequirement.retired_at.is_(None),
        NABHRequirement.publication_status.in_([
            KnowledgePublicationStatus.APPROVED,
            KnowledgePublicationStatus.PUBLISHED,
        ]),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None)
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Hospital requirement state not found")

    req, requirement, chap, std = result
        
    patch_data = patch.model_dump(exclude_unset=True)
    
    # Collect staff IDs to validate in one query
    staff_ids_to_check = []
    if "owner_id" in patch_data and patch_data["owner_id"]:
        staff_ids_to_check.append(("owner_id", patch_data["owner_id"]))
    if "last_reviewed_by" in patch_data and patch_data["last_reviewed_by"]:
        staff_ids_to_check.append(("last_reviewed_by", patch_data["last_reviewed_by"]))
        
    for field_name, staff_id in staff_ids_to_check:
        assert_staff_belongs_to_hospital(db, staff_id, hospital_id, field_name)
        
    try:
        assert_compliant_status_allowed(db, requirement.id, patch_data.get("readiness_status"))
    except NABHQualityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    for key, val in patch_data.items():
        setattr(req, key, val)
        
    db.commit()
    
    rules = db.query(NABHApplicabilityRule).filter(
        NABHApplicabilityRule.requirement_id == requirement.id,
        NABHApplicabilityRule.retired_at.is_(None)
    ).all()
    
    evidences = db.query(NABHEvidenceRequirement).filter(
        NABHEvidenceRequirement.requirement_id == requirement.id,
        NABHEvidenceRequirement.retired_at.is_(None)
    ).all()
    
    citations = db.query(NABHRequirementCitation, NABHSourceDocument).outerjoin(
        NABHSourceDocument, NABHRequirementCitation.document_id == NABHSourceDocument.id
    ).filter(
        NABHRequirementCitation.requirement_id == requirement.id,
        NABHRequirementCitation.retired_at.is_(None)
    ).all()
    citation_schemas = [
        NABHCitationSchema(
            id=citation.id,
            requirement_id=citation.requirement_id,
            measurable_element_id=citation.measurable_element_id,
            document_id=citation.document_id,
            section=citation.section,
            page_number=citation.page_number,
            printed_page_number=citation.printed_page_number,
            pdf_page_index=citation.pdf_page_index,
            source_heading=redact_source_heading(document, citation.source_heading),
            clause_text_summary=citation.clause_text_summary if document and document.may_display_full_text else None,
            file_path=citation.file_path if document and document.may_display_full_text else None,
            url=citation.url if document and document.may_display_full_text else None,
            human_verified=citation.human_verified,
        )
        for citation, document in citations
    ]
    
    links = db.query(HospitalRequirementEvidenceLink).filter(
        HospitalRequirementEvidenceLink.hospital_requirement_id == req.id,
        HospitalRequirementEvidenceLink.retired_at.is_(None)
    ).all()
    
    summary_data = build_evidence_burden_summary(evidences)
    ont_detail = NABHRequirementDetail(
        id=requirement.id,
        code=requirement.official_code,
        canonical_code=requirement.canonical_code,
        description=requirement_public_text(requirement),
        applicability_default=requirement.applicability_default,
        chapter_code=chap.canonical_code,
        chapter_title=chap.title,
        standard_code=std.canonical_code,
        standard_title=std.title,
        objective_element_code=requirement.canonical_code,
        objective_element_description=requirement_public_text(requirement),
        classification=requirement.classification,
        documentation_required=requirement.documentation_required,
        authority_level=requirement.authority_level,
        publication_status=requirement.publication_status,
        source_status=requirement.source_status,
        applicability_rules=[NABHRuleSchema.model_validate(r) for r in rules],
        evidence_requirements=[NABHEvidenceRequirementSchema.model_validate(ev) for ev in evidences],
        citations=citation_schemas,
        has_citation=len(citation_schemas) > 0,
        has_evidence_requirements=len(evidences) > 0,
        **summary_data
    )
    
    return SchemaHospitalRequirementDetail(
        id=req.id,
        hospital_id=req.hospital_id,
        requirement_id=req.canonical_requirement_id,
        applicability_status=req.applicability_status,
        applicability_reason=req.applicability_reason,
        maturity_level=req.maturity_level,
        evidence_status=req.evidence_status,
        owner_id=req.owner_id,
        due_date=req.due_date,
        last_reviewed_at=req.last_reviewed_at,
        last_reviewed_by=req.last_reviewed_by,
        readiness_status=req.readiness_status,
        ontology_requirement=ont_detail,
        evidence_links=[HospitalRequirementEvidenceLinkSchema.model_validate(l) for l in links]
    )
