# 🏥 MedGuardian — The Institutional Nervous System

> **"Every small hospital in the mission network now has the collective intelligence of India's best administrators, updated in real-time."**

MedGuardian is a **world-class, future-ready hospital administration and compliance tracking system** built for the 2026 regulatory era. It automates compliance, asset protection, and operational excellence for healthcare institutions — with special focus on Christian Mission Hospitals operating in rural India.

---

## 🧠 Core Philosophy

**Wise Mentor, Not Task Master.** MedGuardian doesn't add to clinician burnout — it guides, nudges, and protects. Like a senior administrator who's seen every audit, every crisis, every regulatory change — and never sleeps.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEDGUARDIAN PLATFORM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Wise Mentor  │  │  Risk Weather │  │  Bureaucracy Engine  │  │
│  │  UI Layer     │  │  Forecast     │  │  (Auto-Drafting)     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                  │                      │              │
│  ┌──────┴──────────────────┴──────────────────────┴───────────┐ │
│  │              API Gateway (FastAPI)                          │ │
│  └──────┬──────────────────┬──────────────────────┬───────────┘ │
│         │                  │                      │              │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────────┴───────────┐ │
│  │  FCRA        │  │  DPDP        │  │  BMW Sentinel         │ │
│  │  Guardian    │  │  Consent     │  │  (Waste Tracking)     │ │
│  │              │  │  Manager     │  │                       │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
│         │                  │                      │              │
│  ┌──────┴──────────────────┴──────────────────────┴───────────┐ │
│  │           Regulatory Ingestion Engine (RAG)                │ │
│  │           ┌─────────────────────────────────┐              │ │
│  │           │  ChromaDB (Local-First Vector)  │              │ │
│  │           └─────────────────────────────────┘              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              NABH 6th Edition Compliance Tracker            │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## 📋 Key Features

### 1. FCRA Guardian
- Real-time ledger blocking non-compliant fund mixing
- "Continuous Utilization" proof generation
- Automated FCRA renewal application drafting

### 2. DPDP Consent Manager
- Blockchain-timestamped consent artefacts
- Purpose-limited data access for rural OPD
- Consent withdrawal management

### 3. BMW Sentinel
- Image-recognition waste classification
- Automated manifest generation
- 100% audit readiness tracking

### 4. NABH Compliance Tracker
- 6th Edition standards mapping
- Gap analysis and remediation tracking
- Assessment preparation dashboards

### 5. Risk Weather Forecast
- Heatmap of institutional risk
- Predictive alerts for expiring licenses
- Staffing level impact analysis

### 6. Bureaucracy Engine
- Auto-drafts legal appeals and renewals
- Veteran administrator tone matching
- Gazette of India monitoring

---

## 🔧 Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy
- **Vector DB:** ChromaDB (local-first, offline-capable)
- **Frontend:** React 18, TypeScript, Tailwind CSS
- **AI/ML:** Sentence Transformers, RAG Pipeline
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Auth:** JWT + RBAC

---

## 📜 License

MIT License — Built for the mission.
