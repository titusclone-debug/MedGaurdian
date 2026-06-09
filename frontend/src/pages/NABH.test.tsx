import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import NABHPage from './NABH'

const hospitalId = 'hospital-001'

const profileMissing = {
  hospital_id: hospitalId,
  bed_count: 0,
  profile_status: 'draft',
  services_offered: [],
  specialty_services: [],
  has_icu: false,
  has_operation_theatre: false,
  has_emergency: true,
  has_pharmacy: false,
  has_lab: false,
  has_blood_bank: false,
  has_ambulance: false,
  has_maternity: false,
  has_dialysis: false,
  has_imaging: false,
  has_cssd: false,
  scope_exclusions: [],
  exists: false,
}

const profileSaved = {
  ...profileMissing,
  id: 'profile-001',
  bed_count: 50,
  hospital_type: 'mission',
  profile_status: 'draft',
  has_pharmacy: true,
  has_lab: true,
  exists: true,
}

const coverage = {
  ontology_status: 'partial_seed',
  seeded_total_standards: 3,
  seeded_total_elements: 3,
  global_standards_coverage_percent: 3,
  global_elements_coverage_percent: 0.5,
  citation_complete: false,
  chapters: [
    {
      chapter_code: 'FMS',
      title: 'Facility Management and Safety',
      official_standards_count: 7,
      official_objective_elements_count: 43,
      seeded_standards_count: 1,
      seeded_objective_elements_count: 1,
      standards_coverage_percent: 14.3,
      elements_coverage_percent: 2.3,
      citation_count: 1,
      uncited_seeded_elements_count: 0,
      is_fully_seeded: false,
    },
  ],
}

const chapters = [
  {
    id: 'chap-fms',
    code: 'FMS',
    canonical_code: 'FMS',
    title: 'Facility Management and Safety',
    display_order: 1,
    official_standards_count: 7,
    official_measurable_elements_count: 43,
    is_fully_seeded: false,
  },
]

const ontologyRequirements = [
  {
    id: 'req-fms-1',
    code: '1',
    canonical_code: 'FMS-1.a.1',
    description: 'The hospital has a valid Fire NOC.',
    applicability_default: 'applicable',
    chapter_code: 'FMS',
    chapter_title: 'Facility Management and Safety',
    standard_code: 'FMS-1',
    standard_title: 'Fire Prevention and Safety',
    objective_element_code: 'FMS-1.a',
  },
]

const hospitalRequirement = {
  id: 'state-001',
  hospital_id: hospitalId,
  requirement_id: 'req-fms-1',
  applicability_status: 'applicable',
  applicability_reason: 'Default applicability for this requirement.',
  maturity_level: 0,
  evidence_status: 'missing',
  owner_id: null,
  due_date: null,
  last_reviewed_at: null,
  last_reviewed_by: null,
  readiness_status: 'under_review',
  requirement_code: 'FMS-1.a.1',
  requirement_description: 'The hospital has a valid Fire NOC.',
  chapter_code: 'FMS',
  standard_code: 'FMS-1',
  objective_element_code: 'FMS-1.a',
}

const readiness = {
  status: 'in_progress',
  total_state_rows: 1,
  denominator: 1,
  ready_count: 0,
  readiness_score_percent: 0,
  applicable_count: 1,
  conditional_count: 0,
  manual_review_count: 0,
  not_applicable_count: 0,
}

const explanation = {
  requirement_id: 'req-fms-1',
  requirement_code: 'FMS-1.a.1',
  title: 'The hospital has a valid Fire NOC.',
  plain_language_explanation: 'This requirement asks the hospital to ensure: The hospital has a valid Fire NOC.',
  why_it_matters: 'Surveyors use this to verify that the stated process is documented, assigned, and supported by evidence.',
  required_evidence: [
    {
      evidence_code: 'FMS-1.a.1-EV-NOC',
      evidence_type: 'license',
      description: 'Valid Fire NOC certificate.',
      suggested_documentation: 'Original Fire Safety NOC Certificate.',
      is_mandatory: true,
      evidence_frequency: 'yearly',
      minimum_lookback_days: 365,
      default_owner_role: 'facility_director',
    },
  ],
  proof_burden_summary: {
    mandatory_evidence_count: 1,
    optional_evidence_count: 0,
    evidence_types_required: ['license'],
    lookback_days_required: 365,
  },
  responsible_role: 'facility_director',
  responsible_roles: [],
  responsible_owner_id: null,
  responsible_owner_name: null,
  applicability: {
    status: 'applicable',
    reason: 'Default applicability for this requirement.',
  },
  citations: [
    {
      document_title: 'NABH Reference Guide',
      publisher: 'NABH',
      edition_version: '6.0',
      section: 'FMS',
      page_number: '184',
      clause_text_summary: 'Fire clearance is required.',
      effective_date: '2026-01-01T00:00:00',
      file_path: '/excerpt.png',
      url: null,
    },
  ],
  confidence: 'source_cited',
  hospital_state: null,
  limitations: [],
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

function setupStorage() {
  localStorage.setItem('medguardian_token', 'token-001')
  localStorage.setItem('medguardian_user', JSON.stringify({ hospital_id: hospitalId, role: 'hospital_admin', name: 'Admin' }))
}

function mockApi({ profile = profileMissing, requirements = [] as any[] } = {}) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = init?.method || 'GET'

    if (url === '/api/nabh/ontology/coverage') return jsonResponse(coverage)
    if (url === '/api/nabh/ontology/chapters') return jsonResponse(chapters)
    if (url === '/api/nabh/ontology/requirements?limit=1000') {
      return jsonResponse({ total: ontologyRequirements.length, limit: 1000, offset: 0, items: ontologyRequirements })
    }
    if (url === `/api/nabh/profile/${hospitalId}` && method === 'GET') return jsonResponse(profile)
    if (url === `/api/nabh/profile/${hospitalId}` && method === 'PUT') return jsonResponse({ ...profileSaved, exists: true })
    if (url === `/api/nabh/profile/${hospitalId}/compute-applicability`) {
      return jsonResponse({ total_requirements_evaluated: 1, status_counts: { applicable: 1 } })
    }
    if (url === `/api/nabh/requirements/${hospitalId}?limit=1000`) {
      return jsonResponse({ total: requirements.length, limit: 1000, offset: 0, items: requirements })
    }
    if (url === `/api/nabh/readiness/${hospitalId}`) return jsonResponse(requirements.length ? readiness : { ...readiness, total_state_rows: 0, denominator: 0, readiness_score_percent: null })
    if (url === `/api/nabh/ontology/requirements/req-fms-1/explanation?hospital_id=${hospitalId}`) return jsonResponse(explanation)
    if (url === '/api/nabh/ontology/requirements/req-fms-1/explanation') return jsonResponse(explanation)

    return jsonResponse({ detail: `Unhandled ${method} ${url}` }, 404)
  })
}

describe('NABH Phase 1 workspace', () => {
  beforeEach(() => {
    localStorage.clear()
    setupStorage()
    vi.restoreAllMocks()
  })

  it('opens Start Here before the dashboard when profile is missing', async () => {
    vi.stubGlobal('fetch', mockApi())

    render(<NABHPage />)

    expect(await screen.findByRole('heading', { name: 'Start Here' })).toBeDefined()
    expect(screen.queryByText('NABH Agentic Compliance')).toBeNull()
    expect(screen.getByText('Complete Hospital Profile')).toBeDefined()
  })

  it('saves the hospital profile and computes scope from the profile tab', async () => {
    const fetchMock = mockApi({ profile: profileMissing })
    vi.stubGlobal('fetch', fetchMock)

    render(<NABHPage />)

    fireEvent.click(await screen.findByText('Hospital Profile'))
    fireEvent.click(screen.getByText('Save Profile'))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `/api/nabh/profile/${hospitalId}`,
        expect.objectContaining({ method: 'PUT' })
      )
    })

    fireEvent.click(screen.getByText('Compute Scope'))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `/api/nabh/profile/${hospitalId}/compute-applicability`,
        expect.objectContaining({ method: 'POST' })
      )
    })
  })

  it('renders applicable requirement rows after scope exists', async () => {
    vi.stubGlobal('fetch', mockApi({ profile: profileSaved, requirements: [hospitalRequirement] }))

    render(<NABHPage />)

    expect(await screen.findByText('The hospital has a valid Fire NOC.')).toBeDefined()
    expect(screen.getByText('FMS-1.a.1')).toBeDefined()
    expect(screen.getByText('Default applicability for this requirement.')).toBeDefined()
  })

  it('shows standards browser coverage and opens source-cited explanation drawer', async () => {
    vi.stubGlobal('fetch', mockApi({ profile: profileSaved, requirements: [hospitalRequirement] }))

    render(<NABHPage />)

    fireEvent.click(await screen.findByText('Standards Browser'))
    expect(await screen.findByText('Facility Management and Safety')).toBeDefined()
    expect(screen.getByText('0.5% global element coverage')).toBeDefined()

    fireEvent.click(screen.getByText('Explain Requirement'))

    expect(await screen.findByText('What This Means')).toBeDefined()
    expect(screen.getByText('Original Fire Safety NOC Certificate.')).toBeDefined()
    expect(screen.getByText('NABH Reference Guide')).toBeDefined()
  })
})
