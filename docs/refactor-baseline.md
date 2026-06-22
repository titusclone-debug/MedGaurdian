# Post-Phase-1 Refactor Baseline

Baseline captured on June 23, 2026.

| Surface | Baseline |
| --- | ---: |
| `backend/app/api/nabh.py` | 1,397 lines before extraction |
| `frontend/src/pages/NABH.tsx` | 1,594 lines before extraction |
| `backend/app/models/database.py` | 1,105 lines |
| Alembic revisions | 8 |
| `datetime.utcnow()` occurrences in backend app | 67 |

## Public-contract guardrails

- Existing NABH URLs remain unchanged.
- `backend/tests/test_refactor_contracts.py` asserts the Phase 1 route surface.
- The Task 20 browser acceptance gate remains the production behavior gate.
- API helpers contain HTTP validation only; domain logic remains in NABH services.

## State ownership

The NABH frontend state is classified as follows:

- **Route state:** active `tab` query parameter.
- **Session state:** authenticated user and hospital identity.
- **Server state:** profile, ontology coverage, chapters, requirements, evidence
  plan, readiness, and explanations.
- **Derived state:** filtered requirements, chapter coverage, readiness metrics.
- **Form state:** accreditation profile edits.
- **Transient UI state:** loading, notices, errors, filters, and open explanation.

This classification is the boundary for subsequent hook and component extraction.
