# DevOps Handoff: Production Publication of NABH 6th Edition Canonical Corpus

This document provides instructions for the DevOps/Platform engineering team to execute the **Stage E Production Publication** of the aligned NABH 6th Edition knowledge base.

## Prerequisites

1. **Production Database Targeting:** The execution must run against the managed PostgreSQL instance (staging first, then production). The publication script will explicitly block execution if run against SQLite.
2. **Environment Variables:**
   - `DATABASE_URL`: Must point to the target PostgreSQL instance.
   - `NABH_FULL_TEXT_PERMISSION_CONFIRMED`: Must be set to `true`.
3. **Aligned Workspace:** The aligned `workspace/nabh-6-package/` directory and the official source PDF must be accessible from the execution environment.

## Governance & Option B

The corpus has been aligned with **Option B Governance**:
- **Storage Allowed:** The canonical extraction pipeline is authorized to store the official text (`may_store_full_text=true`).
- **Display Restricted:** The source data is protected from being rendered verbatim in UI/API responses (`may_display_full_text=false`).
- **Authorization:** `rights_reference` is logged as `INTERNAL-MGMT-2025-PHASE1.5`, approved by `staff-000` (Super Admin).

## Execution Steps

### 1. Verify Baseline Alignment
Ensure the `package.json` in the workspace correctly reflects the authorized governance data.
```bash
# From the project root
python backend/scripts/stage_a_align_workspace.py
```

### 2. Validate the Aligned Package
Run the validator to confirm structural integrity, governance gates, and source PDF checksum matching.
```bash
# This must output a successful payload with "review_status": "approved"
python backend/scripts/validate_nabh_canonical_package.py workspace/nabh-6-package --source-pdf "workspace/research_data/NABH Hospital Accreditation Standard 6th Edition January 2025.pdf"
```

### 3. Dry-Run Publication
Execute a dry-run against the target database to ensure the transaction will succeed without committing changes.
```bash
# Use PowerShell or bash to set the environment variable
export NABH_FULL_TEXT_PERMISSION_CONFIRMED="true"

python backend/scripts/publish_nabh_canonical_package.py workspace/nabh-6-package --source-pdf "workspace/research_data/NABH Hospital Accreditation Standard 6th Edition January 2025.pdf" --dry-run
```
*Expected Result: The script should complete successfully and explicitly output `"dry_run": true`.*

### 4. Production Publication
Once the dry-run is successful, execute the final publication. **This will commit the canonical corpus to the database.**
```bash
python backend/scripts/publish_nabh_canonical_package.py workspace/nabh-6-package --source-pdf "workspace/research_data/NABH Hospital Accreditation Standard 6th Edition January 2025.pdf"
```

### 5. Verification
Verify that the corpus was successfully published by checking the API or the database directly.
The `nabh_editions` table should show the 6.0 edition, and `nabh_requirements` should have 639 canonical rows marked as `PUBLISHED` and `official_verified`.
