from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.nabh.repository import ComplianceRepository
from app.models.database import ComplianceRecord, ComplianceStatus, NABHObjective, MaturityLevel, SeverityLevel
from app.nabh.agent import InspectorAgent, ConsultantAgent, simulate_tracer_audit

NABH_STANDARDS = {
    "ACC": {
        "name": "Access, Assessment, and Continuity of Care",
        "chapters": {
            "AAC-1.a": "Patient admission protocols and criteria",
            "AAC-1.b": "Registration and initial administrative triage",
            "AAC-2.a": "Comprehensive initial clinical assessment",
            "AAC-3.a": "Continuity of care and transfer protocols",
            "AAC-4.a": "Discharge planning and discharge summary audits",
            "AAC-5.a": "Ambulance and safe patient transport services",
        }
    },
    "PC": {
        "name": "Patient Care",
        "chapters": {
            "PC-1.a": "Patient rights education and informed consent checks",
            "PC-2.a": "Clinical care plan documentation and review",
            "PC-3.a": "Medication reconciliation and expiry management",
            "PC-4.a": "Pre-operative assessment and WHO surgical safety checklist implementation",
            "PC-5.a": "Pre-anesthesia assessment and monitoring standards",
            "PC-6.a": "Blood safety, transfusion audits and cross-matching",
            "PC-7.a": "Hand hygiene WHO 5 Moments audit protocols",
            "PC-8.a": "International Patient Safety Goals (IPSG) tracking",
        }
    },
    "FMS": {
        "name": "Facility Management and Safety",
        "chapters": {
            "FMS-1.a": "Fire Safety NOC, extinguisher mapping and drills",
            "FMS-2.a": "Bio-Medical Waste segregation at source and manifest matching",
            "FMS-3.a": "Disaster preparedness plan and evacuation routes",
            "FMS-4.a": "Security access control and CCTV coverage audits",
            "FMS-5.a": "Medical equipment calibration and maintenance records",
            "FMS-6.a": "Water and power utility checks and back-up testing",
        }
    },
    "QMS": {
        "name": "Quality Management System",
        "chapters": {
            "QMS-1.a": "Quality indicators planning and benchmark reviews",
            "QMS-2.a": "SOP version control and documentation access audits",
            "QMS-3.a": "Internal quality audits schedule and resolution tracking",
            "QMS-4.a": "Management reviews of compliance deficit metrics",
            "QMS-5.a": "Incident reporting CAPA investigations",
        }
    },
    "IS": {
        "name": "Information Management System",
        "chapters": {
            "IS-1.a": "Health information management policy and system access logs",
            "IS-2.a": "Medical records completion audits and restricted access protocols",
            "IS-3.a": "DPDP audit readiness: Patient consent and signature mapping",
            "IS-4.a": "Clinical decision support alerts and algorithm audit records",
        }
    },
    "HR": {
        "name": "Human Resource Management",
        "chapters": {
            "HR-1.a": "Staff credentialing and medical registration checks",
            "HR-2.a": "Staff orientation records and compliance training logs",
            "HR-3.a": "Performance reviews and competency certifications",
            "HR-4.a": "Staff health assessments and immunization records",
        }
    },
}

class ComplianceService:
    @staticmethod
    def get_compliance_status(
        db: Session,
        hospital_id: str,
        chapter: Optional[str],
        status: Optional[ComplianceStatus]
    ) -> Dict[str, Any]:
        """Fetch records and calculate compliance averages and readiness ratings."""
        # A. Trigger Live Agent Audit Scan on fetch
        inspector = InspectorAgent()
        inspector.assess_current_state(db, hospital_id)
        
        # B. Read all granular objectives from DB
        all_records = ComplianceRepository.get_all_for_hospital(db, hospital_id)
        records = []
        for r in all_records:
            if chapter and r.chapter_code != chapter:
                continue
            records.append(r)
        
        chapters = {}
        for r in records:
            ch = r.chapter_code or "Uncategorized"
            if ch not in chapters:
                chapters[ch] = {"total": 0, "compliant": 0, "non_compliant": 0, "partial": 0, "under_review": 0, "score_sum": 0}
            
            chapters[ch]["total"] += 1
            chapters[ch]["score_sum"] += r.monitoring_indicator_rate if r.monitoring_indicator_rate is not None else (r.maturity_level.value * 20.0)
            
            # Map maturity to counts
            if r.maturity_level >= MaturityLevel.IMPLEMENTED:
                chapters[ch]["compliant"] += 1
            elif r.maturity_level == MaturityLevel.DEFINED:
                chapters[ch]["partial"] += 1
            elif r.maturity_level == MaturityLevel.AD_HOC:
                chapters[ch]["non_compliant"] += 1
            else:
                chapters[ch]["under_review"] += 1
                
        for ch in chapters:
            total = chapters[ch]["total"]
            chapters[ch]["compliance_rate"] = round(chapters[ch]["compliant"] / total * 100, 1) if total > 0 else 0
            chapters[ch]["avg_score"] = round(chapters[ch]["score_sum"] / total, 2) if total > 0 else 0
            
        overall_compliant = sum(1 for r in records if r.maturity_level >= MaturityLevel.IMPLEMENTED)
        overall_total = len(records)
        
        return {
            "hospital_id": hospital_id,
            "edition": "6th",
            "overall_compliance_rate": round(overall_compliant / overall_total * 100, 1) if overall_total > 0 else 0,
            "total_standards": overall_total,
            "compliant": overall_compliant,
            "non_compliant": sum(1 for r in records if r.maturity_level == MaturityLevel.AD_HOC),
            "partially_compliant": sum(1 for r in records if r.maturity_level == MaturityLevel.DEFINED),
            "under_review": sum(1 for r in records if r.maturity_level == MaturityLevel.NON_EXISTENT),
            "chapters": chapters,
            "readiness_level": (
                "Assessment Ready" if overall_total > 0 and overall_compliant / overall_total >= 0.90 else
                "Near Ready" if overall_total > 0 and overall_compliant / overall_total >= 0.75 else
                "In Progress" if overall_total > 0 and overall_compliant / overall_total >= 0.50 else
                "Early Stage" if overall_total > 0 else
                "Not Started"
            )
        }

    @staticmethod
    def update_compliance(
        db: Session,
        hospital_id: str,
        update: Any,
        compliance_status: ComplianceStatus,
        remediation_deadline: Optional[datetime]
    ) -> Dict[str, Any]:
        """Update or insert compliance assessments for NABH codes manually."""
        record = db.query(NABHObjective).filter(
            NABHObjective.hospital_id == hospital_id,
            NABHObjective.standard_code == update.standard_code
        ).first()
        
        if not record:
            record = NABHObjective(
                hospital_id=hospital_id,
                standard_code=update.standard_code,
            )
            db.add(record)
            
        # Map manual input status back to maturity levels
        if update.status == "compliant":
            record.maturity_level = MaturityLevel.IMPLEMENTED
        elif update.status == "partially_compliant":
            record.maturity_level = MaturityLevel.DEFINED
        elif update.status == "non_compliant":
            record.maturity_level = MaturityLevel.AD_HOC
        else:
            record.maturity_level = MaturityLevel.NON_EXISTENT
            
        record.monitoring_indicator_rate = update.current_score
        record.policy_doc_url = update.evidence_description
        record.remediation_plan = update.remediation_plan
        record.remediation_deadline = remediation_deadline
        record.last_assessed = datetime.utcnow()
        record.assessed_by = "Manual Officer Audit"
        
        # Populate category metadata
        for category, data in NABH_STANDARDS.items():
            if update.standard_code in data["chapters"]:
                record.standard_name = data["chapters"][update.standard_code]
                record.chapter_code = category
                break
                
        db.commit()
        
        return {
            "standard_code": update.standard_code,
            "status": update.status,
            "message": f"Compliance status updated for {update.standard_code}"
        }

    @staticmethod
    def get_gap_analysis(db: Session, hospital_id: str) -> Dict[str, Any]:
        """Compile a prioritized remediation list of compliance gaps and auto-create CAPA tasks."""
        inspector = InspectorAgent()
        gap_report = inspector.assess_current_state(db, hospital_id)
        
        # Trigger Consultant Agent to verify & create active database CAPA tasks
        consultant = ConsultantAgent()
        consultant.generate_remediation_action_plan(db, hospital_id, gap_report)
        
        # Fetch updated objectives list
        records = ComplianceRepository.get_all_for_hospital(db, hospital_id)
        
        gaps = []
        for record in records:
            if record.maturity_level < MaturityLevel.IMPLEMENTED:
                # Severity-to-priority scaling
                priority = "critical" if record.severity == SeverityLevel.CRITICAL else "high" if record.severity == SeverityLevel.MAJOR else "medium"
                
                gaps.append({
                    "standard_code": record.standard_code,
                    "standard_name": record.standard_name,
                    "chapter": record.chapter_code,
                    "current_status": "non_compliant" if record.maturity_level == MaturityLevel.AD_HOC else "partially_compliant" if record.maturity_level == MaturityLevel.DEFINED else "under_review",
                    "current_score": record.monitoring_indicator_rate or (record.maturity_level.value * 20.0),
                    "gap_percentage": round(100.0 - (record.monitoring_indicator_rate or (record.maturity_level.value * 20.0)), 1),
                    "remediation_plan": record.remediation_plan,
                    "remediation_deadline": record.remediation_deadline.isoformat() if record.remediation_deadline else None,
                    "owner": record.remediation_owner,
                    "priority": priority,
                })
                
        priority_order = {"critical": 0, "high": 1, "medium": 2}
        gaps.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        assessed_codes = set(r.standard_code for r in records)
        missing = []
        for category, data in NABH_STANDARDS.items():
            for code, name in data["chapters"].items():
                if code not in assessed_codes:
                    missing.append({"code": code, "name": name, "category": category})
                    
        return {
            "hospital_id": hospital_id,
            "total_gaps": len(gaps),
            "gaps": gaps,
            "missing_standards": missing,
            "missing_count": len(missing),
            "recommendation": "Consultant Agent: Prioritize critical safety gaps (Fire, BMW, Patient Consent) before scheduling mock audits."
        }
