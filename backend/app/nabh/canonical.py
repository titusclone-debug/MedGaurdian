"""Canonical NABH requirement access and legacy compatibility helpers."""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.database import (
    HospitalNABHRequirement,
    KnowledgeAuthorityLevel,
    KnowledgePublicationStatus,
    NABHApplicabilityRule,
    NABHEdition,
    NABHEvidenceRequirement,
    NABHMeasurableElement,
    NABHObjectiveElement,
    NABHRequirement,
    NABHRequirementCitation,
)


ACTIVE_PUBLICATION_STATUSES = {
    KnowledgePublicationStatus.APPROVED,
    KnowledgePublicationStatus.PUBLISHED,
}


def mirror_legacy_requirement(
    db: Session,
    measurable_element: NABHMeasurableElement,
) -> NABHRequirement:
    """Create the temporary canonical mirror for one Phase 1 synthetic row."""
    existing = db.query(NABHRequirement).filter(
        NABHRequirement.id == measurable_element.id,
    ).first()
    if existing:
        return existing

    objective = db.query(NABHObjectiveElement).filter(
        NABHObjectiveElement.id == measurable_element.objective_element_id,
    ).first()
    if not objective:
        raise ValueError(
            f"Legacy measurable element {measurable_element.id} has no objective element."
        )

    requirement = NABHRequirement(
        id=measurable_element.id,
        edition_id=measurable_element.edition_id,
        standard_id=objective.standard_id,
        official_code=measurable_element.canonical_code,
        canonical_code=measurable_element.canonical_code,
        official_text=None,
        display_text=measurable_element.description,
        classification=None,
        documentation_required=None,
        applicability_default=measurable_element.applicability_default,
        scoring_weight=measurable_element.scoring_weight,
        risk_weight=measurable_element.risk_weight,
        default_owner_role=measurable_element.default_owner_role,
        display_order=measurable_element.display_order,
        authority_level=KnowledgeAuthorityLevel.MEDGUARDIAN_INTERPRETATION,
        publication_status=KnowledgePublicationStatus.PUBLISHED,
        source_status="legacy_synthetic",
        change_reason="Temporary compatibility mirror for the Phase 1 synthetic hierarchy.",
        legacy_measurable_element_id=measurable_element.id,
    )
    db.add(requirement)
    db.flush()

    db.query(NABHEvidenceRequirement).filter(
        NABHEvidenceRequirement.measurable_element_id == measurable_element.id,
        NABHEvidenceRequirement.requirement_id.is_(None),
    ).update(
        {NABHEvidenceRequirement.requirement_id: requirement.id},
        synchronize_session=False,
    )
    db.query(NABHRequirementCitation).filter(
        NABHRequirementCitation.measurable_element_id == measurable_element.id,
        NABHRequirementCitation.requirement_id.is_(None),
    ).update(
        {NABHRequirementCitation.requirement_id: requirement.id},
        synchronize_session=False,
    )
    db.query(NABHApplicabilityRule).filter(
        NABHApplicabilityRule.measurable_element_id == measurable_element.id,
        NABHApplicabilityRule.requirement_id.is_(None),
    ).update(
        {NABHApplicabilityRule.requirement_id: requirement.id},
        synchronize_session=False,
    )
    db.query(HospitalNABHRequirement).filter(
        HospitalNABHRequirement.requirement_id == measurable_element.id,
        HospitalNABHRequirement.canonical_requirement_id.is_(None),
    ).update(
        {HospitalNABHRequirement.canonical_requirement_id: requirement.id},
        synchronize_session=False,
    )
    return requirement


def ensure_canonical_compatibility(
    db: Session,
    edition_id: Optional[str] = None,
) -> int:
    """Mirror still-active legacy requirements during the transition window."""
    query = db.query(NABHMeasurableElement).filter(
        NABHMeasurableElement.retired_at.is_(None),
    )
    if edition_id:
        query = query.filter(NABHMeasurableElement.edition_id == edition_id)

    legacy_rows = query.all()
    existing_ids = {
        row[0]
        for row in db.query(NABHRequirement.legacy_measurable_element_id).filter(
            NABHRequirement.legacy_measurable_element_id.in_(
                [row.id for row in legacy_rows]
            )
        ).all()
    } if legacy_rows else set()

    created = 0
    for legacy_row in legacy_rows:
        if legacy_row.id not in existing_ids:
            mirror_legacy_requirement(db, legacy_row)
            created += 1

    mirrored_rows = db.query(
        NABHRequirement,
        NABHMeasurableElement,
        NABHObjectiveElement,
    ).join(
        NABHMeasurableElement,
        NABHRequirement.legacy_measurable_element_id == NABHMeasurableElement.id,
    ).join(
        NABHObjectiveElement,
        NABHMeasurableElement.objective_element_id == NABHObjectiveElement.id,
    ).filter(
        NABHRequirement.source_status == "legacy_synthetic",
    )
    if edition_id:
        mirrored_rows = mirrored_rows.filter(
            NABHRequirement.edition_id == edition_id,
        )
    for requirement, measurable, objective in mirrored_rows.all():
        retired_at = measurable.retired_at or objective.retired_at
        if retired_at:
            requirement.retired_at = retired_at
            requirement.effective_to = retired_at
            requirement.publication_status = KnowledgePublicationStatus.RETIRED
        elif requirement.publication_status == KnowledgePublicationStatus.RETIRED:
            requirement.retired_at = None
            requirement.effective_to = None
            requirement.publication_status = KnowledgePublicationStatus.PUBLISHED

    link_supporting_records(db, [row.id for row in legacy_rows])
    db.flush()
    return created


def active_requirement_query(
    db: Session,
    *,
    edition: Optional[NABHEdition] = None,
):
    query = db.query(NABHRequirement).filter(
        NABHRequirement.retired_at.is_(None),
        NABHRequirement.publication_status.in_(ACTIVE_PUBLICATION_STATUSES),
    )
    if edition:
        query = query.filter(NABHRequirement.edition_id == edition.id)
    return query


def active_requirement_ids(
    db: Session,
    edition: NABHEdition,
) -> list[str]:
    ensure_canonical_compatibility(db, edition.id)
    return [
        row[0]
        for row in active_requirement_query(db, edition=edition).with_entities(
            NABHRequirement.id
        ).all()
    ]


def link_supporting_records(
    db: Session,
    requirement_ids: Iterable[str],
) -> None:
    """Populate canonical links for support rows that still carry legacy IDs."""
    ids = list(set(requirement_ids))
    if not ids:
        return
    for model in (
        NABHEvidenceRequirement,
        NABHRequirementCitation,
        NABHApplicabilityRule,
    ):
        db.query(model).filter(
            model.measurable_element_id.in_(ids),
            model.requirement_id.is_(None),
        ).update(
            {model.requirement_id: model.measurable_element_id},
            synchronize_session=False,
        )
    db.query(HospitalNABHRequirement).filter(
        HospitalNABHRequirement.requirement_id.in_(ids),
        HospitalNABHRequirement.canonical_requirement_id.is_(None),
    ).update(
        {
            HospitalNABHRequirement.canonical_requirement_id:
                HospitalNABHRequirement.requirement_id
        },
        synchronize_session=False,
    )
    db.flush()
