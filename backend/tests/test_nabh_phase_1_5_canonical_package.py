import csv
import json

import pytest

from app.nabh.canonical_package import (
    CanonicalPackageError,
    EXPECTED_CHAPTERS,
    EXPECTED_CHAPTER_PAGES,
    EXPECTED_CHAPTER_TITLES,
    VERIFIED_SOURCE_ISSUER,
    VERIFIED_SOURCE_SHA256,
    VERIFIED_SOURCE_TITLE,
    load_canonical_package,
    publish_canonical_package,
)


def _letters(index: int) -> str:
    value = ""
    current = index
    while current:
        current, remainder = divmod(current - 1, 26)
        value = chr(97 + remainder) + value
    return value


def _write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_valid_package(tmp_path):
    metadata = {
        "edition_version": "6.0",
        "source_sha256": VERIFIED_SOURCE_SHA256,
        "source_title": VERIFIED_SOURCE_TITLE,
        "source_issuer": VERIFIED_SOURCE_ISSUER,
        "effective_date": "2025-01-01",
        "isbn": "978-81-965264-9-8",
        "review_status": "approved",
        "extracted_by": "extractor-a",
        "reviewed_by": "reviewer-b",
        "approved_by": "approver-c",
        "published_by": "publisher-d",
        "change_reason": "Synthetic contract fixture for Phase 1.5 validation.",
        "extraction_method": "controlled_manual_extraction",
        "rights_status": "permission_required",
        "full_text_storage_permitted": False,
        "display_permission_confirmed": False,
        "embedding_permission_confirmed": False,
    }
    (tmp_path / "package.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    chapters = []
    standards = []
    requirements = []
    citations = []
    for sequence, (chapter, counts) in enumerate(EXPECTED_CHAPTERS.items(), start=1):
        standard_total, requirement_total, core, commitment, achievement, excellence = counts
        first_page, last_page = EXPECTED_CHAPTER_PAGES[chapter]
        chapters.append({
            "sequence": sequence,
            "chapter_code": chapter,
            "official_title": EXPECTED_CHAPTER_TITLES[chapter],
            "first_printed_page": first_page,
            "last_printed_page": last_page,
        })
        chapter_standards = []
        for standard_number in range(1, standard_total + 1):
            code = f"{chapter}.{standard_number}"
            chapter_standards.append(code)
            standards.append({
                "chapter_code": chapter,
                "standard_code": code,
                "exact_title": f"Synthetic standard {code}",
                "printed_page": first_page,
                "display_order": standard_number,
            })

        classifications = (
            ["core"] * core
            + ["commitment"] * commitment
            + ["achievement"] * achievement
            + ["excellence"] * excellence
        )
        per_standard_index = {code: 0 for code in chapter_standards}
        for requirement_index in range(requirement_total):
            standard_code = chapter_standards[requirement_index % standard_total]
            per_standard_index[standard_code] += 1
            code = (
                f"{standard_code}."
                f"{_letters(per_standard_index[standard_code])}"
            )
            requirements.append({
                "chapter_code": chapter,
                "standard_code": standard_code,
                "requirement_code": code,
                "exact_official_text": f"Synthetic non-source requirement {code}.",
                "classification": classifications[requirement_index],
                "printed_page": first_page,
                "pdf_page_index": first_page + 12,
                "documentation_required": "true",
                "display_order": per_standard_index[standard_code],
                "human_verified": "true",
            })
            citations.append({
                "requirement_code": code,
                "printed_page": first_page,
                "pdf_page_index": first_page + 12,
                "source_heading": f"Synthetic heading {code}",
                "human_verified": "true",
            })

    _write_csv(
        tmp_path / "chapters.csv",
        [
            "sequence",
            "chapter_code",
            "official_title",
            "first_printed_page",
            "last_printed_page",
        ],
        chapters,
    )
    _write_csv(
        tmp_path / "standards.csv",
        [
            "chapter_code",
            "standard_code",
            "exact_title",
            "printed_page",
            "display_order",
        ],
        standards,
    )
    _write_csv(
        tmp_path / "requirements.csv",
        [
            "chapter_code",
            "standard_code",
            "requirement_code",
            "exact_official_text",
            "classification",
            "printed_page",
            "pdf_page_index",
            "documentation_required",
            "display_order",
            "human_verified",
        ],
        requirements,
    )
    _write_csv(
        tmp_path / "citations.csv",
        [
            "requirement_code",
            "printed_page",
            "pdf_page_index",
            "source_heading",
            "human_verified",
        ],
        citations,
    )
    return tmp_path


def test_valid_639_record_package_passes_contract(tmp_path):
    package = load_canonical_package(build_valid_package(tmp_path))

    assert len(package.chapters) == 10
    assert len(package.standards) == 100
    assert len(package.requirements) == 639
    assert len(package.citations) == 639


def test_package_rejects_missing_requirement(tmp_path):
    package_dir = build_valid_package(tmp_path)
    requirements_path = package_dir / "requirements.csv"
    rows = list(csv.DictReader(requirements_path.open(encoding="utf-8")))
    _write_csv(requirements_path, list(rows[0]), rows[:-1])

    with pytest.raises(CanonicalPackageError, match="unknown requirement|Expected 639"):
        load_canonical_package(package_dir)


def test_publication_rejects_absent_rights_even_for_valid_package(
    tmp_path,
    db_session,
):
    package = load_canonical_package(build_valid_package(tmp_path))

    with pytest.raises(CanonicalPackageError, match="publication is disabled"):
        publish_canonical_package(
            db_session,
            package,
            allow_full_text=False,
        )
