# MedGuardian

MedGuardian is being rebuilt into an operating system for hospital administration, compliance, accreditation, evidence, and audit readiness.

The current flagship domain is NABH. The immediate north star for the NABH module is:

> Build an accreditation operating system that can take a hospital admin from "I don't understand NABH" to "we are survey-ready with defensible evidence," through a guided, source-cited, agent-assisted workflow.

The product should not be a dashboard first. It should be a guided execution system with dashboards as a byproduct.

## Product Direction

MedGuardian is intended for hospitals that cannot afford fragmented spreadsheets, consultant-dependent compliance memory, or last-minute audit panic. It should help a hospital know:

- what applies to this hospital,
- why it applies,
- what evidence proves it,
- who owns it,
- what is missing,
- what must be done next,
- and whether the answer is defensible under audit.

The long-term platform pattern is the same across domains:

1. Build a source-of-truth layer for the regulation or operating standard.
2. Map it to the hospital's actual profile and services.
3. Convert obligations into requirements, evidence, owners, tasks, and dates.
4. Add beginner guidance and plain-language explanations.
5. Add evidence workflows and audit trails.
6. Add bounded agents that cite sources and require human approval.
7. Generate documents, binders, reports, and management-review artifacts.
8. Harden for multi-hospital operations, performance, security, and governance.

NABH is the proving ground for this architecture. Once the pattern is stable, the same discipline will be applied to FCRA, DPDP, BMW, licenses, risk, HR, pharmacy, infection control, training, incidents, CAPA, and other hospital operations.

## NABH Domain North Star

The NABH module is being rebuilt as a full accreditation operating system, not merely a readiness dashboard.

Core pillars:

- **Truth Layer:** official NABH 6th Edition ontology, chapters, standards, objective elements, measurable elements, evidence requirements, applicability rules, citations, versioning, and retired-state handling.
- **Learning Layer:** beginner-friendly NABH guidance embedded inside the workflow.
- **Accreditation Workspace:** hospital profile, applicable scope, requirement state, readiness diagnosis, owners, due dates, and evidence expectations.
- **Evidence Vault:** uploads, metadata, OCR/text extraction, clause mapping, sufficiency scoring, versioning, approvals, and audit trail.
- **Agent Layer:** guide agent, gap diagnosis agent, roadmap agent, SOP/document agent, evidence-review agent, and mock surveyor agent, all bounded by citations and human approval.
- **Document Factory:** SOPs, policies, forms, registers, checklists, training decks, committee minutes, mock assessment reports, and survey packs.
- **Surveyor Binder:** official chapter/objective organized evidence packages with traceable manifests.
- **Governance Layer:** RBAC, tenant isolation, source-citation enforcement, audit logs, approvals, and reproducibility.

## NABH 8-Phase Roadmap

### Phase 1: Foundation And Truth Layer

Goal: replace the simplified NABH implementation with a defensible accreditation knowledge base.

Deliverables:

- canonical NABH 6th Edition ontology,
- source documents and citations,
- evidence expectations,
- applicability rules,
- hospital accreditation profile,
- hospital-specific requirement state,
- readiness calculation from applicable requirements,
- source-cited deterministic explanations,
- Phase 1 frontend workspace,
- regression tests and data quality guardrails,
- migration bridge from legacy `NABHObjective` records.

Exit criteria:

- the system can tell a hospital which NABH requirements apply to it,
- every displayed production-facing requirement has citation and evidence expectations,
- readiness is based only on applicable hospital-specific requirement state,
- the old simplified model no longer acts as the product source of truth.

### Phase 2: Beginner Guided NABH Journey

Goal: make the NABH tab useful to an administrator with zero prior NABH knowledge.

Deliverables:

- "Start Here" onboarding,
- explanation of NABH process stages,
- accreditation readiness interview,
- first readiness baseline,
- dynamic 16-month roadmap,
- role playbooks for administrator, quality officer, nursing head, medical superintendent, HR, pharmacy, infection control, FMS, MRD, and other owners.

Exit criteria:

- a first-time admin can open NABH and understand what to do next without external consulting,
- the system creates a hospital-specific accreditation roadmap.

### Phase 3: Evidence Vault And Workflow Engine

Goal: move from tracking to execution with proof.

Deliverables:

- upload and indexing for policies, SOPs, registers, licenses, training records, meeting minutes, audit reports, incident records, and calibration certificates,
- evidence metadata and requirement mapping,
- OCR/text extraction,
- evidence sufficiency status,
- tasks, subtasks, owners, reviewers, approvers, due dates, and escalation,
- committee workflows,
- immutable audit log.

Exit criteria:

- every NABH gap can become a task linked to actual evidence,
- the app can explain which proofs are missing, weak, stale, expired, or acceptable.

### Phase 4: Agentic Copilot V1

Goal: introduce useful agents with bounded authority and human approval.

Agents:

- NABH Guide Agent,
- Gap Diagnosis Agent,
- Roadmap Agent,
- SOP Agent,
- Evidence Reviewer Agent,
- Mock Surveyor Agent.

Engineering requirements:

- source-cited regulatory interpretation,
- no silent mutation of accreditation state,
- human approval before saving generated documents or marking evidence sufficient,
- prompt/version registry,
- stored reasoning artifacts, citations, confidence, and review status.

Exit criteria:

- admins can ask hospital-specific NABH questions and receive cited answers,
- admins can draft, review, approve, and link operational documents,
- agents cannot become the source of truth.

### Phase 5: Document Factory

Goal: generate real operational artifacts, not generic markdown.

Deliverables:

- DOCX SOPs, policies, forms, checklists, registers, and committee minutes,
- PPTX staff training decks,
- Excel/CSV register templates,
- hospital branding and document coding,
- draft/review/approved/retired lifecycle,
- automated review cycles.

Exit criteria:

- the system can produce a starter documentation kit for each applicable NABH chapter,
- outputs are editable, versioned, approved, and evidence-linked.

### Phase 6: Operational Integrations And Telemetry

Goal: prove implementation through live operations.

Deliverables:

- integration with DPDP consent, BMW logs, licenses, risk alerts, staff, pharmacy, training, incidents, CAPA, internal audit, equipment calibration, infection control, MRD audit, patient feedback, and fire drill logs,
- replacement of simulated checks with real data checks,
- implementation-duration tracking,
- operational KPI dashboards.

Exit criteria:

- readiness is driven by live operational evidence,
- the system can tell whether the hospital has enough historical proof.

### Phase 7: Mock Assessment And Surveyor Binder

Goal: make the hospital survey-ready.

Deliverables:

- chapter-wise mock assessment,
- surveyor question bank,
- department tracers,
- nonconformity register,
- CAPA closure evidence,
- Surveyor Binder 2.0 organized by official NABH structure,
- exportable evidence manifest with hashes, citations, and missing-evidence report.

Exit criteria:

- the hospital can rehearse survey conditions,
- the final binder is reviewable, traceable, and defensible.

### Phase 8: Enterprise Hardening

Goal: make the system enterprise-grade, multi-hospital, auditable, and safe.

Deliverables:

- multi-tenant isolation,
- organization hierarchy and fleet dashboards,
- advanced RBAC,
- encryption, backups, retention policies, access logs, and signed evidence manifests,
- agent governance and hallucination checks,
- background jobs, queues, vector index monitoring, observability, CI/CD, and production migrations,
- evaluation suites for NABH answers, evidence review, SOP quality, and unsafe actions.

Exit criteria:

- the system is usable across multiple hospitals,
- agent outputs are measurable, reviewable, and safe enough for regulated healthcare operations.

## NABH Phase 1 Task Plan

Phase 1 is the current build track. It exists to create a trustworthy NABH brainstem before advanced agents, OCR, document generation, or mock surveyor workflows.

1. Freeze the current simplified NABH model as legacy.
2. Design the NABH ontology schema.
3. Design hospital accreditation profile schema.
4. Design hospital-specific requirement state.
5. Design citation as first-class infrastructure.
6. Create database migrations / schema support.
7. Build structured ontology seed format.
8. Populate minimum viable official ontology.
9. Build applicability engine.
10. Build NABH ontology APIs.
11. Build hospital profile APIs.
12. Build requirement-state APIs.
13. Replace readiness calculation.
14. Add evidence requirement model.
15. Build source-cited explanation helper.
16. Create frontend Phase 1 NABH skeleton.
17. Add regression tests.
18. Add data quality guardrails.
19. Add migration bridge.
20. Complete Phase 1 demo milestone.

Phase 1 deliberately does not build autonomous agents, OCR, PPT generation, mock surveyor, or advanced dashboards. Those are downstream. Phase 1 succeeds only if the product has a reliable, source-cited, hospital-specific NABH foundation.

## Current NABH Architecture

Backend truth and workflow modules:

- `backend/app/nabh/validator.py` validates structured seed files before database writes.
- `backend/app/nabh/seeder.py` idempotently seeds the versioned NABH ontology.
- `backend/app/nabh/applicability.py` computes hospital-specific requirement applicability.
- `backend/app/nabh/readiness.py` calculates readiness from `HospitalNABHRequirement`.
- `backend/app/nabh/explanation.py` builds deterministic, source-cited explanations.
- `backend/app/nabh/quality.py` enforces runtime quality guardrails.
- `backend/app/nabh/migration_bridge.py` maps legacy `NABHObjective` records into the new model where deterministic.

Frontend NABH workspace:

- `frontend/src/pages/NABH.tsx` contains the Phase 1 scope-first NABH workspace.
- `frontend/src/components/nabh/LegacyNABHDashboard.tsx` preserves the old dashboard as secondary legacy context.

Key Phase 1 API surfaces:

- `GET /api/nabh/ontology/coverage`
- `GET /api/nabh/ontology/chapters`
- `GET /api/nabh/ontology/requirements`
- `GET /api/nabh/ontology/requirements/{requirement_id}`
- `GET /api/nabh/ontology/requirements/{requirement_id}/explanation`
- `GET /api/nabh/profile/{hospital_id}`
- `PUT /api/nabh/profile/{hospital_id}`
- `POST /api/nabh/profile/{hospital_id}/compute-applicability`
- `GET /api/nabh/requirements/{hospital_id}`
- `PATCH /api/nabh/requirements/{hospital_id}/{requirement_id}`
- `GET /api/nabh/readiness/{hospital_id}`
- `POST /api/nabh/migration/{hospital_id}/legacy-bridge`

## Whole-Application Revamp Pattern

The rest of MedGuardian should follow the NABH rebuild pattern.

### FCRA

Move from renewal/ledger screens to a source-cited FCRA operating layer:

- FCRA rules and obligations as structured truth,
- bank account and utilization mapping,
- donor restriction checks,
- evidence and audit trail,
- renewal document factory,
- agent-assisted but human-approved drafting.

### DPDP

Move from consent logging to a privacy operating system:

- purpose and consent truth layer,
- patient/staff data-flow mapping,
- consent evidence and withdrawal workflows,
- breach-response playbooks,
- audit-ready records of access and purpose limitation.

### BMW

Move from waste tracking to biomedical waste proof-of-compliance:

- rule-backed segregation, storage, handover, and manifest obligations,
- live log and evidence capture,
- vendor handover and discrepancy tracking,
- audit-ready manifests and corrective action workflows.

### Licenses And Risk

Move from expiry reminders to operational risk governance:

- license obligation registry,
- renewal evidence checklist,
- owner/deadline workflow,
- predictive risk signals,
- management-review reports.

### Operational Modules

Future modules should not be isolated dashboards. They should become evidence-producing systems connected to accreditation and compliance:

- HR and staff credentialing,
- training attendance,
- pharmacy,
- infection control,
- incident and CAPA,
- internal audit,
- equipment calibration,
- MRD audit,
- patient feedback,
- fire and facility safety.

## Engineering Principles

- The database truth layer beats agent memory.
- Regulatory guidance must be source-cited.
- Partial coverage is allowed, fake completeness is not.
- Hospital-specific state must be separate from read-only ontology/reference data.
- Readiness scores must be explainable and denominator-safe.
- Agents may advise, draft, and review, but not silently mutate regulated state.
- Evidence must be linked, versioned, reviewable, and exportable.
- Legacy systems should be bridged and quarantined, not abruptly deleted.

## Tech Stack

- Backend: FastAPI, SQLAlchemy
- Frontend: React 18, TypeScript, Vite, Tailwind CSS
- Database: SQLite for development, PostgreSQL-compatible architecture for production
- Auth: JWT and RBAC
- Testing: Pytest for backend, Vitest/Testing Library for frontend
- Vector/RAG direction: local-first retrieval infrastructure, to be used only behind source-citation and governance controls

## Quick Start

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Run backend tests:

```bash
cd backend
pytest
```

Run frontend tests:

```bash
cd frontend
npm run test
```

## Repository Structure

```text
backend/
  app/
    api/             FastAPI routes
    models/          SQLAlchemy models
    nabh/            NABH ontology, applicability, readiness, quality, migration
    schemas/         Pydantic response/request schemas
  tests/             Pytest suite

frontend/
  src/
    pages/           Main React pages
    components/      Shared and domain components
```

## Status

The application is mid-rebuild. NABH Phase 1 is the active track and is intended to establish the architectural pattern for the rest of the product.

The current priority is to complete the Phase 1 NABH milestone, verify the migration bridge, then do a deliberate modularization pass before expanding into evidence vault, agents, and document generation.

## License

MIT License. Built for mission-driven hospital operations.
