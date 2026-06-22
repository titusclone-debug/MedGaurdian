export type TabId = 'start' | 'profile' | 'applicable' | 'browser' | 'evidence' | 'dashboard'

export type ApiError = { message: string; status?: number }

export type UserSession = {
  hospital_id?: string
  role?: string
  name?: string
}

export type HospitalProfile = {
  id?: string
  hospital_id: string
  bed_count: number
  hospital_type?: string | null
  profile_status: string
  services_offered: string[]
  specialty_services: string[]
  has_icu: boolean
  has_operation_theatre: boolean
  has_emergency: boolean
  has_pharmacy: boolean
  has_lab: boolean
  has_blood_bank: boolean
  has_ambulance: boolean
  has_maternity: boolean
  has_dialysis: boolean
  has_imaging: boolean
  has_cssd: boolean
  scope_exclusions: string[]
  annual_patient_volume?: number | null
  avg_monthly_opd?: number | null
  last_scoped_at?: string | null
  exists: boolean
}

export type CoverageChapter = {
  chapter_code: string
  title: string
  official_standards_count: number
  official_objective_elements_count?: number
  official_measurable_elements_count?: number
  seeded_standards_count?: number
  seeded_objective_elements_count?: number
  standards_coverage_percent?: number
  elements_coverage_percent?: number
  citation_count?: number
  uncited_seeded_elements_count?: number
  is_fully_seeded?: boolean
}

export type Coverage = {
  ontology_status: string
  seeded_total_standards: number
  seeded_total_elements: number
  global_standards_coverage_percent: number
  global_elements_coverage_percent: number
  citation_complete: boolean
  chapters: CoverageChapter[]
}

export type OntologyChapter = {
  id: string
  code: string
  canonical_code: string
  title: string
  display_order: number
  official_standards_count: number
  official_measurable_elements_count: number
  is_fully_seeded: boolean
}

export type OntologyRequirement = {
  id: string
  code: string
  canonical_code: string
  description: string
  applicability_default: string
  chapter_code: string
  chapter_title: string
  standard_code: string
  standard_title: string
  objective_element_code: string
}

export type HospitalRequirement = {
  id: string
  hospital_id: string
  requirement_id: string
  applicability_status: string
  applicability_reason?: string | null
  maturity_level: number
  evidence_status: string
  owner_id?: string | null
  due_date?: string | null
  last_reviewed_at?: string | null
  last_reviewed_by?: string | null
  readiness_status: string
  requirement_code: string
  requirement_description: string
  chapter_code: string
  standard_code: string
  objective_element_code: string
}

export type Readiness = {
  status: string
  total_state_rows: number
  denominator: number
  ready_count: number
  readiness_score_percent?: number | null
  applicable_count: number
  conditional_count: number
  manual_review_count: number
  not_applicable_count: number
}

export type EvidenceItem = {
  evidence_code: string
  evidence_type: string
  description: string
  suggested_documentation?: string | null
  is_mandatory: boolean
  evidence_frequency?: string | null
  minimum_lookback_days: number
  default_owner_role?: string | null
}

export type RequirementExplanation = {
  requirement_id: string
  requirement_code: string
  title: string
  plain_language_explanation?: string | null
  why_it_matters?: string | null
  required_evidence: EvidenceItem[]
  proof_burden_summary: {
    mandatory_evidence_count: number
    optional_evidence_count: number
    evidence_types_required: string[]
    lookback_days_required: number
  }
  responsible_role: string
  responsible_roles: string[]
  responsible_owner_id?: string | null
  responsible_owner_name?: string | null
  applicability: { status: string; reason: string }
  citations: Array<{
    document_title: string
    publisher: string
    edition_version: string
    section?: string | null
    page_number?: string | null
    clause_text_summary?: string | null
    effective_date?: string | null
    file_path?: string | null
    url?: string | null
  }>
  confidence: string
  hospital_state?: {
    applicability_status: string
    applicability_reason?: string | null
    readiness_status: string
    maturity_level?: number | null
    evidence_status?: string | null
    due_date?: string | null
    owner_id?: string | null
    owner_name?: string | null
    owner_role?: string | null
  } | null
  limitations: string[]
}

export type EvidencePlanItem = {
  requirement_id: string
  requirement_code: string
  title: string
  chapter_code: string
  standard_code: string
  applicability_status: string
  readiness_status: string
  evidence_status: string
  responsible_role: string
  responsible_owner_id?: string | null
  responsible_owner_name?: string | null
  confidence: string
  citation_count: number
  required_evidence: EvidenceItem[]
  proof_burden_summary: RequirementExplanation['proof_burden_summary']
  limitations: string[]
}

export type EvidencePlan = {
  hospital_id: string
  edition_version: string
  total_applicable_requirements: number
  returned_requirements: number
  evidence_item_count: number
  limit: number
  offset: number
  items: EvidencePlanItem[]
}
