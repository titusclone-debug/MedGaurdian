#!/usr/bin/env python3
"""
Build NABH 6th Edition seed data for AAC and COP chapters.
Generates JSON with exact ME counts and classification distributions.
"""
import json
import sys

def build_aac():
    """
    AAC Chapter: Access, Assessment and Continuity of Care
    13 standards, 87 MEs total
    Classifications: 6 core, 68 commitment, 9 achievement, 4 excellence
    """
    # Distribution plan across 13 standards (sum must be 87):
    # AAC-1: 8, AAC-2: 7, AAC-3: 7, AAC-4: 8, AAC-5: 7,
    # AAC-6: 7, AAC-7: 6, AAC-8: 7, AAC-9: 7, AAC-10: 6,
    # AAC-11: 6, AAC-12: 6, AAC-13: 5
    # Total: 8+7+7+8+7+7+6+7+7+6+6+6+5 = 87 ✓

    standards = []

    # ─── AAC-1: Patient Registration and Admission Process ───
    standards.append({
        "code": "AAC-1",
        "title": "Patient Registration and Admission Process",
        "description": "The organization maintains a well-defined registration and admission process ensuring timely and equitable access to healthcare services.",
        "display_order": 1,
        "objective_elements": [
            _oe("AAC-1.a", "Registration procedures are documented covering patient identification, demographic data capture, and unique identifier assignment.", "major", 1, [
                _me("AAC-1.a.1", "The organization has a documented registration process that assigns a unique identification number to each patient.", "applicable", "quality_officer", 1, "commitment"),
                _me("AAC-1.a.2", "Registration staff verify patient identity using at least two identifiers before completing enrollment.", "applicable", "quality_officer", 2, "core"),
            ]),
            _oe("AAC-1.b", "The admission process defines criteria for inpatient, outpatient, and emergency admissions with clearly documented pathways.", "major", 2, [
                _me("AAC-1.b.1", "Admission criteria are documented and communicated to clinical and administrative teams.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-1.b.2", "Clear pathways exist for emergency, elective, and day-care admissions with defined workflows.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-1.c", "Waiting times for registration and admission are monitored and kept within defined benchmarks.", "major", 3, [
                _me("AAC-1.c.1", "The organization monitors and tracks waiting times at registration and admission points.", "applicable", "quality_officer", 1, "commitment"),
                _me("AAC-1.c.2", "Action plans are developed when waiting times exceed pre-defined thresholds.", "applicable", "quality_officer", 2, "achievement"),
            ]),
            _oe("AAC-1.d", "Patient information is collected in a standardized format and verified for accuracy at the time of registration.", "major", 4, [
                _me("AAC-1.d.1", "A standardized registration form is used across all entry points for uniform data collection.", "applicable", "it_director", 1, "commitment"),
                _me("AAC-1.d.2", "Procedures exist for verifying and correcting patient demographic data during the registration encounter.", "applicable", "quality_officer", 2, "commitment"),
            ]),
        ]
    })

    # ─── AAC-2: Emergency Access and Triage ───
    standards.append({
        "code": "AAC-2",
        "title": "Emergency Access and Triage",
        "description": "The organization ensures rapid access to emergency services with an established triage system to prioritize patients based on clinical urgency.",
        "display_order": 2,
        "objective_elements": [
            _oe("AAC-2.a", "A documented triage system categorizes patients based on severity and acuity upon emergency presentation.", "critical", 1, [
                _me("AAC-2.a.1", "A validated triage protocol is implemented in the emergency department to categorize patients by clinical priority.", "applicable", "medical_director", 1, "core"),
                _me("AAC-2.a.2", "Triage assessments are performed by trained clinical staff within a defined timeframe of patient arrival.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-2.b", "Emergency services are accessible around the clock with defined processes for stabilization and escalation.", "critical", 2, [
                _me("AAC-2.b.1", "Emergency services operate 24 hours a day, 7 days a week, with qualified medical and nursing staff.", "applicable", "medical_director", 1, "core"),
                _me("AAC-2.b.2", "Protocols for stabilization and escalation of critically ill patients are documented and rehearsed.", "applicable", "patient_safety_officer", 2, "commitment"),
            ]),
            _oe("AAC-2.c", "The organization tracks emergency response metrics including door-to-doctor time and triage compliance.", "major", 3, [
                _me("AAC-2.c.1", "Key performance indicators for emergency response are defined, monitored, and reviewed periodically.", "applicable", "quality_officer", 1, "commitment"),
                _me("AAC-2.c.2", "Door-to-doctor time and triage-to-treatment intervals are measured and benchmarked.", "applicable", "quality_officer", 2, "achievement"),
                _me("AAC-2.c.3", "Improvement initiatives are implemented based on analysis of emergency response metrics.", "applicable", "quality_officer", 3, "achievement"),
            ]),
        ]
    })

    # ─── AAC-3: Initial Assessment of Patients ───
    standards.append({
        "code": "AAC-3",
        "title": "Initial Assessment of Patients",
        "description": "Every patient receives a timely initial assessment to determine the nature and urgency of clinical needs and to guide the care plan.",
        "display_order": 3,
        "objective_elements": [
            _oe("AAC-3.a", "The initial assessment includes patient history, physical examination, and preliminary diagnosis within defined timeframes.", "major", 1, [
                _me("AAC-3.a.1", "Each patient receives an initial medical assessment including history and physical examination within the defined time window.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-3.a.2", "The scope and content of initial assessment is defined based on patient category (inpatient, outpatient, emergency).", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("AAC-3.b", "Initial nursing assessment covers vital signs, pain screening, nutritional status, and functional assessment.", "major", 2, [
                _me("AAC-3.b.1", "Nursing assessment at admission captures vital signs, pain level, nutritional screening, and fall risk.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-3.b.2", "Standardized nursing assessment forms are utilized across all care units.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-3.c", "Diagnostic investigations are ordered based on clinical findings from the initial assessment.", "major", 3, [
                _me("AAC-3.c.1", "Initial diagnostic workup is ordered promptly based on clinical findings and documented in the medical record.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-3.c.2", "Critical and urgent investigation results are communicated to the treating physician within defined timeframes.", "applicable", "medical_director", 2, "commitment"),
                _me("AAC-3.c.3", "A process exists for tracking and following up on pending diagnostic results.", "applicable", "quality_officer", 3, "commitment"),
            ]),
        ]
    })

    # ─── AAC-4: Nursing Assessment and Reassessment ───
    standards.append({
        "code": "AAC-4",
        "title": "Nursing Assessment and Reassessment",
        "description": "Nursing assessments are conducted at admission and at regular intervals to evaluate patient status, identify risks, and adjust the nursing care plan.",
        "display_order": 4,
        "objective_elements": [
            _oe("AAC-4.a", "Comprehensive nursing assessment is completed within a defined timeframe after admission.", "major", 1, [
                _me("AAC-4.a.1", "A comprehensive nursing assessment is completed within the stipulated time after patient admission.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-4.a.2", "The nursing assessment includes physical, psychological, social, and educational needs of the patient.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-4.b", "Reassessment is performed at defined intervals and when the patient's condition changes significantly.", "major", 2, [
                _me("AAC-4.b.1", "Nursing reassessment is carried out at defined intervals appropriate to the patient's clinical condition.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-4.b.2", "Significant changes in patient condition trigger an immediate nursing reassessment and documentation.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-4.c", "Specialized nursing assessments are performed for vulnerable populations including pediatric, geriatric, and obstetric patients.", "major", 3, [
                _me("AAC-4.c.1", "Age-specific and condition-specific nursing assessment tools are available for pediatric and geriatric patients.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-4.c.2", "Obstetric nursing assessments include maternal and fetal monitoring parameters.", "conditional", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-4.d", "Nursing assessments are documented in a standardized format and integrated into the patient care record.", "minor", 4, [
                _me("AAC-4.d.1", "All nursing assessments and reassessments are documented in a structured, standardized format.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-4.d.2", "Nursing documentation is integrated with the overall patient medical record for continuity of information.", "applicable", "it_director", 2, "commitment"),
            ]),
        ]
    })

    # ─── AAC-5: Medical Assessment and Reassessment ───
    standards.append({
        "code": "AAC-5",
        "title": "Medical Assessment and Reassessment",
        "description": "Medical assessments by qualified physicians are performed on all patients at admission and regularly thereafter, with findings documented to support clinical decision-making.",
        "display_order": 5,
        "objective_elements": [
            _oe("AAC-5.a", "Medical assessment by a qualified physician is completed within a defined timeframe based on patient acuity.", "major", 1, [
                _me("AAC-5.a.1", "A qualified physician completes the medical assessment within the time window defined for the patient's acuity level.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-5.a.2", "Medical assessments for emergency patients are prioritized and completed before routine admissions.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("AAC-5.b", "Medical reassessment occurs at defined intervals and is documented with updated clinical findings.", "major", 2, [
                _me("AAC-5.b.1", "Physician reassessment intervals are defined based on patient acuity and clinical protocols.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-5.b.2", "Changes in the treatment plan following reassessment are documented and communicated to the care team.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("AAC-5.c", "Specialist consultations are obtained in a timely manner when the patient's condition warrants additional expertise.", "major", 3, [
                _me("AAC-5.c.1", "Procedures define how and when specialist consultations are requested and their response timeframes.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-5.c.2", "Specialist consultation findings are documented and incorporated into the treatment plan.", "applicable", "medical_director", 2, "commitment"),
                _me("AAC-5.c.3", "A tracking mechanism ensures specialist consultations are completed within the defined time limits.", "applicable", "quality_officer", 3, "achievement"),
            ]),
        ]
    })

    # ─── AAC-6: Continuity of Care ───
    standards.append({
        "code": "AAC-6",
        "title": "Continuity of Care",
        "description": "The organization ensures seamless continuity of patient care across departments, shifts, and care providers through structured handover and communication processes.",
        "display_order": 6,
        "objective_elements": [
            _oe("AAC-6.a", "Standardized clinical handover processes are implemented across shift changes and inter-departmental transfers.", "critical", 1, [
                _me("AAC-6.a.1", "A standardized handover protocol (such as SBAR or equivalent) is used for shift-to-shift clinical handovers.", "applicable", "patient_safety_officer", 1, "core"),
                _me("AAC-6.a.2", "Handover communication includes critical patient information, pending tasks, and anticipated changes.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-6.b", "Transfer of patients between units or departments follows a defined process with documented transfer summaries.", "major", 2, [
                _me("AAC-6.b.1", "Inter-departmental transfers include a documented transfer summary with clinical status and ongoing care needs.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-6.b.2", "Receiving units acknowledge the transfer and verify patient identity and clinical information.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-6.c", "Care coordination ensures that the patient's care plan is consistently followed across different care settings.", "major", 3, [
                _me("AAC-6.c.1", "A care coordination mechanism ensures that the treatment plan is updated and shared across all involved providers.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-6.c.2", "Multidisciplinary team meetings are conducted for complex cases to ensure coordinated care delivery.", "applicable", "medical_director", 2, "commitment"),
                _me("AAC-6.c.3", "The organization demonstrates measurable improvements in care continuity outcomes through data analysis.", "applicable", "quality_officer", 3, "excellence"),
            ]),
        ]
    })

    # ─── AAC-7: Discharge Planning ───
    standards.append({
        "code": "AAC-7",
        "title": "Discharge Planning and Process",
        "description": "Discharge planning begins at admission and involves the patient and family, ensuring safe transition with appropriate instructions and follow-up arrangements.",
        "display_order": 7,
        "objective_elements": [
            _oe("AAC-7.a", "Discharge planning is initiated early in the admission process and involves multidisciplinary input.", "major", 1, [
                _me("AAC-7.a.1", "Discharge planning begins at or near the time of admission with estimated length of stay considerations.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-7.a.2", "Multidisciplinary team members contribute to the discharge plan based on patient needs.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("AAC-7.b", "Discharge summaries are prepared and provided to patients with medication instructions, follow-up schedules, and danger signs.", "major", 2, [
                _me("AAC-7.b.1", "A comprehensive discharge summary is provided to the patient including diagnosis, treatment given, and medications prescribed.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-7.b.2", "Patients and caregivers receive clear instructions regarding danger signs, dietary guidance, and activity restrictions.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-7.c", "Against medical advice (AMA) discharges are documented with risks explained and patient consent recorded.", "major", 3, [
                _me("AAC-7.c.1", "Patients leaving against medical advice are counseled on risks and a documented AMA form is completed.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-7.c.2", "AMA discharge data is tracked and analyzed for patterns and improvement opportunities.", "applicable", "quality_officer", 2, "achievement"),
            ]),
        ]
    })

    # ─── AAC-8: Referral and Transfer Out ───
    standards.append({
        "code": "AAC-8",
        "title": "Referral and Transfer to Other Facilities",
        "description": "The organization has a defined process for referring and transferring patients to other healthcare facilities when the required services are not available in-house.",
        "display_order": 8,
        "objective_elements": [
            _oe("AAC-8.a", "Criteria and processes for referring patients to external facilities are documented and followed.", "major", 1, [
                _me("AAC-8.a.1", "Documented criteria guide decisions for patient referral or transfer to higher or specialized care centers.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-8.a.2", "Referral communication includes clinical details, reason for referral, and relevant investigation results.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("AAC-8.b", "Patient stabilization is ensured before transfer and appropriate clinical staff accompany critical patients.", "critical", 2, [
                _me("AAC-8.b.1", "Patients are stabilized to the extent possible before being transferred to another facility.", "applicable", "medical_director", 1, "core"),
                _me("AAC-8.b.2", "Critically ill patients are accompanied by qualified clinical staff during inter-facility transfer.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-8.c", "The receiving facility is communicated with prior to transfer, and acceptance is confirmed.", "major", 3, [
                _me("AAC-8.c.1", "The receiving facility is contacted and confirms acceptance before initiating patient transfer.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-8.c.2", "Transfer documentation includes patient clinical status, interventions provided, and ongoing care requirements.", "applicable", "nursing_director", 2, "commitment"),
                _me("AAC-8.c.3", "Patient and family are informed and involved in transfer decisions with consent documented.", "applicable", "patient_safety_officer", 3, "commitment"),
            ]),
        ]
    })

    # ─── AAC-9: Ambulance Services and Patient Transport ───
    standards.append({
        "code": "AAC-9",
        "title": "Ambulance Services and Patient Transport",
        "description": "The organization provides or arranges safe and equipped ambulance and patient transport services for intra- and inter-facility movement.",
        "display_order": 9,
        "objective_elements": [
            _oe("AAC-9.a", "Ambulance services are equipped, staffed, and maintained according to defined standards.", "critical", 1, [
                _me("AAC-9.a.1", "Ambulances are equipped with essential life-support equipment and medications as per defined standards.", "applicable", "facility_director", 1, "commitment"),
                _me("AAC-9.a.2", "Ambulance staff are trained in basic and advanced life support techniques.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("AAC-9.b", "Intra-hospital patient transport follows safety protocols with appropriate monitoring.", "major", 2, [
                _me("AAC-9.b.1", "Intra-hospital transport protocols define the level of monitoring and staffing required based on patient acuity.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-9.b.2", "Transport equipment including portable monitors and oxygen supply is maintained in readiness.", "applicable", "facility_director", 2, "commitment"),
            ]),
            _oe("AAC-9.c", "Transport-related adverse events are reported, tracked, and analyzed for improvement.", "major", 3, [
                _me("AAC-9.c.1", "Adverse events during patient transport are reported through the incident reporting system.", "applicable", "patient_safety_officer", 1, "commitment"),
                _me("AAC-9.c.2", "Transport safety data is analyzed periodically and used to improve transport protocols.", "applicable", "quality_officer", 2, "achievement"),
                _me("AAC-9.c.3", "The organization benchmarks its transport safety outcomes and demonstrates sustained improvement.", "applicable", "quality_officer", 3, "excellence"),
            ]),
        ]
    })

    # ─── AAC-10: Emergency Care Management ───
    standards.append({
        "code": "AAC-10",
        "title": "Emergency Care Management",
        "description": "The emergency department provides rapid assessment and management of acute conditions with defined protocols for common emergencies and mass casualty events.",
        "display_order": 10,
        "objective_elements": [
            _oe("AAC-10.a", "Clinical protocols for management of common medical and surgical emergencies are available and followed.", "critical", 1, [
                _me("AAC-10.a.1", "Evidence-based clinical protocols are available for common emergency presentations including cardiac, trauma, and stroke.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-10.a.2", "Emergency staff are trained on these protocols and competency is verified through periodic assessments.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-10.b", "A disaster and mass casualty response plan is documented, rehearsed, and updated periodically.", "major", 2, [
                _me("AAC-10.b.1", "A documented disaster management plan addresses mass casualty incidents and internal emergencies.", "applicable", "patient_safety_officer", 1, "commitment"),
                _me("AAC-10.b.2", "Disaster drills are conducted at defined intervals and debriefings inform plan revisions.", "applicable", "patient_safety_officer", 2, "commitment"),
            ]),
            _oe("AAC-10.c", "Medico-legal cases presenting to the emergency are handled as per statutory requirements.", "major", 3, [
                _me("AAC-10.c.1", "Procedures for identifying and managing medico-legal cases in the emergency department comply with regulatory requirements.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-10.c.2", "Documentation of medico-legal cases is thorough and preserved as per legal retention policies.", "applicable", "quality_officer", 2, "commitment"),
            ]),
        ]
    })

    # ─── AAC-11: Follow-up Care ───
    standards.append({
        "code": "AAC-11",
        "title": "Follow-up Care and Post-Discharge Communication",
        "description": "The organization establishes mechanisms for post-discharge follow-up to monitor patient outcomes and ensure adherence to the care plan.",
        "display_order": 11,
        "objective_elements": [
            _oe("AAC-11.a", "Follow-up appointments are scheduled prior to discharge and communicated to the patient.", "major", 1, [
                _me("AAC-11.a.1", "Follow-up visit schedules are determined before discharge and communicated to the patient in writing.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-11.a.2", "A reminder system is in place to reduce missed follow-up appointments.", "applicable", "it_director", 2, "achievement"),
            ]),
            _oe("AAC-11.b", "Post-discharge communication mechanisms exist for high-risk patients and surgical cases.", "major", 2, [
                _me("AAC-11.b.1", "High-risk patients receive structured post-discharge follow-up calls or contacts within defined timeframes.", "applicable", "nursing_director", 1, "commitment"),
                _me("AAC-11.b.2", "Post-discharge issues identified through follow-up are documented and escalated to the treating team.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("AAC-11.c", "Follow-up compliance rates are monitored and used to improve discharge planning.", "major", 3, [
                _me("AAC-11.c.1", "The organization tracks follow-up compliance rates and analyzes reasons for non-compliance.", "applicable", "quality_officer", 1, "achievement"),
                _me("AAC-11.c.2", "Outcomes data from follow-up care informs quality improvement in discharge planning processes.", "applicable", "quality_officer", 2, "excellence"),
            ]),
        ]
    })

    # ─── AAC-12: Outpatient and Day Care Services ───
    standards.append({
        "code": "AAC-12",
        "title": "Outpatient and Day Care Services",
        "description": "Outpatient and day care services are organized to provide efficient, safe, and patient-centered ambulatory care.",
        "display_order": 12,
        "objective_elements": [
            _oe("AAC-12.a", "Outpatient services are structured with defined workflows for appointment scheduling, consultation, and investigation coordination.", "major", 1, [
                _me("AAC-12.a.1", "Outpatient clinic workflows are documented covering appointment scheduling through consultation and follow-up.", "applicable", "quality_officer", 1, "commitment"),
                _me("AAC-12.a.2", "Waiting times in outpatient clinics are monitored and steps are taken to minimize delays.", "applicable", "quality_officer", 2, "commitment"),
            ]),
            _oe("AAC-12.b", "Day care services have defined admission and discharge criteria with appropriate monitoring during the stay.", "major", 2, [
                _me("AAC-12.b.1", "Day care admission and discharge criteria are documented and uniformly applied.", "applicable", "medical_director", 1, "commitment"),
                _me("AAC-12.b.2", "Patients undergoing day care procedures are monitored during and after the procedure until safe discharge.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("AAC-12.c", "Outpatient and day care service quality metrics are tracked and benchmarked.", "major", 3, [
                _me("AAC-12.c.1", "Quality indicators for outpatient and day care services are defined and monitored periodically.", "applicable", "quality_officer", 1, "commitment"),
                _me("AAC-12.c.2", "Patient satisfaction surveys for outpatient services are conducted and results drive service improvements.", "applicable", "quality_officer", 2, "excellence"),
            ]),
        ]
    })

    # ─── AAC-13: Patient Access for Special Populations ───
    standards.append({
        "code": "AAC-13",
        "title": "Access for Vulnerable and Special Populations",
        "description": "The organization ensures equitable access to care for vulnerable populations including elderly, disabled, and socially disadvantaged patients.",
        "display_order": 13,
        "objective_elements": [
            _oe("AAC-13.a", "Physical and process accommodations are in place to facilitate access for persons with disabilities and elderly patients.", "major", 1, [
                _me("AAC-13.a.1", "The facility provides physical accessibility features such as ramps, handrails, and designated seating for disabled and elderly patients.", "applicable", "facility_director", 1, "commitment"),
                _me("AAC-13.a.2", "Signage, communication aids, and language support are available for patients with sensory or language barriers.", "applicable", "facility_director", 2, "commitment"),
            ]),
            _oe("AAC-13.b", "Processes ensure that socially disadvantaged and financially weaker patients receive necessary care without discrimination.", "major", 2, [
                _me("AAC-13.b.1", "The organization has a policy for providing care to economically weaker patients including links to government schemes.", "applicable", "quality_officer", 1, "commitment"),
                _me("AAC-13.b.2", "No patient in need of emergency care is denied treatment due to inability to pay.", "applicable", "medical_director", 2, "core"),
                _me("AAC-13.b.3", "The organization tracks and reports the volume and outcomes of care provided to vulnerable populations.", "applicable", "quality_officer", 3, "achievement"),
            ]),
        ]
    })

    return {
        "chapter_code": "AAC",
        "edition_version": "6.0",
        "standards": standards
    }


def build_cop():
    """
    COP Chapter: Care of Patients
    20 standards, 136 MEs total
    Classifications: 13 core, 107 commitment, 12 achievement, 4 excellence
    """
    # Distribution plan across 20 standards (sum must be 136):
    # COP-1: 8, COP-2: 8, COP-3: 8, COP-4: 7, COP-5: 7,
    # COP-6: 7, COP-7: 7, COP-8: 7, COP-9: 7, COP-10: 7,
    # COP-11: 7, COP-12: 7, COP-13: 7, COP-14: 6, COP-15: 7,
    # COP-16: 6, COP-17: 6, COP-18: 7, COP-19: 6, COP-20: 6
    # Total: 8+8+8+7+7+7+7+7+7+7+7+7+7+6+7+6+6+7+6+6 = 136 ✓

    standards = []

    # ─── COP-1: Care Planning and Delivery ───
    standards.append({
        "code": "COP-1",
        "title": "Care Planning and Delivery",
        "description": "Each patient has an individualized care plan developed collaboratively by the clinical team, documented in the medical record, and updated as the patient's condition evolves.",
        "display_order": 1,
        "objective_elements": [
            _oe("COP-1.a", "An individualized care plan is developed for each patient based on the initial assessment findings.", "major", 1, [
                _me("COP-1.a.1", "An individualized care plan is documented for each patient based on clinical assessment and diagnosis.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-1.a.2", "The care plan defines goals, interventions, timelines, and responsibilities of the care team.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-1.b", "Care plans are reviewed and updated at defined intervals and when the clinical condition changes.", "major", 2, [
                _me("COP-1.b.1", "Care plans are reviewed at defined intervals and updated to reflect changes in the patient's condition.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-1.b.2", "Clinical progress notes document the rationale for modifications to the care plan.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-1.c", "Multidisciplinary team involvement in care planning is documented and coordinated.", "major", 3, [
                _me("COP-1.c.1", "Multidisciplinary care conferences are held for complex patients to coordinate the treatment approach.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-1.c.2", "Allied health professionals contribute to the care plan based on their specialized assessment findings.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-1.d", "Patients and families are involved in care planning discussions and their preferences are considered.", "major", 4, [
                _me("COP-1.d.1", "Patients and families are informed about the care plan and their preferences are incorporated.", "applicable", "nursing_director", 1, "commitment"),
                _me("COP-1.d.2", "Patient and family participation in care decisions is documented in the medical record.", "applicable", "nursing_director", 2, "commitment"),
            ]),
        ]
    })

    # ─── COP-2: Clinical Protocols and Guidelines ───
    standards.append({
        "code": "COP-2",
        "title": "Clinical Protocols and Evidence-Based Guidelines",
        "description": "The organization develops, implements, and monitors evidence-based clinical protocols and guidelines to standardize patient care and improve clinical outcomes.",
        "display_order": 2,
        "objective_elements": [
            _oe("COP-2.a", "Evidence-based clinical protocols are developed for high-volume and high-risk conditions.", "major", 1, [
                _me("COP-2.a.1", "Clinical protocols are developed for the most common diagnoses and high-risk conditions seen in the organization.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-2.a.2", "Protocols are based on current evidence and national/international guidelines where available.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-2.b", "Clinical protocols are disseminated, accessible, and compliance is monitored.", "major", 2, [
                _me("COP-2.b.1", "Clinical protocols are made accessible at the point of care and clinicians are trained on their use.", "applicable", "quality_officer", 1, "commitment"),
                _me("COP-2.b.2", "Compliance with clinical protocols is audited periodically and variance is analyzed.", "applicable", "quality_officer", 2, "achievement"),
            ]),
            _oe("COP-2.c", "Protocols are reviewed and updated at defined intervals based on new evidence and audit findings.", "major", 3, [
                _me("COP-2.c.1", "Clinical protocols are reviewed at least annually and updated based on emerging evidence and audit results.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-2.c.2", "A clinical protocols committee oversees the development, review, and approval of all clinical guidelines.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-2.d", "Clinical outcomes are measured against protocol-defined benchmarks and improvement actions are taken.", "major", 4, [
                _me("COP-2.d.1", "Clinical outcome indicators linked to protocol compliance are tracked and analyzed.", "applicable", "quality_officer", 1, "achievement"),
                _me("COP-2.d.2", "Demonstrated improvement in outcomes attributable to protocol adherence is documented.", "applicable", "quality_officer", 2, "excellence"),
            ]),
        ]
    })

    # ─── COP-3: Surgical Care ───
    standards.append({
        "code": "COP-3",
        "title": "Surgical Care and Procedures",
        "description": "Surgical care is planned and delivered in a safe environment with pre-operative assessments, informed consent, surgical safety checklists, and post-operative monitoring.",
        "display_order": 3,
        "objective_elements": [
            _oe("COP-3.a", "Pre-operative assessment and preparation follow a defined protocol including fitness evaluation.", "major", 1, [
                _me("COP-3.a.1", "Pre-operative assessment includes medical fitness evaluation, relevant investigations, and anesthesia review.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-3.a.2", "Pre-operative patient preparation checklist is completed and verified before moving to the operating room.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-3.b", "The WHO Surgical Safety Checklist or equivalent is implemented for all surgical procedures.", "critical", 2, [
                _me("COP-3.b.1", "A surgical safety checklist is used for every surgical procedure covering sign-in, time-out, and sign-out phases.", "applicable", "patient_safety_officer", 1, "core"),
                _me("COP-3.b.2", "Site marking is performed for laterality and level procedures with patient participation.", "applicable", "medical_director", 2, "core"),
            ]),
            _oe("COP-3.c", "Post-operative care includes monitoring, pain management, and complication surveillance.", "major", 3, [
                _me("COP-3.c.1", "Post-operative monitoring protocols define frequency of vital signs, assessment of surgical site, and pain evaluation.", "applicable", "nursing_director", 1, "commitment"),
                _me("COP-3.c.2", "Post-operative complications are tracked, reported, and analyzed for quality improvement.", "applicable", "quality_officer", 2, "achievement"),
            ]),
            _oe("COP-3.d", "Surgical outcome data is collected and reviewed by the surgical team for continuous improvement.", "major", 4, [
                _me("COP-3.d.1", "Surgical outcome indicators including infection rates, re-operation rates, and mortality are monitored.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-3.d.2", "Surgical morbidity and mortality conferences are held regularly to review adverse surgical outcomes.", "applicable", "medical_director", 2, "commitment"),
            ]),
        ]
    })

    # ─── COP-4: Anesthesia Care ───
    standards.append({
        "code": "COP-4",
        "title": "Anesthesia Care and Management",
        "description": "Anesthesia services are provided by qualified personnel following defined protocols for pre-anesthetic evaluation, intra-operative care, and post-anesthetic recovery.",
        "display_order": 4,
        "objective_elements": [
            _oe("COP-4.a", "Pre-anesthetic assessment is performed by a qualified anesthesiologist and documented.", "major", 1, [
                _me("COP-4.a.1", "Every patient scheduled for anesthesia receives a pre-anesthetic evaluation by a qualified anesthesiologist.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-4.a.2", "The pre-anesthetic assessment includes airway evaluation, ASA grading, and anesthesia plan.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-4.b", "Intra-operative anesthesia monitoring follows defined standards with continuous documentation.", "critical", 2, [
                _me("COP-4.b.1", "Intra-operative monitoring includes continuous ECG, pulse oximetry, ETCO2, and blood pressure at defined intervals.", "applicable", "medical_director", 1, "core"),
                _me("COP-4.b.2", "Anesthesia records document all drugs administered, vital sign trends, and intra-operative events.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-4.c", "Post-anesthesia recovery is monitored in a designated area with defined discharge criteria.", "major", 3, [
                _me("COP-4.c.1", "Patients are monitored in a post-anesthesia care unit using a standardized scoring system for discharge readiness.", "applicable", "nursing_director", 1, "commitment"),
                _me("COP-4.c.2", "Discharge from post-anesthesia recovery is authorized by a qualified clinician based on defined criteria.", "applicable", "medical_director", 2, "commitment"),
                _me("COP-4.c.3", "Anesthesia-related adverse events are reported and reviewed by the anesthesia department.", "applicable", "patient_safety_officer", 3, "commitment"),
            ]),
        ]
    })

    # ─── COP-5: Sedation Procedures ───
    standards.append({
        "code": "COP-5",
        "title": "Sedation Practices",
        "description": "Sedation is administered by trained personnel with appropriate monitoring, and policies distinguish between minimal, moderate, and deep sedation levels.",
        "display_order": 5,
        "objective_elements": [
            _oe("COP-5.a", "Sedation policies define levels of sedation, personnel qualifications, and monitoring requirements.", "major", 1, [
                _me("COP-5.a.1", "A documented sedation policy defines levels of sedation and the qualifications required for administering personnel.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-5.a.2", "Monitoring requirements during and after sedation are specified for each sedation level.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-5.b", "Pre-sedation assessment evaluates patient risk and suitability for the planned sedation level.", "major", 2, [
                _me("COP-5.b.1", "Pre-sedation assessment includes airway evaluation, fasting status, and risk stratification.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-5.b.2", "Informed consent for sedation is obtained from the patient or authorized representative.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-5.c", "Rescue equipment and reversal agents are immediately available in all sedation areas.", "critical", 3, [
                _me("COP-5.c.1", "Emergency resuscitation equipment and sedation reversal agents are immediately accessible in sedation areas.", "applicable", "nursing_director", 1, "core"),
                _me("COP-5.c.2", "Staff administering sedation are trained in emergency management of sedation complications.", "applicable", "nursing_director", 2, "commitment"),
                _me("COP-5.c.3", "Sedation-related adverse events are tracked and contribute to safety improvement initiatives.", "applicable", "patient_safety_officer", 3, "commitment"),
            ]),
        ]
    })

    # ─── COP-6: Blood Bank and Transfusion Services ───
    standards.append({
        "code": "COP-6",
        "title": "Blood Bank and Transfusion Services",
        "description": "Blood and blood product management ensures safe collection, storage, compatibility testing, and transfusion with monitoring for adverse reactions.",
        "display_order": 6,
        "objective_elements": [
            _oe("COP-6.a", "Blood bank operations comply with regulatory requirements and follow standard operating procedures.", "critical", 1, [
                _me("COP-6.a.1", "The blood bank operates under valid regulatory licenses and follows documented standard operating procedures.", "applicable", "medical_director", 1, "core"),
                _me("COP-6.a.2", "Blood and blood products are collected, processed, stored, and issued following established safety protocols.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-6.b", "Pre-transfusion testing and compatibility verification are performed for every unit transfused.", "critical", 2, [
                _me("COP-6.b.1", "Cross-matching and compatibility testing are performed for every blood unit before transfusion.", "applicable", "medical_director", 1, "core"),
                _me("COP-6.b.2", "Bedside identity verification of the patient and blood unit is conducted before initiating transfusion.", "applicable", "nursing_director", 2, "core"),
            ]),
            _oe("COP-6.c", "Transfusion reactions are identified promptly, managed, and reported through the adverse event system.", "major", 3, [
                _me("COP-6.c.1", "A protocol for identifying and managing transfusion reactions is documented and staff are trained.", "applicable", "nursing_director", 1, "commitment"),
                _me("COP-6.c.2", "All transfusion reactions are reported, investigated, and analyzed for preventive action.", "applicable", "quality_officer", 2, "commitment"),
                _me("COP-6.c.3", "Blood utilization audits are conducted to optimize transfusion practices and reduce wastage.", "applicable", "quality_officer", 3, "achievement"),
            ]),
        ]
    })

    # ─── COP-7: Organ Transplant Program ───
    standards.append({
        "code": "COP-7",
        "title": "Organ Transplant Program",
        "description": "Organizations performing organ transplants have comprehensive protocols covering donor selection, organ procurement, transplant procedures, and post-transplant care.",
        "display_order": 7,
        "objective_elements": [
            _oe("COP-7.a", "Organ transplant activities comply with national laws and the organization is registered with regulatory authorities.", "major", 1, [
                _me("COP-7.a.1", "The organ transplant program operates under valid regulatory registration and complies with the Transplantation of Human Organs Act or equivalent.", "conditional", "medical_director", 1, "commitment"),
                _me("COP-7.a.2", "An authorized transplant committee oversees organ allocation, donor evaluation, and ethical compliance.", "conditional", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-7.b", "Donor evaluation, organ procurement, and transplant procedures follow evidence-based clinical protocols.", "major", 2, [
                _me("COP-7.b.1", "Donor evaluation protocols include medical, immunological, and psychosocial assessment of living donors.", "conditional", "medical_director", 1, "commitment"),
                _me("COP-7.b.2", "Organ procurement and preservation follow established cold ischemia time limits and handling procedures.", "conditional", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-7.c", "Post-transplant care includes immunosuppression management, infection surveillance, and long-term follow-up.", "major", 3, [
                _me("COP-7.c.1", "Post-transplant care protocols define immunosuppression regimens, infection prophylaxis, and graft monitoring.", "conditional", "medical_director", 1, "commitment"),
                _me("COP-7.c.2", "Long-term follow-up of transplant recipients is structured with defined outcome tracking.", "conditional", "medical_director", 2, "commitment"),
                _me("COP-7.c.3", "Transplant outcome data including graft and patient survival are analyzed and benchmarked.", "conditional", "quality_officer", 3, "achievement"),
            ]),
        ]
    })

    # ─── COP-8: Intensive Care Unit Management ───
    standards.append({
        "code": "COP-8",
        "title": "Intensive Care Unit Management",
        "description": "Intensive care services are provided with defined admission and discharge criteria, appropriate staffing, equipment, and protocols for critically ill patients.",
        "display_order": 8,
        "objective_elements": [
            _oe("COP-8.a", "ICU admission and discharge criteria are defined and applied consistently.", "major", 1, [
                _me("COP-8.a.1", "Documented ICU admission criteria guide decisions for patient entry based on clinical severity.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-8.a.2", "ICU discharge criteria ensure patients are stable before transfer to lower levels of care.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-8.b", "ICU staffing meets defined nurse-to-patient ratios and specialist availability requirements.", "critical", 2, [
                _me("COP-8.b.1", "The ICU maintains defined nurse-to-patient ratios appropriate for the level of critical care provided.", "applicable", "nursing_director", 1, "core"),
                _me("COP-8.b.2", "Intensivist or qualified physician coverage is available for the ICU on a round-the-clock basis.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-8.c", "ICU clinical protocols cover ventilator management, sepsis bundles, and prevention of ICU-related complications.", "major", 3, [
                _me("COP-8.c.1", "Evidence-based ICU bundles are implemented for ventilator-associated pneumonia prevention, central line care, and sepsis management.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-8.c.2", "ICU quality metrics including VAP rates, CLABSI rates, and mortality indices are monitored and benchmarked.", "applicable", "quality_officer", 2, "achievement"),
                _me("COP-8.c.3", "ICU outcome data demonstrates sustained improvement through bundle compliance.", "applicable", "quality_officer", 3, "excellence"),
            ]),
        ]
    })

    # ─── COP-9: Obstetric Care ───
    standards.append({
        "code": "COP-9",
        "title": "Obstetric Care Services",
        "description": "Obstetric services provide comprehensive antenatal, intrapartum, and postnatal care with protocols for normal and high-risk pregnancies, safe delivery practices, and newborn care.",
        "display_order": 9,
        "objective_elements": [
            _oe("COP-9.a", "Antenatal care includes risk stratification, screening, and management plans for identified risks.", "major", 1, [
                _me("COP-9.a.1", "Antenatal care protocols include risk stratification, recommended screening investigations, and referral criteria.", "conditional", "medical_director", 1, "commitment"),
                _me("COP-9.a.2", "High-risk pregnancies are identified early and managed with enhanced surveillance and specialist input.", "conditional", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-9.b", "Intrapartum care follows evidence-based protocols for labor monitoring and safe delivery practices.", "critical", 2, [
                _me("COP-9.b.1", "Labor monitoring uses partographs and continuous or intermittent fetal heart rate monitoring as clinically indicated.", "conditional", "medical_director", 1, "core"),
                _me("COP-9.b.2", "Protocols for management of obstetric emergencies including post-partum hemorrhage and eclampsia are available.", "conditional", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-9.c", "Postnatal care covers maternal recovery, breastfeeding support, and newborn assessment.", "major", 3, [
                _me("COP-9.c.1", "Postnatal care protocols address maternal recovery assessment, breastfeeding initiation, and early complication detection.", "conditional", "nursing_director", 1, "commitment"),
                _me("COP-9.c.2", "Newborn assessment includes APGAR scoring, weight, gestational age assessment, and screening for congenital conditions.", "conditional", "medical_director", 2, "commitment"),
                _me("COP-9.c.3", "Maternal and neonatal outcome data is tracked and reviewed for quality improvement.", "conditional", "quality_officer", 3, "achievement"),
            ]),
        ]
    })

    # ─── COP-10: Pediatric Care ───
    standards.append({
        "code": "COP-10",
        "title": "Pediatric Care Services",
        "description": "Pediatric care is delivered with age-appropriate assessment tools, weight-based medication dosing, family involvement, and specialized monitoring for children.",
        "display_order": 10,
        "objective_elements": [
            _oe("COP-10.a", "Pediatric assessment tools are age-appropriate and cover growth, development, and nutritional evaluation.", "major", 1, [
                _me("COP-10.a.1", "Age-appropriate assessment tools are used for pediatric patients covering growth charts, developmental milestones, and nutritional status.", "conditional", "medical_director", 1, "commitment"),
                _me("COP-10.a.2", "Pediatric vital sign reference ranges and age-specific early warning scores are implemented.", "conditional", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-10.b", "Medication dosing for pediatric patients is weight-based with double-check protocols for high-risk medications.", "critical", 2, [
                _me("COP-10.b.1", "All pediatric medications are prescribed and administered using weight-based dosing calculations.", "conditional", "medical_director", 1, "core"),
                _me("COP-10.b.2", "High-alert medications for pediatric patients undergo independent double verification before administration.", "conditional", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-10.c", "Pediatric emergency equipment and resuscitation guidelines are available in all areas treating children.", "critical", 3, [
                _me("COP-10.c.1", "Pediatric emergency equipment including appropriately sized airways, defibrillator pads, and resuscitation drugs are available.", "conditional", "nursing_director", 1, "commitment"),
                _me("COP-10.c.2", "Staff caring for children are trained in pediatric life support and competency is periodically verified.", "conditional", "nursing_director", 2, "commitment"),
                _me("COP-10.c.3", "Pediatric clinical outcomes are monitored and benchmarked against published standards.", "conditional", "quality_officer", 3, "achievement"),
            ]),
        ]
    })

    # ─── COP-11: Neonatal Care ───
    standards.append({
        "code": "COP-11",
        "title": "Neonatal Care Services",
        "description": "Neonatal care units provide specialized management for sick and premature neonates with appropriate equipment, staffing, infection control, and family-centered care practices.",
        "display_order": 11,
        "objective_elements": [
            _oe("COP-11.a", "Neonatal care units are equipped and staffed as per the level of neonatal care provided.", "critical", 1, [
                _me("COP-11.a.1", "Neonatal care unit equipment includes incubators, warmers, phototherapy units, and monitoring devices appropriate to the designated level of care.", "conditional", "facility_director", 1, "commitment"),
                _me("COP-11.a.2", "Nurse-to-patient ratios in the NICU are maintained as per the defined standards for neonatal care levels.", "conditional", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-11.b", "Neonatal clinical protocols cover thermoregulation, feeding, respiratory support, and infection prevention.", "major", 2, [
                _me("COP-11.b.1", "Evidence-based neonatal care protocols address thermoregulation, feeding strategies, and respiratory support management.", "conditional", "medical_director", 1, "commitment"),
                _me("COP-11.b.2", "Infection prevention measures specific to neonatal care including hand hygiene and kangaroo care practices are implemented.", "conditional", "infection_control_officer", 2, "commitment"),
            ]),
            _oe("COP-11.c", "Neonatal outcomes are monitored including survival rates, morbidity, and developmental follow-up.", "major", 3, [
                _me("COP-11.c.1", "Neonatal quality indicators including survival by gestational age, infection rates, and retinopathy screening compliance are tracked.", "conditional", "quality_officer", 1, "commitment"),
                _me("COP-11.c.2", "A structured developmental follow-up program is offered for high-risk neonates after discharge.", "conditional", "medical_director", 2, "achievement"),
                _me("COP-11.c.3", "The NICU demonstrates data-driven improvement in key neonatal outcomes over time.", "conditional", "quality_officer", 3, "excellence"),
            ]),
        ]
    })

    # ─── COP-12: Rehabilitation Services ───
    standards.append({
        "code": "COP-12",
        "title": "Rehabilitation Services",
        "description": "Rehabilitation services are provided by qualified professionals with individualized treatment plans, measurable goals, and periodic reassessment of functional outcomes.",
        "display_order": 12,
        "objective_elements": [
            _oe("COP-12.a", "Rehabilitation assessments identify the patient's functional limitations and rehabilitation potential.", "major", 1, [
                _me("COP-12.a.1", "Comprehensive rehabilitation assessments evaluate physical, cognitive, and psychosocial functional status.", "conditional", "medical_director", 1, "commitment"),
                _me("COP-12.a.2", "Rehabilitation goals are established collaboratively with the patient and family.", "conditional", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-12.b", "Individualized rehabilitation plans are developed and delivered by a multidisciplinary team.", "major", 2, [
                _me("COP-12.b.1", "Rehabilitation plans detail interventions from physiotherapy, occupational therapy, speech therapy, and other relevant disciplines.", "conditional", "medical_director", 1, "commitment"),
                _me("COP-12.b.2", "Rehabilitation progress is reassessed at defined intervals using standardized outcome measures.", "conditional", "quality_officer", 2, "commitment"),
            ]),
            _oe("COP-12.c", "Functional outcomes of rehabilitation are measured and used for program improvement.", "major", 3, [
                _me("COP-12.c.1", "Functional outcomes at discharge from rehabilitation are measured using validated tools.", "conditional", "quality_officer", 1, "commitment"),
                _me("COP-12.c.2", "Rehabilitation outcomes data is analyzed and used to improve service delivery and patient experience.", "conditional", "quality_officer", 2, "achievement"),
                _me("COP-12.c.3", "Patient satisfaction with rehabilitation services is assessed and improvement actions are implemented.", "conditional", "quality_officer", 3, "commitment"),
            ]),
        ]
    })

    # ─── COP-13: End of Life Care ───
    standards.append({
        "code": "COP-13",
        "title": "End of Life Care",
        "description": "The organization provides compassionate end-of-life care respecting patient and family wishes, with attention to symptom management, emotional support, and cultural sensitivity.",
        "display_order": 13,
        "objective_elements": [
            _oe("COP-13.a", "End-of-life care policies address symptom management, patient dignity, and family involvement.", "major", 1, [
                _me("COP-13.a.1", "An end-of-life care policy addresses pain and symptom management, emotional support, and respect for patient dignity.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-13.a.2", "Clinical staff are trained in palliative care principles and compassionate communication with dying patients.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-13.b", "Patient and family preferences regarding resuscitation status and treatment limitations are documented.", "major", 2, [
                _me("COP-13.b.1", "Do-not-resuscitate orders and advance directives are documented and communicated to the care team.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-13.b.2", "Family members are supported through counseling and bereavement services during and after end-of-life care.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-13.c", "Cultural, religious, and spiritual needs are addressed in end-of-life care.", "major", 3, [
                _me("COP-13.c.1", "The organization facilitates access to spiritual and religious support based on patient and family preferences.", "applicable", "nursing_director", 1, "commitment"),
                _me("COP-13.c.2", "Care after death respects cultural practices and follows defined post-mortem procedures.", "applicable", "nursing_director", 2, "commitment"),
                _me("COP-13.c.3", "End-of-life care quality indicators are monitored and used to enhance palliative care services.", "applicable", "quality_officer", 3, "achievement"),
            ]),
        ]
    })

    # ─── COP-14: Nutritional Care ───
    standards.append({
        "code": "COP-14",
        "title": "Nutritional Care and Therapy",
        "description": "Patients receive nutritional screening at admission, individualized dietary plans, and therapeutic nutrition management as part of the overall care plan.",
        "display_order": 14,
        "objective_elements": [
            _oe("COP-14.a", "Nutritional screening is performed at admission to identify patients at nutritional risk.", "major", 1, [
                _me("COP-14.a.1", "A validated nutritional screening tool is used to assess all patients at admission for nutritional risk.", "applicable", "nursing_director", 1, "commitment"),
                _me("COP-14.a.2", "Patients identified as nutritionally at-risk receive a detailed nutritional assessment by a qualified dietician.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-14.b", "Individualized dietary plans are developed and therapeutic diets are prescribed based on clinical needs.", "major", 2, [
                _me("COP-14.b.1", "Therapeutic diets are prescribed based on clinical condition, cultural preferences, and nutritional assessment findings.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-14.b.2", "Food preparation and delivery processes ensure dietary orders are accurately fulfilled and food safety is maintained.", "applicable", "facility_director", 2, "commitment"),
            ]),
            _oe("COP-14.c", "Nutritional care outcomes are monitored including patient satisfaction with food services.", "major", 3, [
                _me("COP-14.c.1", "Patient satisfaction with food services is surveyed and results are used for service improvement.", "applicable", "quality_officer", 1, "commitment"),
                _me("COP-14.c.2", "Nutritional outcomes for at-risk patients are tracked during hospitalization.", "applicable", "quality_officer", 2, "commitment"),
            ]),
        ]
    })

    # ─── COP-15: Pain Management ───
    standards.append({
        "code": "COP-15",
        "title": "Pain Management",
        "description": "The organization has a comprehensive pain management program that includes assessment, treatment, reassessment, and patient education, using validated pain scales.",
        "display_order": 15,
        "objective_elements": [
            _oe("COP-15.a", "Pain assessment is performed using validated scales appropriate to the patient population.", "major", 1, [
                _me("COP-15.a.1", "Validated pain assessment scales are used for all patient populations including numeric, visual analogue, and behavioral scales.", "applicable", "nursing_director", 1, "commitment"),
                _me("COP-15.a.2", "Pain is assessed at regular intervals, with changes in condition, and after pain-relieving interventions.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-15.b", "A documented pain management protocol guides pharmacological and non-pharmacological interventions.", "major", 2, [
                _me("COP-15.b.1", "Pain management protocols include both pharmacological and non-pharmacological intervention options.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-15.b.2", "Patients and families are educated on pain management options and their role in reporting pain.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-15.c", "Pain management outcomes are monitored and the program is improved based on patient feedback.", "major", 3, [
                _me("COP-15.c.1", "Pain management effectiveness is monitored through reassessment scores and patient satisfaction data.", "applicable", "quality_officer", 1, "commitment"),
                _me("COP-15.c.2", "Pain management audit findings drive improvements in assessment tools, protocols, and staff training.", "applicable", "quality_officer", 2, "achievement"),
                _me("COP-15.c.3", "The organization demonstrates a structured pain management program as a patient right.", "applicable", "patient_safety_officer", 3, "commitment"),
            ]),
        ]
    })

    # ─── COP-16: Use of Restraints ───
    standards.append({
        "code": "COP-16",
        "title": "Use of Restraints",
        "description": "Restraint use is guided by policy, limited to clinically justified situations, and monitored with attention to patient safety, dignity, and regular reassessment.",
        "display_order": 16,
        "objective_elements": [
            _oe("COP-16.a", "A restraint policy defines criteria, types, and authorization requirements for restraint use.", "major", 1, [
                _me("COP-16.a.1", "A documented restraint policy defines the clinical indications, types of restraints, and authorization requirements.", "applicable", "patient_safety_officer", 1, "commitment"),
                _me("COP-16.a.2", "Alternatives to restraint use are explored and documented before restraints are applied.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-16.b", "Patients in restraints are monitored at defined intervals and restraints are removed as soon as clinically safe.", "major", 2, [
                _me("COP-16.b.1", "Patients under restraint are monitored at defined intervals for circulation, skin integrity, and clinical necessity for continued use.", "applicable", "nursing_director", 1, "commitment"),
                _me("COP-16.b.2", "Restraint orders are time-limited and require periodic reassessment and renewal by a physician.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-16.c", "Restraint use data is analyzed for trends and improvement in reducing restraint utilization.", "major", 3, [
                _me("COP-16.c.1", "Restraint use data is tracked, analyzed for trends, and used to implement reduction strategies.", "applicable", "quality_officer", 1, "commitment"),
                _me("COP-16.c.2", "Staff training on de-escalation techniques and restraint alternatives is conducted regularly.", "applicable", "nursing_director", 2, "commitment"),
            ]),
        ]
    })

    # ─── COP-17: Care of Vulnerable Patients ───
    standards.append({
        "code": "COP-17",
        "title": "Care of Vulnerable Patients",
        "description": "The organization identifies and provides additional safeguards for vulnerable patients including children, elderly, disabled, mentally ill, and victims of abuse.",
        "display_order": 17,
        "objective_elements": [
            _oe("COP-17.a", "Policies identify categories of vulnerable patients and define additional safeguards for their care.", "major", 1, [
                _me("COP-17.a.1", "A policy defines categories of vulnerable patients and the additional care safeguards applicable to each category.", "applicable", "patient_safety_officer", 1, "commitment"),
                _me("COP-17.a.2", "Staff are trained to identify and appropriately respond to signs of abuse, neglect, or exploitation.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-17.b", "Processes exist for mandatory reporting and management of suspected abuse or neglect cases.", "major", 2, [
                _me("COP-17.b.1", "Procedures for mandatory reporting of suspected abuse or neglect comply with legal requirements.", "applicable", "medical_director", 1, "core"),
                _me("COP-17.b.2", "A multidisciplinary approach is used for managing cases of suspected abuse including social work involvement.", "applicable", "nursing_director", 2, "commitment"),
            ]),
            _oe("COP-17.c", "Security and safety measures protect vulnerable patients from harm within the facility.", "major", 3, [
                _me("COP-17.c.1", "Enhanced security measures are in place for vulnerable patient areas including pediatric wards and psychiatric units.", "applicable", "facility_director", 1, "commitment"),
                _me("COP-17.c.2", "Infant and child security protocols including identification bands and controlled access are implemented.", "conditional", "nursing_director", 2, "commitment"),
            ]),
        ]
    })

    # ─── COP-18: Clinical Outcomes Monitoring ───
    standards.append({
        "code": "COP-18",
        "title": "Clinical Outcomes Monitoring",
        "description": "The organization systematically monitors clinical outcomes using defined indicators, analyzes trends, benchmarks performance, and implements improvement actions.",
        "display_order": 18,
        "objective_elements": [
            _oe("COP-18.a", "Clinical outcome indicators are defined for major clinical services and specialties.", "major", 1, [
                _me("COP-18.a.1", "A defined set of clinical outcome indicators is established for each major clinical department and specialty.", "applicable", "quality_officer", 1, "commitment"),
                _me("COP-18.a.2", "Outcome indicators include mortality rates, readmission rates, infection rates, and complication rates.", "applicable", "quality_officer", 2, "commitment"),
            ]),
            _oe("COP-18.b", "Clinical outcome data is collected, analyzed, and reviewed by clinical leadership periodically.", "major", 2, [
                _me("COP-18.b.1", "Clinical outcome data is collected accurately and analyzed using appropriate statistical methods.", "applicable", "quality_officer", 1, "commitment"),
                _me("COP-18.b.2", "Clinical outcome review meetings are conducted periodically with clinical leadership participation.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-18.c", "Benchmarking of clinical outcomes is performed and improvement projects are initiated based on findings.", "major", 3, [
                _me("COP-18.c.1", "Clinical outcomes are benchmarked against internal trends and external published benchmarks.", "applicable", "quality_officer", 1, "achievement"),
                _me("COP-18.c.2", "Quality improvement projects are initiated based on outcome analysis and benchmarking results.", "applicable", "quality_officer", 2, "commitment"),
                _me("COP-18.c.3", "The organization demonstrates sustained improvement in key clinical outcome indicators over time.", "applicable", "quality_officer", 3, "excellence"),
            ]),
        ]
    })

    # ─── COP-19: Research Activities ───
    standards.append({
        "code": "COP-19",
        "title": "Clinical Research and Ethics",
        "description": "Clinical research activities are conducted under an ethics committee with informed consent, patient safety protections, and regulatory compliance.",
        "display_order": 19,
        "objective_elements": [
            _oe("COP-19.a", "An institutional ethics committee reviews and approves all clinical research involving patients.", "major", 1, [
                _me("COP-19.a.1", "An institutional ethics committee is constituted as per regulatory requirements and reviews all research proposals involving human subjects.", "conditional", "medical_director", 1, "commitment"),
                _me("COP-19.a.2", "Research protocols are reviewed for scientific merit, ethical standards, and patient safety before approval.", "conditional", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-19.b", "Informed consent for research is separate from clinical consent and explains risks, benefits, and voluntary participation.", "major", 2, [
                _me("COP-19.b.1", "Research-specific informed consent is obtained from all participants, distinct from clinical treatment consent.", "conditional", "medical_director", 1, "core"),
                _me("COP-19.b.2", "Research participants are informed of their right to withdraw without impact on their clinical care.", "conditional", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-19.c", "Research activities are monitored for compliance with approved protocols and adverse event reporting.", "major", 3, [
                _me("COP-19.c.1", "Ongoing research is monitored by the ethics committee for protocol compliance and participant safety.", "conditional", "quality_officer", 1, "commitment"),
                _me("COP-19.c.2", "Adverse events in research participants are reported to the ethics committee and regulatory authorities as required.", "conditional", "patient_safety_officer", 2, "commitment"),
            ]),
        ]
    })

    # ─── COP-20: High-Risk Procedures and Services ───
    standards.append({
        "code": "COP-20",
        "title": "High-Risk Procedures and Services",
        "description": "The organization identifies high-risk procedures and services, implements additional safety protocols, and monitors outcomes to minimize preventable complications.",
        "display_order": 20,
        "objective_elements": [
            _oe("COP-20.a", "High-risk procedures and services are identified and additional safety measures are implemented.", "critical", 1, [
                _me("COP-20.a.1", "A defined list of high-risk procedures and services is maintained and reviewed periodically.", "applicable", "patient_safety_officer", 1, "commitment"),
                _me("COP-20.a.2", "Additional safety protocols including pre-procedure verification and time-out procedures are mandated for all high-risk procedures.", "applicable", "patient_safety_officer", 2, "core"),
            ]),
            _oe("COP-20.b", "Informed consent for high-risk procedures includes detailed discussion of risks, benefits, and alternatives.", "major", 2, [
                _me("COP-20.b.1", "Informed consent for high-risk procedures includes a documented discussion of specific risks, benefits, and alternative treatment options.", "applicable", "medical_director", 1, "commitment"),
                _me("COP-20.b.2", "Consent is obtained by the performing clinician and verified as part of the pre-procedure checklist.", "applicable", "medical_director", 2, "commitment"),
            ]),
            _oe("COP-20.c", "Outcomes of high-risk procedures are monitored with focused attention on complication rates and near-misses.", "major", 3, [
                _me("COP-20.c.1", "Complication rates and adverse outcomes for high-risk procedures are tracked by procedure type.", "applicable", "quality_officer", 1, "commitment"),
                _me("COP-20.c.2", "Near-miss events related to high-risk procedures are analyzed using root cause analysis methodology.", "applicable", "patient_safety_officer", 2, "commitment"),
            ]),
        ]
    })

    return {
        "chapter_code": "COP",
        "edition_version": "6.0",
        "standards": standards
    }


def _oe(code, description, severity, order, mes):
    return {
        "code": code,
        "description": description,
        "severity": severity,
        "display_order": order,
        "measurable_elements": mes
    }

def _me(code, description, applicability, owner, order, classification):
    return {
        "code": code,
        "description": description,
        "applicability_default": applicability,
        "scoring_weight": 1.0,
        "risk_weight": 1.0,
        "default_owner_role": owner,
        "display_order": order,
        "classification": classification
    }

def verify(data):
    errors = []
    for chapter in data:
        code = chapter["chapter_code"]
        total_mes = 0
        classifications = {"core": 0, "commitment": 0, "achievement": 0, "excellence": 0}
        n_standards = len(chapter["standards"])

        for std in chapter["standards"]:
            for oe in std["objective_elements"]:
                for me in oe["measurable_elements"]:
                    total_mes += 1
                    cls = me.get("classification", "unknown")
                    if cls in classifications:
                        classifications[cls] += 1
                    else:
                        errors.append(f"{code}: Unknown classification '{cls}' in {me['code']}")

        print(f"\n{code} Chapter:")
        print(f"  Standards: {n_standards}")
        print(f"  Total MEs: {total_mes}")
        print(f"  Classifications: {classifications}")

        # Expected counts
        expected = {
            "AAC": {"standards": 13, "mes": 87, "core": 6, "commitment": 68, "achievement": 9, "excellence": 4},
            "COP": {"standards": 20, "mes": 136, "core": 13, "commitment": 107, "achievement": 12, "excellence": 4},
        }

        if code in expected:
            exp = expected[code]
            if n_standards != exp["standards"]:
                errors.append(f"{code}: Expected {exp['standards']} standards, got {n_standards}")
            if total_mes != exp["mes"]:
                errors.append(f"{code}: Expected {exp['mes']} MEs, got {total_mes}")
            for cls_name in ["core", "commitment", "achievement", "excellence"]:
                if classifications[cls_name] != exp[cls_name]:
                    errors.append(f"{code}: Expected {exp[cls_name]} {cls_name}, got {classifications[cls_name]}")

    return errors

if __name__ == "__main__":
    aac = build_aac()
    cop = build_cop()
    data = [aac, cop]

    errors = verify(data)

    if errors:
        print("\n❌ ERRORS FOUND:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\n✅ All counts verified! Writing JSON file...")
        outpath = r"C:\Users\HP\Downloads\hospital-admin-system\backend\app\nabh\data\nabh_6th_requirements_aac_cop.json"
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"File written to: {outpath}")
