"""
MedGuardian — Database Models
Comprehensive models for hospital administration and compliance tracking.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import enum
import uuid


Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


# ============================================================
# ENUMS
# ============================================================

class UserRole(enum.Enum):
    SUPER_ADMIN = "super_admin"
    HOSPITAL_ADMIN = "hospital_admin"
    COMPLIANCE_OFFICER = "compliance_officer"
    DOCTOR = "doctor"
    NURSE = "nurse"
    PHARMACIST = "pharmacist"
    LAB_TECHNICIAN = "lab_technician"
    ACCOUNTANT = "accountant"
    WARD_BOY = "ward_boy"
    VIEWER = "viewer"


class RiskLevel(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class ComplianceStatus(enum.Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNDER_REVIEW = "under_review"
    NOT_APPLICABLE = "not_applicable"


class ConsentStatus(enum.Enum):
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class BMWCategory(enum.Enum):
    YELLOW = "yellow"      # Human anatomical, soiled waste
    RED = "red"            # Contaminated recyclable
    WHITE = "white"        # Sharps waste
    BLUE = "blue"          # Medicines, cytotoxic
    BLACK = "black"        # General municipal


class LicenseStatus(enum.Enum):
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"  # < 90 days
    EXPIRED = "expired"
    RENEWAL_IN_PROGRESS = "renewal_in_progress"
    SUSPENDED = "suspended"


class FundType(enum.Enum):
    FCRA_FOREIGN = "fcra_foreign"
    FCRA_DOMESTIC = "fcra_domestic"
    GOVERNMENT_GRANT = "government_grant"
    PATIENT_FEES = "patient_fees"
    DONATION_DOMESTIC = "donation_domestic"
    CSR_FUNDS = "csr_funds"


class SeverityLevel(str, enum.Enum):
    CRITICAL = "critical"  # Direct patient safety or strict legal rules (BMW, Fire, etc.)
    MAJOR = "major"        # Systemic process gaps
    MINOR = "minor"        # Documentation and minor typos


class MaturityLevel(int, enum.Enum):
    NON_EXISTENT = 0
    AD_HOC = 1
    DEFINED = 2
    IMPLEMENTED = 3
    MEASURED = 4
    OPTIMIZED = 5


# ============================================================
# CORE MODELS
# ============================================================

class Hospital(Base):
    """The institution itself — the entity being protected."""
    __tablename__ = "hospitals"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    registration_number = Column(String(100), unique=True)
    fcra_number = Column(String(100), unique=True, nullable=True)
    fcra_expiry = Column(DateTime, nullable=True)
    nabh_accreditation_id = Column(String(100), nullable=True)
    nabh_edition = Column(String(20), default="6th")
    nabh_expiry = Column(DateTime, nullable=True)
    
    # Location
    state = Column(String(100))
    district = Column(String(100))
    address = Column(Text)
    pincode = Column(String(10))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Classification
    hospital_type = Column(String(50))  # mission, government, private, trust
    bed_count = Column(Integer, default=0)
    is_rural = Column(Boolean, default=False)
    has_emergency = Column(Boolean, default=True)
    has_icu = Column(Boolean, default=False)
    has_operation_theatre = Column(Boolean, default=False)
    
    # Risk Profile
    overall_risk_score = Column(Float, default=0.0)
    risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.MEDIUM)
    last_audit_date = Column(DateTime, nullable=True)
    next_audit_date = Column(DateTime, nullable=True)
    onboarding_stage = Column(String(50), default="profile")
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    licenses = relationship("License", back_populates="hospital")
    fund_accounts = relationship("FundAccount", back_populates="hospital")
    compliance_records = relationship("ComplianceRecord", back_populates="hospital")
    nabh_objectives = relationship("NABHObjective", back_populates="hospital", cascade="all, delete-orphan")
    bmw_logs = relationship("BMWLog", back_populates="hospital")
    consent_records = relationship("ConsentRecord", back_populates="hospital")
    risk_alerts = relationship("RiskAlert", back_populates="hospital")
    staff = relationship("Staff", back_populates="hospital")
    accreditation_profile = relationship("HospitalAccreditationProfile", back_populates="hospital", uselist=False, cascade="all, delete-orphan")
    nabh_requirements = relationship("HospitalNABHRequirement", back_populates="hospital", cascade="all, delete-orphan")


class Staff(Base):
    """Hospital staff with role-based access."""
    __tablename__ = "staff"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    employee_id = Column(String(50), unique=True)
    name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    department = Column(String(100))
    email = Column(String(255), unique=True)
    phone = Column(String(20))
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    
    # Qualifications
    qualification = Column(String(255))
    registration_number = Column(String(100))  # Medical council registration
    registration_expiry = Column(DateTime, nullable=True)
    
    # NABH Compliance
    training_records = Column(JSON, default=[])
    last_training_date = Column(DateTime, nullable=True)
    next_training_due = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    hospital = relationship("Hospital", back_populates="staff")


# ============================================================
# FCRA GUARDIAN MODELS
# ============================================================

class FundAccount(Base):
    """FCRA-compliant fund tracking. Separate accounts for foreign vs domestic."""
    __tablename__ = "fund_accounts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    account_name = Column(String(255), nullable=False)
    account_number = Column(String(50), nullable=False)
    bank_name = Column(String(255))
    branch = Column(String(255))
    fund_type = Column(SQLEnum(FundType), nullable=False)
    
    # FCRA Specific
    is_fcra_designated = Column(Boolean, default=False)
    fcra_utilization_purpose = Column(Text)
    
    # Balances
    current_balance = Column(Float, default=0.0)
    annual_budget = Column(Float, default=0.0)
    ytd_expenditure = Column(Float, default=0.0)
    
    # Compliance
    last_reconciliation = Column(DateTime, nullable=True)
    compliance_status = Column(SQLEnum(ComplianceStatus), default=ComplianceStatus.UNDER_REVIEW)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    hospital = relationship("Hospital", back_populates="fund_accounts")
    transactions = relationship("FundTransaction", back_populates="account")


class FundTransaction(Base):
    """Every rupee tracked. FCRA demands nothing less."""
    __tablename__ = "fund_transactions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    account_id = Column(String, ForeignKey("fund_accounts.id"), nullable=False)
    
    transaction_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(20))  # credit, debit
    description = Column(Text)
    purpose = Column(String(255))
    
    # FCRA Compliance Fields
    donor_name = Column(String(255), nullable=True)
    donor_country = Column(String(100), nullable=True)
    donor_passport_or_id = Column(String(100), nullable=True)
    utilization_certificate_ref = Column(String(100), nullable=True)
    
    # Audit Trail
    approved_by = Column(String, ForeignKey("staff.id"))
    approval_date = Column(DateTime, nullable=True)
    is_compliant = Column(Boolean, default=True)
    compliance_notes = Column(Text)
    
    # Hash chain for tamper-proof ledger
    transaction_hash = Column(String(64))
    previous_hash = Column(String(64))
    
    created_at = Column(DateTime, server_default=func.now())
    
    account = relationship("FundAccount", back_populates="transactions")
    
    __table_args__ = (
        Index("idx_transaction_date", "transaction_date"),
        Index("idx_fund_type_date", "account_id", "transaction_date"),
    )


# ============================================================
# DPDP CONSENT MANAGER MODELS
# ============================================================

class ConsentRecord(Base):
    """Digital Consent Artefact — blockchain-timestamped per DPDP 2026."""
    __tablename__ = "consent_records"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    
    # Patient Identity (purpose-limited)
    patient_id = Column(String(100), nullable=False)
    patient_name_hash = Column(String(64))  # Hashed for privacy
    patient_name = Column(String(255), nullable=True)
    patient_mobile = Column(String(20), nullable=True)
    patient_address = Column(Text, nullable=True)
    digital_signature = Column(Text, nullable=True)
    
    # Consent Details
    consent_type = Column(String(100))  # treatment, data_sharing, research, billing
    purpose = Column(Text, nullable=False)
    data_categories = Column(JSON)  # ["name", "diagnosis", "lab_results"]
    third_parties = Column(JSON, nullable=True)  # Who can access
    
    # Status
    status = Column(SQLEnum(ConsentStatus), default=ConsentStatus.PENDING)
    granted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)
    withdrawal_reason = Column(Text, nullable=True)
    
    # Verification
    consent_method = Column(String(50))  # digital_signature, otp, verbal_witness, thumbprint
    witness_id = Column(String, ForeignKey("staff.id"), nullable=True)
    otp_verified = Column(Boolean, default=False)
    
    # Blockchain/Tamper-proof
    artefact_hash = Column(String(64))
    previous_hash = Column(String(64))
    timestamp_proof = Column(Text)  # RFC 3161 timestamp or blockchain ref
    
    # DPDP Specific
    is_minor = Column(Boolean, default=False)
    guardian_consent_id = Column(String, nullable=True)
    language_preference = Column(String(20), default="en")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    hospital = relationship("Hospital", back_populates="consent_records")
    
    __table_args__ = (
        Index("idx_consent_patient", "patient_id"),
        Index("idx_consent_status", "status"),
        Index("idx_consent_expiry", "expires_at"),
    )


class DataBreachLog(Base):
    """DPDP mandates 72-hour breach notification. Track everything."""
    __tablename__ = "data_breach_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id"))
    
    breach_detected_at = Column(DateTime, nullable=False)
    breach_type = Column(String(100))  # unauthorized_access, data_leak, system_breach
    affected_records_count = Column(Integer, default=0)
    data_categories_affected = Column(JSON)
    
    # Response
    contained_at = Column(DateTime, nullable=True)
    notified_dpo_at = Column(DateTime, nullable=True)
    notified_board_at = Column(DateTime, nullable=True)
    notified_patients_at = Column(DateTime, nullable=True)
    notified_dpdp_board_at = Column(DateTime, nullable=True)  # Within 72 hours
    
    # Resolution
    root_cause = Column(Text)
    corrective_actions = Column(JSON)
    status = Column(String(50))  # detected, contained, investigating, resolved
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# BMW SENTINEL MODELS
# ============================================================

class BMWLog(Base):
    """Bio-Medical Waste tracking — every bag, every treatment, every disposal."""
    __tablename__ = "bmw_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    
    # Waste Details
    waste_date = Column(DateTime, nullable=False)
    category = Column(SQLEnum(BMWCategory), nullable=False)
    weight_kg = Column(Float, nullable=False)
    source_department = Column(String(100))
    source_ward = Column(String(100))
    
    # Treatment
    treatment_method = Column(String(50))  # autoclave, incineration, chemical, shredding
    treatment_date = Column(DateTime, nullable=True)
    treatment_operator = Column(String(255))
    treatment_machine_id = Column(String(100))
    treatment_temperature = Column(Float, nullable=True)
    treatment_duration_min = Column(Integer, nullable=True)
    
    # Disposal
    disposal_date = Column(DateTime, nullable=True)
    disposal_agency = Column(String(255))
    disposal_manifest_number = Column(String(100))
    disposal_vehicle_number = Column(String(50))
    
    # Compliance
    is_properly_segregated = Column(Boolean, default=True)
    is_properly_labeled = Column(Boolean, default=True)
    is_properly_stored = Column(Boolean, default=True)
    compliance_notes = Column(Text)
    
    # Image Recognition (for audit)
    image_path = Column(String(500), nullable=True)
    ai_classification = Column(String(50), nullable=True)
    ai_confidence = Column(Float, nullable=True)
    
    # Audit Trail
    recorded_by = Column(String, ForeignKey("staff.id"))
    verified_by = Column(String, ForeignKey("staff.id"), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    hospital = relationship("Hospital", back_populates="bmw_logs")
    
    __table_args__ = (
        Index("idx_bmw_date", "waste_date"),
        Index("idx_bmw_category", "category"),
        Index("idx_bmw_hospital_date", "hospital_id", "waste_date"),
    )


# ============================================================
# LICENSE & COMPLIANCE TRACKING
# ============================================================

class License(Base):
    """Every license, registration, and accreditation that keeps the hospital legal."""
    __tablename__ = "licenses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    
    license_name = Column(String(255), nullable=False)
    license_number = Column(String(100))
    issuing_authority = Column(String(255))
    license_type = Column(String(100))  # clinical_establishment, pharmacy, blood_bank, fire, pollution
    
    issued_date = Column(DateTime)
    expiry_date = Column(DateTime, nullable=True)
    renewal_date = Column(DateTime, nullable=True)
    
    status = Column(SQLEnum(LicenseStatus), default=LicenseStatus.ACTIVE)
    document_path = Column(String(500), nullable=True)
    
    # Auto-renewal tracking
    renewal_reminder_days = Column(Integer, default=90)
    last_reminder_sent = Column(DateTime, nullable=True)
    renewal_application_filed = Column(Boolean, default=False)
    renewal_application_date = Column(DateTime, nullable=True)
    
    # Compliance
    conditions = Column(JSON, nullable=True)  # Special conditions attached
    last_verified = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    hospital = relationship("Hospital", back_populates="licenses")
    
    __table_args__ = (
        Index("idx_license_expiry", "expiry_date"),
        Index("idx_license_status", "status"),
    )


class ComplianceRecord(Base):
    """NABH 6th Edition compliance tracking — every standard, every element."""
    __tablename__ = "compliance_records"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    
    # NABH Reference
    standard_code = Column(String(50), nullable=False)  # e.g., "PC-1", "FMS-2"
    standard_name = Column(String(255))
    chapter = Column(String(100))  # Patient Care, Facility Management, etc.
    element_description = Column(Text)
    
    # Compliance Status
    status = Column(SQLEnum(ComplianceStatus), default=ComplianceStatus.UNDER_REVIEW)
    evidence_path = Column(String(500), nullable=True)
    evidence_description = Column(Text)
    
    # Scoring
    max_score = Column(Float, default=1.0)
    current_score = Column(Float, default=0.0)
    gap_percentage = Column(Float, default=0.0)
    
    # Remediation
    remediation_plan = Column(Text, nullable=True)
    remediation_deadline = Column(DateTime, nullable=True)
    remediation_owner = Column(String, ForeignKey("staff.id"), nullable=True)
    
    # Audit Trail
    last_assessed = Column(DateTime, nullable=True)
    assessed_by = Column(String(255), nullable=True)
    next_assessment = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    hospital = relationship("Hospital", back_populates="compliance_records")
    
    __table_args__ = (
        Index("idx_compliance_standard", "standard_code"),
        Index("idx_compliance_status", "status"),
    )


# ============================================================
# RISK & ALERTS
# ============================================================

class RiskAlert(Base):
    """Proactive risk detection — the 'Weather Forecast' for institutional risk."""
    __tablename__ = "risk_alerts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    
    alert_type = Column(String(100))  # fcra, dpdp, bmw, nabh, license, staffing, equipment
    severity = Column(SQLEnum(RiskLevel), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Risk Scoring
    risk_score = Column(Float, default=0.0)
    probability = Column(Float, default=0.0)  # 0-1
    impact = Column(Float, default=0.0)  # 0-10
    
    # Action
    recommended_action = Column(Text)
    assigned_to = Column(String, ForeignKey("staff.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    # Status
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String, ForeignKey("staff.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Auto-escalation
    escalation_level = Column(Integer, default=1)
    escalated_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    hospital = relationship("Hospital", back_populates="risk_alerts")
    
    __table_args__ = (
        Index("idx_alert_severity", "severity"),
        Index("idx_alert_type", "alert_type"),
        Index("idx_alert_resolved", "is_resolved"),
    )


class RegulatoryUpdate(Base):
    """Tracks changes in Gazette of India, MoHFW, NABH updates."""
    __tablename__ = "regulatory_updates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    
    source = Column(String(100))  # gazette, mohfw, nabh, state_health
    update_type = Column(String(100))  # new_rule, amendment, notification, circular
    title = Column(String(500))
    summary = Column(Text)
    full_text = Column(Text)
    url = Column(String(1000))
    published_date = Column(DateTime)
    
    # AI Analysis
    semantic_diff = Column(Text)  # What changed from previous version
    impact_analysis = Column(Text)  # How this affects hospitals
    affected_areas = Column(JSON)  # ["fcra", "bmw", "nabh", "dpdp"]
    compliance_actions_required = Column(JSON)
    
    # Processing
    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    embeddings_stored = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index("idx_regulatory_date", "published_date"),
        Index("idx_regulatory_source", "source"),
    )


class AuditLog(Base):
    """Immutable audit trail for all system actions."""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    
    user_id = Column(String, ForeignKey("staff.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String)
    
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Hash chain
    entry_hash = Column(String(64))
    previous_hash = Column(String(64))
    
    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
    )


class NABHObjective(Base):
    """
    Granular NABH 6th Edition Standard & Element Compliance Tracking.
    
    WARNING: LEGACY MODEL
    Do not build new features on this model; use the upcoming versioned ontology models.
    """
    __tablename__ = "nabh_objectives"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    
    # Hierarchical Code Identifiers (e.g., PC-4.a)
    chapter_code = Column(String(50), nullable=False)   # e.g., "PC"
    objective_number = Column(Integer, nullable=False)  # e.g., 4
    element_letter = Column(String(10), nullable=False)  # e.g., "a"
    standard_code = Column(String(100), nullable=False)  # Unique full index (e.g. "PC-4.a")
    standard_name = Column(String(255), nullable=False)
    
    # Severity & Maturity Level
    severity = Column(SQLEnum(SeverityLevel), default=SeverityLevel.MAJOR)
    maturity_level = Column(SQLEnum(MaturityLevel), default=MaturityLevel.NON_EXISTENT)
    
    # 4-Tier Evidentiary Paths (The core audit trail)
    policy_doc_url = Column(String(500), nullable=True)          # SOP document reference
    implementation_logs_count = Column(Integer, default=0)        # Auto-scanned database items count
    monitoring_indicator_rate = Column(Float, nullable=True)     # Auto-calculated performance percentage
    cqi_project_id = Column(String(100), nullable=True)          # Reference to active CAPA loops
    
    # Remediation Workflow
    remediation_plan = Column(Text, nullable=True)
    remediation_deadline = Column(DateTime, nullable=True)
    remediation_owner = Column(String, ForeignKey("staff.id"), nullable=True)
    
    # Auditing metadata
    last_assessed = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assessed_by = Column(String(255), default="System Agent")
    
    # Relationships
    hospital = relationship("Hospital", back_populates="nabh_objectives")


# ============================================================
# NEW VERSIONED NABH ONTOLOGY MODELS (Task 2)
# ============================================================

class EditionStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class ApplicabilityDefault(enum.Enum):
    APPLICABLE = "applicable"
    CONDITIONAL = "conditional"
    NOT_APPLICABLE = "not_applicable"
    MANUAL_REVIEW = "manual_review"


class EvidenceType(enum.Enum):
    SOP = "sop"
    REGISTER = "register"
    TRAINING_RECORD = "training_record"
    LICENSE = "license"
    AUDIT_LOG = "audit_log"
    PHOTO = "photo"
    COMMITTEE_MINUTES = "committee_minutes"
    TELEMETRY = "telemetry"
    CAPA = "capa"


class NABHEdition(Base):
    """Accreditation standards edition."""
    __tablename__ = "nabh_editions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    version = Column(String(50), unique=True, nullable=False)
    status = Column(SQLEnum(EditionStatus), default=EditionStatus.DRAFT, nullable=False)
    effective_date = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    source_documents = relationship("NABHSourceDocument", back_populates="edition", cascade="all, delete-orphan")
    chapters = relationship("NABHChapter", back_populates="edition", cascade="all, delete-orphan")


class NABHSourceDocument(Base):
    """Source documentation backing the standards."""
    __tablename__ = "nabh_source_documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    edition_id = Column(String, ForeignKey("nabh_editions.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    publisher = Column(String(255), nullable=False)
    edition_version = Column(String(50), nullable=False)
    file_path_or_url = Column(String(500), nullable=True)
    checksum = Column(String(64), nullable=True)
    publication_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    edition = relationship("NABHEdition", back_populates="source_documents")
    citations = relationship("NABHRequirementCitation", back_populates="document")

    __table_args__ = (
        Index("idx_source_doc_edition", "edition_id"),
    )


class NABHChapter(Base):
    """High-level chapters (e.g. ACC, HIC, MOM)."""
    __tablename__ = "nabh_chapters"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    edition_id = Column(String, ForeignKey("nabh_editions.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    canonical_code = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    
    official_standards_count = Column(Integer, nullable=True)
    official_measurable_elements_count = Column(Integer, nullable=True)
    is_fully_seeded = Column(Boolean, default=False, nullable=False)

    # Category counts
    core_count = Column(Integer, nullable=True)
    commitment_count = Column(Integer, nullable=True)
    achievement_count = Column(Integer, nullable=True)
    excellence_count = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    edition = relationship("NABHEdition", back_populates="chapters")
    standards = relationship("NABHStandard", back_populates="chapter", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("edition_id", "canonical_code", name="uq_chapter_edition_code"),
        Index("idx_chapter_edition", "edition_id"),
    )


class NABHStandard(Base):
    """Specific standard groups under chapters (e.g. AAC 1, FMS 2)."""
    __tablename__ = "nabh_standards"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    edition_id = Column(String, ForeignKey("nabh_editions.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(String, ForeignKey("nabh_chapters.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    canonical_code = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    chapter = relationship("NABHChapter", back_populates="standards")
    objective_elements = relationship("NABHObjectiveElement", back_populates="standard", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("edition_id", "canonical_code", name="uq_standard_edition_code"),
        Index("idx_standard_edition", "edition_id"),
        Index("idx_standard_chapter", "chapter_id"),
    )


class NABHObjectiveElement(Base):
    """Accreditation Objective Elements (e.g. AAC 1a, FMS 1b)."""
    __tablename__ = "nabh_objective_elements"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    edition_id = Column(String, ForeignKey("nabh_editions.id", ondelete="CASCADE"), nullable=False)
    standard_id = Column(String, ForeignKey("nabh_standards.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    canonical_code = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(SeverityLevel), default=SeverityLevel.MAJOR, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    standard = relationship("NABHStandard", back_populates="objective_elements")
    measurable_elements = relationship("NABHMeasurableElement", back_populates="objective_element", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("edition_id", "canonical_code", name="uq_obj_element_edition_code"),
        Index("idx_obj_element_edition", "edition_id"),
        Index("idx_obj_element_standard", "standard_id"),
    )


class NABHMeasurableElement(Base):
    """Granular measurable requirements (e.g. AAC 1a.1)."""
    __tablename__ = "nabh_measurable_elements"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    edition_id = Column(String, ForeignKey("nabh_editions.id", ondelete="CASCADE"), nullable=False)
    objective_element_id = Column(String, ForeignKey("nabh_objective_elements.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    canonical_code = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    applicability_default = Column(SQLEnum(ApplicabilityDefault), default=ApplicabilityDefault.APPLICABLE, nullable=False)
    scoring_weight = Column(Float, default=1.0, nullable=False)
    risk_weight = Column(Float, default=1.0, nullable=False)
    default_owner_role = Column(String(100), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    objective_element = relationship("NABHObjectiveElement", back_populates="measurable_elements")
    evidence_requirements = relationship("NABHEvidenceRequirement", back_populates="measurable_element", cascade="all, delete-orphan")
    citations = relationship("NABHRequirementCitation", back_populates="measurable_element", cascade="all, delete-orphan")
    applicability_rules = relationship("NABHApplicabilityRule", back_populates="measurable_element", cascade="all, delete-orphan")
    hospital_states = relationship("HospitalNABHRequirement", back_populates="measurable_element", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("edition_id", "canonical_code", name="uq_meas_element_edition_code"),
        Index("idx_meas_element_edition", "edition_id"),
        Index("idx_meas_element_obj_el", "objective_element_id"),
    )


class NABHEvidenceRequirement(Base):
    """Evidentiary path details needed for audit readiness verification."""
    __tablename__ = "nabh_evidence_requirements"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    measurable_element_id = Column(String, ForeignKey("nabh_measurable_elements.id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(SQLEnum(EvidenceType), nullable=False)
    description = Column(Text, nullable=False)
    suggested_documentation = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    evidence_frequency = Column(String(50), nullable=True)
    minimum_lookback_days = Column(Integer, default=90, nullable=False)
    default_owner_role = Column(String(100), nullable=True)
    
    evidence_code = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    measurable_element = relationship("NABHMeasurableElement", back_populates="evidence_requirements")
    evidence_links = relationship("HospitalRequirementEvidenceLink", back_populates="evidence_requirement", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("measurable_element_id", "evidence_code", name="uq_evidence_req_element_code"),
        Index("idx_evidence_req_meas_el", "measurable_element_id"),
    )


class NABHRequirementCitation(Base):
    """Reference guide/statutory citations for compliance guidelines."""
    __tablename__ = "nabh_requirement_citations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    measurable_element_id = Column(String, ForeignKey("nabh_measurable_elements.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String, ForeignKey("nabh_source_documents.id", ondelete="SET NULL"), nullable=True)
    section = Column(String(100), nullable=True)
    page_number = Column(String(50), nullable=True)
    clause_text_summary = Column(Text, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    file_path = Column(String(500), nullable=True)
    url = Column(String(1000), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    measurable_element = relationship("NABHMeasurableElement", back_populates="citations")
    document = relationship("NABHSourceDocument", back_populates="citations")

    __table_args__ = (
        Index("idx_citation_meas_el", "measurable_element_id"),
        Index("idx_citation_document", "document_id"),
    )


class NABHApplicabilityRule(Base):
    """Computed applicability logic rule specifications."""
    __tablename__ = "nabh_applicability_rules"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    measurable_element_id = Column(String, ForeignKey("nabh_measurable_elements.id", ondelete="CASCADE"), nullable=False)
    rule_code = Column(String(100), nullable=False)
    rule_json = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    action_if_true = Column(String(50), default="applicable", nullable=False)
    action_if_false = Column(String(50), default="not_applicable", nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    measurable_element = relationship("NABHMeasurableElement", back_populates="applicability_rules")

    __table_args__ = (
        Index("idx_app_rule_meas_el", "measurable_element_id"),
    )


class ProfileStatus(enum.Enum):
    DRAFT = "draft"
    COMPLETE = "complete"
    NEEDS_REVIEW = "needs_review"


class HospitalAccreditationProfile(Base):
    """Hospital clinical capabilities and exclusions for accreditation scoping."""
    __tablename__ = "hospital_accreditation_profiles"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    bed_count = Column(Integer, default=0, nullable=False)
    hospital_type = Column(String(50), nullable=True)
    profile_status = Column(SQLEnum(ProfileStatus), default=ProfileStatus.DRAFT, nullable=False)
    
    services_offered = Column(JSON, default=[], nullable=False)
    specialty_services = Column(JSON, default=[], nullable=False)
    
    has_icu = Column(Boolean, default=False, nullable=False)
    has_operation_theatre = Column(Boolean, default=False, nullable=False)
    has_emergency = Column(Boolean, default=True, nullable=False)
    has_pharmacy = Column(Boolean, default=False, nullable=False)
    has_lab = Column(Boolean, default=False, nullable=False)
    has_blood_bank = Column(Boolean, default=False, nullable=False)
    has_ambulance = Column(Boolean, default=False, nullable=False)
    has_maternity = Column(Boolean, default=False, nullable=False)
    has_dialysis = Column(Boolean, default=False, nullable=False)
    has_imaging = Column(Boolean, default=False, nullable=False)
    has_cssd = Column(Boolean, default=False, nullable=False)
    
    annual_patient_volume = Column(Integer, nullable=True)
    avg_monthly_opd = Column(Integer, nullable=True)
    
    scope_exclusions = Column(JSON, default=[], nullable=False)
    
    last_scoped_at = Column(DateTime, nullable=True)
    scoped_by = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="accreditation_profile")

    __table_args__ = (
        Index("idx_accred_profile_hospital", "hospital_id"),
    )


class EvidenceStatus(enum.Enum):
    MISSING = "missing"
    DRAFT = "draft"
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    EXPIRED = "expired"


class VerificationStatus(enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class HospitalNABHRequirement(Base):
    """Accreditation progress and ownership per requirement per hospital."""
    __tablename__ = "hospital_nabh_requirements"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_id = Column(String, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    requirement_id = Column(String, ForeignKey("nabh_measurable_elements.id", ondelete="CASCADE"), nullable=False)
    
    applicability_status = Column(SQLEnum(ApplicabilityDefault), default=ApplicabilityDefault.APPLICABLE, nullable=False)
    applicability_reason = Column(Text, nullable=True)
    maturity_level = Column(SQLEnum(MaturityLevel), default=MaturityLevel.NON_EXISTENT, nullable=False)
    evidence_status = Column(SQLEnum(EvidenceStatus), default=EvidenceStatus.MISSING, nullable=False)
    
    owner_id = Column(String, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    last_reviewed_by = Column(String, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    readiness_status = Column(SQLEnum(ComplianceStatus), default=ComplianceStatus.UNDER_REVIEW, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="nabh_requirements")
    measurable_element = relationship("NABHMeasurableElement", back_populates="hospital_states")
    owner = relationship("Staff", foreign_keys=[owner_id])
    reviewer = relationship("Staff", foreign_keys=[last_reviewed_by])
    evidence_links = relationship("HospitalRequirementEvidenceLink", back_populates="hospital_requirement", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("hospital_id", "requirement_id", name="uq_hospital_requirement"),
        Index("idx_hosp_req_hospital", "hospital_id"),
        Index("idx_hosp_req_requirement", "requirement_id"),
        Index("idx_hosp_req_owner", "owner_id"),
        Index("idx_hosp_req_reviewer", "last_reviewed_by"),
    )


class HospitalRequirementEvidenceLink(Base):
    """Links specific uploaded documents or proof artifacts to a hospital's requirement state."""
    __tablename__ = "hospital_requirement_evidence_links"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    hospital_requirement_id = Column(String, ForeignKey("hospital_nabh_requirements.id", ondelete="CASCADE"), nullable=False)
    evidence_requirement_id = Column(String, ForeignKey("nabh_evidence_requirements.id", ondelete="CASCADE"), nullable=False)
    
    document_name = Column(String(255), nullable=False)
    file_path_or_url = Column(String(500), nullable=False)
    notes = Column(Text, nullable=True)
    verification_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False)
    
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())
    uploaded_by = Column(String, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    retired_at = Column(DateTime, nullable=True)

    # Relationships
    hospital_requirement = relationship("HospitalNABHRequirement", back_populates="evidence_links")
    evidence_requirement = relationship("NABHEvidenceRequirement", back_populates="evidence_links")
    uploader = relationship("Staff", foreign_keys=[uploaded_by])
    verifier = relationship("Staff", foreign_keys=[verified_by])

    __table_args__ = (
        UniqueConstraint("hospital_requirement_id", "evidence_requirement_id", name="uq_hosp_req_evidence_req"),
        Index("idx_evidence_link_requirement", "hospital_requirement_id"),
        Index("idx_evidence_link_evidence_req", "evidence_requirement_id"),
        Index("idx_evidence_link_uploader", "uploaded_by"),
        Index("idx_evidence_link_verifier", "verified_by"),
    )


