# NABH Phase 1.5: Knowledge And Source Ingestion

## Purpose

Phase 1.5 turns the Phase 1 accreditation foundation into a governed NABH
knowledge base before the Beginner Guided NABH Journey begins.

Its purpose is not to make an uploaded PDF searchable. Its purpose is to ensure
that every normative requirement used by MedGuardian is:

- derived from an identified authoritative source,
- represented at the correct official hierarchy level,
- independently reviewed,
- linked to a stable source locator,
- versioned and publishable through a controlled transaction,
- distinguishable from MedGuardian interpretation and implementation guidance,
- and reproducible under audit.

## Authority Model

The authority order is:

1. The applicable NABH edition and its governed official source documents.
2. The published canonical ontology derived from those sources.
3. Hospital-specific applicability and requirement state.
4. Approved evidence and human approvals.
5. MedGuardian interpretations, implementation guidance, and agent output.

Lower layers may explain or operationalize higher layers. They may not silently
override them.

## Verified Source Identity

The registered source is:

- Title: `NABH Accreditation Standards for Hospitals`
- Issuer: `National Accreditation Board for Hospitals and Healthcare Providers`
- Edition: `6th Edition`
- Effective date: `2025-01-01`
- ISBN: `978-81-965264-9-8`
- SHA-256:
  `0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A`
- Physical PDF pages: `242`
- Last visible printed page: `230`

The protected PDF is operator-held research material and is intentionally
excluded from Git. The repository stores only non-copyright source metadata,
checksums, counts, page ranges, and anomaly records until rights permit more.

## Canonical Hierarchy

The 6th Edition source establishes this normative hierarchy:

```text
Edition
  Chapter
    Standard
      Objective Element
```

MedGuardian represents one official Objective Element as one
`NABHRequirement`. The Phase 1 `NABHObjectiveElement` and
`NABHMeasurableElement` tables remain only as temporary compatibility
structures for the synthetic seed and legacy migration bridge.

The reconciled official totals are:

| Chapter | Standards | Requirements | Core | Commitment | Achievement | Excellence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AAC | 13 | 87 | 6 | 68 | 9 | 4 |
| COP | 20 | 136 | 13 | 107 | 12 | 4 |
| MOM | 11 | 68 | 13 | 48 | 6 | 1 |
| PRE | 8 | 52 | 12 | 32 | 7 | 1 |
| IPC | 8 | 49 | 13 | 33 | 3 | 0 |
| PSQ | 7 | 46 | 8 | 28 | 7 | 3 |
| ROM | 6 | 37 | 4 | 23 | 8 | 2 |
| FMS | 7 | 43 | 11 | 29 | 2 | 1 |
| HRM | 13 | 76 | 16 | 56 | 4 | 0 |
| IMS | 7 | 45 | 9 | 33 | 2 | 1 |
| **Total** | **100** | **639** | **105** | **457** | **60** | **17** |

## Source Anomalies

Source-authored discrepancies are preserved in `NABHSourceAnomaly`; they are
not silently erased.

The initial register records:

- the page 19 COP summary value of 135, reconciled to 136 from the detailed COP
  enumeration and the `13 + 107 + 12 + 4` classification total,
- the contents-page HRM start of 159, reconciled to printed page 150,
- the contents-page IMS start of 186, reconciled to printed page 166.

The coverage API reports unresolved anomalies separately from reconciled ones.

## Knowledge Governance Model

Every knowledge record has an authority level:

- `normative`: official requirements and source-authored content,
- `official_interpretation`: interpretation issued by NABH or another
  authorized official source,
- `medguardian_interpretation`: governed MedGuardian explanation,
- `implementation_guidance`: operational advice, examples, and templates.

Every governed record also has a publication lifecycle:

```text
discovered -> extracted -> under_review -> verified -> approved -> published
                                                        |
                                                        +-> rejected
published -> superseded or retired
```

Normative publication requires separation of extractor, reviewer, and approver.
The package records what changed and why through `NABHKnowledgeChange`.
Interpretations and guidance live in `NABHKnowledgeContent`, with their own
authority, version, source link, change reason, approval history, effective
dates, and optional hospital scope. They are never written into normative
requirement text.

## Rights Boundary

The source copyright notice requires written permission for reproduction or
transmission. Therefore:

- the PDF is ignored by Git,
- full official text is not published merely because the file exists locally,
- validation can occur before publication,
- database publication of full official text requires both the
  `NABH_FULL_TEXT_PERMISSION_CONFIRMED=true` environment gate and explicit
  rights evidence in the approved package,
- display and embedding permissions are separate decisions,
- no web endpoint can seed or publish the corpus.

Legal approval must determine whether storage, display, derived summaries,
search indexing, and embeddings are permitted. The code does not infer these
rights.

## Canonical Release Package

An external controlled package contains:

```text
package.json
chapters.csv
standards.csv
requirements.csv
citations.csv
```

`package.json` must include:

- source identity, checksum, ISBN, edition, and effective date,
- extractor, reviewer, approver, and publisher Staff identities,
- review status and change reason,
- extraction method,
- rights status, rights reference, rights approver, and approval time,
- explicit storage, display, and embedding permissions.

Extractor, reviewer, approver, and publisher values must be IDs of active
`Staff` records. Publication persists those identities across the source
document, requirements, citations, and knowledge-change record. The approver
and publisher must be active super administrators because the canonical corpus
is global rather than hospital-scoped.

The CSV contracts are:

```text
chapters.csv:
sequence,chapter_code,official_title,first_printed_page,last_printed_page

standards.csv:
chapter_code,standard_code,exact_title,printed_page,display_order

requirements.csv:
chapter_code,standard_code,requirement_code,exact_official_text,
classification,printed_page,pdf_page_index,documentation_required,
display_order,human_verified

citations.csv:
requirement_code,printed_page,pdf_page_index,source_heading,human_verified
```

Page indices are one-based physical PDF page numbers. Printed page numbers are
the numbers shown in the source document.

Create a verified empty scaffold outside the repository:

```bash
cd backend
python scripts/create_nabh_canonical_package.py \
  /secure/path/nabh-6-package \
  --source-pdf /secure/path/nabh-6-official.pdf
```

The scaffold contains only source identity, chapter codes/page ranges, and CSV
headers. Controlled extraction and independent review populate the protected
standard and Objective Element fields.

## Validation Gates

`validate_nabh_canonical_package.py` performs no database mutation and rejects:

- the wrong source hash, edition, title, issuer, ISBN, or effective date,
- missing package files or columns,
- non-independent review roles,
- wrong chapter order or page spans,
- anything other than 10 chapters, 100 standards, and 639 requirements,
- any chapter or classification count mismatch,
- duplicate or malformed official codes,
- empty or ellipsized official text,
- invalid documentation flags or page locators,
- unverified requirements or citations,
- requirements without citations,
- citation locators that disagree with their requirement records.

## Publication Gates

`publish_nabh_canonical_package.py` additionally requires:

- the database to be at the current Alembic head,
- PostgreSQL for a real publication,
- exact operator confirmation of edition `6.0`, requirement count `639`, and
  the verified source checksum,
- explicit full-text permission metadata,
- explicit permission to display the official requirement text,
- `NABH_FULL_TEXT_PERMISSION_CONFIRMED=true`,
- and an exclusive PostgreSQL advisory transaction lock.

Publication is transactional. Failure rolls back the complete release.

Example validation:

```bash
cd backend
python scripts/validate_nabh_canonical_package.py \
  /secure/path/nabh-6-package \
  --source-pdf /secure/path/nabh-6-official.pdf
```

Example database dry run:

```bash
cd backend
NABH_FULL_TEXT_PERMISSION_CONFIRMED=true \
python scripts/publish_nabh_canonical_package.py \
  /secure/path/nabh-6-package \
  --source-pdf /secure/path/nabh-6-official.pdf \
  --dry-run
```

Example approved publication:

```bash
cd backend
NABH_FULL_TEXT_PERMISSION_CONFIRMED=true \
python scripts/publish_nabh_canonical_package.py \
  /secure/path/nabh-6-package \
  --source-pdf /secure/path/nabh-6-official.pdf \
  --confirm-edition 6.0 \
  --confirm-requirements 639 \
  --confirm-source-sha256 \
  0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A
```

## Cutover Behavior

On successful publication:

- official Objective Elements are published as canonical `NABHRequirement`
  rows,
- every requirement has a source citation and passage checksum,
- official requirements default to `manual_review` until governed
  hospital-context applicability rules exist,
- the synthetic Phase 1 canonical mirrors are marked `superseded` and retained
  for audit history,
- noncanonical synthetic standards are retired,
- legacy hospital state is preserved but excluded from active readiness views,
- and a knowledge-change record captures the publication event.

No legacy data is deleted.

## Operational Verification

After publication:

1. Confirm Alembic is at head.
2. Confirm seed health reports 10 chapters, 100 standards, 639 requirements,
   and 639 cited requirements.
3. Confirm ontology coverage reports `canonical_complete`.
4. Confirm the three source anomalies remain visible as reconciled records.
5. Recompute hospital applicability; the newly published corpus should enter
   `manual_review` unless governed rules say otherwise.
6. Confirm old synthetic states are absent from active readiness totals but
   remain queryable for audit/migration purposes.
7. Run backend, frontend, migration, and browser acceptance suites.
8. Back up PostgreSQL and record the package digest and change code.

## Phase 1.5 Exit Criteria

The implementation substrate is complete when the migration, models,
validators, publisher, API integration, and governance documentation are
deployed.

The knowledge-content phase is complete only when:

- the 639-record package has been extracted from the verified source,
- all records have independent human review,
- rights approval permits the intended storage/use,
- the package validates with no exceptions,
- publication succeeds transactionally,
- post-publication health and acceptance gates pass,
- and the package digest, approvers, change reason, and deployment are recorded.

Until then, MedGuardian must continue to describe the live corpus as a partial
Phase 1 seed, not the complete official 6th Edition knowledge base.
