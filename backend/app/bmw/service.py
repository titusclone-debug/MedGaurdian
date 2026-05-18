from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.bmw.repository import BMWRepository
from app.models.database import BMWLog, BMWCategory, Hospital

BMW_CATEGORY_INFO = {
    "yellow": {
        "name": "Yellow Category",
        "description": "Human Anatomical Waste, Soiled Waste, Expired Medicines",
        "examples": ["Body parts", "Soiled cotton", "Expired medicines", "Chemical waste"],
        "treatment": "Incineration / Deep Burial",
        "containers": "Yellow bags",
    },
    "red": {
        "name": "Red Category",
        "description": "Contaminated Waste (Recyclable)",
        "examples": ["Tubing", "Bottles", "IV bags", "Catheters"],
        "treatment": "Autoclaving / Microwaving / Chemical Treatment",
        "containers": "Red bags",
    },
    "white": {
        "name": "White Category",
        "description": "Sharps Waste",
        "examples": ["Needles", "Scalpels", "Blades", "Glass"],
        "treatment": "Autoclaving / Shredding / Encapsulation",
        "containers": "White puncture-proof containers",
    },
    "blue": {
        "name": "Blue Category",
        "description": "Medicines, Cytotoxic Waste",
        "examples": ["Cytotoxic drugs", "Chemotherapy waste"],
        "treatment": "Incineration / Chemical Treatment",
        "containers": "Blue bags/containers",
    },
    "black": {
        "name": "Black Category",
        "description": "General Municipal Solid Waste",
        "examples": ["Non-contaminated packaging", "Food waste"],
        "treatment": "Disposal in secured landfill",
        "containers": "Black bags",
    },
}

class BMWService:
    @staticmethod
    def log_entry(db: Session, entry: Any, hospital_id: str, category: BMWCategory) -> Dict[str, Any]:
        """Record a bio-medical waste entry with full chain-of-custody tracking."""
        new_log = BMWLog(
            hospital_id=hospital_id,
            waste_date=datetime.utcnow(),
            category=category,
            weight_kg=entry.weight_kg,
            source_department=entry.source_department,
            source_ward=entry.source_ward,
            treatment_method=entry.treatment_method,
            treatment_operator=entry.treatment_operator,
            treatment_machine_id=entry.treatment_machine_id,
            treatment_temperature=entry.treatment_temperature,
            treatment_duration_min=entry.treatment_duration_min,
            disposal_agency=entry.disposal_agency,
            disposal_manifest_number=entry.disposal_manifest_number,
            disposal_vehicle_number=entry.disposal_vehicle_number,
            is_properly_segregated=True,
            is_properly_labeled=True,
            is_properly_stored=True,
        )
        saved_log = BMWRepository.create_entry(db, new_log)
        
        return {
            "log_id": saved_log.id,
            "category": category.value,
            "category_info": BMW_CATEGORY_INFO.get(category.value, {}),
            "weight_kg": saved_log.weight_kg,
            "status": "logged",
            "message": f"BMW entry logged: {saved_log.weight_kg}kg of {category.value} waste from {saved_log.source_department}"
        }

    @staticmethod
    def verify_entry(db: Session, log: BMWLog, verification: Any) -> Dict[str, Any]:
        """Verify compliance fields (segregation, labeling, storage) on a BMW entry."""
        log.is_properly_segregated = verification.is_properly_segregated
        log.is_properly_labeled = verification.is_properly_labeled
        log.is_properly_stored = verification.is_properly_stored
        log.compliance_notes = verification.compliance_notes
        
        BMWRepository.save(db, log)
        
        is_compliant = all([
            verification.is_properly_segregated,
            verification.is_properly_labeled,
            verification.is_properly_stored
        ])
        
        return {
            "log_id": log.id,
            "is_compliant": is_compliant,
            "status": "compliant" if is_compliant else "non_compliant",
            "message": "BMW entry verified" if is_compliant else "⚠️ BMW compliance issue detected"
        }

    @staticmethod
    def get_dashboard(db: Session, hospital_id: str, days: int) -> Dict[str, Any]:
        """Compile waste generation trends and category breakdowns for the dashboard."""
        start_date = datetime.utcnow() - timedelta(days=days)
        logs = BMWRepository.get_logs_since(db, hospital_id, start_date)
        
        # Category-wise breakdown
        category_stats = {}
        for cat in BMWCategory:
            cat_logs = [l for l in logs if l.category == cat]
            category_stats[cat.value] = {
                "total_entries": len(cat_logs),
                "total_weight_kg": sum(l.weight_kg for l in cat_logs),
                "properly_segregated": sum(1 for l in cat_logs if l.is_properly_segregated),
                "properly_labeled": sum(1 for l in cat_logs if l.is_properly_labeled),
                "properly_stored": sum(1 for l in cat_logs if l.is_properly_stored),
                "compliance_rate": (
                    sum(1 for l in cat_logs if l.is_properly_segregated and l.is_properly_labeled and l.is_properly_stored) / len(cat_logs) * 100
                ) if cat_logs else 100,
            }
        
        # Daily trends
        daily_trends = {}
        for log in logs:
            date_key = log.waste_date.strftime("%Y-%m-%d")
            if date_key not in daily_trends:
                daily_trends[date_key] = {"weight": 0, "entries": 0, "compliant": 0}
            daily_trends[date_key]["weight"] += log.weight_kg
            daily_trends[date_key]["entries"] += 1
            if log.is_properly_segregated and log.is_properly_labeled and log.is_properly_stored:
                daily_trends[date_key]["compliant"] += 1
        
        # Department-wise breakdown
        dept_stats = {}
        for log in logs:
            dept = log.source_department or "Unknown"
            if dept not in dept_stats:
                dept_stats[dept] = {"weight": 0, "entries": 0}
            dept_stats[dept]["weight"] += log.weight_kg
            dept_stats[dept]["entries"] += 1
        
        total_weight = sum(l.weight_kg for l in logs)
        total_compliant = sum(1 for l in logs if l.is_properly_segregated and l.is_properly_labeled and l.is_properly_stored)
        compliance_ratio = (total_compliant / len(logs)) if logs else 1

        return {
            "hospital_id": hospital_id,
            "period_days": days,
            "summary": {
                "total_entries": len(logs),
                "total_weight_kg": round(total_weight, 2),
                "avg_daily_weight_kg": round(total_weight / days, 2) if days > 0 else 0,
                "overall_compliance_rate": round(total_compliant / len(logs) * 100, 1) if logs else 100,
                "treatment_methods_used": list(set(l.treatment_method for l in logs if l.treatment_method)),
            },
            "category_breakdown": category_stats,
            "daily_trends": [
                {"date": k, **v, "compliance_rate": round(v["compliant"] / v["entries"] * 100, 1) if v["entries"] > 0 else 100}
                for k, v in sorted(daily_trends.items())
            ],
            "department_breakdown": [
                {"department": k, **v}
                for k, v in sorted(dept_stats.items(), key=lambda x: x[1]["weight"], reverse=True)
            ],
            "logs": [
                {
                    "id": l.id,
                    "date": l.waste_date.strftime("%Y-%m-%d"),
                    "category": l.category.value,
                    "weight": l.weight_kg,
                    "dept": l.source_department,
                    "ward": l.source_ward or "-",
                    "treatment": l.treatment_method or "-",
                    "compliant": (l.is_properly_segregated and l.is_properly_labeled and l.is_properly_stored)
                }
                for l in logs
            ],
            "compliance_status": "no_data" if not logs else "audit_ready" if compliance_ratio >= 0.95 else "needs_attention" if compliance_ratio >= 0.80 else "non_compliant"
        }

    @staticmethod
    def generate_audit_report(db: Session, hospital_id: str, month: int, year: int) -> Dict[str, Any]:
        """Compile a monthly BMW SPCB regulatory audit report."""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # We query the repository using get_logs_since between start and end date
        # (For simpler repository reuse we filter dates, or let DB handle it)
        logs = db.query(BMWLog).filter(
            BMWLog.hospital_id == hospital_id,
            BMWLog.waste_date >= start_date,
            BMWLog.waste_date < end_date
        ).all()
        
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        
        report = {
            "report_type": "BMW Monthly Compliance Report",
            "period": f"{start_date.strftime('%B %Y')}",
            "hospital": {
                "name": hospital.name if hospital else "Unknown",
                "address": hospital.address if hospital else "",
                "bed_count": hospital.bed_count if hospital else 0,
            },
            "summary": {
                "total_waste_kg": round(sum(l.weight_kg for l in logs), 2),
                "total_entries": len(logs),
                "categories": {},
                "treatment_summary": {},
            },
            "category_wise": {},
            "daily_log": [],
            "compliance_declaration": "I hereby certify that the above information is true and correct to the best of my knowledge and the bio-medical waste has been handled and disposed of in accordance with the Bio-Medical Waste Management Rules, 2016.",
        }
        
        for cat in BMWCategory:
            cat_logs = [l for l in logs if l.category == cat]
            report["category_wise"][cat.value] = {
                "total_kg": round(sum(l.weight_kg for l in cat_logs), 2),
                "entries": len(cat_logs),
                "treatment_methods": list(set(l.treatment_method for l in cat_logs if l.treatment_method)),
            }
        
        treatment_methods = {}
        for log in logs:
            method = log.treatment_method or "pending"
            if method not in treatment_methods:
                treatment_methods[method] = {"kg": 0, "entries": 0}
            treatment_methods[method]["kg"] += log.weight_kg
            treatment_methods[method]["entries"] += 1
            
        report["treatment_summary"] = {k: {"total_kg": round(v["kg"], 2), "entries": v["entries"]} for k, v in treatment_methods.items()}
        
        return report
