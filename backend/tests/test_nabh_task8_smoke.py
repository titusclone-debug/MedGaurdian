"""
Smoke Tests: Task 8 — Populate Minimum Viable Official Ontology & Coverage API

Covers:
  - Seeding the 10 official 6th Edition chapters with exact counts.
  - Seeding the minimal, source-backed requirements for IPC, MOM, FMS.
  - Ensuring every seeded element has at least one citation and one evidence requirement.
  - Verifying the GET /api/nabh/ontology/coverage endpoint returns correct counts and partial status.
"""

import os
import pytest
from sqlalchemy import text

from app.api.auth import get_current_user
from app.models.database import (
    NABHEdition, NABHChapter, NABHStandard,
    NABHObjectiveElement, NABHMeasurableElement, NABHRequirement,
    NABHSourceDocument, NABHRequirementCitation,
    NABHEvidenceRequirement, NABHSourceAnomaly, Staff, UserRole
)
from app.main import app
from app.nabh.seeder import seed_versioned_ontology


def test_ontology_seeding_and_coverage_api_smoke(db_session, client):
    # Enable foreign keys for SQLite in-memory DB connection
    db_session.execute(text("PRAGMA foreign_keys=ON"))

    # Override auth dependency to allow route access
    def mock_user():
        return Staff(
            id="mock-staff",
            hospital_id="mock-hosp",
            role=UserRole.SUPER_ADMIN,
            name="Mock Admin",
            is_active=True
        )
    app.dependency_overrides[get_current_user] = mock_user

    # Clean any existing data to guarantee a fresh run
    db_session.execute(text("DELETE FROM nabh_requirement_citations"))
    db_session.execute(text("DELETE FROM nabh_applicability_rules"))
    db_session.execute(text("DELETE FROM nabh_evidence_requirements"))
    db_session.execute(text("DELETE FROM nabh_source_anomalies"))
    db_session.execute(text("DELETE FROM nabh_requirements"))
    db_session.execute(text("DELETE FROM nabh_measurable_elements"))
    db_session.execute(text("DELETE FROM nabh_objective_elements"))
    db_session.execute(text("DELETE FROM nabh_standards"))
    db_session.execute(text("DELETE FROM nabh_chapters"))
    db_session.execute(text("DELETE FROM nabh_source_documents"))
    db_session.execute(text("DELETE FROM nabh_editions"))
    db_session.commit()

    # Find the real seed data directory relative to this file
    test_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(os.path.join(test_dir, "..", "app", "nabh", "data"))

    # 1. Run the versioned ontology seeder
    seed_versioned_ontology(db_session, data_dir, "6.0")

    # 2. Assert seeder populated database models cleanly
    edition = db_session.query(NABHEdition).filter(NABHEdition.version == "6.0").first()
    assert edition is not None
    assert edition.name == "NABH 6.0 Edition"

    # All 10 official chapters must be in the DB
    official_chapter_codes = ["AAC", "COP", "MOM", "PRE", "IPC", "PSQ", "ROM", "FMS", "HRM", "IMS"]
    db_chapters = db_session.query(NABHChapter).filter(NABHChapter.edition_id == edition.id).all()
    assert len(db_chapters) == 10
    for chap in db_chapters:
        assert chap.canonical_code in official_chapter_codes
        assert chap.is_fully_seeded is False
        assert chap.official_standards_count is not None
        assert chap.official_requirements_count is not None
        assert chap.official_measurable_elements_count is not None

    # Total official chapter counts check
    official_standards_total = sum(c.official_standards_count for c in db_chapters)
    official_elements_total = sum(c.official_requirements_count for c in db_chapters)
    assert official_standards_total == 100
    assert official_elements_total == 639

    # Assert seeded requirement entities exist and match IPC, MOM, FMS
    seeded_elements = db_session.query(NABHMeasurableElement).all()
    assert len(seeded_elements) == 3
    element_codes = {el.canonical_code for el in seeded_elements}
    assert element_codes == {"IPC-1.a.1", "MOM-1.a.1", "FMS.1.a.1"}
    canonical_requirements = db_session.query(NABHRequirement).all()
    assert {item.id for item in canonical_requirements} == {
        item.id for item in seeded_elements
    }

    # Assert every seeded element has at least one citation and one evidence requirement
    for el in seeded_elements:
        ev_reqs = db_session.query(NABHEvidenceRequirement).filter(
            NABHEvidenceRequirement.measurable_element_id == el.id
        ).all()
        assert len(ev_reqs) >= 1

        citations = db_session.query(NABHRequirementCitation).filter(
            NABHRequirementCitation.measurable_element_id == el.id
        ).all()
        assert len(citations) >= 1

    # 3. Call the coverage API endpoint
    response = client.get("/api/nabh/ontology/coverage")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ontology_status"] == "partial_seed"
    assert data["official_declared_total_standards"] == 100
    assert data["official_declared_total_elements"] == 639
    assert data["official_chapter_sum_standards"] == 100
    assert data["official_chapter_sum_elements"] == 639
    assert data["official_chapter_objective_elements_sum"] == 639
    assert data["official_category_breakdown_sum"] == 639
    assert data["official_standards_discrepancy"] == 0
    assert data["official_elements_discrepancy"] == 0
    assert data["has_source_inconsistency"] is False
    assert data["inconsistencies"] == []
    assert len(data["source_anomalies"]) == 3
    assert all(
        anomaly["status"] == "reconciled"
        for anomaly in data["source_anomalies"]
    )
    
    assert data["seeded_total_standards"] == 3
    assert data["seeded_total_elements"] == 3
    assert data["global_standards_coverage_percent"] == 3.0
    assert data["global_elements_coverage_percent"] == 0.5
    assert data["citation_complete"] is False

    source_response = client.get("/api/nabh/ontology/sources")
    assert source_response.status_code == 200
    official_sources = [
        source for source in source_response.json()
        if source["checksum"]
        == "0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A"
    ]
    assert len(official_sources) == 1
    assert official_sources[0]["rights_status"] == "permission_required"
    assert official_sources[0]["may_store_full_text"] is False
    assert len(official_sources[0]["anomalies"]) == 3

    # Assert ordering of chapters matches display_order
    chapters_resp = data["chapters"]
    display_orders = [c.canonical_code for c in sorted(db_chapters, key=lambda x: x.display_order)]
    resp_codes = [c["chapter_code"] for c in chapters_resp]
    assert resp_codes == display_orders

    official_category_counts = {
        "AAC": {"core": 6, "commitment": 68, "achievement": 9, "excellence": 4},
        "COP": {"core": 13, "commitment": 107, "achievement": 12, "excellence": 4},
        "MOM": {"core": 13, "commitment": 48, "achievement": 6, "excellence": 1},
        "PRE": {"core": 12, "commitment": 32, "achievement": 7, "excellence": 1},
        "IPC": {"core": 13, "commitment": 33, "achievement": 3, "excellence": 0},
        "PSQ": {"core": 8, "commitment": 28, "achievement": 7, "excellence": 3},
        "ROM": {"core": 4, "commitment": 23, "achievement": 8, "excellence": 2},
        "FMS": {"core": 11, "commitment": 29, "achievement": 2, "excellence": 1},
        "HRM": {"core": 16, "commitment": 56, "achievement": 4, "excellence": 0},
        "IMS": {"core": 9, "commitment": 33, "achievement": 2, "excellence": 1},
    }
    chapters_by_code = {c["chapter_code"]: c for c in chapters_resp}
    for code, counts in official_category_counts.items():
        chapter = chapters_by_code[code]
        assert chapter["core_count"] == counts["core"]
        assert chapter["commitment_count"] == counts["commitment"]
        assert chapter["achievement_count"] == counts["achievement"]
        assert chapter["excellence_count"] == counts["excellence"]

    # Check COP category counts
    cop_resp = [c for c in chapters_resp if c["chapter_code"] == "COP"][0]
    assert cop_resp["core_count"] == 13
    assert cop_resp["commitment_count"] == 107
    assert cop_resp["achievement_count"] == 12
    assert cop_resp["excellence_count"] == 4

    # Check IPC breakdown details
    ipc_resp = [c for c in chapters_resp if c["chapter_code"] == "IPC"][0]
    assert ipc_resp["title"] == "Infection Prevention and Control"
    assert ipc_resp["official_standards_count"] == 8
    assert ipc_resp["official_objective_elements_count"] == 49
    assert ipc_resp["core_count"] == 13
    assert ipc_resp["commitment_count"] == 33
    assert ipc_resp["achievement_count"] == 3
    assert ipc_resp["excellence_count"] == 0
    assert ipc_resp["seeded_standards_count"] == 1
    assert ipc_resp["seeded_objective_elements_count"] == 1
    assert ipc_resp["standards_coverage_percent"] == 12.5 # 1/8
    assert ipc_resp["elements_coverage_percent"] == 2.0  # 1/49 = 2.04% -> 2.0
    assert ipc_resp["citation_count"] == 1
    assert ipc_resp["uncited_seeded_elements_count"] == 0
    assert ipc_resp["is_fully_seeded"] is False

    # Check FMS breakdown details
    fms_resp = [c for c in chapters_resp if c["chapter_code"] == "FMS"][0]
    assert fms_resp["title"] == "Facility Management and Safety"
    assert fms_resp["official_standards_count"] == 7
    assert fms_resp["official_objective_elements_count"] == 43
    assert fms_resp["core_count"] == 11
    assert fms_resp["commitment_count"] == 29
    assert fms_resp["achievement_count"] == 2
    assert fms_resp["excellence_count"] == 1
    assert fms_resp["seeded_standards_count"] == 1
    assert fms_resp["seeded_objective_elements_count"] == 1
    assert fms_resp["standards_coverage_percent"] == 14.3 # 1/7
    assert fms_resp["elements_coverage_percent"] == 2.3  # 1/43 = 2.32% -> 2.3
    assert fms_resp["citation_count"] == 1
    assert fms_resp["uncited_seeded_elements_count"] == 0
    assert fms_resp["is_fully_seeded"] is False

    # Check MOM breakdown details
    mom_resp = [c for c in chapters_resp if c["chapter_code"] == "MOM"][0]
    assert mom_resp["title"] == "Management of Medication"
    assert mom_resp["official_standards_count"] == 11
    assert mom_resp["official_objective_elements_count"] == 68
    assert mom_resp["seeded_standards_count"] == 1
    assert mom_resp["seeded_objective_elements_count"] == 1
    assert mom_resp["standards_coverage_percent"] == 9.1  # 1/11
    assert mom_resp["elements_coverage_percent"] == 1.5  # 1/68 = 1.47% -> 1.5
    assert mom_resp["citation_count"] == 1
    assert mom_resp["uncited_seeded_elements_count"] == 0
    assert mom_resp["is_fully_seeded"] is False

    # Check IMS breakdown details
    ims_resp = [c for c in chapters_resp if c["chapter_code"] == "IMS"][0]
    assert ims_resp["core_count"] == 9
    assert ims_resp["commitment_count"] == 33
    assert ims_resp["achievement_count"] == 2
    assert ims_resp["excellence_count"] == 1

    # Clean up overrides
    app.dependency_overrides.clear()
