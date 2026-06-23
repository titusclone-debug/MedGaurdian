# NABH Phase 1.5 Governance Decisions

This document establishes the binding rules for how the NABH 6th Edition knowledge layer is extracted, stored, and managed within MedGuardian.

## 1. Source Material Boundaries
*   **PDF Exclusion:** The official NABH PDF document **remains outside of Git**. Under no circumstances should the source PDF be committed to the repository.
*   **No Full Text in Repo:** No full official requirement text is committed directly to the codebase or seed files.
*   **Publication Constraints:** Full-text database publication requires explicit legal/rights-holder approval.
*   **Citation Mode:** Until rights are approved, the system operates strictly in "citation/reference mode", capturing metadata, citations, and source locators without duplicating copyrighted text.

## 2. Canonical Entities
*   **NABHRequirement is Canonical:** `NABHRequirement` is the definitive, canonical entity representing an official Objective Element.
*   **Legacy Data Quarantine:** Phase 1 synthetic measurable elements (`NABHMeasurableElement`) remain as legacy only. They are not to be used for new development.

## 3. Workflow Gates
*   **Phase 2 Blocker:** Phase 2 (Beginner Journey/Guided Execution) **cannot begin** until the entire 639-element corpus is extracted, reviewed, and published according to these governance rules.
