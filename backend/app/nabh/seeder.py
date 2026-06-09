"""Database seeder to initialize NABH 6th Edition standards and objective elements."""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import (
    NABHObjective, SeverityLevel, MaturityLevel,
    NABHEdition, NABHChapter, NABHStandard, 
    NABHObjectiveElement, NABHMeasurableElement, 
    NABHEvidenceRequirement, NABHApplicabilityRule,
    NABHSourceDocument, NABHRequirementCitation,
    EditionStatus, ApplicabilityDefault, EvidenceType
)
from app.nabh.service import LEGACY_NABH_MODEL_NOTICE
from app.nabh.validator import validate_ontology_seeds

logger = logging.getLogger(__name__)

# WARNING: LEGACY STRUCTURE
# Do not build new features on this model; use the upcoming versioned ontology models.
# Notice: LEGACY MODEL: This is a simplified 33-item NABH model.
NABH_ELEMENTS_SEED = [
    # ACC: Access, Assessment, and Continuity of Care
    {"code": "AAC-1.a", "chapter": "ACC", "num": 1, "letter": "a", "name": "Patient admission protocols and criteria", "severity": SeverityLevel.MAJOR},
    {"code": "AAC-1.b", "chapter": "ACC", "num": 1, "letter": "b", "name": "Registration and initial administrative triage", "severity": SeverityLevel.MAJOR},
    {"code": "AAC-2.a", "chapter": "ACC", "num": 2, "letter": "a", "name": "Comprehensive initial clinical assessment", "severity": SeverityLevel.MAJOR},
    {"code": "AAC-3.a", "chapter": "ACC", "num": 3, "letter": "a", "name": "Continuity of care and transfer protocols", "severity": SeverityLevel.MAJOR},
    {"code": "AAC-4.a", "chapter": "ACC", "num": 4, "letter": "a", "name": "Discharge planning and discharge summary audits", "severity": SeverityLevel.MAJOR},
    {"code": "AAC-5.a", "chapter": "ACC", "num": 5, "letter": "a", "name": "Ambulance and safe patient transport services", "severity": SeverityLevel.MAJOR},

    # PC: Patient Care
    {"code": "PC-1.a", "chapter": "PC", "num": 1, "letter": "a", "name": "Patient rights education and informed consent checks", "severity": SeverityLevel.CRITICAL},
    {"code": "PC-2.a", "chapter": "PC", "num": 2, "letter": "a", "name": "Clinical care plan documentation and review", "severity": SeverityLevel.MAJOR},
    {"code": "PC-3.a", "chapter": "PC", "num": 3, "letter": "a", "name": "Medication reconciliation and expiry management", "severity": SeverityLevel.CRITICAL},
    {"code": "PC-4.a", "chapter": "PC", "num": 4, "letter": "a", "name": "Pre-operative assessment and WHO surgical safety checklist implementation", "severity": SeverityLevel.CRITICAL},
    {"code": "PC-5.a", "chapter": "PC", "num": 5, "letter": "a", "name": "Pre-anesthesia assessment and monitoring standards", "severity": SeverityLevel.CRITICAL},
    {"code": "PC-6.a", "chapter": "PC", "num": 6, "letter": "a", "name": "Blood safety, transfusion audits and cross-matching", "severity": SeverityLevel.CRITICAL},
    {"code": "PC-7.a", "chapter": "PC", "num": 7, "letter": "a", "name": "Hand hygiene WHO 5 Moments audit protocols", "severity": SeverityLevel.CRITICAL},
    {"code": "PC-8.a", "chapter": "PC", "num": 8, "letter": "a", "name": "International Patient Safety Goals (IPSG) tracking", "severity": SeverityLevel.CRITICAL},

    # FMS: Facility Management and Safety
    {"code": "FMS-1.a", "chapter": "FMS", "num": 1, "letter": "a", "name": "Fire Safety NOC, extinguisher mapping and drills", "severity": SeverityLevel.CRITICAL},
    {"code": "FMS-2.a", "chapter": "FMS", "num": 2, "letter": "a", "name": "Bio-Medical Waste segregation at source and manifest matching", "severity": SeverityLevel.CRITICAL},
    {"code": "FMS-3.a", "chapter": "FMS", "num": 3, "letter": "a", "name": "Disaster preparedness plan and evacuation routes", "severity": SeverityLevel.CRITICAL},
    {"code": "FMS-4.a", "chapter": "FMS", "num": 4, "letter": "a", "name": "Security access control and CCTV coverage audits", "severity": SeverityLevel.MAJOR},
    {"code": "FMS-5.a", "chapter": "FMS", "num": 5, "letter": "a", "name": "Medical equipment calibration and maintenance records", "severity": SeverityLevel.MAJOR},
    {"code": "FMS-6.a", "chapter": "FMS", "num": 6, "letter": "a", "name": "Water and power utility checks and back-up testing", "severity": SeverityLevel.MAJOR},

    # QMS: Quality Management System
    {"code": "QMS-1.a", "chapter": "QMS", "num": 1, "letter": "a", "name": "Quality indicators planning and benchmark reviews", "severity": SeverityLevel.MAJOR},
    {"code": "QMS-2.a", "chapter": "QMS", "num": 2, "letter": "a", "name": "SOP version control and documentation access audits", "severity": SeverityLevel.MINOR},
    {"code": "QMS-3.a", "chapter": "QMS", "num": 3, "letter": "a", "name": "Internal quality audits schedule and resolution tracking", "severity": SeverityLevel.MAJOR},
    {"code": "QMS-4.a", "chapter": "QMS", "num": 4, "letter": "a", "name": "Management reviews of compliance deficit metrics", "severity": SeverityLevel.MAJOR},
    {"code": "QMS-5.a", "chapter": "QMS", "num": 5, "letter": "a", "name": "Incident reporting CAPA investigations", "severity": SeverityLevel.CRITICAL},

    # IS: Information Management System
    {"code": "IS-1.a", "chapter": "IS", "num": 1, "letter": "a", "name": "Health information management policy and system access logs", "severity": SeverityLevel.MAJOR},
    {"code": "IS-2.a", "chapter": "IS", "num": 2, "letter": "a", "name": "Medical records completion audits and restricted access protocols", "severity": SeverityLevel.MAJOR},
    {"code": "IS-3.a", "chapter": "IS", "num": 3, "letter": "a", "name": "DPDP audit readiness: Patient consent and signature mapping", "severity": SeverityLevel.CRITICAL},
    {"code": "IS-4.a", "chapter": "IS", "num": 4, "letter": "a", "name": "Clinical decision support alerts and algorithm audit records", "severity": SeverityLevel.MINOR},

    # HR: Human Resource Management
    {"code": "HR-1.a", "chapter": "HR", "num": 1, "letter": "a", "name": "Staff credentialing and medical registration checks", "severity": SeverityLevel.CRITICAL},
    {"code": "HR-2.a", "chapter": "HR", "num": 2, "letter": "a", "name": "Staff orientation records and compliance training logs", "severity": SeverityLevel.MAJOR},
    {"code": "HR-3.a", "chapter": "HR", "num": 3, "letter": "a", "name": "Performance reviews and competency certifications", "severity": SeverityLevel.MAJOR},
    {"code": "HR-4.a", "chapter": "HR", "num": 4, "letter": "a", "name": "Staff health assessments and immunization records", "severity": SeverityLevel.MAJOR},
]

def seed_nabh_objectives(db: Session, hospital_id: str):
    """
    Seed base compliance objectives for a hospital if they don't exist.
    
    WARNING: LEGACY SEEDER
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    logger.info(f"🌱 Seeding NABH objectives for hospital: {hospital_id}")
    
    count = 0
    for element in NABH_ELEMENTS_SEED:
        existing = db.query(NABHObjective).filter(
            NABHObjective.hospital_id == hospital_id,
            NABHObjective.standard_code == element["code"]
        ).first()
        
        if not existing:
            new_obj = NABHObjective(
                hospital_id=hospital_id,
                chapter_code=element["chapter"],
                objective_number=element["num"],
                element_letter=element["letter"],
                standard_code=element["code"],
                standard_name=element["name"],
                severity=element["severity"],
                maturity_level=MaturityLevel.NON_EXISTENT
            )
            db.add(new_obj)
            count += 1
            
    db.commit()
    logger.info(f"✅ Seeding complete. Added {count} new objectives.")


def seed_versioned_ontology(db: Session, data_dir: str, target_version: str = "6.0"):
    """
    Idempotent seeding engine to populate the versioned NABH reference ontology.
    Wraps validation and seeding in a single outer database transaction.

    NOTE (WP3): This function always calls validate_ontology_seeds with
    allow_missing_citations=False and allow_bare_citation_array=False
    (the production defaults). The only way to bypass either guard is to
    call validate_ontology_seeds directly in tests with those flags set.
    Never pass those flags through this function in production code paths.
    """
    logger.info(f"🌱 Validating ontology seed files under: {data_dir}")
    loaded_data = validate_ontology_seeds(data_dir, target_version)

    # WP4: Warn explicitly when the citations file marks itself as non-complete so that
    # production logs make partial citation coverage visible rather than silently passing.
    citation_meta = loaded_data.get("citation_meta", {})
    if citation_meta and not citation_meta.get("citation_complete", True):
        logger.warning(
            "⚠️  Citation seed file is marked citation_complete=false. "
            "Citations seeded are a partial proof-of-concept set only. "
            "Do NOT infer citation completeness for any chapter from this seed run."
        )

    logger.info("🌱 Starting database seeding transaction...")
    try:
        # 1. Upsert Edition
        edition = db.query(NABHEdition).filter(NABHEdition.version == target_version).first()
        if not edition:
            edition = NABHEdition(
                name=f"NABH {target_version} Edition",
                version=target_version,
                status=EditionStatus.ACTIVE,
                effective_date=datetime(2026, 1, 1)
            )
            db.add(edition)
            db.flush()
        else:
            edition.status = EditionStatus.ACTIVE
            edition.effective_date = datetime(2026, 1, 1)
            db.flush()

        # 2. Upsert Chapters
        chapter_id_map = {}
        for chap_data in loaded_data["chapters"]:
            code = chap_data["code"]
            chap = db.query(NABHChapter).filter(
                NABHChapter.edition_id == edition.id,
                NABHChapter.canonical_code == code
            ).first()
            
            if not chap:
                chap = NABHChapter(
                    edition_id=edition.id,
                    code=code,
                    canonical_code=code,
                    title=chap_data["title"],
                    description=chap_data["description"],
                    display_order=chap_data["display_order"],
                    official_standards_count=chap_data["official_standards_count"],
                    official_measurable_elements_count=chap_data["official_measurable_elements_count"],
                    is_fully_seeded=chap_data["is_fully_seeded"],
                    core_count=chap_data.get("core_count"),
                    commitment_count=chap_data.get("commitment_count"),
                    achievement_count=chap_data.get("achievement_count"),
                    excellence_count=chap_data.get("excellence_count")
                )
                db.add(chap)
            else:
                chap.title = chap_data["title"]
                chap.description = chap_data["description"]
                chap.display_order = chap_data["display_order"]
                chap.official_standards_count = chap_data["official_standards_count"]
                chap.official_measurable_elements_count = chap_data["official_measurable_elements_count"]
                chap.is_fully_seeded = chap_data["is_fully_seeded"]
                chap.core_count = chap_data.get("core_count")
                chap.commitment_count = chap_data.get("commitment_count")
                chap.achievement_count = chap_data.get("achievement_count")
                chap.excellence_count = chap_data.get("excellence_count")
            
            db.flush()
            chapter_id_map[code] = chap.id

        # 3. Upsert Standards, Objective Elements, and Measurable Elements
        meas_id_map = {}
        for chap_req in loaded_data["requirements"]:
            chap_code = chap_req["chapter_code"]
            chapter_id = chapter_id_map[chap_code]
            
            for std_data in chap_req["standards"]:
                std_canonical = std_data["code"]
                std_relative = std_canonical.split("-")[-1]
                
                std = db.query(NABHStandard).filter(
                    NABHStandard.edition_id == edition.id,
                    NABHStandard.canonical_code == std_canonical
                ).first()
                
                if not std:
                    std = NABHStandard(
                        edition_id=edition.id,
                        chapter_id=chapter_id,
                        code=std_relative,
                        canonical_code=std_canonical,
                        title=std_data["title"],
                        description=std_data["description"],
                        display_order=std_data["display_order"]
                    )
                    db.add(std)
                else:
                    std.chapter_id = chapter_id
                    std.code = std_relative
                    std.title = std_data["title"]
                    std.description = std_data["description"]
                    std.display_order = std_data["display_order"]
                
                db.flush()
                
                for obj_data in std_data["objective_elements"]:
                    obj_canonical = obj_data["code"]
                    obj_relative = obj_canonical.split(".")[-1]
                    
                    obj = db.query(NABHObjectiveElement).filter(
                        NABHObjectiveElement.edition_id == edition.id,
                        NABHObjectiveElement.canonical_code == obj_canonical
                    ).first()
                    
                    severity_enum = SeverityLevel[obj_data["severity"].upper()]
                    
                    if not obj:
                        obj = NABHObjectiveElement(
                            edition_id=edition.id,
                            standard_id=std.id,
                            code=obj_relative,
                            canonical_code=obj_canonical,
                            description=obj_data["description"],
                            severity=severity_enum,
                            display_order=obj_data["display_order"]
                        )
                        db.add(obj)
                    else:
                        obj.standard_id = std.id
                        obj.code = obj_relative
                        obj.description = obj_data["description"]
                        obj.severity = severity_enum
                        obj.display_order = obj_data["display_order"]
                    
                    db.flush()
                    
                    for meas_data in obj_data["measurable_elements"]:
                        meas_canonical = meas_data["code"]
                        meas_relative = meas_canonical.split(".")[-1]
                        
                        meas = db.query(NABHMeasurableElement).filter(
                            NABHMeasurableElement.edition_id == edition.id,
                            NABHMeasurableElement.canonical_code == meas_canonical
                        ).first()
                        
                        app_default_enum = ApplicabilityDefault[meas_data["applicability_default"].upper()]
                        
                        if not meas:
                            meas = NABHMeasurableElement(
                                edition_id=edition.id,
                                objective_element_id=obj.id,
                                code=meas_relative,
                                canonical_code=meas_canonical,
                                description=meas_data["description"],
                                applicability_default=app_default_enum,
                                scoring_weight=meas_data["scoring_weight"],
                                risk_weight=meas_data["risk_weight"],
                                default_owner_role=meas_data["default_owner_role"],
                                display_order=meas_data["display_order"]
                            )
                            db.add(meas)
                        else:
                            meas.objective_element_id = obj.id
                            meas.code = meas_relative
                            meas.description = meas_data["description"]
                            meas.applicability_default = app_default_enum
                            meas.scoring_weight = meas_data["scoring_weight"]
                            meas.risk_weight = meas_data["risk_weight"]
                            meas.default_owner_role = meas_data["default_owner_role"]
                            meas.display_order = meas_data["display_order"]
                        
                        db.flush()
                        meas_id_map[meas_canonical] = meas.id

        # 4. Upsert Evidence Requirements
        for ev_data in loaded_data["evidence_requirements"]:
            meas_canonical = ev_data["measurable_element_code"]
            meas_id = meas_id_map[meas_canonical]
            ev_code = ev_data["evidence_code"]
            
            ev_type_enum = EvidenceType[ev_data["evidence_type"].upper()]
            
            ev_record = db.query(NABHEvidenceRequirement).filter(
                NABHEvidenceRequirement.measurable_element_id == meas_id,
                NABHEvidenceRequirement.evidence_code == ev_code
            ).first()
            
            evidence_frequency = ev_data.get("evidence_frequency")
            minimum_lookback_days = ev_data.get("minimum_lookback_days", 90)
            default_owner_role = ev_data.get("default_owner_role")
            suggested_documentation = ev_data.get("suggested_documentation")
            
            if not ev_record:
                ev_record = NABHEvidenceRequirement(
                    measurable_element_id=meas_id,
                    evidence_code=ev_code,
                    evidence_type=ev_type_enum,
                    description=ev_data["description"],
                    suggested_documentation=suggested_documentation,
                    is_mandatory=ev_data["is_mandatory"],
                    evidence_frequency=evidence_frequency,
                    minimum_lookback_days=minimum_lookback_days,
                    default_owner_role=default_owner_role
                )
                db.add(ev_record)
            else:
                ev_record.evidence_type = ev_type_enum
                ev_record.description = ev_data["description"]
                ev_record.suggested_documentation = suggested_documentation
                ev_record.is_mandatory = ev_data["is_mandatory"]
                ev_record.evidence_frequency = evidence_frequency
                ev_record.minimum_lookback_days = minimum_lookback_days
                ev_record.default_owner_role = default_owner_role
            
            db.flush()

        # 5. Upsert Applicability Rules
        for rule_data in loaded_data["applicability_rules"]:
            meas_canonical = rule_data["measurable_element_code"]
            meas_id = meas_id_map[meas_canonical]
            rule_code = rule_data["rule_code"]
            
            rule_record = db.query(NABHApplicabilityRule).filter(
                NABHApplicabilityRule.measurable_element_id == meas_id,
                NABHApplicabilityRule.rule_code == rule_code
            ).first()
            
            if not rule_record:
                rule_record = NABHApplicabilityRule(
                    measurable_element_id=meas_id,
                    rule_code=rule_code,
                    rule_json=rule_data["rule_json"],
                    description=rule_data["description"],
                    action_if_true=rule_data["action_if_true"],
                    action_if_false=rule_data["action_if_false"]
                )
                db.add(rule_record)
            else:
                rule_record.rule_json = rule_data["rule_json"]
                rule_record.description = rule_data["description"]
                rule_record.action_if_true = rule_data["action_if_true"]
                rule_record.action_if_false = rule_data["action_if_false"]
            
            db.flush()

        # 6. Upsert Source Documents and Requirement Citations
        # Build a per-(edition_id, title) map to avoid duplicate source document lookups.
        source_doc_cache: dict = {}
        for cit_data in loaded_data.get("citations", []):
            doc_key = (edition.id, cit_data["document_title"])

            if doc_key not in source_doc_cache:
                doc_record = db.query(NABHSourceDocument).filter(
                    NABHSourceDocument.edition_id == edition.id,
                    NABHSourceDocument.title == cit_data["document_title"]
                ).first()

                if not doc_record:
                    doc_record = NABHSourceDocument(
                        edition_id=edition.id,
                        title=cit_data["document_title"],
                        publisher=cit_data["document_publisher"],
                        edition_version=cit_data["document_version"],
                        # WP1: effective_date is set once on creation from the first citation
                        # encountered for this document title. On re-runs it is intentionally
                        # NOT overwritten — the first-seen date (typically the edition's
                        # publication date) is the stable anchor. A future task may derive
                        # this as min(citation.effective_date) across all citations if needed.
                        effective_date=datetime.strptime(cit_data["effective_date"], "%Y-%m-%d")
                    )
                    db.add(doc_record)
                else:
                    # Update publisher/version metadata in-place to keep them fresh.
                    # effective_date is deliberately preserved (see WP1 above).
                    doc_record.publisher = cit_data["document_publisher"]
                    doc_record.edition_version = cit_data["document_version"]

                db.flush()
                source_doc_cache[doc_key] = doc_record

            doc_record = source_doc_cache[doc_key]
            meas_id = meas_id_map[cit_data["measurable_element_code"]]
            section = cit_data.get("section")
            page_number = cit_data.get("page_number")

            # Upsert citation matched on (measurable_element_id, document_id, section, page_number).
            # WP2 (deferred): If two distinct clause summaries exist on the same page/section for
            # the same element+document, the second will silently overwrite the first. This is
            # acceptable until real source density proves otherwise. A future citation_code field
            # on the seed record would provide a collision-safe upsert key.
            cit_record = db.query(NABHRequirementCitation).filter(
                NABHRequirementCitation.measurable_element_id == meas_id,
                NABHRequirementCitation.document_id == doc_record.id,
                NABHRequirementCitation.section == section,
                NABHRequirementCitation.page_number == page_number
            ).first()

            file_path_val = cit_data.get("file_path") or None
            url_val = cit_data.get("url") or None

            if not cit_record:
                cit_record = NABHRequirementCitation(
                    measurable_element_id=meas_id,
                    document_id=doc_record.id,
                    section=section,
                    page_number=page_number,
                    clause_text_summary=cit_data.get("clause_text_summary"),
                    effective_date=datetime.strptime(cit_data["effective_date"], "%Y-%m-%d"),
                    file_path=file_path_val,
                    url=url_val
                )
                db.add(cit_record)
            else:
                cit_record.clause_text_summary = cit_data.get("clause_text_summary")
                cit_record.effective_date = datetime.strptime(cit_data["effective_date"], "%Y-%m-%d")
                cit_record.file_path = file_path_val
                cit_record.url = url_val

            db.flush()

        db.commit()
        logger.info(f"✅ Seeding transaction committed successfully for edition '{target_version}'.")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Seeding transaction failed and was rolled back: {e}")
        raise e

