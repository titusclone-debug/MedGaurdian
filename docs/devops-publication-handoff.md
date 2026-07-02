# DevOps Handoff: NABH 6th Edition Canonical Corpus Publication

This runbook is for the Stage E production publication of the governed NABH 6th Edition corpus. Run it against staging PostgreSQL first, then production PostgreSQL after staging verification passes.

## Governance

The package follows Option B:

- Official text may be stored in the protected database for provenance and internal traceability.
- Official text must not be displayed verbatim through UI/API surfaces.
- `NABHSourceDocument.may_store_full_text` must be `true`.
- `NABHSourceDocument.may_display_full_text` must be `false`.
- Internal governance reference: `INTERNAL-MGMT-2025-PHASE1.5`.
- Publishing/approval account: active `SUPER_ADMIN` staff ID `staff-000`.

## Required Inputs

- Managed PostgreSQL `DATABASE_URL` for the target environment.
- `workspace/nabh-6-package/` aligned package directory.
- `workspace/research_data/NABH Hospital Accreditation Standard 6th Edition January 2025.pdf`.
- Expected PDF SHA-256: `0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A`.

## Preflight Gates

1. Confirm the target database name and environment in writing.
2. Confirm `DATABASE_URL` points to PostgreSQL, not SQLite.
3. Confirm Alembic is at head.
4. Take a managed PostgreSQL backup/export.
5. Confirm the restore/rollback procedure before publication.

## Execution

### 1. Align Local Package Metadata

```bash
python backend/scripts/stage_a_align_workspace.py
```

Confirm `workspace/nabh-6-package/package.json` includes:

- `full_text_storage_permitted: true`
- `display_permission_confirmed: false`
- `rights_reference: "INTERNAL-MGMT-2025-PHASE1.5"`
- `rights_approved_by: "staff-000"`

### 2. Validate Package and Source PDF

```bash
python backend/scripts/validate_nabh_canonical_package.py workspace/nabh-6-package --source-pdf "workspace/research_data/NABH Hospital Accreditation Standard 6th Edition January 2025.pdf"
```

Expected counts:

- 10 chapters
- 100 standards
- 639 requirements
- 639 citations

### 3. Dry-Run Against Target PostgreSQL

```bash
export NABH_FULL_TEXT_PERMISSION_CONFIRMED=true

python backend/scripts/publish_nabh_canonical_package.py workspace/nabh-6-package \
  --source-pdf "workspace/research_data/NABH Hospital Accreditation Standard 6th Edition January 2025.pdf" \
  --dry-run
```

Expected result: command succeeds and outputs `"dry_run": true`.

### 4. Publish With Explicit Confirmations

```bash
export NABH_FULL_TEXT_PERMISSION_CONFIRMED=true

python backend/scripts/publish_nabh_canonical_package.py workspace/nabh-6-package \
  --source-pdf "workspace/research_data/NABH Hospital Accreditation Standard 6th Edition January 2025.pdf" \
  --confirm-edition 6.0 \
  --confirm-requirements 639 \
  --confirm-source-sha256 0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A
```

## Post-Publication Verification

Verify all of the following before marking Stage E complete:

- 10 active NABH chapters.
- 100 active NABH standards.
- 639 active `NABHRequirement` rows.
- 639 active citations.
- 639 requirements have `publication_status = PUBLISHED`.
- 639 requirements have `source_status = official_verified`.
- Seed health reports `corpus_mode = canonical_published`.
- Source document checksum matches the official PDF.
- Source document has `may_store_full_text = true`.
- Source document has `may_display_full_text = false`.
- Application restart logs show legacy JSON seeding is bypassed for edition 6.0.
- UI/API smoke checks do not expose official full text verbatim.

## Rollback

If publication or verification fails, restore the managed PostgreSQL backup taken in preflight and redeploy the last known good application revision.
