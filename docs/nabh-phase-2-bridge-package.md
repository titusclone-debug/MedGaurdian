# NABH Phase 2 Bridge Package

This document bridges the governed Phase 1.5 NABH 6th Edition knowledge layer to the Phase 2 Beginner Guided Journey.

## 1. Corpus Readiness
**STATUS: CANONICAL CORPUS PUBLISHED**

The official Phase 1.5 canonical package has been published to the managed PostgreSQL environment under Option B governance.

Published production corpus:
- 10 NABH 6th Edition chapters.
- 100 standards.
- 639 Objective Element requirements.
- 639 official verified published requirements.
- 639 official canonical citations with source locators.
- Source checksum verified against the governed PDF package.

Production API verification confirmed:
- Ontology coverage reports `canonical_complete`.
- Hospital applicability computation evaluates 639 requirements.
- Hospital requirement state contains 639 rows for the checked hospital.
- Readiness denominator is 639 after recomputation.
- Public UI/API responses do not display official NABH text verbatim; they expose requirement codes, hierarchy, classifications, locators, and governance notices.

## 2. Governance Boundary
The corpus follows Option B:
- Official source text may be stored in the protected database for provenance and traceability.
- Official source text must not be displayed verbatim through public UI/API surfaces unless the source document explicitly permits display.
- MedGuardian-authored explanations, questions, workflows, evidence prompts, and guided journey content must be original operational expression derived from the governed source layer, not reproduced NABH prose.

## 3. Phase 2 Receives
Phase 2 can build on:
- Complete canonical requirement codes and hierarchy.
- Chapter, standard, and requirement classification metadata.
- Documentation-required flags.
- Citation metadata and page locators.
- Published source document provenance.
- Hospital-specific applicability/readiness state after recomputation.
- Legacy ID compatibility through `resolve_canonical_requirement_id`.

## 4. Phase 2 Must Author
Phase 2 still needs original, MedGuardian-authored operational content:
- Beginner glossary and concept explanations.
- Hospital profiling question bank and rationales.
- Evidence expectation prompts and guidance.
- Applicability rule explanations and manual-review playbooks.
- Readiness journey copy, role playbooks, and workflow text.

## 5. Quarantined Agents
Legacy agent routes (`/agent/*`) remain quarantined with `501 Not Implemented` and are awaiting the Phase 4 rebuild on top of the verified canonical corpus.
