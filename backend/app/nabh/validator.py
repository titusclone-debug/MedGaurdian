import os
import json
import re
from datetime import datetime
from typing import Dict, List, Set, Any
from app.nabh.constants import (
    SUPPORTED_RULE_OPERATORS,
    VALID_SEVERITY_LEVELS,
    VALID_APPLICABILITY_DEFAULTS,
    VALID_EVIDENCE_TYPES,
    VALID_EVIDENCE_FREQUENCIES
)

class ValidationError(Exception):
    """Custom exception raised when JSON seed validation fails."""
    pass

def validate_ontology_seeds(
    data_dir: str, 
    target_version: str = "6.0", 
    allow_missing_citations: bool = False,
    allow_bare_citation_array: bool = False,
    is_fixture: bool = False
) -> Dict[str, Any]:
    """
    Validates all ontology seed files under the data_dir directory.
    Raises ValidationError if any check fails.
    Returns loaded data dictionary on success.

    Parameters
    ----------
    allow_missing_citations : bool
        If True, the nabh_6th_citations.json file is not required.
        Use only in test/draft environments. Never set True in production.
    allow_bare_citation_array : bool
        If True, a bare JSON array is accepted as the citations file format.
        Production seeds must use the envelope format
        {"_meta": {...}, "citations": [...]}.
        Use only in test/draft environments. Never set True in production.
    """
    chapters_path = os.path.join(data_dir, "nabh_6th_chapters.json")
    requirements_path = os.path.join(data_dir, "nabh_6th_requirements.json")
    evidence_path = os.path.join(data_dir, "nabh_6th_evidence_requirements.json")
    rules_path = os.path.join(data_dir, "nabh_6th_applicability_rules.json")
    citations_path = os.path.join(data_dir, "nabh_6th_citations.json")

    # Required files checks
    for path in [chapters_path, requirements_path, evidence_path, rules_path]:
        if not os.path.exists(path):
            raise ValidationError(f"Missing required seed file: {os.path.basename(path)}")

    # Citations file check (conditional)
    citations_exists = os.path.exists(citations_path)
    if not citations_exists and not allow_missing_citations:
        raise ValidationError(f"Missing required seed file: {os.path.basename(citations_path)}")

    # 1. Load and Validate Chapters
    try:
        with open(chapters_path, "r", encoding="utf-8") as f:
            chapters = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in chapters file: {e}")

    if not isinstance(chapters, list):
        raise ValidationError("Chapters seed must be a JSON array.")

    chapter_codes: Set[str] = set()
    chapter_metadata: Dict[str, Dict[str, Any]] = {}
    
    required_chapter_keys = {
        "code", "title", "description", "display_order", 
        "official_standards_count", "official_measurable_elements_count", "is_fully_seeded"
    }

    for idx, chap in enumerate(chapters):
        missing = required_chapter_keys - chap.keys()
        if missing:
            raise ValidationError(f"Chapter at index {idx} is missing keys: {missing}")

        code = chap["code"]
        if not isinstance(code, str) or not code.strip():
            raise ValidationError(f"Chapter at index {idx} has an invalid code: {code}")
        
        if " " in code:
            raise ValidationError(f"Chapter code '{code}' must not contain spaces.")

        if code in chapter_codes:
            raise ValidationError(f"Duplicate chapter code '{code}' found in chapters seed.")
        
        chapter_codes.add(code)
        chapter_metadata[code] = chap

    # 2. Load and Validate Requirements (Hierarchy)
    try:
        with open(requirements_path, "r", encoding="utf-8") as f:
            requirements = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in requirements file: {e}")

    if not isinstance(requirements, list):
        raise ValidationError("Requirements seed must be a JSON array.")

    seeded_standards_per_chapter: Dict[str, int] = {code: 0 for code in chapter_codes}
    seeded_measurable_elements_per_chapter: Dict[str, int] = {code: 0 for code in chapter_codes}
    defined_measurable_codes: Set[str] = set()
    
    required_req_keys = {"chapter_code", "edition_version", "standards"}
    required_standard_keys = {"code", "title", "description", "display_order", "objective_elements"}
    required_obj_keys = {"code", "description", "severity", "display_order", "measurable_elements"}
    required_meas_keys = {
        "code", "description", "applicability_default", "scoring_weight", 
        "risk_weight", "default_owner_role", "display_order"
    }

    for idx, chap_req in enumerate(requirements):
        missing = required_req_keys - chap_req.keys()
        if missing:
            raise ValidationError(f"Requirement group at index {idx} is missing keys: {missing}")

        chap_code = chap_req["chapter_code"]
        if chap_code not in chapter_codes:
            raise ValidationError(f"Requirement group at index {idx} references unknown chapter: {chap_code}")

        version = chap_req["edition_version"]
        if version != target_version:
            raise ValidationError(f"Edition version mismatch in requirement chapter '{chap_code}'. Expected '{target_version}', got '{version}'.")

        standards = chap_req["standards"]
        if not isinstance(standards, list):
            raise ValidationError(f"Standards for chapter '{chap_code}' must be a list.")

        standard_codes: Set[str] = set()
        for s_idx, std in enumerate(standards):
            s_missing = required_standard_keys - std.keys()
            if s_missing:
                raise ValidationError(f"Standard at index {s_idx} in chapter '{chap_code}' is missing keys: {s_missing}")

            std_code = std["code"]
            if is_fixture:
                if not re.match(rf"^{chap_code}-\d+$", std_code):
                    raise ValidationError(f"Standard code '{std_code}' in chapter '{chap_code}' must be format '{chap_code}-<number>'.")
            else:
                if not re.match(rf"^{chap_code}\.\d+$", std_code):
                    raise ValidationError(f"Standard code '{std_code}' in chapter '{chap_code}' must be format '{chap_code}.<number>'.")

            if std_code in standard_codes:
                raise ValidationError(f"Duplicate standard code '{std_code}' in chapter '{chap_code}'.")
            
            if not is_fixture and "Synthetic" in std.get("title", ""):
                raise ValidationError(f"Standard '{std_code}' contains 'Synthetic' title which is forbidden in canonical seed.")

            standard_codes.add(std_code)
            seeded_standards_per_chapter[chap_code] += 1

            obj_elements = std["objective_elements"]
            if not isinstance(obj_elements, list):
                raise ValidationError(f"Objective elements for standard '{std_code}' must be a list.")

            obj_codes: Set[str] = set()
            for o_idx, obj in enumerate(obj_elements):
                o_missing = required_obj_keys - obj.keys()
                if o_missing:
                    raise ValidationError(f"Objective element at index {o_idx} under standard '{std_code}' is missing keys: {o_missing}")

                obj_code = obj["code"]
                if is_fixture:
                    if not re.match(rf"^{std_code}\.[a-z]+$", obj_code):
                        raise ValidationError(f"Objective element code '{obj_code}' under standard '{std_code}' must be format '{std_code}.<letter>'.")
                else:
                    if not re.match(rf"^{std_code}\.[a-z]+$", obj_code):
                        raise ValidationError(f"Objective element code '{obj_code}' under standard '{std_code}' must be format '{std_code}.<letter>'.")
                    if not re.match(rf"^{chap_code}\.\d+\.[a-z]+$", obj_code):
                        raise ValidationError(f"Official Objective Element code '{obj_code}' must follow format 'CHAP.num.letter' (e.g., AAC.1.a).")

                if obj_code in obj_codes:
                    raise ValidationError(f"Duplicate objective element code '{obj_code}' under standard '{std_code}'.")
                obj_codes.add(obj_code)

                if not is_fixture:
                    # Enforce official objective element code format (e.g. AAC.1.a)
                    if not re.match(rf"^{chap_code}\.\d+\.[a-z]+$", obj_code):
                        raise ValidationError(f"Official Objective Element code '{obj_code}' must follow format 'CHAP.num.letter' (e.g., AAC.1.a).")

                severity = obj["severity"]
                if severity not in VALID_SEVERITY_LEVELS:
                    raise ValidationError(f"Invalid severity level '{severity}' in objective element '{obj_code}'.")

                if not is_fixture:
                    if "measurable_elements" in obj:
                        raise ValidationError(f"Objective element '{obj_code}' contains 'measurable_elements' which are legacy synthetic constructs and forbidden in canonical schema.")
                    # In canonical schema, the objective element IS the requirement
                    defined_measurable_codes.add(obj_code)
                    seeded_measurable_elements_per_chapter[chap_code] += 1
                    continue

                meas_elements = obj.get("measurable_elements", [])
                if not isinstance(meas_elements, list):
                    raise ValidationError(f"Measurable elements for objective element '{obj_code}' must be a list.")

                meas_codes: Set[str] = set()
                for m_idx, meas in enumerate(meas_elements):
                    m_missing = required_meas_keys - meas.keys()
                    if m_missing:
                        raise ValidationError(f"Measurable element at index {m_idx} under objective element '{obj_code}' is missing keys: {m_missing}")

                    meas_code = meas["code"]
                    if not re.match(rf"^{obj_code}\.\d+$", meas_code):
                        raise ValidationError(f"Measurable element code '{meas_code}' under objective element '{obj_code}' must be format '{obj_code}.<number>'.")

                    if not is_fixture:
                        if "Synthetic" in meas.get("description", ""):
                            raise ValidationError(f"Measurable element '{meas_code}' contains 'Synthetic' description which is forbidden.")
                        if re.match(rf"^{chap_code}-\d+\.[a-z]+\.\d+$", meas_code):
                            raise ValidationError(f"Measurable element code '{meas_code}' uses legacy hyphenated format which is forbidden in canonical seed.")

                    if meas_code in meas_codes:
                        raise ValidationError(f"Duplicate measurable element code '{meas_code}' under objective element '{obj_code}'.")
                    meas_codes.add(meas_code)

                    app_def = meas["applicability_default"]
                    if app_def not in VALID_APPLICABILITY_DEFAULTS:
                        raise ValidationError(f"Invalid applicability default '{app_def}' in measurable element '{meas_code}'.")

                    if meas_code in defined_measurable_codes:
                        raise ValidationError(f"Duplicate global measurable element code '{meas_code}'.")
                    defined_measurable_codes.add(meas_code)
                    seeded_measurable_elements_per_chapter[chap_code] += 1

    # 3. Validate Chapter Coverage Sanity
    for code, chap in chapter_metadata.items():
        seeded_std_count = seeded_standards_per_chapter[code]
        seeded_meas_count = seeded_measurable_elements_per_chapter[code]
        
        official_std = chap["official_standards_count"]
        official_meas = chap["official_measurable_elements_count"]
        is_fully = chap["is_fully_seeded"]

        if official_std is not None and seeded_std_count > official_std:
            raise ValidationError(f"Chapter '{code}' seeded standard count ({seeded_std_count}) exceeds official standards count ({official_std}).")
        
        if official_meas is not None and seeded_meas_count > official_meas:
            raise ValidationError(f"Chapter '{code}' seeded measurable element count ({seeded_meas_count}) exceeds official measurable elements count ({official_meas}).")

        if is_fully:
            if official_std is None or official_meas is None:
                raise ValidationError(f"Chapter '{code}' is marked as 'is_fully_seeded=true' but official counts are not specified.")
            if seeded_std_count != official_std:
                raise ValidationError(f"Chapter '{code}' is marked as fully seeded, but seeded standard count ({seeded_std_count}) does not match official count ({official_std}).")
            if seeded_meas_count != official_meas:
                raise ValidationError(f"Chapter '{code}' is marked as fully seeded, but seeded measurable element count ({seeded_meas_count}) does not match official count ({official_meas}).")

    # 4. Load and Validate Evidence Requirements
    try:
        with open(evidence_path, "r", encoding="utf-8") as f:
            evidence_requirements = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in evidence file: {e}")

    if not isinstance(evidence_requirements, list):
        raise ValidationError("Evidence requirements seed must be a JSON array.")

    required_evidence_keys = {
        "measurable_element_code", "edition_version", "evidence_code", 
        "evidence_type", "description", "is_mandatory"
    }

    evidence_codes_per_element: Dict[str, Set[str]] = {}

    for idx, ev in enumerate(evidence_requirements):
        missing = required_evidence_keys - ev.keys()
        if missing:
            raise ValidationError(f"Evidence requirement at index {idx} is missing keys: {missing}")

        ev_version = ev["edition_version"]
        if ev_version != target_version:
            raise ValidationError(f"Edition version mismatch in evidence requirement code '{ev['evidence_code']}'. Expected '{target_version}', got '{ev_version}'.")

        meas_code = ev["measurable_element_code"]
        if meas_code not in defined_measurable_codes:
            raise ValidationError(f"Evidence requirement at index {idx} references unknown measurable element code: {meas_code}")

        ev_code = ev["evidence_code"]
        if not isinstance(ev_code, str) or not ev_code.strip():
            raise ValidationError(f"Evidence requirement at index {idx} has invalid evidence_code.")

        if meas_code not in evidence_codes_per_element:
            evidence_codes_per_element[meas_code] = set()
        
        if ev_code in evidence_codes_per_element[meas_code]:
            raise ValidationError(f"Duplicate evidence code '{ev_code}' for measurable element '{meas_code}'.")
        
        if not is_fixture and "Synthetic" in ev.get("description", ""):
            raise ValidationError(f"Evidence '{ev_code}' contains 'Synthetic' description which is forbidden in canonical seed.")
            
        evidence_codes_per_element[meas_code].add(ev_code)

        ev_type = ev["evidence_type"]
        if ev_type not in VALID_EVIDENCE_TYPES:
            raise ValidationError(f"Invalid evidence type '{ev_type}' in evidence requirement '{ev_code}'.")

        # Frequency validation: if present, must be one of VALID_EVIDENCE_FREQUENCIES
        if "evidence_frequency" in ev and ev["evidence_frequency"] is not None:
            freq = ev["evidence_frequency"]
            if freq not in VALID_EVIDENCE_FREQUENCIES:
                raise ValidationError(f"Invalid evidence frequency '{freq}' in evidence requirement '{ev_code}'.")

        # Minimum lookback days validation: if present, must be >= 0
        if "minimum_lookback_days" in ev and ev["minimum_lookback_days"] is not None:
            days = ev["minimum_lookback_days"]
            if not isinstance(days, int) or days < 0:
                raise ValidationError(f"Invalid minimum_lookback_days '{days}' in evidence requirement '{ev_code}': must be a non-negative integer.")

        # Default owner role validation: if present, must be a string and not empty
        if "default_owner_role" in ev and ev["default_owner_role"] is not None:
            role = ev["default_owner_role"]
            if not isinstance(role, str) or not role.strip():
                raise ValidationError(f"Invalid default_owner_role '{role}' in evidence requirement '{ev_code}': must be a non-empty string.")

    # 5. Load and Validate Applicability Rules
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            applicability_rules = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in applicability rules file: {e}")

    if not isinstance(applicability_rules, list):
        raise ValidationError("Applicability rules seed must be a JSON array.")

    required_rule_keys = {
        "measurable_element_code", "edition_version", "rule_code", 
        "rule_json", "description", "action_if_true", "action_if_false"
    }

    rules_per_element: Dict[str, Set[str]] = {}

    for idx, rule in enumerate(applicability_rules):
        missing = required_rule_keys - rule.keys()
        if missing:
            raise ValidationError(f"Applicability rule at index {idx} is missing keys: {missing}")

        rule_version = rule["edition_version"]
        if rule_version != target_version:
            raise ValidationError(f"Edition version mismatch in applicability rule code '{rule['rule_code']}'. Expected '{target_version}', got '{rule_version}'.")

        meas_code = rule["measurable_element_code"]
        if meas_code not in defined_measurable_codes:
            raise ValidationError(f"Applicability rule at index {idx} references unknown measurable element code: {meas_code}")

        rule_code = rule["rule_code"]
        if not isinstance(rule_code, str) or not rule_code.strip():
            raise ValidationError(f"Applicability rule at index {idx} has invalid rule_code.")

        if meas_code not in rules_per_element:
            rules_per_element[meas_code] = set()

        if rule_code in rules_per_element[meas_code]:
            raise ValidationError(f"Duplicate rule code '{rule_code}' for measurable element '{meas_code}'.")
        rules_per_element[meas_code].add(rule_code)

        action_true = rule["action_if_true"]
        action_false = rule["action_if_false"]
        for act in [action_true, action_false]:
            if act not in VALID_APPLICABILITY_DEFAULTS:
                raise ValidationError(f"Invalid rule action '{act}' in rule '{rule_code}'.")

        rule_json = rule["rule_json"]
        if not isinstance(rule_json, dict):
            raise ValidationError(f"Rule JSON for rule '{rule_code}' must be a dictionary.")

        dsl_keys = {"field", "operator", "value"}
        r_missing = dsl_keys - rule_json.keys()
        if r_missing:
            raise ValidationError(f"Rule JSON for rule '{rule_code}' is missing DSL keys: {r_missing}")

        field = rule_json["field"]
        if not isinstance(field, str) or not field.strip():
            raise ValidationError(f"Invalid rule field in rule '{rule_code}': must be a non-empty string.")

        operator = rule_json["operator"]
        if operator not in SUPPORTED_RULE_OPERATORS:
            raise ValidationError(f"Unsupported rule operator '{operator}' in rule '{rule_code}'. Supported: {SUPPORTED_RULE_OPERATORS}")

        value = rule_json["value"]
        if operator == "in" and not isinstance(value, list):
            raise ValidationError(f"Operator 'in' in rule '{rule_code}' requires a list value.")

    # 6. Load and Validate Citations (Conditional)
    citations = []
    citation_meta: dict = {}
    if citations_exists:
        try:
            with open(citations_path, "r", encoding="utf-8") as f:
                raw_citations_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in citations file: {e}")

        # Accept the envelope format (production) or, if explicitly permitted,
        # a bare array (tests / draft fixtures only).
        #
        # Envelope format (required in production):
        #   {"_meta": {"citation_complete": false, ...}, "citations": [...]}
        #
        # Bare array (test/draft only, requires allow_bare_citation_array=True):
        #   [{...}, {...}]
        if isinstance(raw_citations_data, list):
            if not allow_bare_citation_array:
                raise ValidationError(
                    "Citations seed file must use the envelope format "
                    '{"_meta": {...}, "citations": [...]}. '
                    "Bare JSON arrays are only accepted in test/draft mode "
                    "(pass allow_bare_citation_array=True)."
                )
            citations = raw_citations_data
        elif isinstance(raw_citations_data, dict):
            citation_meta = raw_citations_data.get("_meta", {})
            if citation_meta:
                # _meta must not be silently malformed: citation_complete is
                # required and must be an actual JSON boolean (true/false),
                # not a string, null, or integer.
                if "citation_complete" not in citation_meta:
                    raise ValidationError(
                        "Citation _meta block exists but is missing the required "
                        "'citation_complete' key (boolean)."
                    )
                citation_complete_val = citation_meta["citation_complete"]
                if not isinstance(citation_complete_val, bool):
                    raise ValidationError(
                        f"Citation _meta.citation_complete must be a JSON boolean "
                        f"(true or false), got "
                        f"{type(citation_complete_val).__name__}: "
                        f"{citation_complete_val!r}."
                    )
            citations = raw_citations_data.get("citations", [])
            if not isinstance(citations, list):
                raise ValidationError(
                    "Citations seed envelope 'citations' key must be a JSON array."
                )
        else:
            raise ValidationError(
                "Citations seed must be a JSON object envelope "
                '{"_meta": {...}, "citations": [...]}. '
                "Bare arrays require allow_bare_citation_array=True."
            )

        required_citation_keys = {
            "measurable_element_code", "edition_version", "document_title",
            "document_publisher", "document_version", "section", "page_number",
            "clause_text_summary", "effective_date", "file_path", "url"
        }

        for idx, cit in enumerate(citations):
            missing = required_citation_keys - cit.keys()
            if missing:
                raise ValidationError(f"Citation at index {idx} is missing keys: {missing}")

            cit_version = cit["edition_version"]
            if cit_version != target_version:
                raise ValidationError(f"Edition version mismatch in citation for '{cit['measurable_element_code']}'. Expected '{target_version}', got '{cit_version}'.")

            meas_code = cit["measurable_element_code"]
            if meas_code not in defined_measurable_codes:
                raise ValidationError(f"Citation at index {idx} references unknown measurable element code: {meas_code}")

            # Validate date string YYYY-MM-DD
            eff_date_str = cit["effective_date"]
            if not isinstance(eff_date_str, str) or not eff_date_str.strip():
                raise ValidationError(f"Citation at index {idx} has invalid effective_date.")
                
            if not is_fixture and "Synthetic" in cit.get("clause_text_summary", ""):
                raise ValidationError(f"Citation for '{meas_code}' contains 'Synthetic' text which is forbidden in canonical seed.")
            
            try:
                datetime.strptime(eff_date_str, "%Y-%m-%d")
            except ValueError:
                raise ValidationError(f"Invalid date format in citation '{cit['document_title']}'. Expected YYYY-MM-DD, got '{eff_date_str}'.")

            # Validate that at least one of file_path or url is provided as non-empty string
            file_path = cit["file_path"]
            url = cit["url"]
            file_path_valid = isinstance(file_path, str) and bool(file_path.strip())
            url_valid = isinstance(url, str) and bool(url.strip())
            if not file_path_valid and not url_valid:
                raise ValidationError(f"Citation at index {idx} for '{meas_code}' must have at least one non-empty string file_path or url.")

    # 7. Cross-Ontology Validation
    # Enforce that every seeded measurable element has at least one evidence requirement,
    # and at least one must be is_mandatory = True
    for code in defined_measurable_codes:
        if code not in evidence_codes_per_element or len(evidence_codes_per_element[code]) == 0:
            raise ValidationError(f"Measurable element '{code}' does not have any evidence requirements.")
        
        # Check if there is at least one mandatory evidence requirement
        ev_items = [ev for ev in evidence_requirements if ev["measurable_element_code"] == code]
        has_mandatory = any(ev.get("is_mandatory") is True for ev in ev_items)
        if not has_mandatory:
            raise ValidationError(f"Measurable element '{code}' does not have any mandatory evidence requirement.")

    # Enforce that in production (allow_missing_citations is False), each seeded measurable element
    # has at least one citation.
    if not allow_missing_citations:
        cited_element_codes = {cit["measurable_element_code"] for cit in citations}
        for code in defined_measurable_codes:
            if code not in cited_element_codes:
                raise ValidationError(f"Measurable element '{code}' does not have any citations.")

    return {
        "chapters": chapters,
        "requirements": requirements,
        "evidence_requirements": evidence_requirements,
        "applicability_rules": applicability_rules,
        "citations": citations,
        "citation_meta": citation_meta  # contains citation_complete flag and notes
    }
