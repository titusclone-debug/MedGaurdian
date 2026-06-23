"""Publish an approved NABH package transactionally; no web mutation endpoint."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, engine
from app.core.migrations import inspect_migration_state
from app.nabh.canonical_package import (
    VERIFIED_SOURCE_SHA256,
    full_text_permission_enabled,
    load_canonical_package,
    publish_canonical_package,
    verify_source_file,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_dir")
    parser.add_argument("--source-pdf", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-edition")
    parser.add_argument("--confirm-requirements", type=int)
    parser.add_argument("--confirm-source-sha256")
    args = parser.parse_args()

    package = load_canonical_package(args.package_dir)
    source_file = verify_source_file(args.source_pdf)
    migration_state = inspect_migration_state(engine)
    if not migration_state["is_current"]:
        raise SystemExit(
            f"Database is not at Alembic head: {migration_state}"
        )
    if not args.dry_run:
        confirmations = (
            args.confirm_edition == "6.0",
            args.confirm_requirements == 639,
            args.confirm_source_sha256 == VERIFIED_SOURCE_SHA256,
        )
        if not all(confirmations):
            raise SystemExit(
                "Publication requires exact --confirm-edition 6.0, "
                "--confirm-requirements 639, and --confirm-source-sha256."
            )
        if engine.dialect.name != "postgresql":
            raise SystemExit(
                "Canonical publication is restricted to PostgreSQL. "
                "Use --dry-run for non-production validation."
            )

    db = SessionLocal()
    try:
        result = publish_canonical_package(
            db,
            package,
            allow_full_text=full_text_permission_enabled(),
            source_verified=True,
        )
        result["source_file_sha256"] = source_file["sha256"]
        if args.dry_run:
            db.rollback()
            result["dry_run"] = True
        else:
            db.commit()
            result["dry_run"] = False
        print(json.dumps(result, indent=2, sort_keys=True))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
