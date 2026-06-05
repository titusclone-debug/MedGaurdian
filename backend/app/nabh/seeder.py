"""Database seeder to initialize NABH 6th Edition standards and objective elements."""
import logging
from sqlalchemy.orm import Session
from app.models.database import NABHObjective, SeverityLevel, MaturityLevel

logger = logging.getLogger(__name__)

# Complete mapping of NABH 6th Edition Objectives & Default Severity
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
    """Seed base compliance objectives for a hospital if they don't exist."""
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
