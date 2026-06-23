"""Create a non-copyright canonical package scaffold in a secure directory."""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.nabh.canonical_package import (
    EXPECTED_CHAPTER_PAGES,
    EXPECTED_CHAPTER_TITLES,
    VERIFIED_SOURCE_ISSUER,
    VERIFIED_SOURCE_SHA256,
    VERIFIED_SOURCE_TITLE,
    verify_source_file,
)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    parser.add_argument("--source-pdf", required=True)
    args = parser.parse_args()

    source = verify_source_file(args.source_pdf)
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise SystemExit(
            f"Refusing to write into non-empty package directory: {output}"
        )

    metadata = {
        "edition_version": "6.0",
        "source_title": VERIFIED_SOURCE_TITLE,
        "source_issuer": VERIFIED_SOURCE_ISSUER,
        "source_sha256": VERIFIED_SOURCE_SHA256,
        "source_file_size_bytes": source["file_size_bytes"],
        "effective_date": "2025-01-01",
        "isbn": "978-81-965264-9-8",
        "extraction_method": "controlled_manual_extraction",
        "extracted_by": "",
        "reviewed_by": "",
        "approved_by": "",
        "published_by": "",
        "review_status": "under_review",
        "change_reason": "",
        "rights_status": "permission_required",
        "rights_reference": "",
        "rights_approved_by": "",
        "rights_approved_at": "",
        "full_text_storage_permitted": False,
        "display_permission_confirmed": False,
        "embedding_permission_confirmed": False,
    }
    (output / "package.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    chapter_rows = [
        {
            "sequence": sequence,
            "chapter_code": chapter,
            "official_title": EXPECTED_CHAPTER_TITLES[chapter],
            "first_printed_page": pages[0],
            "last_printed_page": pages[1],
        }
        for sequence, (chapter, pages) in enumerate(
            EXPECTED_CHAPTER_PAGES.items(),
            start=1,
        )
    ]
    _write_csv(
        output / "chapters.csv",
        [
            "sequence",
            "chapter_code",
            "official_title",
            "first_printed_page",
            "last_printed_page",
        ],
        chapter_rows,
    )
    _write_csv(
        output / "standards.csv",
        [
            "chapter_code",
            "standard_code",
            "exact_title",
            "printed_page",
            "display_order",
        ],
        [],
    )
    _write_csv(
        output / "requirements.csv",
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
        [],
    )
    _write_csv(
        output / "citations.csv",
        [
            "requirement_code",
            "printed_page",
            "pdf_page_index",
            "source_heading",
            "human_verified",
        ],
        [],
    )
    print(json.dumps({
        "package_dir": str(output),
        "source_sha256": source["sha256"],
        "status": "scaffold_created",
    }, indent=2))


if __name__ == "__main__":
    main()
