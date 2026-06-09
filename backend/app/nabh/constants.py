SUPPORTED_RULE_OPERATORS = {"eq", "neq", "in", "gt", "gte", "lt", "lte"}

VALID_SEVERITY_LEVELS = {"minor", "major", "critical"}

VALID_APPLICABILITY_DEFAULTS = {"applicable", "conditional", "not_applicable", "manual_review"}

VALID_EVIDENCE_TYPES = {
    "sop", "register", "training_record", "license", "audit_log", 
    "photo", "committee_minutes", "telemetry", "capa"
}

VALID_EVIDENCE_FREQUENCIES = {
    "one_time", "daily", "weekly", "monthly", "quarterly", 
    "yearly", "per_event", "continuous", "not_applicable"
}

