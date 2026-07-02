"""Validation and controlled publication for the official NABH 6th corpus."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.database import (
    ApplicabilityDefault,
    EditionStatus,
    KnowledgeAuthorityLevel,
    KnowledgePublicationStatus,
    NABHChapter,
    NABHEdition,
    NABHKnowledgeChange,
    NABHRequirement,
    NABHRequirementClassification,
    NABHRequirementCitation,
    NABHSourceDocument,
    NABHStandard,
    SourceRightsStatus,
    Staff,
    UserRole,
)


EXPECTED_CHAPTERS = {
    "AAC": (13, 87, 6, 68, 9, 4),
    "COP": (20, 136, 13, 107, 12, 4),
    "MOM": (11, 68, 13, 48, 6, 1),
    "PRE": (8, 52, 12, 32, 7, 1),
    "IPC": (8, 49, 13, 33, 3, 0),
    "PSQ": (7, 46, 8, 28, 7, 3),
    "ROM": (6, 37, 4, 23, 8, 2),
    "FMS": (7, 43, 11, 29, 2, 1),
    "HRM": (13, 76, 16, 56, 4, 0),
    "IMS": (7, 45, 9, 33, 2, 1),
}
EXPECTED_TOTALS = {
    "chapters": 10,
    "standards": 100,
    "requirements": 639,
    "core": 105,
    "commitment": 457,
    "achievement": 60,
    "excellence": 17,
}
EXPECTED_CHAPTER_PAGES = {
    "AAC": (55, 67),
    "COP": (68, 88),
    "MOM": (89, 100),
    "PRE": (101, 109),
    "IPC": (110, 118),
    "PSQ": (119, 131),
    "ROM": (132, 139),
    "FMS": (140, 149),
    "HRM": (150, 165),
    "IMS": (166, 174),
}
EXPECTED_CHAPTER_TITLES = {
    "AAC": "Access, Assessment and Continuity of Care",
    "COP": "Care of Patients",
    "MOM": "Management of Medication",
    "PRE": "Patient Rights and Education",
    "IPC": "Infection Prevention and Control",
    "PSQ": "Patient Safety and Quality Improvement",
    "ROM": "Responsibility of Management",
    "FMS": "Facility Management and Safety",
    "HRM": "Human Resource Management",
    "IMS": "Information Management System",
}
VERIFIED_SOURCE_SHA256 = (
    "0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A"
)
VERIFIED_SOURCE_TITLE = "NABH Accreditation Standards for Hospitals"
VERIFIED_SOURCE_ISSUER = (
    "National Accreditation Board for Hospitals and Healthcare Providers"
)
VERIFIED_SOURCE_SIZE_BYTES = 16_404_482
CLASSIFICATIONS = {
    item.value: item
    for item in NABHRequirementClassification
}
REQUIRED_FILES = {
    "package.json",
    "chapters.csv",
    "standards.csv",
    "requirements.csv",
    "citations.csv",
}
STANDARD_CODE_RE = re.compile(r"^(AAC|COP|MOM|PRE|IPC|PSQ|ROM|FMS|HRM|IMS)\.\d+$")
REQUIREMENT_CODE_RE = re.compile(
    r"^(AAC|COP|MOM|PRE|IPC|PSQ|ROM|FMS|HRM|IMS)\.\d+\.[a-z]+$"
)


class CanonicalPackageError(ValueError):
    """Raised when the release package is not safe to publish."""


@dataclass
class CanonicalPackage:
    root: Path
    metadata: dict[str, Any]
    chapters: list[dict[str, str]]
    standards: list[dict[str, str]]
    requirements: list[dict[str, str]]
    citations: list[dict[str, str]]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _required_fields(
    rows: list[dict[str, str]],
    fields: set[str],
    label: str,
) -> None:
    if not rows:
        raise CanonicalPackageError(f"{label} is empty.")
    missing = fields - set(rows[0])
    if missing:
        raise CanonicalPackageError(
            f"{label} is missing columns: {sorted(missing)}"
        )


def _alpha_index(value: str) -> int:
    result = 0
    for character in value:
        result = result * 26 + (ord(character) - ord("a") + 1)
    return result


def load_canonical_package(package_dir: str | Path) -> CanonicalPackage:
    root = Path(package_dir).resolve()
    if not root.is_dir():
        raise CanonicalPackageError(f"Package directory not found: {root}")
    missing_files = REQUIRED_FILES - {path.name for path in root.iterdir()}
    if missing_files:
        raise CanonicalPackageError(
            f"Canonical package is missing files: {sorted(missing_files)}"
        )
    metadata = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package = CanonicalPackage(
        root=root,
        metadata=metadata,
        chapters=_read_csv(root / "chapters.csv"),
        standards=_read_csv(root / "standards.csv"),
        requirements=_read_csv(root / "requirements.csv"),
        citations=_read_csv(root / "citations.csv"),
    )
    validate_canonical_package(package)
    return package


def verify_source_file(source_pdf: str | Path) -> dict[str, Any]:
    path = Path(source_pdf).resolve()
    if not path.is_file():
        raise CanonicalPackageError(f"Verified source PDF not found: {path}")
    file_size = path.stat().st_size
    if file_size != VERIFIED_SOURCE_SIZE_BYTES:
        raise CanonicalPackageError(
            f"Source PDF size mismatch: expected {VERIFIED_SOURCE_SIZE_BYTES}, "
            f"found {file_size}."
        )
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    sha256 = digest.hexdigest().upper()
    if sha256 != VERIFIED_SOURCE_SHA256:
        raise CanonicalPackageError(
            f"Source PDF checksum mismatch: expected {VERIFIED_SOURCE_SHA256}, "
            f"found {sha256}."
        )
    return {
        "path": str(path),
        "file_size_bytes": file_size,
        "sha256": sha256,
    }


def validate_canonical_package(package: CanonicalPackage) -> dict[str, Any]:
    _required_fields(
        package.chapters,
        {
            "sequence",
            "chapter_code",
            "official_title",
            "first_printed_page",
            "last_printed_page",
        },
        "chapters.csv",
    )
    _required_fields(
        package.standards,
        {
            "chapter_code",
            "standard_code",
            "exact_title",
            "printed_page",
            "display_order",
        },
        "standards.csv",
    )
    _required_fields(
        package.requirements,
        {
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
        },
        "requirements.csv",
    )
    _required_fields(
        package.citations,
        {
            "requirement_code",
            "printed_page",
            "pdf_page_index",
            "source_heading",
            "human_verified",
        },
        "citations.csv",
    )

    if package.metadata.get("edition_version") != "6.0":
        raise CanonicalPackageError("package.json edition_version must be '6.0'.")
    if package.metadata.get("source_sha256") != VERIFIED_SOURCE_SHA256:
        raise CanonicalPackageError("package.json source_sha256 is not the verified source.")
    if package.metadata.get("source_title") != VERIFIED_SOURCE_TITLE:
        raise CanonicalPackageError("package.json source_title does not match the source.")
    if package.metadata.get("source_issuer") != VERIFIED_SOURCE_ISSUER:
        raise CanonicalPackageError("package.json source_issuer does not match the source.")
    if package.metadata.get("effective_date") != "2025-01-01":
        raise CanonicalPackageError("package.json effective_date must be 2025-01-01.")
    if package.metadata.get("isbn") != "978-81-965264-9-8":
        raise CanonicalPackageError("package.json ISBN does not match the source.")
    if package.metadata.get("review_status") != "approved":
        raise CanonicalPackageError("Canonical package must be independently approved.")
    for field in (
        "extracted_by",
        "reviewed_by",
        "approved_by",
        "published_by",
        "change_reason",
    ):
        if not str(package.metadata.get(field, "")).strip():
            raise CanonicalPackageError(f"package.json must contain {field}.")
    if package.metadata["extracted_by"] == package.metadata["reviewed_by"]:
        raise CanonicalPackageError("Extractor and reviewer must be different people.")
    if package.metadata["reviewed_by"] == package.metadata["approved_by"]:
        raise CanonicalPackageError("Reviewer and approver must be different people.")
    if package.metadata["extracted_by"] == package.metadata["approved_by"]:
        raise CanonicalPackageError("Extractor and approver must be different people.")

    chapter_codes = [row["chapter_code"].strip() for row in package.chapters]
    if len(chapter_codes) != 10 or set(chapter_codes) != set(EXPECTED_CHAPTERS):
        raise CanonicalPackageError("Chapter register must contain the 10 canonical chapters.")
    ordered_chapters = sorted(package.chapters, key=lambda row: int(row["sequence"]))
    if [row["chapter_code"].strip() for row in ordered_chapters] != list(EXPECTED_CHAPTERS):
        raise CanonicalPackageError("Chapter sequence does not match the official order.")
    for expected_sequence, row in enumerate(ordered_chapters, start=1):
        chapter = row["chapter_code"].strip()
        try:
            sequence = int(row["sequence"])
            first_page = int(row["first_printed_page"])
            last_page = int(row["last_printed_page"])
        except ValueError as exc:
            raise CanonicalPackageError(
                f"{chapter}: sequence and page range must be integers."
            ) from exc
        if sequence != expected_sequence:
            raise CanonicalPackageError(f"{chapter}: invalid chapter sequence {sequence}.")
        if (first_page, last_page) != EXPECTED_CHAPTER_PAGES[chapter]:
            raise CanonicalPackageError(
                f"{chapter}: page range {(first_page, last_page)} does not match "
                f"{EXPECTED_CHAPTER_PAGES[chapter]}."
            )
        if row["official_title"].strip() != EXPECTED_CHAPTER_TITLES[chapter]:
            raise CanonicalPackageError(
                f"{chapter}: official chapter title does not match the source."
            )

    standard_codes: set[str] = set()
    standards_by_chapter: Counter[str] = Counter()
    standard_codes_by_chapter: dict[str, set[str]] = defaultdict(set)
    for row in package.standards:
        chapter = row["chapter_code"].strip()
        code = row["standard_code"].strip()
        if chapter not in EXPECTED_CHAPTERS or not STANDARD_CODE_RE.fullmatch(code):
            raise CanonicalPackageError(f"Invalid standard row: {chapter}/{code}")
        if not code.startswith(f"{chapter}."):
            raise CanonicalPackageError(f"Standard {code} is in the wrong chapter.")
        if code in standard_codes:
            raise CanonicalPackageError(f"Duplicate standard code: {code}")
        if not row["exact_title"].strip():
            raise CanonicalPackageError(f"Standard {code} has no title.")
        try:
            printed_page = int(row["printed_page"])
            display_order = int(row["display_order"])
        except ValueError as exc:
            raise CanonicalPackageError(
                f"Standard {code} has invalid page or display order."
            ) from exc
        first_page, last_page = EXPECTED_CHAPTER_PAGES[chapter]
        if not first_page <= printed_page <= last_page:
            raise CanonicalPackageError(
                f"Standard {code} page {printed_page} is outside {chapter}."
            )
        if display_order < 1:
            raise CanonicalPackageError(f"Standard {code} has invalid display order.")
        if display_order != int(code.split(".")[-1]):
            raise CanonicalPackageError(
                f"Standard {code} display order must match its official number."
            )
        standard_codes.add(code)
        standards_by_chapter[chapter] += 1
        standard_codes_by_chapter[chapter].add(code)

    for chapter, expected in EXPECTED_CHAPTERS.items():
        expected_codes = {
            f"{chapter}.{number}"
            for number in range(1, expected[0] + 1)
        }
        if standard_codes_by_chapter[chapter] != expected_codes:
            raise CanonicalPackageError(
                f"{chapter}: standard numbering is incomplete or noncanonical."
            )

    requirement_codes: set[str] = set()
    requirements_by_chapter: Counter[str] = Counter()
    classifications_by_chapter: dict[str, Counter[str]] = defaultdict(Counter)
    requirements_by_standard: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for row in package.requirements:
        chapter = row["chapter_code"].strip()
        standard_code = row["standard_code"].strip()
        code = row["requirement_code"].strip()
        classification = row["classification"].strip().lower()
        official_text = row["exact_official_text"].strip()
        if chapter not in EXPECTED_CHAPTERS:
            raise CanonicalPackageError(f"Unknown requirement chapter: {chapter}")
        if standard_code not in standard_codes:
            raise CanonicalPackageError(
                f"Requirement {code} references unknown standard {standard_code}."
            )
        if not REQUIREMENT_CODE_RE.fullmatch(code):
            raise CanonicalPackageError(f"Invalid official requirement code: {code}")
        if not code.startswith(f"{standard_code}."):
            raise CanonicalPackageError(
                f"Requirement {code} is not under standard {standard_code}."
            )
        if code in requirement_codes:
            raise CanonicalPackageError(f"Duplicate requirement code: {code}")
        if classification not in CLASSIFICATIONS:
            raise CanonicalPackageError(
                f"Requirement {code} has invalid classification {classification}."
            )
        if not official_text or "..." in official_text:
            raise CanonicalPackageError(
                f"Requirement {code} must contain complete, non-ellipsized official text."
            )
        if row["human_verified"].strip().lower() not in {"true", "yes", "1"}:
            raise CanonicalPackageError(f"Requirement {code} is not human verified.")
        documentation_required = row["documentation_required"].strip().lower()
        if documentation_required not in {"true", "false", "yes", "no", "1", "0"}:
            raise CanonicalPackageError(
                f"Requirement {code} has invalid documentation_required."
            )
        try:
            printed_page = int(row["printed_page"])
            pdf_page_index = int(row["pdf_page_index"])
            display_order = int(row["display_order"])
        except ValueError as exc:
            raise CanonicalPackageError(
                f"Requirement {code} has invalid page locators or display order."
            ) from exc
        first_page, last_page = EXPECTED_CHAPTER_PAGES[chapter]
        if not first_page <= printed_page <= last_page:
            raise CanonicalPackageError(
                f"Requirement {code} page {printed_page} is outside {chapter}."
            )
        if pdf_page_index < 1 or pdf_page_index > 242 or display_order < 1:
            raise CanonicalPackageError(
                f"Requirement {code} has an invalid PDF locator or display order."
            )
        objective_suffix = code.rsplit(".", 1)[-1]
        objective_index = _alpha_index(objective_suffix)
        if display_order != objective_index:
            raise CanonicalPackageError(
                f"Requirement {code} display order must match its official letter."
            )
        requirement_codes.add(code)
        requirements_by_chapter[chapter] += 1
        classifications_by_chapter[chapter][classification] += 1
        requirements_by_standard[standard_code].append((code, objective_index))

    for standard_code in standard_codes:
        objective_rows = requirements_by_standard.get(standard_code, [])
        if not objective_rows:
            raise CanonicalPackageError(
                f"Standard {standard_code} has no Objective Elements."
            )
        objective_indexes = sorted(index for _code, index in objective_rows)
        if objective_indexes != list(range(1, len(objective_indexes) + 1)):
            raise CanonicalPackageError(
                f"Standard {standard_code} has non-contiguous Objective Element letters."
            )

    citations_by_requirement: Counter[str] = Counter()
    for row in package.citations:
        code = row["requirement_code"].strip()
        if code not in requirement_codes:
            raise CanonicalPackageError(
                f"Citation references unknown requirement {code}."
            )
        if row["human_verified"].strip().lower() not in {"true", "yes", "1"}:
            raise CanonicalPackageError(f"Citation for {code} is not human verified.")
        if not row["source_heading"].strip():
            raise CanonicalPackageError(f"Citation for {code} has no source heading.")
        try:
            printed_page = int(row["printed_page"])
            pdf_page_index = int(row["pdf_page_index"])
        except ValueError as exc:
            raise CanonicalPackageError(
                f"Citation for {code} has invalid page locators."
            ) from exc
        requirement_row = next(
            item for item in package.requirements
            if item["requirement_code"].strip() == code
        )
        if printed_page != int(requirement_row["printed_page"]):
            raise CanonicalPackageError(
                f"Citation for {code} does not match the requirement printed page."
            )
        if pdf_page_index != int(requirement_row["pdf_page_index"]):
            raise CanonicalPackageError(
                f"Citation for {code} does not match the requirement PDF page."
            )
        citations_by_requirement[code] += 1
    uncited = sorted(code for code in requirement_codes if citations_by_requirement[code] == 0)
    if uncited:
        raise CanonicalPackageError(
            f"{len(uncited)} requirements have no citation; first: {uncited[:5]}"
        )

    if len(standard_codes) != EXPECTED_TOTALS["standards"]:
        raise CanonicalPackageError(
            f"Expected 100 standards, found {len(standard_codes)}."
        )
    if len(requirement_codes) != EXPECTED_TOTALS["requirements"]:
        raise CanonicalPackageError(
            f"Expected 639 requirements, found {len(requirement_codes)}."
        )

    total_classes: Counter[str] = Counter()
    for chapter, expected in EXPECTED_CHAPTERS.items():
        expected_standards, expected_requirements, core, commitment, achievement, excellence = expected
        if standards_by_chapter[chapter] != expected_standards:
            raise CanonicalPackageError(
                f"{chapter}: expected {expected_standards} standards, "
                f"found {standards_by_chapter[chapter]}."
            )
        if requirements_by_chapter[chapter] != expected_requirements:
            raise CanonicalPackageError(
                f"{chapter}: expected {expected_requirements} requirements, "
                f"found {requirements_by_chapter[chapter]}."
            )
        expected_classes = {
            "core": core,
            "commitment": commitment,
            "achievement": achievement,
            "excellence": excellence,
        }
        if dict(classifications_by_chapter[chapter]) != {
            key: value for key, value in expected_classes.items() if value
        }:
            raise CanonicalPackageError(
                f"{chapter}: classification totals do not match {expected_classes}; "
                f"found {dict(classifications_by_chapter[chapter])}."
            )
        total_classes.update(classifications_by_chapter[chapter])

    for classification in CLASSIFICATIONS:
        if total_classes[classification] != EXPECTED_TOTALS[classification]:
            raise CanonicalPackageError(
                f"Expected {EXPECTED_TOTALS[classification]} {classification} "
                f"requirements, found {total_classes[classification]}."
            )

    return {
        "chapters": len(chapter_codes),
        "standards": len(standard_codes),
        "requirements": len(requirement_codes),
        "classifications": dict(total_classes),
        "citations": sum(citations_by_requirement.values()),
        "source_sha256": package.metadata["source_sha256"],
        "review_status": package.metadata["review_status"],
    }


def _package_digest(package: CanonicalPackage) -> str:
    digest = hashlib.sha256()
    for name in sorted(REQUIRED_FILES):
        digest.update((package.root / name).read_bytes())
    return digest.hexdigest()


def publish_canonical_package(
    db: Session,
    package: CanonicalPackage,
    *,
    allow_full_text: bool = False,
    source_verified: bool = False,
) -> dict[str, Any]:
    """Upsert an approved package. Caller owns commit/rollback."""
    validation = validate_canonical_package(package)
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": 604_639_2025},
        )
    if not allow_full_text:
        raise CanonicalPackageError(
            "Full official requirement text publication is disabled. "
            "Set NABH_FULL_TEXT_PERMISSION_CONFIRMED=true only after written rights approval."
        )
    if not source_verified:
        raise CanonicalPackageError(
            "The operator-held source PDF must be checksum-verified before publication."
        )
    if package.metadata.get("rights_status") != "full_text_permitted":
        raise CanonicalPackageError(
            "package.json rights_status must be 'full_text_permitted' before publication."
        )
    if package.metadata.get("full_text_storage_permitted") is not True:
        raise CanonicalPackageError(
            "package.json must explicitly confirm full_text_storage_permitted=true."
        )

    for field in ("rights_reference", "rights_approved_by", "rights_approved_at"):
        if not str(package.metadata.get(field, "")).strip():
            raise CanonicalPackageError(
                f"package.json must contain publication rights evidence: {field}."
            )

    accountable_staff_ids = {
        package.metadata["extracted_by"],
        package.metadata["reviewed_by"],
        package.metadata["approved_by"],
        package.metadata["published_by"],
    }
    accountable_staff = db.query(Staff).filter(
        Staff.id.in_(accountable_staff_ids),
        Staff.is_active.is_(True),
    ).all()
    found_staff_ids = {staff.id for staff in accountable_staff}
    missing_staff_ids = sorted(accountable_staff_ids - found_staff_ids)
    if missing_staff_ids:
        raise CanonicalPackageError(
            "Package accountability identities must be active Staff records; "
            f"missing: {missing_staff_ids}"
        )
    staff_by_id = {staff.id: staff for staff in accountable_staff}
    for field in ("approved_by", "published_by"):
        staff = staff_by_id[package.metadata[field]]
        if staff.role != UserRole.SUPER_ADMIN:
            raise CanonicalPackageError(
                f"{field} must identify an active super administrator."
            )

    now = datetime.utcnow()
    edition = db.query(NABHEdition).filter(NABHEdition.version == "6.0").first()
    if not edition:
        edition = NABHEdition(
            name="NABH Accreditation Standards for Hospitals - 6th Edition",
            version="6.0",
            status=EditionStatus.ACTIVE,
            effective_date=datetime(2025, 1, 1),
        )
        db.add(edition)
        db.flush()
    edition.name = "NABH Accreditation Standards for Hospitals - 6th Edition"
    edition.status = EditionStatus.ACTIVE
    edition.effective_date = datetime(2025, 1, 1)
    edition.retired_at = None

    source = db.query(NABHSourceDocument).filter(
        NABHSourceDocument.edition_id == edition.id,
        NABHSourceDocument.checksum == package.metadata["source_sha256"],
    ).first()
    if not source:
        source = NABHSourceDocument(
            edition_id=edition.id,
            title=package.metadata["source_title"],
            publisher=package.metadata["source_issuer"],
            edition_version="6th Edition",
            checksum=package.metadata["source_sha256"],
            effective_date=datetime(2025, 1, 1),
            authority_level=KnowledgeAuthorityLevel.NORMATIVE,
            rights_status=SourceRightsStatus.FULL_TEXT_PERMITTED,
            may_store_full_text=True,
            may_display_full_text=bool(
                package.metadata.get("display_permission_confirmed", False)
            ),
            may_create_embeddings=bool(
                package.metadata.get("embedding_permission_confirmed", False)
            ),
            verification_status=KnowledgePublicationStatus.APPROVED,
        )
        db.add(source)
        db.flush()
    source.title = package.metadata["source_title"]
    source.publisher = package.metadata["source_issuer"]
    source.edition_version = "6th Edition"
    source.checksum = package.metadata["source_sha256"]
    source.file_size_bytes = VERIFIED_SOURCE_SIZE_BYTES
    source.pdf_page_count = 242
    source.printed_page_start = 1
    source.printed_page_end = 230
    source.isbn = package.metadata["isbn"]
    source.document_type = "accreditation_standard"
    source.programme = "Hospitals Accreditation Programme"
    source.acquisition_method = "operator_provided_protected_copy"
    source.acquired_at = source.acquired_at or now
    source.authority_level = KnowledgeAuthorityLevel.NORMATIVE
    source.rights_status = SourceRightsStatus.FULL_TEXT_PERMITTED
    source.rights_note = (
        f"Rights approval reference: {package.metadata['rights_reference']}; "
        f"approved by {package.metadata['rights_approved_by']} at "
        f"{package.metadata['rights_approved_at']}."
    )
    source.may_store_full_text = True
    source.may_display_full_text = bool(
        package.metadata.get("display_permission_confirmed", False)
    )
    source.may_create_embeddings = bool(
        package.metadata.get("embedding_permission_confirmed", False)
    )
    source.verification_status = KnowledgePublicationStatus.APPROVED
    source.verified_by = package.metadata["reviewed_by"]
    source.verified_at = now
    source.approved_by = package.metadata["approved_by"]
    source.approved_at = now
    source.effective_date = datetime(2025, 1, 1)
    source.retired_at = None

    chapter_by_code: dict[str, NABHChapter] = {}
    for row in package.chapters:
        code = row["chapter_code"].strip()
        expected = EXPECTED_CHAPTERS[code]
        chapter = db.query(NABHChapter).filter(
            NABHChapter.edition_id == edition.id,
            NABHChapter.canonical_code == code,
        ).first()
        if not chapter:
            chapter = NABHChapter(
                edition_id=edition.id,
                code=code,
                canonical_code=code,
                title=row["official_title"].strip(),
                display_order=int(row["sequence"]),
            )
            db.add(chapter)
        chapter.title = row["official_title"].strip()
        chapter.display_order = int(row["sequence"])
        chapter.official_standards_count = expected[0]
        chapter.official_requirements_count = expected[1]
        chapter.official_measurable_elements_count = expected[1]
        chapter.core_count = expected[2]
        chapter.commitment_count = expected[3]
        chapter.achievement_count = expected[4]
        chapter.excellence_count = expected[5]
        chapter.is_fully_seeded = True
        db.flush()
        chapter_by_code[code] = chapter

    standard_by_code: dict[str, NABHStandard] = {}
    for row in package.standards:
        code = row["standard_code"].strip()
        chapter = chapter_by_code[row["chapter_code"].strip()]
        standard = db.query(NABHStandard).filter(
            NABHStandard.edition_id == edition.id,
            NABHStandard.canonical_code == code,
        ).first()
        if not standard:
            standard = NABHStandard(
                edition_id=edition.id,
                chapter_id=chapter.id,
                code=code.split(".")[-1],
                canonical_code=code,
                title=row["exact_title"].strip(),
                display_order=int(row["display_order"]),
            )
            db.add(standard)
        standard.chapter_id = chapter.id
        standard.code = code.split(".")[-1]
        standard.title = row["exact_title"].strip()
        standard.display_order = int(row["display_order"])
        standard.retired_at = None
        db.flush()
        standard_by_code[code] = standard

    requirement_by_code: dict[str, NABHRequirement] = {}
    for row in package.requirements:
        code = row["requirement_code"].strip()
        standard = standard_by_code[row["standard_code"].strip()]
        requirement = db.query(NABHRequirement).filter(
            NABHRequirement.edition_id == edition.id,
            NABHRequirement.canonical_code == code,
        ).first()
        if not requirement:
            requirement = NABHRequirement(
                edition_id=edition.id,
                standard_id=standard.id,
                official_code=code,
                canonical_code=code,
                display_text=row["exact_official_text"].strip(),
            )
            db.add(requirement)
        requirement.standard_id = standard.id
        requirement.official_code = code
        requirement.canonical_code = code
        requirement.official_text = row["exact_official_text"].strip()
        requirement.display_text = row["exact_official_text"].strip()
        requirement.classification = CLASSIFICATIONS[
            row["classification"].strip().lower()
        ]
        requirement.documentation_required = (
            row["documentation_required"].strip().lower() in {"true", "yes", "1"}
        )
        # Applicability is a hospital-contextual interpretation. Until governed
        # rules exist, the official corpus must not silently claim applicability.
        requirement.applicability_default = ApplicabilityDefault.MANUAL_REVIEW
        requirement.display_order = int(row["display_order"])
        requirement.authority_level = KnowledgeAuthorityLevel.NORMATIVE
        requirement.publication_status = KnowledgePublicationStatus.PUBLISHED
        requirement.source_status = "official_verified"
        requirement.effective_from = edition.effective_date
        requirement.verified_by = package.metadata["reviewed_by"]
        requirement.verified_at = now
        requirement.approved_by = package.metadata["approved_by"]
        requirement.approved_at = now
        requirement.change_reason = package.metadata["change_reason"]
        requirement.retired_at = None
        db.flush()
        requirement_by_code[code] = requirement

    for row in package.citations:
        requirement = requirement_by_code[row["requirement_code"].strip()]
        printed_page = row["printed_page"].strip()
        pdf_page_index = int(row["pdf_page_index"])
        citation = db.query(NABHRequirementCitation).filter(
            NABHRequirementCitation.requirement_id == requirement.id,
            NABHRequirementCitation.document_id == source.id,
            NABHRequirementCitation.printed_page_number == printed_page,
            NABHRequirementCitation.pdf_page_index == pdf_page_index,
        ).first()
        if not citation:
            citation = NABHRequirementCitation(
                requirement_id=requirement.id,
                document_id=source.id,
            )
            db.add(citation)
        citation.section = row.get("section") or requirement.canonical_code
        citation.page_number = printed_page
        citation.printed_page_number = printed_page
        citation.pdf_page_index = pdf_page_index
        citation.source_heading = row["source_heading"].strip()
        citation.clause_text_summary = None
        citation.passage_checksum = hashlib.sha256(
            requirement.official_text.encode("utf-8")
        ).hexdigest()
        citation.extraction_method = package.metadata.get(
            "extraction_method",
            "controlled_manual_extraction",
        )
        citation.human_verified = True
        citation.verified_by = package.metadata["reviewed_by"]
        citation.verified_at = now
        citation.effective_date = edition.effective_date
        citation.file_path = None
        citation.url = None

    published_codes = set(requirement_by_code)
    legacy_requirements = db.query(NABHRequirement).filter(
        NABHRequirement.edition_id == edition.id,
        NABHRequirement.source_status == "legacy_synthetic",
        NABHRequirement.retired_at.is_(None),
    ).all()
    for legacy_requirement in legacy_requirements:
        legacy_requirement.publication_status = KnowledgePublicationStatus.SUPERSEDED
        legacy_requirement.effective_to = now
        legacy_requirement.retired_at = now
        legacy_requirement.change_reason = (
            "Superseded by the independently reviewed official NABH 6th Edition corpus."
        )

    noncanonical_standards = db.query(NABHStandard).filter(
        NABHStandard.edition_id == edition.id,
        NABHStandard.canonical_code.notin_(set(standard_by_code)),
        NABHStandard.retired_at.is_(None),
    ).all()
    for standard in noncanonical_standards:
        standard.retired_at = now

    if len(published_codes) != 639:
        raise CanonicalPackageError(
            "Publication cutover requires exactly 639 canonical requirements."
        )

    package_digest = _package_digest(package)
    change_code = package.metadata.get(
        "change_code",
        f"NABH-6-PUBLISH-{package_digest[:12].upper()}",
    )
    change = db.query(NABHKnowledgeChange).filter(
        NABHKnowledgeChange.change_code == change_code,
    ).first()
    if not change:
        change = NABHKnowledgeChange(
            edition_id=edition.id,
            change_code=change_code,
            what_changed="Published the verified NABH 6th Edition canonical corpus.",
            why_changed=package.metadata["change_reason"],
            supporting_source_ids=[source.id],
            impacted_requirement_ids=[
                requirement.id for requirement in requirement_by_code.values()
            ],
            hospitals_requiring_recompute=[],
            hospitals_requiring_notification=[],
            proposed_by=package.metadata["extracted_by"],
            reviewed_by=package.metadata["reviewed_by"],
            approved_by=package.metadata["approved_by"],
            published_by=package.metadata["published_by"],
            status=KnowledgePublicationStatus.PUBLISHED,
            effective_date=edition.effective_date,
        )
        db.add(change)

    db.flush()
    return {
        **validation,
        "package_digest": package_digest,
        "edition_id": edition.id,
        "source_document_id": source.id,
        "change_code": change_code,
    }


def full_text_permission_enabled() -> bool:
    return os.getenv("NABH_FULL_TEXT_PERMISSION_CONFIRMED", "").lower() == "true"
