# NABH Phase 1 Tasks 1-19 Completion Report

Date: 2026-06-12

## Purpose

This document records what the first 19 tasks of the NABH Phase 1 checklist accomplished.

Phase 1 is the foundation-and-truth-layer phase for the NABH domain. Its north star is to move a hospital admin from "I do not understand NABH" to "we are survey-ready with defensible evidence" through a guided, source-cited, agent-assisted workflow.

The first 19 tasks do not complete the full product vision. They build the reliable substrate needed before Task 20, the Phase 1 demo milestone, and before later Phase 2 work such as evidence vault workflows, agents, document generation, OCR, and mock surveyor flows.

## Current Phase 1 Position

- Tasks completed: 1-19 of 20.
- Remaining Phase 1 task: Task 20, the demo milestone.
- Verification status: the CTO reported 168 backend tests passing after Task 19, including 9 dedicated Task 19 migration bridge tests.
- Important scope note: the NABH 6th Edition ontology infrastructure models the official 10-chapter, 100-standard, 638-measurable-element universe, while the current seed set is intentionally partial and source-backed for Phase 1 validation.
- Refactor status: a modularization/refactor pass is still planned before Phase 2, but is outside the original 20-task Phase 1 checklist.

## Phase 1 Checklist Summary

| Task | Original task | Completion status |
| --- | --- | --- |
| 1 | Freeze the current simplified NABH model as legacy | Complete |
| 2 | Design the NABH ontology schema | Complete |
| 3 | Design hospital accreditation profile schema | Complete |
| 4 | Design hospital-specific requirement state | Complete |
| 5 | Design citation as first-class infrastructure | Complete |
| 6 | Create database migrations / schema support | Complete |
| 7 | Build structured ontology seed format | Complete |
| 8 | Populate minimum viable official ontology | Complete |
| 9 | Build applicability engine | Complete |
| 10 | Build NABH ontology APIs | Complete |
| 11 | Build hospital profile APIs | Complete |
| 12 | Build requirement-state APIs | Complete |
| 13 | Replace readiness calculation | Complete |
| 14 | Add evidence requirement model | Complete |
| 15 | Build source-cited explanation helper | Complete |
| 16 | Create frontend Phase 1 NABH skeleton | Complete |
| 17 | Add regression tests | Complete |
| 18 | Add data quality guardrails | Complete |
| 19 | Add migration bridge | Complete |

## Task 1: Freeze The Current Simplified NABH Model As Legacy

Original intent:
Preserve the existing simplified NABH implementation instead of deleting or silently mutating it, so the system could move toward a defensible 6th Edition model without breaking existing hospital data or older agent/report features.

What was completed:
- The existing `NABHObjective` model remains as the legacy hospital-level representation.
- Legacy APIs and agent workflows that depend on `NABHObjective` continue to exist.
- New Phase 1 models were added beside the old model rather than replacing it in place.
- Later tasks explicitly verified that legacy `NABHObjective` and `ComplianceRecord` data do not contaminate new ontology, readiness, evidence, or explanation outputs.

Key repo proof points:
- `backend/app/models/database.py`: legacy `NABHObjective` remains defined separately from the new versioned ontology tables.
- `backend/tests/test_nabh_task13_readiness.py`: readiness ignores legacy records.
- `backend/tests/test_nabh_task14_evidence.py`: evidence detail endpoints ignore legacy records.
- `backend/tests/test_nabh_task15_explanation.py`: explanation output ignores legacy records.
- `backend/tests/test_nabh_task17_legacy_isolation.py`: regression coverage for old/new separation.

Why it matters:
This gave the project a safe migration path. The new NABH operating system could be built without pretending the old simplified model was official truth, and without immediately destroying data that may still matter for continuity.

## Task 2: Design The NABH Ontology Schema

Original intent:
Create a versioned NABH ontology capable of representing the official standard hierarchy: edition, chapter, standard, objective element, and measurable element.

What was completed:
- Added versioned ontology tables for:
  - `NABHEdition`
  - `NABHChapter`
  - `NABHStandard`
  - `NABHObjectiveElement`
  - `NABHMeasurableElement`
- Added status/retirement fields so editions and ontology nodes can be active, draft, superseded, or retired without deleting history.
- Added canonical codes for deterministic lookup and stable cross-task references.
- Added official count metadata at the chapter level to distinguish complete official universe counts from currently seeded Phase 1 content.

Key repo proof points:
- `backend/app/models/database.py`: new versioned ontology model block.
- `backend/tests/test_nabh_task4_smoke.py`: relationship and persistence smoke coverage.
- `backend/tests/test_nabh_task8_smoke.py`: verifies 10 official NABH 6th Edition chapters and official aggregate counts.

Why it matters:
This became the authoritative "NABH truth layer." Every later Phase 1 feature depends on requirements being versioned, hierarchical, and traceable instead of being loose strings in a hospital checklist.

## Task 3: Design Hospital Accreditation Profile Schema

Original intent:
Capture hospital-specific facts needed to decide which NABH requirements apply, rather than treating every hospital as identical.

What was completed:
- Added `HospitalAccreditationProfile` as the hospital-scoped profile for NABH applicability.
- Captured operational attributes such as facility type, bed count, ICU availability, emergency services, blood bank, dialysis, imaging, laboratory services, ownership, teaching status, and profile status.
- Connected profile creation/update flows to applicability computation.

Key repo proof points:
- `backend/app/models/database.py`: `HospitalAccreditationProfile`.
- `backend/app/schemas/nabh.py`: Task 11 profile request/response schemas.
- `backend/app/api/nabh.py`: `GET /api/nabh/profile/{hospital_id}` and `PUT /api/nabh/profile/{hospital_id}`.
- `backend/tests/test_nabh_tasks10_12_api.py`: profile API coverage.
- `backend/tests/test_nabh_task9_smoke.py`: profile-driven applicability smoke coverage.

Why it matters:
The product can now guide a hospital based on what it actually is. That is essential for a beginner-friendly accreditation workflow because applicability must be explained and defensible, not guessed.

## Task 4: Design Hospital-Specific Requirement State

Original intent:
Create a hospital-specific state table that links a hospital to an official measurable element, allowing each hospital to track applicability, readiness, owner, evidence status, due dates, and reviewer state.

What was completed:
- Added `HospitalNABHRequirement`.
- Linked hospital state to official `NABHMeasurableElement` rows.
- Added fields for applicability status, readiness status, evidence status, maturity level, owner, reviewer, due date, notes, and timestamps.
- Enforced uniqueness for one hospital-state row per hospital and requirement.
- Added evidence link support through `HospitalRequirementEvidenceLink`.

Key repo proof points:
- `backend/app/models/database.py`: `HospitalNABHRequirement` and `HospitalRequirementEvidenceLink`.
- `backend/tests/test_nabh_task4_smoke.py`: relationship, cascade, and uniqueness smoke checks.
- `backend/tests/test_nabh_tasks10_12_api.py`: hospital requirement API checks.

Why it matters:
This is the operational bridge between official NABH truth and a hospital's day-to-day survey readiness work.

## Task 5: Design Citation As First-Class Infrastructure

Original intent:
Make source citation a core part of the NABH model, not a UI decoration or afterthought.

What was completed:
- Added `NABHSourceDocument` for source metadata.
- Added `NABHRequirementCitation` linking measurable elements to source documents.
- Added citation fields such as section, page number, clause reference, excerpt, and confidence.
- Added a citation service for fetching requirement-linked citation metadata.
- Ensured later APIs could include citation data with requirement detail and explanations.

Key repo proof points:
- `backend/app/models/database.py`: `NABHSourceDocument`, `NABHRequirementCitation`.
- `backend/app/nabh/citation_service.py`: citation lookup service.
- `backend/tests/test_nabh_task5_smoke.py`: citation infrastructure smoke coverage.
- `backend/tests/test_nabh_task7_5_smoke.py`: citation seeding and validation refinements.

Why it matters:
The north star requires defensible evidence. Defensibility starts with being able to say where each requirement came from.

## Task 6: Create Database Migrations / Schema Support

Original intent:
Make the new NABH ontology schema durable in the database, with appropriate indexes and idempotent schema support.

What was completed:
- Added schema support for the new ontology, citation, applicability, evidence, and hospital-state tables.
- Added explicit indexes for high-traffic joins and lookups across edition, chapter, standard, objective element, measurable element, citation, evidence, and applicability tables.
- Verified idempotency behavior for dynamic schema checks.

Key repo proof points:
- `backend/app/models/database.py`: table definitions and index declarations.
- `backend/tests/test_nabh_task6_smoke.py`: checks required indexes and idempotent schema behavior.
- `backend/scripts/verify_task6_db.py`: database verification script.

Why it matters:
The new NABH layer is query-heavy. The schema had to support browsing, filtering, state updates, explanations, and readiness calculation without relying on fragile ad hoc joins.

## Task 7: Build Structured Ontology Seed Format

Original intent:
Create a structured seed format for NABH 6th Edition data so ontology data, evidence requirements, applicability rules, and citations could be loaded deterministically.

What was completed:
- Added JSON seed files for:
  - chapters
  - requirements
  - evidence requirements
  - applicability rules
  - citations
- Added `validate_ontology_seeds` to catch missing files, missing keys, mixed versions, duplicate codes, broken references, and coverage mismatches.
- Added `seed_versioned_ontology` for deterministic database loading.
- Added citation-specific seed validation refinements.

Key repo proof points:
- `backend/app/nabh/data/nabh_6th_chapters.json`
- `backend/app/nabh/data/nabh_6th_requirements.json`
- `backend/app/nabh/data/nabh_6th_evidence_requirements.json`
- `backend/app/nabh/data/nabh_6th_applicability_rules.json`
- `backend/app/nabh/data/nabh_6th_citations.json`
- `backend/app/nabh/validator.py`
- `backend/app/nabh/seeder.py`
- `backend/tests/test_nabh_task7_smoke.py`
- `backend/tests/test_nabh_task7_5_smoke.py`

Why it matters:
The seed format is the ingestion contract for official NABH knowledge. It makes the ontology reproducible and reviewable rather than hand-entered through scattered code.

## Task 8: Populate Minimum Viable Official Ontology

Original intent:
Seed enough official NABH 6th Edition structure to validate the product flow end to end, while clearly tracking that the full official universe is larger than the Phase 1 seed subset.

What was completed:
- Seeded all 10 official NABH 6th Edition chapter codes:
  - AAC
  - COP
  - MOM
  - PRE
  - IPC
  - PSQ
  - ROM
  - FMS
  - HRM
  - IMS
- Preserved official aggregate counts of 100 standards and 638 measurable elements.
- Seeded a minimum viable official subset of requirements, evidence, applicability rules, and citations for Phase 1 validation.
- Added ontology coverage API support to expose seeded-versus-official coverage and partial status.

Key repo proof points:
- `backend/app/nabh/data/*.json`
- `backend/app/api/nabh.py`: `GET /api/nabh/ontology/coverage`.
- `backend/tests/test_nabh_task8_smoke.py`: verifies chapter set, official counts, seeded partial status, evidence, and citations.

Why it matters:
This created an honest MVP: enough official data to prove the system architecture, without falsely claiming the entire 638-element corpus had been fully seeded.

## Task 9: Build Applicability Engine

Original intent:
Compute which official NABH requirements apply to a specific hospital based on its accreditation profile and deterministic rules.

What was completed:
- Added an applicability engine that evaluates JSON rule conditions.
- Supported default applicability when no rule exists.
- Supported conditions such as numeric comparisons and profile-field matching.
- Created or updated `HospitalNABHRequirement` rows based on computed applicability.
- Ensured retired editions, standards, objective elements, and measurable elements are excluded.
- Preserved legacy `NABHObjective` records without mutating them.

Key repo proof points:
- `backend/app/nabh/applicability.py`
- `backend/app/api/nabh.py`: `POST /api/nabh/profile/{hospital_id}/compute-applicability`.
- `backend/tests/test_nabh_task9_smoke.py`
- `backend/tests/test_nabh_task17_applicability.py`

Why it matters:
This is the first major beginner-guidance step. The system can now tell a hospital which requirements matter to them, instead of handing them an undifferentiated NABH manual.

## Task 10: Build NABH Ontology APIs

Original intent:
Expose the official NABH ontology to the application through API endpoints for browsing editions, chapters, requirements, details, citations, and coverage.

What was completed:
- Added APIs for ontology coverage, editions, chapters, requirement search/listing, requirement details, and citation detail.
- Added filters for edition, chapter, standard, applicability, and requirement lookups.
- Included citations, evidence requirements, and applicability rules in requirement detail responses.
- Preserved active-edition and non-retired filtering.

Key repo proof points:
- `backend/app/api/nabh.py`:
  - `GET /api/nabh/ontology/coverage`
  - `GET /api/nabh/ontology/editions`
  - `GET /api/nabh/ontology/chapters`
  - `GET /api/nabh/ontology/requirements`
  - `GET /api/nabh/ontology/requirements/{requirement_id}`
  - `GET /api/nabh/ontology/citations/{citation_id}`
- `backend/app/schemas/nabh.py`: Task 10 ontology schemas.
- `backend/tests/test_nabh_tasks10_12_api.py`

Why it matters:
The frontend and later agent layer need an API contract over the source-cited ontology. This task made the official truth layer usable outside the database.

## Task 11: Build Hospital Profile APIs

Original intent:
Let hospital users create and update the profile data needed for applicability decisions.

What was completed:
- Added profile read and update endpoints.
- Added profile schemas for structured request and response behavior.
- Added hospital access checks so users cannot casually read or mutate another hospital's NABH profile.
- Connected profile state to the applicability workflow.

Key repo proof points:
- `backend/app/api/nabh.py`:
  - `GET /api/nabh/profile/{hospital_id}`
  - `PUT /api/nabh/profile/{hospital_id}`
- `backend/app/schemas/nabh.py`: Task 11 hospital profile schemas.
- `backend/tests/test_nabh_tasks10_12_api.py`

Why it matters:
The product can now ask hospital-specific questions and persist answers. This is the beginning of the guided workflow promised by the north star.

## Task 12: Build Requirement-State APIs

Original intent:
Expose hospital-specific requirement state so admins can see and update readiness, applicability, owner, evidence status, and review metadata.

What was completed:
- Added APIs to list hospital requirements and fetch detailed state for a single requirement.
- Added PATCH support for requirement state updates.
- Added response schemas for paginated summaries, detail responses, update requests, and evidence links.
- Added RBAC and hospital-access protection.
- Kept official ontology details and hospital state connected in the response shape.

Key repo proof points:
- `backend/app/api/nabh.py`:
  - `GET /api/nabh/requirements/{hospital_id}`
  - `GET /api/nabh/requirements/{hospital_id}/{requirement_id}`
  - `PATCH /api/nabh/requirements/{hospital_id}/{requirement_id}`
- `backend/app/schemas/nabh.py`: Task 12 requirement-state schemas.
- `backend/tests/test_nabh_tasks10_12_api.py`

Why it matters:
The hospital admin now has an operational work queue over official NABH requirements, instead of a static reference library.

## Task 13: Replace Readiness Calculation

Original intent:
Replace the old readiness calculation with one based only on the new hospital-specific, applicable NABH requirements.

What was completed:
- Added a readiness service over `HospitalNABHRequirement`.
- Readiness now excludes not-applicable requirements from score calculations.
- Readiness is grouped by chapter.
- Counts compliant, partially compliant, non-compliant, under-review, applicable, conditional, manual-review, and not-applicable states.
- Filters out retired ontology layers and inactive/irrelevant state.
- Ensures legacy `NABHObjective` and `ComplianceRecord` data do not affect new readiness scores.

Key repo proof points:
- `backend/app/nabh/readiness.py`
- `backend/app/api/nabh.py`: `GET /api/nabh/readiness/{hospital_id}`
- `backend/tests/test_nabh_task13_readiness.py`
- `backend/tests/test_nabh_task17_readiness.py`

Why it matters:
This made the readiness score defensible. The score now reflects the hospital's applicable official requirements, not a legacy simplified checklist.

## Task 14: Add Evidence Requirement Model

Original intent:
Attach required evidence definitions to official NABH requirements, so each requirement can tell a hospital what proof it must prepare.

What was completed:
- Added `NABHEvidenceRequirement`.
- Added evidence type, description, mandatory flag, default owner role, suggested documentation, and display order.
- Included evidence requirements in ontology and hospital requirement detail responses.
- Added hospital evidence-link support through `HospitalRequirementEvidenceLink`.
- Seeded evidence requirements through the structured seed files.
- Preserved legacy isolation: old compliance records and objectives do not affect evidence requirement output.

Key repo proof points:
- `backend/app/models/database.py`: `NABHEvidenceRequirement`, `HospitalRequirementEvidenceLink`.
- `backend/app/nabh/data/nabh_6th_evidence_requirements.json`
- `backend/app/nabh/seeder.py`: evidence seeding.
- `backend/app/api/nabh.py`: requirement detail responses include evidence.
- `backend/tests/test_nabh_task14_evidence.py`

Why it matters:
The system moved from "what does NABH ask?" toward "what proof should I prepare?" That is central to survey readiness.

## Task 15: Build Source-Cited Explanation Helper

Original intent:
Build a deterministic, non-LLM explanation helper that explains each requirement in plain language, cites its source, and avoids hallucination.

What was completed:
- Added `build_requirement_explanation`.
- Added `GET /api/nabh/ontology/requirements/{requirement_id}/explanation`.
- Built deterministic explanation text from chapter, standard, objective element, measurable element, severity, evidence, citation, and optional hospital state.
- Added source-citation confidence behavior:
  - source-cited when active citation and active source document exist,
  - missing-citation confidence and limitation when no citation is available.
- Added responsible-role resolution:
  - hospital owner,
  - dominant evidence owner role,
  - measurable element default owner,
  - fallback role.
- Added staff owner lookup protection and active-edition filtering.
- Ensured retired/no-locator citations do not create false source confidence.

Key repo proof points:
- `backend/app/nabh/explanation.py`
- `backend/app/api/nabh.py`: explanation endpoint.
- `backend/app/schemas/nabh.py`: Task 15 explanation schemas.
- `backend/tests/test_nabh_task15_explanation.py`
- `backend/tests/test_nabh_task17_explanation_regressions.py`
- `backend/tests/test_nabh_task18_quality_guardrails.py`

Why it matters:
This is the beginner-facing explanation layer. It helps an admin understand the requirement while keeping the system deterministic and source-bound.

## Task 16: Create Frontend Phase 1 NABH Skeleton

Original intent:
Create a frontend workspace that exposes the Phase 1 backend flow: hospital profile, applicability, official chapters, evidence needs, requirement explanations, and readiness.

What was completed:
- Reworked `frontend/src/pages/NABH.tsx` into a scope-first Phase 1 workspace.
- Added tabs for:
  - Start Here
  - Hospital Profile
  - Applicable Requirements
  - Standards Browser
  - Evidence Needed
  - Dashboard
- Added frontend integration with Phase 1 APIs.
- Added an explanation drawer for Task 15 requirement explanations.
- Moved the older NABH dashboard into `LegacyNABHDashboard`.
- Added frontend tests for major workspace flows.

Key repo proof points:
- `frontend/src/pages/NABH.tsx`
- `frontend/src/components/nabh/LegacyNABHDashboard.tsx`
- `frontend/src/pages/NABH.test.tsx`

Why it matters:
This gave the NABH foundation a usable first-screen experience. A hospital admin can now start interacting with the new guided model rather than only hitting backend endpoints.

Known follow-up:
URL query-parameter syncing for active tabs was discussed as a small enhancement but is not part of the completed Phase 1 checklist unless implemented separately.

## Task 17: Add Regression Tests

Original intent:
Add a regression shield around the new Phase 1 NABH architecture so later changes do not accidentally collapse new official behavior back into legacy behavior.

What was completed:
- Added regression coverage for seed integrity.
- Added applicability regression tests.
- Added readiness regression tests.
- Added legacy isolation tests.
- Added explanation regression tests.
- Preserved frontend workspace tests.

Key repo proof points:
- `backend/tests/test_nabh_task17_seed_integrity.py`
- `backend/tests/test_nabh_task17_applicability.py`
- `backend/tests/test_nabh_task17_readiness.py`
- `backend/tests/test_nabh_task17_legacy_isolation.py`
- `backend/tests/test_nabh_task17_explanation_regressions.py`
- `frontend/src/pages/NABH.test.tsx`

Why it matters:
Phase 1 created a lot of new contract surface. Task 17 made those contracts harder to break silently.

## Task 18: Add Data Quality Guardrails

Original intent:
Prevent bad or incomplete NABH data from entering runtime as if it were official, especially when the application depends on citations and evidence requirements.

What was completed:
- Added a quality module with explicit runtime validation.
- Added guardrails for:
  - missing active requirements,
  - retired edition/chapter/standard/objective/requirement layers,
  - missing active citations,
  - citations without active source documents,
  - citations without usable locators,
  - missing evidence definitions,
  - attempts to mark requirements compliant without evidence definitions.
- Added post-seed runtime quality checks for seeded requirements.
- Hardened the explanation helper so retired or locatorless citations do not count as source-cited.
- Updated smoke tests to use canonical IPC rather than outdated synthetic HIC data.

Key repo proof points:
- `backend/app/nabh/quality.py`
- `backend/app/nabh/seeder.py`: post-database runtime quality gate.
- `backend/app/api/nabh.py`: compliant-status guard in requirement PATCH flow.
- `backend/app/nabh/explanation.py`: active citation/source/locator filtering.
- `backend/tests/test_nabh_task18_quality_guardrails.py`
- `backend/tests/test_nabh_task7_smoke.py`
- `backend/tests/test_nabh_task7_5_smoke.py`
- `backend/tests/test_nabh_task5_smoke.py`

Why it matters:
This task protected the north star from a subtle failure mode: showing official-looking guidance without defensible sources or evidence expectations.

## Task 19: Add Migration Bridge

Original intent:
Create a deterministic bridge from legacy hospital-level `NABHObjective` records to the new official `HospitalNABHRequirement` model, without fuzzy mapping or destructive mutation.

What was completed:
- Added `NABHLegacyMigrationMap` provenance table.
- Added `migrate_hospital_legacy_nabh_state`.
- Added `migrate_all_hospitals_legacy_nabh_state`.
- Added deterministic mapping by:
  - exact measurable element canonical code,
  - exact objective element canonical code,
  - exact standard canonical code.
- Added unmapped reporting when no deterministic official target exists.
- Added dry-run support.
- Added idempotency behavior.
- Preserved existing `HospitalNABHRequirement` rows rather than overwriting them.
- Converted legacy maturity into readiness/evidence states conservatively.
- Protected cross-hospital staff ownership/reviewer migration.
- Recorded provenance for mapped, skipped, and unmapped results.
- Exposed migration through `POST /api/nabh/migration/{hospital_id}/legacy-bridge`.

Key repo proof points:
- `backend/app/models/database.py`: `NABHLegacyMigrationMap`.
- `backend/app/nabh/migration_bridge.py`
- `backend/app/api/nabh.py`: migration bridge endpoint.
- `backend/app/schemas/nabh.py`: Task 19 migration report schemas.
- `backend/tests/test_nabh_task19_migration_bridge.py`

Why it matters:
This lets the project move real hospitals from the old simplified NABH model into the new official architecture without making unsupported claims. It is the final bridge before the Phase 1 demo milestone.

## Cross-Cutting Outcomes After Tasks 1-19

The NABH domain now has:

- A preserved legacy model instead of a risky in-place replacement.
- A versioned official ontology schema.
- Hospital-specific profile and requirement-state models.
- First-class source citations.
- Evidence requirement definitions.
- Deterministic applicability.
- Deterministic readiness scoring over applicable requirements.
- Deterministic, source-cited explanations.
- A frontend Phase 1 workspace.
- Regression coverage over seed integrity, applicability, readiness, legacy isolation, explanations, quality gates, and migration.
- Runtime quality guardrails to avoid source-free or evidence-free official-looking output.
- A deterministic migration bridge from old hospital NABH data to new hospital requirement state.

## What Is Deliberately Not Claimed Yet

Tasks 1-19 do not claim that:

- the full 638 measurable elements have all been seeded,
- autonomous NABH agents are production-ready,
- OCR evidence ingestion exists,
- evidence vault workflows are complete,
- surveyor binder generation has been rebuilt on the new ontology,
- mock assessment workflows are complete,
- the frontend is final production UX,
- the codebase has already had its planned post-Phase-1 modularization pass.

These are later roadmap concerns.

## Task 20 Readiness

The remaining Phase 1 demo milestone should prove the following flow:

1. Admin opens the NABH tab.
2. Admin completes or reviews the hospital profile.
3. System computes applicable requirements.
4. Admin browses official chapters.
5. Admin sees evidence required per requirement.
6. Admin opens deterministic source-cited explanations.
7. Readiness score is calculated only from applicable requirements.
8. Displayed requirements are source-cited.
9. Legacy data can be bridged through the migration report without silent mutation.

If Task 20 demonstrates those flows cleanly, Phase 1 has achieved its intended foundation.
