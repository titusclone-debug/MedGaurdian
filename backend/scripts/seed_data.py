"""
Seed data script — Populates MedGuardian with sample data for development.
Run this after initial database creation.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from app.core.database import engine, SessionLocal
from app.core.security import hash_password
from app.models.database import (
    Base, Hospital, Staff, FundAccount, FundTransaction,
    ConsentRecord, BMWLog, License, ComplianceRecord,
    RiskAlert, RegulatoryUpdate,
    UserRole, FundType, ConsentStatus, BMWCategory,
    LicenseStatus, ComplianceStatus, RiskLevel
)


def _seed_password(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is required for sample-data seeding. "
            "Passwords are never embedded in source control."
        )
    return value


def seed():
    """Seed the database with realistic sample data."""
    print("Seeding MedGuardian database...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        existing_hospital = db.query(Hospital).filter(Hospital.id == "hospital-001").first()
        if existing_hospital:
            print("Sample database already exists; no credentials or records were changed.")
            return

        # === HOSPITAL ===
        hospital = Hospital(
            id="hospital-001",
            name="St. Mary's Mission Hospital",
            registration_number="CE/KL/2024/1847",
            fcra_number="FCRA/05284019",
            fcra_expiry=datetime(2027, 1, 1),
            nabh_accreditation_id="NABH/2024/H/1847",
            nabh_edition="6th",
            nabh_expiry=datetime(2027, 5, 31),
            state="Kerala",
            district="Kottayam",
            address="Pala Road, Kottayam, Kerala 686001",
            pincode="686001",
            hospital_type="mission",
            bed_count=200,
            is_rural=True,
            has_emergency=True,
            has_icu=True,
            has_operation_theatre=True,
            overall_risk_score=35.2,
            risk_level=RiskLevel.MEDIUM,
            last_audit_date=datetime(2025, 6, 15),
            next_audit_date=datetime(2026, 6, 15),
            onboarding_stage="completed",
        )
        db.add(hospital)
        
        # === STAFF ===
        staff_members = [
            Staff(id="staff-000", hospital_id="hospital-001", employee_id="SUPER001", name="CEO Master Admin", role=UserRole.SUPER_ADMIN, department="HQ Governance", email="ceo@medguardian.org", phone="+91-9999999999", hashed_password=hash_password(_seed_password("MEDGUARDIAN_SEED_SUPER_ADMIN_PASSWORD")), qualification="MedGuardian Executive Founder", is_active=True),
            Staff(id="staff-001", hospital_id="hospital-001", employee_id="EMP001", name="Dr. Sarah Chen", role=UserRole.HOSPITAL_ADMIN, department="Administration", email="admin@stmarys.org", phone="+91-9487000001", hashed_password=hash_password(_seed_password("MEDGUARDIAN_SEED_HOSPITAL_ADMIN_PASSWORD")), qualification="MBBS, MD (Hospital Administration)", is_active=True),
            Staff(id="staff-002", hospital_id="hospital-001", employee_id="EMP002", name="Dr. Thomas Mathew", role=UserRole.DOCTOR, department="General Medicine", email="thomas@stmarys.org", phone="+91-9487000002", hashed_password=hash_password(_seed_password("MEDGUARDIAN_SEED_DOCTOR_PASSWORD")), qualification="MBBS, MD (General Medicine)", registration_number="KMC/2015/4521", is_active=True),
            Staff(id="staff-003", hospital_id="hospital-001", employee_id="EMP003", name="Nurse Priya Joseph", role=UserRole.NURSE, department="Surgery", email="priya@stmarys.org", phone="+91-9487000003", hashed_password=hash_password(_seed_password("MEDGUARDIAN_SEED_NURSE_PASSWORD")), qualification="B.Sc Nursing", registration_number="KNR/2018/7832", is_active=True),
            Staff(id="staff-004", hospital_id="hospital-001", employee_id="EMP004", name="Dr. Mary Varghese", role=UserRole.COMPLIANCE_OFFICER, department="Quality", email="mary@stmarys.org", phone="+91-9487000004", hashed_password=hash_password(_seed_password("MEDGUARDIAN_SEED_COMPLIANCE_PASSWORD")), qualification="MBBS, PGDHM", is_active=True),
            Staff(id="staff-005", hospital_id="hospital-001", employee_id="EMP005", name="James Kurien", role=UserRole.ACCOUNTANT, department="Finance", email="james@stmarys.org", phone="+91-9487000005", hashed_password=hash_password(_seed_password("MEDGUARDIAN_SEED_ACCOUNTANT_PASSWORD")), qualification="CA, MBA", is_active=True),
        ]
        for s in staff_members:
            db.add(s)
        db.commit()
        
        # === FCRA ACCOUNTS ===
        fcra_acc1 = FundAccount(id="acc-001", hospital_id="hospital-001", account_name="FCRA Designated Account", account_number="3847562910", bank_name="State Bank of India", branch="Kottayam Main", fund_type=FundType.FCRA_FOREIGN, is_fcra_designated=True, fcra_utilization_purpose="Healthcare services, medical equipment, and community health programs", current_balance=2450000, annual_budget=5000000, ytd_expenditure=1850000, last_reconciliation=datetime(2026, 5, 1), compliance_status=ComplianceStatus.COMPLIANT)
        fcra_acc2 = FundAccount(id="acc-002", hospital_id="hospital-001", account_name="FCRA Savings Account", account_number="9281746503", bank_name="Federal Bank", branch="Pala Branch", fund_type=FundType.FCRA_FOREIGN, is_fcra_designated=True, fcra_utilization_purpose="Infrastructure development and staff training", current_balance=890000, annual_budget=2000000, ytd_expenditure=720000, last_reconciliation=datetime(2026, 5, 1), compliance_status=ComplianceStatus.COMPLIANT)
        db.add_all([fcra_acc1, fcra_acc2])
        
        # === LICENSES ===
        licenses = [
            License(id="lic-001", hospital_id="hospital-001", license_name="Clinical Establishment Registration", license_number="CE/KL/2024/1847", issuing_authority="District Health Officer", license_type="clinical_establishment", issued_date=datetime(2024, 4, 1), expiry_date=datetime(2026, 3, 31), status=LicenseStatus.EXPIRED, renewal_reminder_days=90),
            License(id="lic-002", hospital_id="hospital-001", license_name="Fire Safety NOC", license_number="FS/KTM/2023/421", issuing_authority="Fire & Rescue Services", license_type="fire", issued_date=datetime(2023, 6, 15), expiry_date=datetime(2026, 6, 14), status=LicenseStatus.EXPIRING_SOON, renewal_reminder_days=90),
            License(id="lic-003", hospital_id="hospital-001", license_name="Pharmacy License", license_number="PH/KL/2025/1205", issuing_authority="Drug Control Department", license_type="pharmacy", issued_date=datetime(2025, 1, 1), expiry_date=datetime(2027, 12, 31), status=LicenseStatus.ACTIVE, renewal_reminder_days=90),
            License(id="lic-004", hospital_id="hospital-001", license_name="Pollution Control Consent", license_number="PCB/KTM/2024/892", issuing_authority="Kerala PCB", license_type="pollution", issued_date=datetime(2024, 7, 1), expiry_date=datetime(2026, 6, 30), status=LicenseStatus.EXPIRING_SOON, renewal_reminder_days=90),
            License(id="lic-005", hospital_id="hospital-001", license_name="Blood Bank License", license_number="BB/KL/2025/067", issuing_authority="Drug Controller", license_type="blood_bank", issued_date=datetime(2025, 3, 1), expiry_date=datetime(2028, 2, 28), status=LicenseStatus.ACTIVE, renewal_reminder_days=90),
            License(id="lic-006", hospital_id="hospital-001", license_name="Biomedical Waste Authorization", license_number="BMW/SPCB/2024/334", issuing_authority="Kerala PCB", license_type="bmw", issued_date=datetime(2024, 1, 1), expiry_date=datetime(2026, 12, 31), status=LicenseStatus.ACTIVE, renewal_reminder_days=90),
            License(id="lic-007", hospital_id="hospital-001", license_name="NABH Accreditation", license_number="NABH/2024/H/1847", issuing_authority="NABH", license_type="nabh", issued_date=datetime(2024, 6, 1), expiry_date=datetime(2027, 5, 31), status=LicenseStatus.ACTIVE, renewal_reminder_days=180),
            License(id="lic-008", hospital_id="hospital-001", license_name="FCRA Registration", license_number="FCRA/05284019", issuing_authority="MHA, Govt of India", license_type="fcra", issued_date=datetime(2022, 1, 1), expiry_date=datetime(2027, 1, 1), status=LicenseStatus.ACTIVE, renewal_reminder_days=180),
        ]
        for lic in licenses:
            db.add(lic)
        
        # === NABH COMPLIANCE RECORDS ===
        nabh_records = [
            ComplianceRecord(id="comp-001", hospital_id="hospital-001", standard_code="AAC-1", standard_name="Patient Access Services", chapter="ACC", status=ComplianceStatus.COMPLIANT, current_score=0.9, gap_percentage=10),
            ComplianceRecord(id="comp-002", hospital_id="hospital-001", standard_code="AAC-2", standard_name="Assessment of Patients", chapter="ACC", status=ComplianceStatus.COMPLIANT, current_score=0.85, gap_percentage=15),
            ComplianceRecord(id="comp-003", hospital_id="hospital-001", standard_code="PC-1", standard_name="Patient Rights and Education", chapter="PC", status=ComplianceStatus.COMPLIANT, current_score=0.88, gap_percentage=12),
            ComplianceRecord(id="comp-004", hospital_id="hospital-001", standard_code="PC-3", standard_name="Medication Management", chapter="PC", status=ComplianceStatus.PARTIALLY_COMPLIANT, current_score=0.65, gap_percentage=35, remediation_plan="Implement medication reconciliation protocol", remediation_owner="staff-002"),
            ComplianceRecord(id="comp-005", hospital_id="hospital-001", standard_code="PC-7", standard_name="Infection Prevention and Control", chapter="PC", status=ComplianceStatus.COMPLIANT, current_score=0.92, gap_percentage=8),
            ComplianceRecord(id="comp-006", hospital_id="hospital-001", standard_code="PC-8", standard_name="Patient Safety Goals", chapter="PC", status=ComplianceStatus.PARTIALLY_COMPLIANT, current_score=0.75, gap_percentage=25, remediation_plan="Complete PSG-3 documentation"),
            ComplianceRecord(id="comp-007", hospital_id="hospital-001", standard_code="FMS-1", standard_name="Fire Safety", chapter="FMS", status=ComplianceStatus.COMPLIANT, current_score=0.95, gap_percentage=5),
            ComplianceRecord(id="comp-008", hospital_id="hospital-001", standard_code="FMS-2", standard_name="Biomedical Waste Management", chapter="FMS", status=ComplianceStatus.COMPLIANT, current_score=0.95, gap_percentage=5),
            ComplianceRecord(id="comp-009", hospital_id="hospital-001", standard_code="QMS-3", standard_name="Internal Audit", chapter="QMS", status=ComplianceStatus.PARTIALLY_COMPLIANT, current_score=0.70, gap_percentage=30, remediation_plan="Schedule quarterly internal audits"),
            ComplianceRecord(id="comp-010", hospital_id="hospital-001", standard_code="HR-1", standard_name="Staff Qualifications", chapter="HR", status=ComplianceStatus.COMPLIANT, current_score=0.95, gap_percentage=5),
        ]
        for c in nabh_records:
            db.add(c)
        
        # === RISK ALERTS ===
        alerts = [
            RiskAlert(id="alert-001", hospital_id="hospital-001", alert_type="license_expiry", severity=RiskLevel.CRITICAL, title="Clinical Establishment Registration Expired", description="CE registration expired 47 days ago.", recommended_action="File emergency renewal.", risk_score=95, probability=1.0, impact=10.0, due_date=datetime(2026, 5, 20)),
            RiskAlert(id="alert-002", hospital_id="hospital-001", alert_type="license_expiry", severity=RiskLevel.HIGH, title="Fire Safety NOC expiring in 28 days", description="Fire NOC expires June 14, 2026.", recommended_action="File renewal with Fire & Rescue Services.", risk_score=72, probability=1.0, impact=8.0, due_date=datetime(2026, 5, 25)),
            RiskAlert(id="alert-003", hospital_id="hospital-001", alert_type="nabh", severity=RiskLevel.HIGH, title="NABH Gap: Medication Management", description="35% compliance gap in PC-3.", recommended_action="Implement medication reconciliation.", risk_score=70, probability=0.8, impact=7.0, due_date=datetime(2026, 6, 1)),
            RiskAlert(id="alert-004", hospital_id="hospital-001", alert_type="fcra", severity=RiskLevel.HIGH, title="FCRA quarterly utilization report due", description="Q4 FY2025-26 certificate due May 30.", recommended_action="Prepare utilization certificate.", risk_score=65, probability=1.0, impact=6.0, due_date=datetime(2026, 5, 30)),
        ]
        for a in alerts:
            db.add(a)
        
        # === BMW LOGS (Recent) ===
        import random
        departments = ["Surgery", "ICU", "Laboratory", "Maternity", "Emergency", "Pharmacy", "OPD"]
        categories = list(BMWCategory)
        
        for day in range(14):
            date = datetime.utcnow() - timedelta(days=day)
            for _ in range(random.randint(3, 8)):
                cat = random.choice(categories)
                bmw = BMWLog(
                    hospital_id="hospital-001",
                    waste_date=date,
                    category=cat,
                    weight_kg=round(random.uniform(0.5, 25.0), 1),
                    source_department=random.choice(departments),
                    treatment_method="Incineration" if cat in [BMWCategory.YELLOW, BMWCategory.BLUE] else "Autoclaving",
                    is_properly_segregated=random.random() > 0.05,
                    is_properly_labeled=random.random() > 0.03,
                    is_properly_stored=random.random() > 0.02,
                )
                db.add(bmw)
        
        # Seed granular NABH objectives
        from app.nabh.seeder import seed_nabh_objectives
        seed_nabh_objectives(db, "hospital-001")
        
        db.commit()
        print("Database seeded successfully!")
        print("   1 hospital")
        print(f"   {len(staff_members)} staff members")
        print("   2 FCRA accounts")
        print(f"   {len(licenses)} licenses")
        print(f"   {len(nabh_records)} NABH compliance records")
        print(f"   {len(alerts)} risk alerts")
        print("   ~70 BMW log entries")
        
    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
