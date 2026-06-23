# Task 20: Production Performance Root Cause Analysis

During our execution of **Task 20 (Production Performance Check)**, we utilized both static code analysis and a live Playwright UI automation script against the latest `main` branch deployed on the Render production environment (`medgaurdian.onrender.com`). 

The manual execution definitively validated severe systemic N+1 performance bottlenecks that critically degrade the Phase 1 UI.

## Executive Summary of Findings

1. **Massive Render UI Freeze**: Loading the initial Phase 1 workspace took a staggering **26.01 seconds** to mount.
2. **Total UI Lockup on Tab Switch**: Clicking the "Evidence Needed" tab triggered a catastrophic `Promise.all` network storm, resulting in a **30,000ms+ hard timeout** that essentially crashed the browser session.

## Detailed Root Causes

### 1. Frontend `Promise.all` Network DDoS
**Location**: `frontend/src/pages/NABH.tsx`
The React component architecture does not utilize pagination or lazy-loading for the "Evidence Needed" tab. Instead, it attempts to fetch the explanation details for *every single applicable requirement* instantly.
- When a hospital has ~600 applicable requirements, the frontend fires a 600-request `Promise.all` array to the `/explanation` endpoint.
- Browsers (like Chrome) limit concurrent connections per domain to 6. This causes the remaining 594 requests to stall in the network queue, heavily degrading the user experience and freezing the DOM.

### 2. Backend `/explanation` N+1 Query Avalanche
**Location**: `backend/app/nabh/router.py` -> `get_requirement_explanation`
While the frontend fires 600 concurrent HTTP requests, each individual request on the backend triggers a cascading N+1 database query pattern:
- `SELECT` requirement row
- `SELECT` parent objective element
- `SELECT` parent standard
- `SELECT` parent chapter
**Impact**: 600 concurrent HTTP requests × 4 sequential DB queries = **2,400 synchronous database queries** hitting the Render PostgreSQL instance simultaneously, causing connection starvation and massive response latency.

### 3. Applicability Engine Loop Fetching
**Location**: `backend/app/nabh/applicability.py` -> `compute_applicability_for_hospital`
The applicability engine evaluates hospital scope against the NABH ruleset. However, it retrieves the ontology data by querying the database sequentially inside a `for` loop for every single requirement.
- **Impact**: Computing applicability for a hospital triggers over **1,278 individual, synchronous database queries** in a single HTTP lifecycle, rather than executing a single bulk-fetch query and processing the tree in memory.

### 4. Over-fetching via Hardcoded Limits
**Location**: `frontend/src/pages/NABH.tsx`
The UI requests data using hardcoded pagination bypasses (e.g., `limit=1000`). While this works during local development with empty DB states, it fails catastrophically when populated with the dense NABH 6th Edition payload, forcing the React virtual DOM to render thousands of heavy nodes at once.

## Conclusion

The Render instance is not necessarily underpowered; it is being DDos'd by its own application logic. Resolving these bottlenecks requires shifting the architecture from "per-item fetching" to **Bulk Aggregation**.

**Next Steps (Task 21)**:
- Implement a backend `/api/nabh/explanations/bulk` endpoint.
- Refactor the `ApplicabilityEngine` to perform an upfront `in` query to load the ontology into memory before computing.
- Introduce virtualized lists or paginated chunks on the frontend.
