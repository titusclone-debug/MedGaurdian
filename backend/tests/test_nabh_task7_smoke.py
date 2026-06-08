import os
import json
import pytest
from sqlalchemy import text
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard, 
    NABHObjectiveElement, NABHMeasurableElement, 
    NABHEvidenceRequirement, NABHApplicabilityRule,
    SeverityLevel, ApplicabilityDefault, EvidenceType
)
from app.nabh.validator import validate_ontology_seeds, ValidationError
from app.nabh.seeder import seed_versioned_ontology

def test_validation_errors(tmp_path):
    data_dir = str(tmp_path)
    
    # 1. Test missing files (chapters is still the first required file check)
    with pytest.raises(ValidationError, match="Missing required seed file"):
        validate_ontology_seeds(data_dir, allow_missing_citations=True)
        
    # Write a base set of files but with missing keys
    chapters = [{"code": "HIC", "title": "Infection Control"}] # missing other keys
    with open(os.path.join(data_dir, "nabh_6th_chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters, f)
    with open(os.path.join(data_dir, "nabh_6th_requirements.json"), "w", encoding="utf-8") as f:
        json.dump([], f)
    with open(os.path.join(data_dir, "nabh_6th_evidence_requirements.json"), "w", encoding="utf-8") as f:
        json.dump([], f)
    with open(os.path.join(data_dir, "nabh_6th_applicability_rules.json"), "w", encoding="utf-8") as f:
        json.dump([], f)
        
    with pytest.raises(ValidationError, match="missing keys"):
        validate_ontology_seeds(data_dir, allow_missing_citations=True)


def test_validation_coverage_mismatch(tmp_path):
    data_dir = str(tmp_path)
    
    chapters = [{
        "code": "HIC",
        "title": "Hospital Infection Control",
        "description": "Standards",
        "display_order": 1,
        "official_standards_count": 2,
        "official_measurable_elements_count": 5,
        "is_fully_seeded": True
    }]
    requirements = [{
        "chapter_code": "HIC",
        "edition_version": "6.0",
        "standards": [
            {
                "code": "HIC-1",
                "title": "Standard 1",
                "description": "Desc",
                "display_order": 1,
                "objective_elements": []
            }
        ]
    }]
    
    with open(os.path.join(data_dir, "nabh_6th_chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters, f)
    with open(os.path.join(data_dir, "nabh_6th_requirements.json"), "w", encoding="utf-8") as f:
        json.dump(requirements, f)
    with open(os.path.join(data_dir, "nabh_6th_evidence_requirements.json"), "w", encoding="utf-8") as f:
        json.dump([], f)
    with open(os.path.join(data_dir, "nabh_6th_applicability_rules.json"), "w", encoding="utf-8") as f:
        json.dump([], f)
        
    # Should raise error because is_fully_seeded is True but standard counts mismatch (seeded 1, official 2)
    with pytest.raises(ValidationError, match="marked as fully seeded, but seeded standard count"):
        validate_ontology_seeds(data_dir, allow_missing_citations=True)


def test_validation_mixed_versions(tmp_path):
    data_dir = str(tmp_path)
    chapters = [{
        "code": "HIC",
        "title": "Hospital Infection Control",
        "description": "Desc",
        "display_order": 1,
        "official_standards_count": 1,
        "official_measurable_elements_count": 1,
        "is_fully_seeded": False
    }]
    requirements = [{
        "chapter_code": "HIC",
        "edition_version": "7.0", # mismatch version
        "standards": []
    }]
    
    with open(os.path.join(data_dir, "nabh_6th_chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters, f)
    with open(os.path.join(data_dir, "nabh_6th_requirements.json"), "w", encoding="utf-8") as f:
        json.dump(requirements, f)
    with open(os.path.join(data_dir, "nabh_6th_evidence_requirements.json"), "w", encoding="utf-8") as f:
        json.dump([], f)
    with open(os.path.join(data_dir, "nabh_6th_applicability_rules.json"), "w", encoding="utf-8") as f:
        json.dump([], f)

    with pytest.raises(ValidationError, match="Edition version mismatch"):
        validate_ontology_seeds(data_dir, target_version="6.0", allow_missing_citations=True)


def test_validation_dsl_contract(tmp_path):
    data_dir = str(tmp_path)
    chapters = [{
        "code": "HIC",
        "title": "Hospital Infection Control",
        "description": "Desc",
        "display_order": 1,
        "official_standards_count": 1,
        "official_measurable_elements_count": 1,
        "is_fully_seeded": False
    }]
    requirements = [{
        "chapter_code": "HIC",
        "edition_version": "6.0",
        "standards": [
            {
                "code": "HIC-1",
                "title": "Std 1",
                "description": "Desc",
                "display_order": 1,
                "objective_elements": [
                    {
                        "code": "HIC-1.a",
                        "description": "Obj a",
                        "severity": "major",
                        "display_order": 1,
                        "measurable_elements": [
                            {
                                "code": "HIC-1.a.1",
                                "description": "Meas 1",
                                "applicability_default": "applicable",
                                "scoring_weight": 1.0,
                                "risk_weight": 1.0,
                                "default_owner_role": "owner",
                                "display_order": 1
                            }
                        ]
                    }
                ]
            }
        ]
    }]
    
    # Bad rule operator
    rules = [{
        "measurable_element_code": "HIC-1.a.1",
        "edition_version": "6.0",
        "rule_code": "rule_triage",
        "rule_json": {
            "field": "has_emergency",
            "operator": "bad_op", # invalid operator
            "value": True
        },
        "description": "Desc",
        "action_if_true": "applicable",
        "action_if_false": "not_applicable"
    }]

    with open(os.path.join(data_dir, "nabh_6th_chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters, f)
    with open(os.path.join(data_dir, "nabh_6th_requirements.json"), "w", encoding="utf-8") as f:
        json.dump(requirements, f)
    with open(os.path.join(data_dir, "nabh_6th_evidence_requirements.json"), "w", encoding="utf-8") as f:
        json.dump([], f)
    with open(os.path.join(data_dir, "nabh_6th_applicability_rules.json"), "w", encoding="utf-8") as f:
        json.dump(rules, f)

    with pytest.raises(ValidationError, match="Unsupported rule operator"):
        validate_ontology_seeds(data_dir, allow_missing_citations=True)


def test_seeding_happy_path_and_idempotency(db_session, tmp_path):
    data_dir = str(tmp_path)
    
    chapters = [{
        "code": "HIC",
        "title": "Hospital Infection Control",
        "description": "Standards for infection control.",
        "display_order": 1,
        "official_standards_count": 1,
        "official_measurable_elements_count": 1,
        "is_fully_seeded": True
    }]
    requirements = [{
        "chapter_code": "HIC",
        "edition_version": "6.0",
        "standards": [
            {
                "code": "HIC-1",
                "title": "Std 1",
                "description": "Infection Control Program",
                "display_order": 1,
                "objective_elements": [
                    {
                        "code": "HIC-1.a",
                        "description": "Manual is updated.",
                        "severity": "major",
                        "display_order": 1,
                        "measurable_elements": [
                            {
                                "code": "HIC-1.a.1",
                                "description": "Triage checks exist.",
                                "applicability_default": "applicable",
                                "scoring_weight": 1.0,
                                "risk_weight": 1.0,
                                "default_owner_role": "officer",
                                "display_order": 1
                            }
                        ]
                    }
                ]
            }
        ]
    }]
    evidence = [{
        "measurable_element_code": "HIC-1.a.1",
        "edition_version": "6.0",
        "evidence_code": "HIC-1.a.1-EV-SOP-01",
        "evidence_type": "sop",
        "description": "Standard Operating Procedure for Triage",
        "is_mandatory": True,
        "evidence_frequency": "yearly",
        "minimum_lookback_days": 180,
        "default_owner_role": "officer"
    }]
    rules = [{
        "measurable_element_code": "HIC-1.a.1",
        "edition_version": "6.0",
        "rule_code": "rule_triage",
        "rule_json": {
            "field": "has_emergency",
            "operator": "eq",
            "value": True
        },
        "description": "Applies if active emergency",
        "action_if_true": "applicable",
        "action_if_false": "not_applicable"
    }]

    with open(os.path.join(data_dir, "nabh_6th_chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters, f)
    with open(os.path.join(data_dir, "nabh_6th_requirements.json"), "w", encoding="utf-8") as f:
        json.dump(requirements, f)
    with open(os.path.join(data_dir, "nabh_6th_evidence_requirements.json"), "w", encoding="utf-8") as f:
        json.dump(evidence, f)
    with open(os.path.join(data_dir, "nabh_6th_applicability_rules.json"), "w", encoding="utf-8") as f:
        json.dump(rules, f)

    # Clean existing data to ensure independent smoke test
    db_session.execute(text("DELETE FROM nabh_applicability_rules"))
    db_session.execute(text("DELETE FROM nabh_evidence_requirements"))
    db_session.execute(text("DELETE FROM nabh_measurable_elements"))
    db_session.execute(text("DELETE FROM nabh_objective_elements"))
    db_session.execute(text("DELETE FROM nabh_standards"))
    db_session.execute(text("DELETE FROM nabh_chapters"))
    db_session.execute(text("DELETE FROM nabh_editions"))
    db_session.commit()

    # 1. Run seeder (citations file not provided; test validates non-citation seeding)
    from unittest.mock import patch as _patch
    from app.nabh import validator as _val_mod
    _orig_validate = _val_mod.validate_ontology_seeds
    def _validate_no_cit(data_dir, target_version="6.0", allow_missing_citations=False):
        return _orig_validate(data_dir, target_version, allow_missing_citations=True)
    with _patch("app.nabh.seeder.validate_ontology_seeds", side_effect=_validate_no_cit):
        seed_versioned_ontology(db_session, data_dir, "6.0")

    # Assert entities exist
    edition = db_session.query(NABHEdition).filter(NABHEdition.version == "6.0").first()
    assert edition is not None
    
    chapter = db_session.query(NABHChapter).filter(NABHChapter.edition_id == edition.id).first()
    assert chapter is not None
    assert chapter.code == "HIC"
    assert chapter.is_fully_seeded is True
    
    std = db_session.query(NABHStandard).filter(NABHStandard.edition_id == edition.id).first()
    assert std is not None
    assert std.canonical_code == "HIC-1"
    assert std.code == "1"

    obj = db_session.query(NABHObjectiveElement).filter(NABHObjectiveElement.edition_id == edition.id).first()
    assert obj is not None
    assert obj.canonical_code == "HIC-1.a"

    meas = db_session.query(NABHMeasurableElement).filter(NABHMeasurableElement.edition_id == edition.id).first()
    assert meas is not None
    assert meas.canonical_code == "HIC-1.a.1"

    ev = db_session.query(NABHEvidenceRequirement).filter(NABHEvidenceRequirement.measurable_element_id == meas.id).first()
    assert ev is not None
    assert ev.evidence_code == "HIC-1.a.1-EV-SOP-01"

    rule = db_session.query(NABHApplicabilityRule).filter(NABHApplicabilityRule.measurable_element_id == meas.id).first()
    assert rule is not None
    assert rule.rule_code == "rule_triage"
    assert rule.rule_json["operator"] == "eq"

    # 2. Idempotency test (re-run seeder, counts must not change)
    with _patch("app.nabh.seeder.validate_ontology_seeds", side_effect=_validate_no_cit):
        seed_versioned_ontology(db_session, data_dir, "6.0")
    
    assert db_session.query(NABHChapter).count() == 1
    assert db_session.query(NABHStandard).count() == 1
    assert db_session.query(NABHObjectiveElement).count() == 1
    assert db_session.query(NABHMeasurableElement).count() == 1
    assert db_session.query(NABHEvidenceRequirement).count() == 1
    assert db_session.query(NABHApplicabilityRule).count() == 1

    # 3. In-place Update test
    chapters[0]["title"] = "Hospital Infection Control UPDATED"
    evidence[0]["minimum_lookback_days"] = 999
    
    with open(os.path.join(data_dir, "nabh_6th_chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters, f)
    with open(os.path.join(data_dir, "nabh_6th_evidence_requirements.json"), "w", encoding="utf-8") as f:
        json.dump(evidence, f)

    with _patch("app.nabh.seeder.validate_ontology_seeds", side_effect=_validate_no_cit):
        seed_versioned_ontology(db_session, data_dir, "6.0")
    
    db_session.refresh(chapter)
    db_session.refresh(ev)
    
    assert chapter.title == "Hospital Infection Control UPDATED"
    assert ev.minimum_lookback_days == 999


def test_seeding_transaction_safety(db_session, tmp_path, monkeypatch):
    data_dir = str(tmp_path)
    
    chapters = [{
        "code": "HIC",
        "title": "Hospital Infection Control",
        "description": "Standards for infection control.",
        "display_order": 1,
        "official_standards_count": 1,
        "official_measurable_elements_count": 1,
        "is_fully_seeded": False
    }]
    requirements = [{
        "chapter_code": "HIC",
        "edition_version": "6.0",
        "standards": [
            {
                "code": "HIC-1",
                "title": "Std 1",
                "description": "Infection Control Program",
                "display_order": 1,
                "objective_elements": [
                    {
                        "code": "HIC-1.a",
                        "description": "Manual is updated.",
                        "severity": "major",
                        "display_order": 1,
                        "measurable_elements": [
                            {
                                "code": "HIC-1.a.1",
                                "description": "Triage checks exist.",
                                "applicability_default": "applicable",
                                "scoring_weight": 1.0,
                                "risk_weight": 1.0,
                                "default_owner_role": "officer",
                                "display_order": 1
                            }
                        ]
                    }
                ]
            }
        ]
    }]

    with open(os.path.join(data_dir, "nabh_6th_chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters, f)
    with open(os.path.join(data_dir, "nabh_6th_requirements.json"), "w", encoding="utf-8") as f:
        json.dump(requirements, f)
    with open(os.path.join(data_dir, "nabh_6th_evidence_requirements.json"), "w", encoding="utf-8") as f:
        json.dump([], f)
    with open(os.path.join(data_dir, "nabh_6th_applicability_rules.json"), "w", encoding="utf-8") as f:
        json.dump([], f)

    # Clean existing data
    db_session.execute(text("DELETE FROM nabh_applicability_rules"))
    db_session.execute(text("DELETE FROM nabh_evidence_requirements"))
    db_session.execute(text("DELETE FROM nabh_measurable_elements"))
    db_session.execute(text("DELETE FROM nabh_objective_elements"))
    db_session.execute(text("DELETE FROM nabh_standards"))
    db_session.execute(text("DELETE FROM nabh_chapters"))
    db_session.execute(text("DELETE FROM nabh_editions"))
    db_session.commit()

    # Monkeypatch the db_session.flush to simulate a failure midway through seeding
    # (specifically after the edition and chapter are flushed, but before standards are completed)
    original_flush = db_session.flush
    flush_count = 0
    
    def mock_flush(*args, **kwargs):
        nonlocal flush_count
        flush_count += 1
        if flush_count > 2:
            raise ValueError("Simulated Seeding Failure Midway")
        return original_flush(*args, **kwargs)
    
    monkeypatch.setattr(db_session, "flush", mock_flush)

    # Executing the seeder should raise the ValueError and rollback everything.
    from unittest.mock import patch as _patch
    from app.nabh import validator as _val_mod
    _orig_validate = _val_mod.validate_ontology_seeds
    def _validate_no_cit(data_dir, target_version="6.0", allow_missing_citations=False):
        return _orig_validate(data_dir, target_version, allow_missing_citations=True)
    with pytest.raises(ValueError, match="Simulated Seeding Failure Midway"):
        with _patch("app.nabh.seeder.validate_ontology_seeds", side_effect=_validate_no_cit):
            seed_versioned_ontology(db_session, data_dir, "6.0")

    # Assert that NOTHING was committed (the database remains completely empty)
    assert db_session.query(NABHEdition).count() == 0
    assert db_session.query(NABHChapter).count() == 0
    assert db_session.query(NABHStandard).count() == 0
