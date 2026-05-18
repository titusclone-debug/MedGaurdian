from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.nabh.repository import ComplianceRepository
from app.models.database import ComplianceRecord, ComplianceStatus

NABH_STANDARDS = {
    "ACC": {
        "name": "Access, Assessment, and Continuity of Care",
        "chapters": {
            "AAC-1": "Patient Access Services",
            "AAC-2": "Assessment of Patients",
            "AAC-3": "Continuity and Coordination of Care",
            "AAC-4": "Discharge Planning",
            "AAC-5": "Transportation Services",
        }
    },
    "PC": {
        "name": "Patient Care",
        "chapters": {
            "PC-1": "Patient Rights and Education",
            "PC-2": "Clinical Care Plan",
            "PC-3": "Medication Management",
            "PC-4": "Surgical Care",
            "PC-5": "Anesthesia Care",
            "PC-6": "Blood and Blood Products",
            "PC-7": "Infection Prevention and Control",
            "PC-8": "Patient Safety Goals",
        }
    },
    "FMS": {
        "name": "Facility Management and Safety",
        "chapters": {
            "FMS-1": "Fire Safety",
            "FMS-2": "Biomedical Waste Management",
            "FMS-3": "Disaster Preparedness",
            "FMS-4": "Security Management",
            "FMS-5": "Equipment Management",
            "FMS-6": "Utility Management",
        }
    },
    "QMS": {
        "name": "Quality Management System",
        "chapters": {
            "QMS-1": "Quality Planning",
            "QMS-2": "Documentation and Records",
            "QMS-3": "Internal Audit",
            "QMS-4": "Management Review",
            "QMS-5": "Incident Reporting and Analysis",
        }
    },
    "IS": {
        "name": "Information Management System",
        "chapters": {
            "IS-1": "Health Information Management",
            "IS-2": "Medical Records",
            "IS-3": "Data Privacy and Security",
            "IS-4": "Clinical Decision Support",
        }
    },
    "HR": {
        "name": "Human Resource Management",
        "chapters": {
            "HR-1": "Staff Qualifications and Credentialing",
            "HR-2": "Orientation and Training",
            "HR-3": "Performance Management",
            "HR-4": "Staff Health and Safety",
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
        records = ComplianceRepository.get_all_for_hospital(db, hospital_id)
        
        # Filter in-memory to simplify repository layer
        filtered = []
        for r in records:
            if chapter and r.chapter != chapter:
                continue
            if status and r.status != status:
                continue
            filtered.append(r)
            
        chapters = {}
        for r in filtered:
            ch = r.chapter or "Uncategorized"
            if ch not in chapters:
                chapters[ch] = {"total": 0, "compliant": 0, "non_compliant": 0, "partial": 0, "under_review": 0, "score_sum": 0}
            chapters[ch]["total"] += 1
            chapters[ch]["score_sum"] += r.current_score
            
            if r.status == ComplianceStatus.COMPLIANT:
                chapters[ch]["compliant"] += 1
            elif r.status == ComplianceStatus.NON_COMPLIANT:
                chapters[ch]["non_compliant"] += 1
            elif r.status == ComplianceStatus.PARTIALLY_COMPLIANT:
                chapters[ch]["partial"] += 1
            elif r.status == ComplianceStatus.UNDER_REVIEW:
                chapters[ch]["under_review"] += 1
                
        for ch in chapters:
            total = chapters[ch]["total"]
            chapters[ch]["compliance_rate"] = round(chapters[ch]["compliant"] / total * 100, 1) if total > 0 else 0
            chapters[ch]["avg_score"] = round(chapters[ch]["score_sum"] / total, 2) if total > 0 else 0
            
        overall_compliant = sum(1 for r in filtered if r.status == ComplianceStatus.COMPLIANT)
        overall_total = len(filtered)
        
        return {
            "hospital_id": hospital_id,
            "edition": "6th",
            "overall_compliance_rate": round(overall_compliant / overall_total * 100, 1) if overall_total > 0 else 0,
            "total_standards": overall_total,
            "compliant": overall_compliant,
            "non_compliant": sum(1 for r in filtered if r.status == ComplianceStatus.NON_COMPLIANT),
            "partially_compliant": sum(1 for r in filtered if r.status == ComplianceStatus.PARTIALLY_COMPLIANT),
            "under_review": sum(1 for r in filtered if r.status == ComplianceStatus.UNDER_REVIEW),
            "chapters": chapters,
            "readiness_level": (
                "Assessment Ready" if overall_compliant / overall_total >= 0.90 else
                "Near Ready" if overall_compliant / overall_total >= 0.75 else
                "In Progress" if overall_compliant / overall_total >= 0.50 else
                "Early Stage" if overall_total > 0 else
                "Not Started"
            ) if overall_total > 0 else "Not Started"
        }

    @staticmethod
    def update_compliance(
        db: Session,
        hospital_id: str,
        update: Any,
        compliance_status: ComplianceStatus,
        remediation_deadline: Optional[datetime]
    ) -> Dict[str, Any]:
        """Update or insert compliance assessments for NABH codes."""
        record = ComplianceRepository.get_by_standard_code(db, hospital_id, update.standard_code)
        
        if not record:
            record = ComplianceRecord(
                hospital_id=hospital_id,
                standard_code=update.standard_code,
            )
            ComplianceRepository.create(db, record)
            
        record.status = compliance_status
        record.current_score = update.current_score
        record.evidence_description = update.evidence_description
        record.remediation_plan = update.remediation_plan
        record.remediation_deadline = remediation_deadline
        record.last_assessed = datetime.utcnow()
        
        # Populate category metadata
        for category, data in NABH_STANDARDS.items():
            if update.standard_code in data["chapters"]:
                record.standard_name = data["chapters"][update.standard_code]
                record.chapter = category
                break
                
        ComplianceRepository.save(db, record)
        
        return {
            "standard_code": update.standard_code,
            "status": update.status,
            "message": f"Compliance status updated for {update.standard_code}"
        }

    @staticmethod
    def get_gap_analysis(db: Session, hospital_id: str) -> Dict[str, Any]:
        """Compile a prioritized remediation list of compliance gaps."""
        records = ComplianceRepository.get_all_for_hospital(db, hospital_id)
        
        gaps = []
        for record in records:
            if record.status in [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.PARTIALLY_COMPLIANT]:
                gaps.append({
                    "standard_code": record.standard_code,
                    "standard_name": record.standard_name,
                    "chapter": record.chapter,
                    "current_status": record.status.value,
                    "current_score": record.current_score,
                    "gap_percentage": record.gap_percentage,
                    "remediation_plan": record.remediation_plan,
                    "remediation_deadline": record.remediation_deadline.isoformat() if record.remediation_deadline else None,
                    "owner": record.remediation_owner,
                    "priority": "critical" if record.gap_percentage > 50 else "high" if record.gap_percentage > 25 else "medium",
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
            "recommendation": "Focus on critical gaps first. Aim for 90% compliance before scheduling NABH assessment."
        }
