"""Validate a reviewed NABH canonical package without database mutation."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.nabh.canonical_package import (
    load_canonical_package,
    validate_canonical_package,
    verify_source_file,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_dir")
    parser.add_argument("--source-pdf", required=True)
    args = parser.parse_args()
    package = load_canonical_package(args.package_dir)
    report = validate_canonical_package(package)
    report["source_file"] = verify_source_file(args.source_pdf)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
