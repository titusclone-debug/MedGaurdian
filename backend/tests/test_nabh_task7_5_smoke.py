"""
Smoke Tests: Task 7.5 — Citation Seeding & Validator Refinements

Covers:
  - Validator: missing citations file (required by default, optional with flag)
  - Validator: invalid date format raises ValidationError
  - Validator: missing file_path AND url raises ValidationError
  - Validator: citation referencing unknown measurable element code
  - Validator: edition_version mismatch in citation
  - Validator: envelope format required; bare arrays only with allow_bare_citation_array=True
  - Validator: _meta.citation_complete must be a boolean when _meta exists
  - Seeder: NABHSourceDocument upserted with publisher/version
  - Seeder: NABHRequirementCitation created and linked
  - Seeder: re-run is idempotent (no duplicates)
  - Seeder: in-place update of clause_text_summary and url
"""

import os
import json
import pytest
from sqlalchemy import text

from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement,
    NABHSourceDocument, NABHRequirementCitation,
)
from app.nabh.validator import validate_ontology_seeds, ValidationError
from app.nabh.seeder import seed_versioned_ontology


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_citations():
    """Two well-formed citations covering both measurable elements (bare list).

    Tests use this as the inner citations list; _base_seed_files wraps it in
    the production envelope format before writing to disk.
    """
    return [
        {
            "measurable_element_code": "IPC-1.a.1",
            "edition_version": "6.0",
            "document_title": "NABH 6th Edition Reference Guide",
            "document_publisher": "National Accreditation Board for Hospitals & Healthcare Providers",
            "document_version": "6.0",
            "section": "Chapter IPC",
            "page_number": "142",
            "clause_text_summary": "Triage protocols must include infection control scanning.",
            "effective_date": "2026-01-01",
            "file_path": "/excerpts/IPC_1a1_triage.png",
            "url": None,
        },
        {
            "measurable_element_code": "IPC-1.a.2",
            "edition_version": "6.0",
            "document_title": "NABH 6th Edition Reference Guide",
            "document_publisher": "National Accreditation Board for Hospitals & Healthcare Providers",
            "document_version": "6.0",
            "section": "Chapter IPC",
            "page_number": "143",
            "clause_text_summary": "Manual reviewed annually by Infection Control Committee.",
            "effective_date": "2026-01-01",
            "file_path": None,
            "url": "https://nabh.co/standards/hic-manual-review",
        },
    ]


def _wrap_envelope(citations_list, *, citation_complete=False):
    """Wrap a citations list in the production envelope format."""
    return {
        "_meta": {
            "citation_complete": citation_complete,
            "description": "Test citation seed (proof-of-concept, not production-complete).",
        },
        "citations": citations_list,
    }


def _base_seed_files(tmp_path, *, include_citations=False, citations=None,
                     raw_citations_payload=None):
    """Write the four mandatory seed files plus, optionally, citations.

    Parameters
    ----------
    include_citations : bool
        Write a citations file.
    citations : list or None
        A bare citations list (will be wrapped in envelope format automatically).
    raw_citations_payload : any
        Write this value directly to disk without envelope-wrapping.
        Use for testing bare-array or malformed-envelope scenarios.
    """
    chapters = [{
        "code": "IPC",
        "title": "Infection Prevention and Control",
        "description": "Standards for infection control.",
        "display_order": 1,
        "official_standards_count": 1,
        "official_measurable_elements_count": 2,
        "is_fully_seeded": True,
    }]
    requirements = [{
        "chapter_code": "IPC",
        "edition_version": "6.0",
        "standards": [{
            "code": "IPC-1",
            "title": "Infection Control Program",
            "description": "Infection Control Program.",
            "display_order": 1,
            "objective_elements": [{
                "code": "IPC-1.a",
                "description": "Manual is updated.",
                "severity": "major",
                "display_order": 1,
                "measurable_elements": [
                    {
                        "code": "IPC-1.a.1",
                        "description": "Triage checks.",
                        "applicability_default": "applicable",
                        "scoring_weight": 1.0,
                        "risk_weight": 1.0,
                        "default_owner_role": "officer",
                        "display_order": 1,
                    },
                    {
                        "code": "IPC-1.a.2",
                        "description": "Annual manual review.",
                        "applicability_default": "applicable",
                        "scoring_weight": 1.0,
                        "risk_weight": 1.0,
                        "default_owner_role": "infection_control_officer",
                        "display_order": 2,
                    },
                ],
            }],
        }],
    }]

    evidence = [
        {
            "measurable_element_code": "IPC-1.a.1",
            "edition_version": "6.0",
            "evidence_code": "IPC-1.a.1-EV-SOP-01",
            "evidence_type": "sop",
            "description": "Standard Operating Procedure for Triage",
            "is_mandatory": True,
            "evidence_frequency": "yearly",
            "minimum_lookback_days": 180,
            "default_owner_role": "officer"
        },
        {
            "measurable_element_code": "IPC-1.a.2",
            "edition_version": "6.0",
            "evidence_code": "IPC-1.a.2-EV-SOP-01",
            "evidence_type": "sop",
            "description": "Annual manual review checklist",
            "is_mandatory": True,
            "evidence_frequency": "yearly",
            "minimum_lookback_days": 180,
            "default_owner_role": "infection_control_officer"
        }
    ]

    for name, data in [
        ("nabh_6th_chapters.json", chapters),
        ("nabh_6th_requirements.json", requirements),
        ("nabh_6th_evidence_requirements.json", evidence),
        ("nabh_6th_applicability_rules.json", []),
    ]:
        with open(os.path.join(str(tmp_path), name), "w", encoding="utf-8") as f:
            json.dump(data, f)

    if raw_citations_payload is not None:
        # Write raw (for testing malformed/bare-array scenarios)
        with open(os.path.join(str(tmp_path), "nabh_6th_citations.json"), "w", encoding="utf-8") as f:
            json.dump(raw_citations_payload, f)
    elif include_citations:
        # Always write in envelope format so tests match production expectations
        cit_list = citations if citations is not None else _good_citations()
        payload = _wrap_envelope(cit_list)
        with open(os.path.join(str(tmp_path), "nabh_6th_citations.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f)


def _clear_ontology_tables(db_session):
    """Delete all versioned ontology rows to give each test a clean slate."""
    for tbl in [
        "nabh_requirement_citations",
        "nabh_source_documents",
        "nabh_applicability_rules",
        "nabh_evidence_requirements",
        "nabh_measurable_elements",
        "nabh_objective_elements",
        "nabh_standards",
        "nabh_chapters",
        "nabh_editions",
    ]:
        db_session.execute(text(f"DELETE FROM {tbl}"))
    db_session.commit()


# ---------------------------------------------------------------------------
# Validator — missing citations file
# ---------------------------------------------------------------------------

class TestValidatorCitationsFilePresence:
    def test_missing_citations_file_raises_by_default(self, tmp_path):
        """nabh_6th_citations.json is required when allow_missing_citations=False (default)."""
        _base_seed_files(tmp_path)
        with pytest.raises(ValidationError, match="nabh_6th_citations.json"):
            validate_ontology_seeds(str(tmp_path))

    def test_missing_citations_file_allowed_with_flag(self, tmp_path):
        """allow_missing_citations=True lets validation pass even without the file."""
        _base_seed_files(tmp_path)
        result = validate_ontology_seeds(str(tmp_path), allow_missing_citations=True)
        assert result["citations"] == []

    def test_present_citations_file_parsed_normally(self, tmp_path):
        """When the file exists and is valid it is returned in the loaded data."""
        _base_seed_files(tmp_path, include_citations=True)
        result = validate_ontology_seeds(str(tmp_path))
        assert len(result["citations"]) == 2


# ---------------------------------------------------------------------------
# Validator — envelope format enforcement
# ---------------------------------------------------------------------------

class TestValidatorEnvelopeFormat:
    def test_bare_array_raises_by_default(self, tmp_path):
        """A bare JSON array without envelope raises by default (production guard)."""
        _base_seed_files(tmp_path, raw_citations_payload=_good_citations())
        with pytest.raises(ValidationError, match="envelope format"):
            validate_ontology_seeds(str(tmp_path))

    def test_bare_array_allowed_with_flag(self, tmp_path):
        """A bare array is accepted when allow_bare_citation_array=True (test/draft mode)."""
        _base_seed_files(tmp_path, raw_citations_payload=_good_citations())
        result = validate_ontology_seeds(str(tmp_path), allow_bare_citation_array=True)
        assert len(result["citations"]) == 2

    def test_envelope_with_citation_complete_false_passes(self, tmp_path):
        """Envelope with citation_complete=false is valid."""
        _base_seed_files(tmp_path, include_citations=True)  # default wraps with False
        result = validate_ontology_seeds(str(tmp_path))
        assert len(result["citations"]) == 2
        assert result["citation_meta"]["citation_complete"] is False

    def test_envelope_with_citation_complete_true_passes(self, tmp_path):
        """Envelope with citation_complete=true is valid."""
        payload = _wrap_envelope(_good_citations(), citation_complete=True)
        _base_seed_files(tmp_path, raw_citations_payload=payload)
        result = validate_ontology_seeds(str(tmp_path))
        assert result["citation_meta"]["citation_complete"] is True

    def test_meta_citation_complete_string_raises(self, tmp_path):
        """_meta.citation_complete must be a boolean, not a string."""
        bad_payload = {
            "_meta": {"citation_complete": "false"},  # string, not bool
            "citations": _good_citations(),
        }
        _base_seed_files(tmp_path, raw_citations_payload=bad_payload)
        with pytest.raises(ValidationError, match="must be a JSON boolean"):
            validate_ontology_seeds(str(tmp_path))

    def test_meta_citation_complete_null_raises(self, tmp_path):
        """_meta.citation_complete=null (None) is not a valid boolean."""
        bad_payload = {
            "_meta": {"citation_complete": None},
            "citations": _good_citations(),
        }
        _base_seed_files(tmp_path, raw_citations_payload=bad_payload)
        with pytest.raises(ValidationError, match="must be a JSON boolean"):
            validate_ontology_seeds(str(tmp_path))

    def test_meta_citation_complete_integer_raises(self, tmp_path):
        """_meta.citation_complete=0 (integer) is not a valid boolean."""
        bad_payload = {
            "_meta": {"citation_complete": 0},
            "citations": _good_citations(),
        }
        _base_seed_files(tmp_path, raw_citations_payload=bad_payload)
        with pytest.raises(ValidationError, match="must be a JSON boolean"):
            validate_ontology_seeds(str(tmp_path))

    def test_meta_missing_citation_complete_key_raises(self, tmp_path):
        """_meta block without citation_complete key is malformed and must raise."""
        bad_payload = {
            "_meta": {"description": "Missing the required key"},
            "citations": _good_citations(),
        }
        _base_seed_files(tmp_path, raw_citations_payload=bad_payload)
        with pytest.raises(ValidationError, match="missing the required 'citation_complete' key"):
            validate_ontology_seeds(str(tmp_path))

    def test_empty_meta_block_is_treated_as_absent(self, tmp_path):
        """An empty _meta dict ({}) is treated as no _meta; no validation applied to it."""
        payload = {"_meta": {}, "citations": _good_citations()}
        _base_seed_files(tmp_path, raw_citations_payload=payload)
        # Empty dict is falsy → skips _meta validation, bare citations still validated
        result = validate_ontology_seeds(str(tmp_path))
        assert len(result["citations"]) == 2


# ---------------------------------------------------------------------------
# Validator — date format
# ---------------------------------------------------------------------------

class TestValidatorDateFormat:
    def test_bad_date_format_raises(self, tmp_path):
        bad = _good_citations()
        bad[0]["effective_date"] = "01-01-2026"  # wrong format
        _base_seed_files(tmp_path, include_citations=True, citations=bad)
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_ontology_seeds(str(tmp_path))

    def test_non_date_string_raises(self, tmp_path):
        bad = _good_citations()
        bad[0]["effective_date"] = "not-a-date"
        _base_seed_files(tmp_path, include_citations=True, citations=bad)
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_ontology_seeds(str(tmp_path))

    def test_valid_iso_date_passes(self, tmp_path):
        _base_seed_files(tmp_path, include_citations=True)
        result = validate_ontology_seeds(str(tmp_path))
        assert result["citations"][0]["effective_date"] == "2026-01-01"


# ---------------------------------------------------------------------------
# Validator — file_path / url presence
# ---------------------------------------------------------------------------

class TestValidatorExcerptPresence:
    def test_both_null_raises(self, tmp_path):
        bad = _good_citations()
        bad[0]["file_path"] = None
        bad[0]["url"] = None
        _base_seed_files(tmp_path, include_citations=True, citations=bad)
        with pytest.raises(ValidationError, match="must have at least one non-empty string file_path or url"):
            validate_ontology_seeds(str(tmp_path))

    def test_both_empty_string_raises(self, tmp_path):
        bad = _good_citations()
        bad[0]["file_path"] = ""
        bad[0]["url"] = "   "
        _base_seed_files(tmp_path, include_citations=True, citations=bad)
        with pytest.raises(ValidationError, match="must have at least one non-empty string file_path or url"):
            validate_ontology_seeds(str(tmp_path))

    def test_file_path_only_passes(self, tmp_path):
        """file_path alone (no url) is sufficient."""
        good = _good_citations()
        good[0]["url"] = None
        _base_seed_files(tmp_path, include_citations=True, citations=good)
        result = validate_ontology_seeds(str(tmp_path))
        assert len(result["citations"]) == 2

    def test_url_only_passes(self, tmp_path):
        """url alone (no file_path) is sufficient."""
        good = _good_citations()
        good[1]["file_path"] = None
        _base_seed_files(tmp_path, include_citations=True, citations=good)
        result = validate_ontology_seeds(str(tmp_path))
        assert len(result["citations"]) == 2


# ---------------------------------------------------------------------------
# Validator — cross-references
# ---------------------------------------------------------------------------

class TestValidatorCrossReferences:
    def test_unknown_measurable_element_raises(self, tmp_path):
        bad = _good_citations()
        bad[0]["measurable_element_code"] = "IPC-99.z.999"
        _base_seed_files(tmp_path, include_citations=True, citations=bad)
        with pytest.raises(ValidationError, match="unknown measurable element code"):
            validate_ontology_seeds(str(tmp_path))

    def test_edition_version_mismatch_raises(self, tmp_path):
        bad = _good_citations()
        bad[0]["edition_version"] = "5.0"
        _base_seed_files(tmp_path, include_citations=True, citations=bad)
        with pytest.raises(ValidationError, match="Edition version mismatch"):
            validate_ontology_seeds(str(tmp_path))


# ---------------------------------------------------------------------------
# Seeder — citation seeding happy path
# ---------------------------------------------------------------------------

class TestSeederCitationsHappyPath:
    def test_source_document_created_with_correct_metadata(self, db_session, tmp_path):
        _clear_ontology_tables(db_session)
        _base_seed_files(tmp_path, include_citations=True)
        seed_versioned_ontology(db_session, str(tmp_path), "6.0")

        edition = db_session.query(NABHEdition).filter(NABHEdition.version == "6.0").first()
        assert edition is not None

        doc = db_session.query(NABHSourceDocument).filter(
            NABHSourceDocument.edition_id == edition.id
        ).first()
        assert doc is not None
        assert doc.title == "NABH 6th Edition Reference Guide"
        assert doc.publisher == "National Accreditation Board for Hospitals & Healthcare Providers"
        assert doc.edition_version == "6.0"

    def test_citations_created_and_linked(self, db_session, tmp_path):
        _clear_ontology_tables(db_session)
        _base_seed_files(tmp_path, include_citations=True)
        seed_versioned_ontology(db_session, str(tmp_path), "6.0")

        citations = db_session.query(NABHRequirementCitation).all()
        assert len(citations) == 2

        # Verify both measurable elements received citations
        meas_ids = {c.measurable_element_id for c in citations}
        assert len(meas_ids) == 2

        # Verify the file_path-only citation
        cit_142 = next(c for c in citations if c.page_number == "142")
        assert cit_142.file_path is not None
        assert cit_142.url is None

        # Verify the url-only citation
        cit_143 = next(c for c in citations if c.page_number == "143")
        assert cit_143.url is not None
        assert cit_143.file_path is None

    def test_single_source_document_for_same_title(self, db_session, tmp_path):
        """Both citations share the same document_title → only 1 NABHSourceDocument."""
        _clear_ontology_tables(db_session)
        _base_seed_files(tmp_path, include_citations=True)
        seed_versioned_ontology(db_session, str(tmp_path), "6.0")

        edition = db_session.query(NABHEdition).filter(NABHEdition.version == "6.0").first()
        doc_count = db_session.query(NABHSourceDocument).filter(
            NABHSourceDocument.edition_id == edition.id
        ).count()
        assert doc_count == 1


# ---------------------------------------------------------------------------
# Seeder — idempotency
# ---------------------------------------------------------------------------

class TestSeederCitationsIdempotency:
    def test_re_run_does_not_duplicate(self, db_session, tmp_path):
        _clear_ontology_tables(db_session)
        _base_seed_files(tmp_path, include_citations=True)

        seed_versioned_ontology(db_session, str(tmp_path), "6.0")
        seed_versioned_ontology(db_session, str(tmp_path), "6.0")

        assert db_session.query(NABHSourceDocument).count() == 1
        assert db_session.query(NABHRequirementCitation).count() == 2

    def test_in_place_update_of_clause_and_url(self, db_session, tmp_path):
        _clear_ontology_tables(db_session)
        _base_seed_files(tmp_path, include_citations=True)
        seed_versioned_ontology(db_session, str(tmp_path), "6.0")

        # Mutate the citation data
        updated = _good_citations()
        updated[0]["clause_text_summary"] = "UPDATED: Enhanced triage protocols."
        updated[0]["file_path"] = "/excerpts/IPC_1a1_triage_v2.png"

        _base_seed_files(tmp_path, include_citations=True, citations=updated)
        seed_versioned_ontology(db_session, str(tmp_path), "6.0")

        citations = db_session.query(NABHRequirementCitation).all()
        # Still only 2 records
        assert len(citations) == 2

        updated_cit = next(c for c in citations if c.page_number == "142")
        assert updated_cit.clause_text_summary == "UPDATED: Enhanced triage protocols."
        assert updated_cit.file_path == "/excerpts/IPC_1a1_triage_v2.png"


# ---------------------------------------------------------------------------
# Seeder — no citations file (allow_missing_citations)
# ---------------------------------------------------------------------------

class TestSeederWithoutCitationsFile:
    def test_seeder_without_citations_fails_quality_gate(self, db_session, tmp_path):
        """Seeder should fail quality validation if citations are missing, even if validation flag is patched."""
        _clear_ontology_tables(db_session)
        _base_seed_files(tmp_path)  # no citations file

        # Patch validate to allow missing citations so seeder itself can pass validation
        from unittest.mock import patch
        from app.nabh import validator as val_mod
        from app.nabh.quality import NABHQualityError

        original_validate = val_mod.validate_ontology_seeds

        def patched_validate(data_dir, target_version="6.0", allow_missing_citations=False,
                             allow_bare_citation_array=False):
            return original_validate(data_dir, target_version, allow_missing_citations=True)

        with patch("app.nabh.seeder.validate_ontology_seeds", side_effect=patched_validate):
            with pytest.raises(NABHQualityError, match="missing active citation"):
                seed_versioned_ontology(db_session, str(tmp_path), "6.0")

        # Transaction was rolled back: nothing should be present
        assert db_session.query(NABHSourceDocument).count() == 0
        assert db_session.query(NABHRequirementCitation).count() == 0
        assert db_session.query(NABHEdition).count() == 0
