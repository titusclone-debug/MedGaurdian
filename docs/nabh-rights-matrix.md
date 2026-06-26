# NABH 6th Edition Rights Matrix

This document defines the strict usage constraints and permitted operations for the NABH 6th Edition Accreditation Standards content within the MedGuardian system.

## Source Document Metadata
- **Title**: NABH Accreditation Standards for Hospitals
- **Issuer**: National Accreditation Board for Hospitals and Healthcare Providers
- **Edition**: 6th Edition (January 2025)
- **ISBN**: 978-81-965264-9-8
- **SHA-256 Checksum**: `0C684E6B71A9D582E50966A13E2BE3859EE5CA50C90D172D4FE57B79315C791A`

## Active Rights Mode
**Current Status**: `citation_only`

Until explicit legal and rights-holder permissions are obtained, MedGuardian operates in a strictly governed `citation_only` mode. No full verbatim text of the copyrighted standards may be persisted directly into the codebase or published to the application endpoints.

## Permitted Operations Matrix

| Operation | Permitted | Conditions & Constraints |
| :--- | :---: | :--- |
| **Archival Storage** | ❌ No | The original PDF must NOT be committed to the Git repository. It resides only in local, out-of-band `workspace/research_data/` environments. |
| **Internal Extraction** | ✅ Yes | Structural extraction (codes, hierarchy, classifications) is allowed. Verbatim text extraction is permitted *only* into the isolated `nabh-6-package/` for internal review, NOT into Git. |
| **DB Storage** | ⚠️ Partial | The database may store structural metadata, classifications, and page locators. It may **not** store full verbatim descriptions without a rights-mode upgrade. |
| **UI Display** | ⚠️ Partial | The UI may display the structural hierarchy, codes, and citations. It must rely on plain-language guidance or summaries rather than verbatim replication of the official PDF text. |
| **Export** | ❌ No | MedGuardian will not facilitate the export, download, or syndication of the NABH standards text. |
| **Embeddings & Search** | ❌ No | Generating vector embeddings from the full normative text for RAG (Retrieval-Augmented Generation) is prohibited under the current `citation_only` mode. |
| **Quotation Limits** | ✅ Yes | Brief snippet quotations strictly used for citation reference (e.g., "clause text summary") are permitted under fair use/reference boundaries, limited to the minimum necessary for identification. |

## Governance Enforcement
The database `NABHSourceDocument` enforces this rights matrix actively at runtime via boolean constraints (`may_store_full_text: false`, `may_display_full_text: false`, `may_create_embeddings: false`). Any attempt to sync the full corpus text into these endpoints will be blocked unless the rights matrix is legally upgraded.
