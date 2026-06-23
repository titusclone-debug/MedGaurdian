from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException
from collections import defaultdict
from app.models.database import (
    Hospital, NABHEdition, HospitalNABHRequirement,
    NABHRequirement,
    NABHStandard, NABHChapter
)
from app.nabh.canonical import ACTIVE_PUBLICATION_STATUSES, ensure_canonical_compatibility

def calculate_hospital_readiness(
    db: Session,
    hospital_id: str,
    edition_version: str = "6.0"
) -> dict:
    """
    Calculate readiness scores and per-chapter breakdown for a hospital
    using the new ontology/applicability system.
    """
    # Verify hospital exists
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=404,
            detail=f"Hospital with ID '{hospital_id}' does not exist."
        )

    # Verify edition exists and is not retired
    edition = db.query(NABHEdition).filter(
        NABHEdition.version == edition_version,
        NABHEdition.retired_at.is_(None)
    ).first()
    if not edition:
        raise HTTPException(
            status_code=404,
            detail=f"NABH Edition version '{edition_version}' does not exist or is retired."
        )

    ensure_canonical_compatibility(db, edition.id)

    # Join hospital state to the canonical Objective Element requirement.
    official_chapters = ["AAC", "COP", "MOM", "PRE", "IPC", "PSQ", "ROM", "FMS", "HRM", "IMS"]
    
    rows = db.query(
        HospitalNABHRequirement,
        NABHRequirement,
        NABHStandard,
        NABHChapter,
        NABHEdition
    ).join(
        NABHRequirement,
        HospitalNABHRequirement.canonical_requirement_id == NABHRequirement.id
    ).join(
        NABHStandard, NABHRequirement.standard_id == NABHStandard.id
    ).join(
        NABHChapter, NABHStandard.chapter_id == NABHChapter.id
    ).join(
        NABHEdition, NABHChapter.edition_id == NABHEdition.id
    ).filter(
        HospitalNABHRequirement.hospital_id == hospital_id,
        NABHEdition.version == edition_version,
        HospitalNABHRequirement.retired_at.is_(None),
        NABHRequirement.retired_at.is_(None),
        NABHRequirement.publication_status.in_(ACTIVE_PUBLICATION_STATUSES),
        NABHStandard.retired_at.is_(None),
        NABHChapter.retired_at.is_(None),
        NABHEdition.retired_at.is_(None),
        NABHChapter.canonical_code.in_(official_chapters)
    ).all()

    now = datetime.utcnow()
    total_state_rows = len(rows)

    # Global Calculations
    if total_state_rows == 0:
        status = "not_scoped"
        denominator = 0
        ready_count = 0
        readiness_score_percent = None
    else:
        # Denominator excludes not_applicable
        denominator_rows = [
            row for row in rows
            if row.HospitalNABHRequirement.applicability_status.value in ("applicable", "conditional", "manual_review")
        ]
        denominator = len(denominator_rows)
        
        # Numerator (ready count): only compliant rows that are in the denominator
        ready_count = sum(
            1 for row in denominator_rows
            if row.HospitalNABHRequirement.readiness_status.value == "compliant"
        )
        
        if denominator == 0:
            status = "no_applicable_requirements"
            readiness_score_percent = None
        else:
            readiness_score_percent = round((ready_count / denominator) * 100, 1)
            if readiness_score_percent == 100.0:
                status = "ready"
            else:
                status = "in_progress"

    # Status counts across all state rows
    applicable_count = sum(1 for r in rows if r.HospitalNABHRequirement.applicability_status.value == "applicable")
    conditional_count = sum(1 for r in rows if r.HospitalNABHRequirement.applicability_status.value == "conditional")
    manual_review_count = sum(1 for r in rows if r.HospitalNABHRequirement.applicability_status.value == "manual_review")
    not_applicable_count = sum(1 for r in rows if r.HospitalNABHRequirement.applicability_status.value == "not_applicable")

    compliant_count = sum(1 for r in rows if r.HospitalNABHRequirement.readiness_status.value == "compliant")
    non_compliant_count = sum(1 for r in rows if r.HospitalNABHRequirement.readiness_status.value == "non_compliant")
    partially_compliant_count = sum(1 for r in rows if r.HospitalNABHRequirement.readiness_status.value == "partially_compliant")
    under_review_count = sum(1 for r in rows if r.HospitalNABHRequirement.readiness_status.value == "under_review")

    # Group by Chapter code
    rows_by_chapter = defaultdict(list)
    for row in rows:
        rows_by_chapter[row.NABHChapter.canonical_code].append(row)

    # Sort chapters by their display order in DB
    sorted_chapters = sorted(
        rows_by_chapter.keys(),
        key=lambda code: rows_by_chapter[code][0].NABHChapter.display_order
    )

    chapters_breakdown = []
    for ch_code in sorted_chapters:
        ch_rows = rows_by_chapter[ch_code]
        ch_title = ch_rows[0].NABHChapter.title
        ch_total_state_rows = len(ch_rows)

        ch_denominator_rows = [
            row for row in ch_rows
            if row.HospitalNABHRequirement.applicability_status.value in ("applicable", "conditional", "manual_review")
        ]
        ch_denominator = len(ch_denominator_rows)

        ch_ready_count = sum(
            1 for row in ch_denominator_rows
            if row.HospitalNABHRequirement.readiness_status.value == "compliant"
        )

        if ch_total_state_rows == 0:
            ch_status = "not_scoped"
            ch_score = None
        elif ch_denominator == 0:
            ch_status = "no_applicable_requirements"
            ch_score = None
        else:
            ch_score = round((ch_ready_count / ch_denominator) * 100, 1)
            if ch_score == 100.0:
                ch_status = "ready"
            else:
                ch_status = "in_progress"

        ch_applicable = sum(1 for r in ch_rows if r.HospitalNABHRequirement.applicability_status.value == "applicable")
        ch_conditional = sum(1 for r in ch_rows if r.HospitalNABHRequirement.applicability_status.value == "conditional")
        ch_manual_review = sum(1 for r in ch_rows if r.HospitalNABHRequirement.applicability_status.value == "manual_review")
        ch_not_applicable = sum(1 for r in ch_rows if r.HospitalNABHRequirement.applicability_status.value == "not_applicable")

        ch_compliant = sum(1 for r in ch_rows if r.HospitalNABHRequirement.readiness_status.value == "compliant")
        ch_non_compliant = sum(1 for r in ch_rows if r.HospitalNABHRequirement.readiness_status.value == "non_compliant")
        ch_partially_compliant = sum(1 for r in ch_rows if r.HospitalNABHRequirement.readiness_status.value == "partially_compliant")
        ch_under_review = sum(1 for r in ch_rows if r.HospitalNABHRequirement.readiness_status.value == "under_review")

        chapters_breakdown.append({
            "chapter_code": ch_code,
            "chapter_title": ch_title,
            "total_state_rows": ch_total_state_rows,
            "denominator": ch_denominator,
            "ready_count": ch_ready_count,
            "readiness_score_percent": ch_score,
            "status": ch_status,
            "applicable_count": ch_applicable,
            "conditional_count": ch_conditional,
            "manual_review_count": ch_manual_review,
            "not_applicable_count": ch_not_applicable,
            "compliant_count": ch_compliant,
            "non_compliant_count": ch_non_compliant,
            "partially_compliant_count": ch_partially_compliant,
            "under_review_count": ch_under_review
        })

    return {
        "hospital_id": hospital_id,
        "edition_version": edition_version,
        "status": status,
        "calculated_at": now,
        "generated_at": now,
        "total_state_rows": total_state_rows,
        "denominator": denominator,
        "ready_count": ready_count,
        "readiness_score_percent": readiness_score_percent,
        "not_applicable_count": not_applicable_count,
        "applicable_count": applicable_count,
        "conditional_count": conditional_count,
        "manual_review_count": manual_review_count,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "partially_compliant_count": partially_compliant_count,
        "under_review_count": under_review_count,
        "chapters": chapters_breakdown
    }
