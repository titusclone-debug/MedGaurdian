"""
Seed Regulations Script — Ingests official NABH 6th Edition requirements and mock policies.
Run this script to initialize the local-first ChromaDB vector store.
"""
import sys
import os
from datetime import datetime

# Include backend path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.vector_store import init_chromadb, get_collection, add_documents

# Official NABH 6th Edition requirements text
OFFICIAL_NABH_RULES = {
    "AAC-1.a": "Standard Operating Procedure (SOP) for Patient Admission. Standard AAC-1.a requires defined admission criteria, registration procedures, and a formal clinical admission policy matching the hospital's capabilities and bed count.",
    "AAC-1.b": "Standard Operating Procedure (SOP) for Registration and initial administrative triage. Requires a structured patient intake process, demographic logging, and initial prioritization of emergency cases.",
    "AAC-2.a": "Standard Operating Procedure (SOP) for Comprehensive initial clinical assessment. Requires that all admitted patients receive a comprehensive medical and nursing assessment within 24 hours of admission.",
    "AAC-3.a": "Standard Operating Procedure (SOP) for Continuity of care and transfer protocols. Requires defined criteria for transferring patients internally between wards or externally to higher-care centers, ensuring safety during transport.",
    "AAC-4.a": "Standard Operating Procedure (SOP) for Discharge planning and discharge summary audits. Requires structured discharge plans, patient education, and periodic auditing of discharge summaries for completeness.",
    "AAC-5.a": "Standard Operating Procedure (SOP) for Ambulance and safe patient transport services. Requires medical equipment compliance, oxygen checks, and trained paramedics for patient transport.",
    
    "PC-1.a": "Standard Operating Procedure (SOP) for Patient rights education and informed consent checks. Requires patient rights displays, informed consent in vernacular language before any procedure, patient signature, doctor/nurse witness, and cryptographic time stamp verification to prevent backdating.",
    "PC-2.a": "Standard Operating Procedure (SOP) for Clinical care plan documentation and review. Requires that a structured clinical care plan is documented in medical records and reviewed daily by the clinical team.",
    "PC-3.a": "Standard Operating Procedure (SOP) for Medication reconciliation and expiry management. Requires medication reconciliation, double signatures for high-alert drugs/narcotics, LASA drug segregation, and barcode scan logs.",
    "PC-4.a": "Standard Operating Procedure (SOP) for Pre-operative assessment and WHO surgical safety checklist implementation. Requires pre-surgery time-out check logs, site-marking confirmations, and signed-off pre-surgery checklists.",
    "PC-5.a": "Standard Operating Procedure (SOP) for Pre-anesthesia assessment and monitoring standards. Requires pre-anesthesia assessment checklist records matched to active surgical operation records.",
    "PC-6.a": "Standard Operating Procedure (SOP) for Blood safety, transfusion audits and cross-matching. Requires recipient blood cross-match signatures, vitals monitoring logs, and blood bank storage refrigerator temperature logs.",
    "PC-7.a": "Standard Operating Procedure (SOP) for Hand hygiene WHO 5 Moments audit protocols. Requires weekly observational WHO 5 Moments hand hygiene auditing and compliance logging per ward.",
    "PC-8.a": "Standard Operating Procedure (SOP) for International Patient Safety Goals (IPSG) tracking. Requires double-patient identifier wristband checks before drug administration, surgery, or transfusion.",
    
    "FMS-1.a": "Standard Operating Procedure (SOP) for Fire Safety NOC, extinguisher mapping and drills. Requires a valid Fire NOC from the State Fire Services, geofenced weekly extinguisher inspections, and monthly mock fire drills mapped to staff rosters.",
    "FMS-2.a": "Standard Operating Procedure (SOP) for Bio-Medical Waste segregation at source and manifest matching. Requires BMW segregation in color-coded bins (Yellow, Red, White, Blue), barcoded bags, daily weight checks, and CBWTF manifest matching with <5% variance.",
    "FMS-3.a": "Standard Operating Procedure (SOP) for Disaster preparedness plan and evacuation routes. Requires a documented disaster management plan, visible evacuation routes, and staff emergency training records.",
    "FMS-4.a": "Standard Operating Procedure (SOP) for Security access control and CCTV coverage audits. Requires restricted access in high-risk zones (NICU, ICU, server rooms) and periodic CCTV feed uptime audits.",
    "FMS-5.a": "Standard Operating Procedure (SOP) for Medical equipment calibration and maintenance records. Requires positive chemical/biological indicator stamp uploads for autoclave validation, and maintenance logs.",
    "FMS-6.a": "Standard Operating Procedure (SOP) for Water and power utility checks and back-up testing. Requires daily logs of backup generator diesel levels, water quality filtration checks, and utility uptime reports.",
    
    "QMS-1.a": "Standard Operating Procedure (SOP) for Quality indicators planning and benchmark reviews. Requires tracking clinical indicators (e.g. infection rates, readmission rates) against national benchmarks.",
    "QMS-2.a": "Standard Operating Procedure (SOP) for SOP version control and documentation access audits. Requires version numbers, effective dates, authorized approvals, and change management headers on all policies.",
    "QMS-3.a": "Standard Operating Procedure (SOP) for Internal quality audits schedule and resolution tracking. Requires a structured annual audit calendar and resolution logs for identified non-conformities.",
    "QMS-4.a": "Standard Operating Procedure (SOP) for Management reviews of compliance deficit metrics. Requires periodic review meetings of hospital directors, agenda logs, and resolution tracking.",
    "QMS-5.a": "Standard Operating Procedure (SOP) for Incident reporting CAPA investigations. Requires incident reports logged within 24 hours, connected to RCA records, and closed CAPA tasks.",
    
    "IS-1.a": "Standard Operating Procedure (SOP) for Health information management policy and system access logs. Requires health information access controls, database logging, and user privilege audits.",
    "IS-2.a": "Standard Operating Procedure (SOP) for Medical records completion audits and restricted access protocols. Requires medical records audits, completion timelines, and vault access logs.",
    "IS-3.a": "Standard Operating Procedure (SOP) for DPDP audit readiness: Patient consent and signature mapping. Requires data protection compliance, patient consent records, and digital signature mapping.",
    "IS-4.a": "Standard Operating Procedure (SOP) for Clinical decision support alerts and algorithm audit records. Requires tracking of clinical decision alerts, overrides, and physician audits.",
    
    "HR-1.a": "Standard Operating Procedure (SOP) for Staff credentialing and medical registration checks. Requires primary source verification of degrees, active council registrations, and license verification logs.",
    "HR-2.a": "Standard Operating Procedure (SOP) for Staff orientation records and compliance training logs. Requires mandatory orientation for new staff, training schedules, and evaluation scores.",
    "HR-3.a": "Standard Operating Procedure (SOP) for Performance reviews and competency certifications. Requires structured staff competency evaluations, performance review registers, and skill certificates.",
    "HR-4.a": "Standard Operating Procedure (SOP) for Staff health assessments and immunization records. Requires medical screening for employees, vaccination records (Hepatitis B, etc.), and health audit logs."
}

# Mock Hospital Policies representing different levels of compliance
MOCK_POLICIES = [
    {
        "standard_code": "FMS-1.a",
        "title": "St. Mary's Fire Safety and NOC Protocol",
        "content": "Standard Operating Procedure (SOP) for Fire NOC compliance. Version 2.1. Effective Date: January 1, 2026. Approved by: Dr. Sarah Chen. Authorized Signatory. This policy defines Fire safety compliance at St. Mary's Mission Hospital. Weekly fire extinguisher pressure gauge inspections are logged. Monthly mock fire evacuation drills must be conducted for all ward staff.",
        "uploaded_at": datetime.utcnow().isoformat()
    },
    {
        "standard_code": "FMS-2.a",
        "title": "Bio-Medical Waste Segregation Policy",
        "content": "Standard Operating Procedure (SOP) for Bio-Medical Waste management. Version 1.0. Effective Date: January 1, 2026. Approved by: Nurse Priya Joseph. Waste must be segregated at source in color-coded bins: yellow (anatomical/soiled), red (recyclable), white (sharps), and blue (medicines). Weights must be verified against transporter manifests to check for discrepancies.",
        "uploaded_at": datetime.utcnow().isoformat()
    },
    {
        "standard_code": "PC-1.a",
        "title": "Informed Patient Consent Standard",
        "content": "Informed Patient Consent Policy. Version 1.2. Effective Date: January 1, 2026. Approved by: Dr. Thomas Mathew. Consent must be obtained before surgery. Demands cryptographic digital signature hashes and witness logging. Backdating signatures is strictly prohibited.",
        "uploaded_at": datetime.utcnow().isoformat()
    },
    {
        "standard_code": "PC-3.a",
        "title": "Pharmacy Medication Management SOP",
        "content": "Standard Operating Procedure (SOP) for Medication management. Version 1.0. Effective Date: January 1, 2026. Approved by: Pharmacist. Checks for expiry must be run daily. LASA drug segregation, narcotics double-signature, and reconciliation logs must be maintained.",
        "uploaded_at": datetime.utcnow().isoformat()
    },
    {
        "standard_code": "AAC-1.a",
        "title": "Patient Admission SOP (Stale Document)",
        "content": "Patient Admission Protocol. Version 1.0. Effective Date: August 15, 2024. Approved by: Admin. This policy governs admission criteria and bed allocations.",
        "uploaded_at": datetime(2024, 8, 15).isoformat()  # Outdated (>12 months ago)
    },
    {
        "standard_code": "HR-2.a",
        "title": "Staff Onboarding Policy (Generic Policy - No headers)",
        "content": "This document outlines how we onboarding staff at the mission clinic. Staff must complete training when they join, and we keep paper records of rosters in the cabinet.",
        "uploaded_at": datetime.utcnow().isoformat()  # Generic policy (fails Keyword Gate and Structural headers)
    }
]

def seed():
    print("Initializing ChromaDB vector store...")
    collections = init_chromadb()
    
    # 1. Seed Regulations
    print("Ingesting 33 official NABH 6th Edition rules...")
    reg_coll = get_collection(settings.CHROMA_COLLECTION_REGULATIONS)
    
    reg_ids = []
    reg_docs = []
    reg_metas = []
    
    for code, text in OFFICIAL_NABH_RULES.items():
        doc_id = f"reg-{code}"
        reg_ids.append(doc_id)
        reg_docs.append(text)
        reg_metas.append({
            "standard_code": code,
            "source": "NABH 6th Edition",
            "type": "official_rule",
            "ingested_at": datetime.utcnow().isoformat()
        })
        
    reg_coll.add(
        ids=reg_ids,
        documents=reg_docs,
        metadatas=reg_metas
    )
    print(f"Regulations seeding complete. Added {len(reg_docs)} rules to regulations collection.")
    
    # 2. Seed Mock Policies
    print("Ingesting mock hospital policy documents...")
    pol_coll = get_collection(settings.CHROMA_COLLECTION_POLICIES)
    
    pol_ids = []
    pol_docs = []
    pol_metas = []
    
    for i, p in enumerate(MOCK_POLICIES):
        doc_id = f"pol-{p['standard_code']}-{i}"
        pol_ids.append(doc_id)
        pol_docs.append(p["content"])
        pol_metas.append({
            "standard_code": p["standard_code"],
            "hospital_id": "hospital-001",
            "title": p["title"],
            "uploaded_at": p["uploaded_at"],
            "type": "hospital_policy"
        })
        
    pol_coll.add(
        ids=pol_ids,
        documents=pol_docs,
        metadatas=pol_metas
    )
    print(f"Policies seeding complete. Added {len(pol_docs)} policies to policies collection.")

if __name__ == "__main__":
    seed()
