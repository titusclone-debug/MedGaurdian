from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.models.database import (
    HospitalAccreditationProfile, HospitalNABHRequirement,
    NABHMeasurableElement, NABHApplicabilityRule,
    ApplicabilityDefault, MaturityLevel, EvidenceStatus, ComplianceStatus,
    NABHEdition, NABHChapter, NABHStandard, NABHObjectiveElement
)

PROFILE_WHITELIST = {
    "bed_count",
    "hospital_type",
    "services_offered",
    "specialty_services",
    "has_icu",
    "has_operation_theatre",
    "has_emergency",
    "has_pharmacy",
    "has_lab",
    "has_blood_bank",
    "has_ambulance",
    "has_maternity",
    "has_dialysis",
    "has_imaging",
    "has_cssd",
    "scope_exclusions",
    "annual_patient_volume",
    "avg_monthly_opd"
}

def evaluate_rule_json(profile: Optional[HospitalAccreditationProfile], rule_json: dict) -> dict:
    """
    Evaluates a single applicability rule JSON against the hospital profile.
    Returns a dictionary of:
      { "matched": bool, "status_override": Optional[ApplicabilityDefault], "reason": Optional[str] }
    """
    if profile is None:
        return {
            "matched": False,
            "status_override": ApplicabilityDefault.MANUAL_REVIEW,
            "reason": "Hospital accreditation profile is missing."
        }
        
    field = rule_json.get("field")
    operator = rule_json.get("operator")
    value = rule_json.get("value")
    
    if field not in PROFILE_WHITELIST:
        return {
            "matched": False,
            "status_override": ApplicabilityDefault.MANUAL_REVIEW,
            "reason": f"Unknown or non-whitelisted profile field: '{field}'."
        }
        
    if not hasattr(profile, field):
        return {
            "matched": False,
            "status_override": ApplicabilityDefault.MANUAL_REVIEW,
            "reason": f"Profile field '{field}' is missing or incomplete on database model."
        }
        
    profile_val = getattr(profile, field)
    if profile_val is None:
        return {
            "matched": False,
            "status_override": ApplicabilityDefault.MANUAL_REVIEW,
            "reason": f"Profile field '{field}' is missing or incomplete."
        }
        
    # Standard comparisons
    if operator == "eq":
        return {"matched": profile_val == value, "status_override": None, "reason": None}
    elif operator == "neq":
        return {"matched": profile_val != value, "status_override": None, "reason": None}
        
    # Operator 'in' logic
    elif operator == "in":
        # Scalar in list: e.g. profile_val = "general", value = ["general", "eye"]
        if not isinstance(profile_val, list) and isinstance(value, list):
            return {"matched": profile_val in value, "status_override": None, "reason": None}
        # List contains scalar: e.g. profile_val = ["icu", "ot"], value = "icu"
        elif isinstance(profile_val, list) and not isinstance(value, list):
            return {"matched": value in profile_val, "status_override": None, "reason": None}
        # List intersects list: e.g. profile_val = ["icu", "ot"], value = ["icu", "maternity"]
        elif isinstance(profile_val, list) and isinstance(value, list):
            matched = any(item in value for item in profile_val)
            return {"matched": matched, "status_override": None, "reason": None}
        else:
            # Fallback if both are scalars, or unexpected structure
            return {"matched": profile_val == value, "status_override": None, "reason": None}
            
    # Numeric operators: gt, gte, lt, lte
    elif operator in {"gt", "gte", "lt", "lte"}:
        if not isinstance(profile_val, (int, float)) or not isinstance(value, (int, float)):
            return {
                "matched": False,
                "status_override": ApplicabilityDefault.MANUAL_REVIEW,
                "reason": f"Non-numeric values in numeric comparison for field '{field}'."
            }
        
        if operator == "gt":
            matched = profile_val > value
        elif operator == "gte":
            matched = profile_val >= value
        elif operator == "lt":
            matched = profile_val < value
        elif operator == "lte":
            matched = profile_val <= value
            
        return {"matched": matched, "status_override": None, "reason": None}
        
    # Unknown operator
    return {
        "matched": False,
        "status_override": ApplicabilityDefault.MANUAL_REVIEW,
        "reason": f"Unsupported rule operator: '{operator}'."
    }

class ApplicabilityEngine:
    @staticmethod
    def compute_applicability(db: Session, hospital_id: str) -> dict:
        """
        Computes the applicability statuses of all active 6.0 NABH requirements
        for the specified hospital, updates the DB state, and returns a summary.
        """
        # 1. Fetch HospitalAccreditationProfile
        profile = db.query(HospitalAccreditationProfile).filter(
            HospitalAccreditationProfile.hospital_id == hospital_id,
            HospitalAccreditationProfile.retired_at.is_(None)
        ).first()
        
        # 2. Get active edition (6.0)
        edition = db.query(NABHEdition).filter(
            NABHEdition.version == "6.0",
            NABHEdition.retired_at.is_(None)
        ).first()
        
        if not edition:
            return {
                "total_requirements_evaluated": 0,
                "status_counts": {
                    "applicable": 0,
                    "conditional": 0,
                    "not_applicable": 0,
                    "manual_review": 0
                },
                "created_rows_count": 0,
                "updated_rows_count": 0,
                "unchanged_rows_count": 0,
                "results": []
            }
            
        # 3. Load all active 6th Edition measurable elements
        official_chapter_codes = ["AAC", "COP", "MOM", "PRE", "IPC", "PSQ", "ROM", "FMS", "HRM", "IMS"]
        elements = db.query(NABHMeasurableElement).join(NABHObjectiveElement).join(NABHStandard).join(NABHChapter).filter(
            NABHChapter.edition_id == edition.id,
            NABHChapter.canonical_code.in_(official_chapter_codes),
            NABHChapter.retired_at.is_(None),
            NABHStandard.retired_at.is_(None),
            NABHObjectiveElement.retired_at.is_(None),
            NABHMeasurableElement.retired_at.is_(None)
        ).all()
        
        total_evaluated = len(elements)
        created_count = 0
        updated_count = 0
        unchanged_count = 0
        status_counts = {
            "applicable": 0,
            "conditional": 0,
            "not_applicable": 0,
            "manual_review": 0
        }
        
        results = []
        
        # Mapping precedence order to resolve multiple rules
        # Precedence: not_applicable > manual_review > conditional > applicable
        PRECEDENCE_MAP = {
            ApplicabilityDefault.NOT_APPLICABLE: 0,
            ApplicabilityDefault.MANUAL_REVIEW: 1,
            ApplicabilityDefault.CONDITIONAL: 2,
            ApplicabilityDefault.APPLICABLE: 3
        }
        
        for element in elements:
            rules = db.query(NABHApplicabilityRule).filter(
                NABHApplicabilityRule.measurable_element_id == element.id,
                NABHApplicabilityRule.retired_at.is_(None)
            ).all()
            
            winning_status = None
            winning_reason = None
            
            def update_status(new_status: ApplicabilityDefault, new_reason: str):
                nonlocal winning_status, winning_reason
                if winning_status is None:
                    winning_status = new_status
                    winning_reason = new_reason
                else:
                    if PRECEDENCE_MAP[new_status] < PRECEDENCE_MAP[winning_status]:
                        winning_status = new_status
                        winning_reason = new_reason
            
            if profile is None:
                winning_status = ApplicabilityDefault.MANUAL_REVIEW
                winning_reason = "Hospital accreditation profile is missing."
            elif not rules:
                winning_status = element.applicability_default
                winning_reason = "Default applicability for this requirement."
            else:
                for rule in rules:
                    eval_res = evaluate_rule_json(profile, rule.rule_json)
                    
                    if eval_res.get("status_override") is not None:
                        update_status(eval_res["status_override"], eval_res["reason"])
                    else:
                        if eval_res["matched"]:
                            try:
                                status = ApplicabilityDefault(rule.action_if_true)
                            except ValueError:
                                status = ApplicabilityDefault.MANUAL_REVIEW
                            reason = rule.description or f"Matched rule: {rule.rule_code}"
                            update_status(status, reason)
                        else:
                            try:
                                status = ApplicabilityDefault(rule.action_if_false)
                            except ValueError:
                                status = ApplicabilityDefault.MANUAL_REVIEW
                            rule_context = rule.description or f"Rule {rule.rule_code}"
                            reason = f"{rule_context} Rule did not match; applying {status.value}."
                            update_status(status, reason)
            
            if winning_status is None:
                winning_status = ApplicabilityDefault.APPLICABLE
                winning_reason = "Default applicability for this requirement."
                
            status_counts[winning_status.value] += 1
            
            # Query existing requirement progress record
            req_state = db.query(HospitalNABHRequirement).filter(
                HospitalNABHRequirement.hospital_id == hospital_id,
                HospitalNABHRequirement.requirement_id == element.id
            ).first()
            
            if not req_state:
                req_state = HospitalNABHRequirement(
                    hospital_id=hospital_id,
                    requirement_id=element.id,
                    applicability_status=winning_status,
                    applicability_reason=winning_reason,
                    maturity_level=MaturityLevel.NON_EXISTENT,
                    evidence_status=EvidenceStatus.MISSING,
                    readiness_status=ComplianceStatus.UNDER_REVIEW
                )
                db.add(req_state)
                created_count += 1
            else:
                # Update only applicability attributes, preserving user compliance progress
                if (req_state.applicability_status != winning_status or
                        req_state.applicability_reason != winning_reason):
                    req_state.applicability_status = winning_status
                    req_state.applicability_reason = winning_reason
                    updated_count += 1
                else:
                    unchanged_count += 1
                    
            results.append({
                "requirement_code": element.canonical_code,
                "applicability_status": winning_status.value,
                "applicability_reason": winning_reason
            })
            
        if profile:
            profile.last_scoped_at = datetime.utcnow()
            db.add(profile)
            
        db.flush()
        
        return {
            "total_requirements_evaluated": total_evaluated,
            "status_counts": status_counts,
            "created_rows_count": created_count,
            "updated_rows_count": updated_count,
            "unchanged_rows_count": unchanged_count,
            "results": results
        }
