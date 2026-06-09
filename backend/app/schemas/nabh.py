from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from app.models.database import (
    EditionStatus, ApplicabilityDefault, MaturityLevel, EvidenceStatus,
    ComplianceStatus, ProfileStatus, VerificationStatus, EvidenceType
)

# --- Task 10: Ontology Schemas ---

class NABHEditionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    version: str
    status: EditionStatus
    effective_date: datetime
    retired_at: Optional[datetime] = None

class NABHChapterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    canonical_code: str
    title: str
    display_order: int
    official_standards_count: int
    official_measurable_elements_count: int
    core_count: Optional[int] = None
    commitment_count: Optional[int] = None
    achievement_count: Optional[int] = None
    excellence_count: Optional[int] = None
    is_fully_seeded: bool

class NABHRequirementSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    canonical_code: str
    description: str
    applicability_default: ApplicabilityDefault
    chapter_code: str
    chapter_title: str
    standard_code: str
    standard_title: str
    objective_element_code: str

class PaginatedRequirementSummary(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[NABHRequirementSummary]

class NABHRuleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    rule_code: str
    rule_json: dict
    description: Optional[str] = None
    action_if_true: str
    action_if_false: str

class NABHEvidenceRequirementSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    evidence_code: Optional[str] = None
    evidence_type: EvidenceType
    description: str
    suggested_documentation: Optional[str] = None
    is_mandatory: bool
    evidence_frequency: Optional[str] = None
    minimum_lookback_days: int = 90
    default_owner_role: Optional[str] = None

class NABHCitationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    measurable_element_id: str
    document_id: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[str] = None
    clause_text_summary: Optional[str] = None
    file_path: Optional[str] = None
    url: Optional[str] = None

class NABHRequirementDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    canonical_code: str
    description: str
    applicability_default: ApplicabilityDefault
    chapter_code: str
    chapter_title: str
    standard_code: str
    standard_title: str
    objective_element_code: str
    objective_element_description: str
    applicability_rules: List[NABHRuleSchema] = []
    evidence_requirements: List[NABHEvidenceRequirementSchema] = []
    citations: List[NABHCitationSchema] = []
    has_citation: bool
    has_evidence_requirements: bool
    mandatory_evidence_count: int = 0
    optional_evidence_count: int = 0
    evidence_types_required: List[str] = Field(default_factory=list)
    lookback_days_required: int = 0

class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    measurable_element_id: str
    document: Optional[dict] = None
    section: Optional[str] = None
    page_number: Optional[str] = None
    clause_text_summary: Optional[str] = None
    file_path: Optional[str] = None
    url: Optional[str] = None
    effective_date_override: Optional[str] = None
    resolved_effective_date: Optional[str] = None
    ontology: Optional[dict] = None

# --- Task 11: Hospital Profile Schemas ---

class HospitalProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    hospital_id: str
    bed_count: int
    hospital_type: Optional[str] = None
    profile_status: ProfileStatus
    services_offered: List[str] = []
    specialty_services: List[str] = []
    has_icu: bool = False
    has_operation_theatre: bool = False
    has_emergency: bool = False
    has_pharmacy: bool = False
    has_lab: bool = False
    has_blood_bank: bool = False
    has_ambulance: bool = False
    has_maternity: bool = False
    has_dialysis: bool = False
    has_imaging: bool = False
    has_cssd: bool = False
    scope_exclusions: List[str] = []
    annual_patient_volume: Optional[int] = None
    avg_monthly_opd: Optional[int] = None
    last_scoped_at: Optional[datetime] = None
    exists: bool = True

class HospitalProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bed_count: Optional[int] = Field(default=None, ge=0)
    hospital_type: Optional[str] = None
    profile_status: Optional[ProfileStatus] = None
    services_offered: Optional[List[str]] = None
    specialty_services: Optional[List[str]] = None
    has_icu: Optional[bool] = None
    has_operation_theatre: Optional[bool] = None
    has_emergency: Optional[bool] = None
    has_pharmacy: Optional[bool] = None
    has_lab: Optional[bool] = None
    has_blood_bank: Optional[bool] = None
    has_ambulance: Optional[bool] = None
    has_maternity: Optional[bool] = None
    has_dialysis: Optional[bool] = None
    has_imaging: Optional[bool] = None
    has_cssd: Optional[bool] = None
    scope_exclusions: Optional[List[str]] = None
    annual_patient_volume: Optional[int] = Field(default=None, ge=0)
    avg_monthly_opd: Optional[int] = Field(default=None, ge=0)

class ApplicabilityComputeResponse(BaseModel):
    total_requirements_evaluated: int
    status_counts: dict
    created_rows_count: int
    updated_rows_count: int
    unchanged_rows_count: int
    warnings: List[str] = []

# --- Task 12: Hospital Requirement State Schemas ---

class HospitalRequirementSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    hospital_id: str
    requirement_id: str
    applicability_status: ApplicabilityDefault
    applicability_reason: Optional[str] = None
    maturity_level: MaturityLevel
    evidence_status: EvidenceStatus
    owner_id: Optional[str] = None
    due_date: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    last_reviewed_by: Optional[str] = None
    readiness_status: ComplianceStatus
    requirement_code: str
    requirement_description: str
    chapter_code: str
    standard_code: str
    objective_element_code: str

class PaginatedHospitalRequirementSummary(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[HospitalRequirementSummary]

class HospitalRequirementEvidenceLinkSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    evidence_requirement_id: str
    document_name: str
    file_path_or_url: str
    notes: Optional[str] = None
    verification_status: VerificationStatus
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    uploaded_at: datetime
    uploaded_by: Optional[str] = None

class HospitalRequirementDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    hospital_id: str
    requirement_id: str
    applicability_status: ApplicabilityDefault
    applicability_reason: Optional[str] = None
    maturity_level: MaturityLevel
    evidence_status: EvidenceStatus
    owner_id: Optional[str] = None
    due_date: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    last_reviewed_by: Optional[str] = None
    readiness_status: ComplianceStatus
    ontology_requirement: NABHRequirementDetail
    evidence_links: List[HospitalRequirementEvidenceLinkSchema] = []

class HospitalRequirementPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    maturity_level: Optional[MaturityLevel] = None
    evidence_status: Optional[EvidenceStatus] = None
    owner_id: Optional[str] = None
    due_date: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    last_reviewed_by: Optional[str] = None
    readiness_status: Optional[ComplianceStatus] = None


class ReadinessChapterBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    chapter_code: str
    chapter_title: str
    total_state_rows: int
    denominator: int
    ready_count: int
    readiness_score_percent: Optional[float] = None
    status: str
    applicable_count: int
    conditional_count: int
    manual_review_count: int
    not_applicable_count: int
    compliant_count: int
    non_compliant_count: int
    partially_compliant_count: int
    under_review_count: int


class HospitalReadinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    hospital_id: str
    edition_version: str
    status: str
    calculated_at: datetime
    generated_at: datetime
    total_state_rows: int
    denominator: int
    ready_count: int
    readiness_score_percent: Optional[float] = None
    not_applicable_count: int
    applicable_count: int
    conditional_count: int
    manual_review_count: int
    compliant_count: int
    non_compliant_count: int
    partially_compliant_count: int
    under_review_count: int
    chapters: List[ReadinessChapterBreakdown]

