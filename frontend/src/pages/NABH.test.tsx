import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import * as reactRouterDom from 'react-router-dom'
import { MemoryRouter } from 'react-router-dom'
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
    console.log('[MOCK FETCH]', method, url)

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

    render(
      <MemoryRouter>
        <NABHPage />
      </MemoryRouter>
    )

    expect(await screen.findByRole('heading', { name: 'Start Here' })).toBeDefined()
    expect(screen.queryByText('NABH Agentic Compliance')).toBeNull()
    expect(screen.getByText('Complete Hospital Profile')).toBeDefined()
  })

  it('saves the hospital profile and computes scope from the profile tab', async () => {
    const fetchMock = mockApi({ profile: profileMissing })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <NABHPage />
      </MemoryRouter>
    )

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

    render(
      <MemoryRouter>
        <NABHPage />
      </MemoryRouter>
    )

    expect(await screen.findByText('The hospital has a valid Fire NOC.')).toBeDefined()
    expect(screen.getByText('FMS-1.a.1')).toBeDefined()
    expect(screen.getByText('Default applicability for this requirement.')).toBeDefined()
  })

  it('shows standards browser coverage and opens source-cited explanation drawer', async () => {
    vi.stubGlobal('fetch', mockApi({ profile: profileSaved, requirements: [hospitalRequirement] }))

    render(
      <MemoryRouter>
        <NABHPage />
      </MemoryRouter>
    )

    fireEvent.click(await screen.findByText('Standards Browser'))
    expect(await screen.findByText('Facility Management and Safety')).toBeDefined()
    expect(screen.getByText('0.5% global element coverage')).toBeDefined()

    fireEvent.click(screen.getByText('Explain Requirement'))

    expect(await screen.findByText('What This Means')).toBeDefined()
    expect(screen.getByText('Original Fire Safety NOC Certificate.')).toBeDefined()
    expect(screen.getByText('NABH Reference Guide')).toBeDefined()
  })

  it('falls back to computed default tab when an invalid tab is provided in URL', async () => {
    vi.stubGlobal('fetch', mockApi({ profile: profileSaved, requirements: [hospitalRequirement] }))

    render(
      <MemoryRouter initialEntries={['/nabh?tab=garbage']}>
        <NABHPage />
        <TestSearchParamsExporter />
      </MemoryRouter>
    )

    // Since profile exists and requirements exist, it should fallback to 'applicable'
    expect(await screen.findByRole('heading', { name: 'Applicable Requirements' })).toBeDefined()
    expect(screen.getByTestId('current-tab').textContent).toBe('applicable')
  })

  it('respects a valid tab provided in the URL and does not redirect', async () => {
    vi.stubGlobal('fetch', mockApi({ profile: profileSaved, requirements: [hospitalRequirement] }))

    render(
      <MemoryRouter initialEntries={['/nabh?tab=browser']}>
        <NABHPage />
        <TestSearchParamsExporter />
      </MemoryRouter>
    )

    // Should render browser directly
    expect(await screen.findByText('Official Chapters')).toBeDefined()
    expect(screen.getByTestId('current-tab').textContent).toBe('browser')
  })

  it('respects the evidence tab provided in the URL directly and does not redirect', async () => {
    vi.stubGlobal('fetch', mockApi({ profile: profileSaved, requirements: [hospitalRequirement] }))

    render(
      <MemoryRouter initialEntries={['/nabh?tab=evidence']}>
        <NABHPage />
        <TestSearchParamsExporter />
      </MemoryRouter>
    )

    expect(await screen.findByRole('button', { name: 'Evidence Needed' })).toBeDefined()
    expect(screen.getByTestId('current-tab').textContent).toBe('evidence')
  })

  it('computes default tab based on profile and scope state when no tab param is provided', async () => {
    // Case A: Profile missing -> defaults to start
    const fetchMockA = mockApi({ profile: profileMissing, requirements: [] })
    vi.stubGlobal('fetch', fetchMockA)
    const { unmount: unmountA } = render(
      <MemoryRouter initialEntries={['/nabh']}>
        <NABHPage />
        <TestSearchParamsExporter />
      </MemoryRouter>
    )
    expect(await screen.findByRole('heading', { name: 'Start Here' })).toBeDefined()
    expect(screen.getByTestId('current-tab').textContent).toBe('start')
    unmountA()

    // Case B: Profile saved, no requirements -> defaults to profile
    const fetchMockB = mockApi({ profile: profileSaved, requirements: [] })
    vi.stubGlobal('fetch', fetchMockB)
    const { unmount: unmountB } = render(
      <MemoryRouter initialEntries={['/nabh']}>
        <NABHPage />
        <TestSearchParamsExporter />
      </MemoryRouter>
    )
    expect(await screen.findByText('Hospital Accreditation Profile')).toBeDefined()
    expect(screen.getByTestId('current-tab').textContent).toBe('profile')
    unmountB()

    // Case C: Profile saved, requirements exist -> defaults to applicable
    const fetchMockC = mockApi({ profile: profileSaved, requirements: [hospitalRequirement] })
    vi.stubGlobal('fetch', fetchMockC)
    render(
      <MemoryRouter initialEntries={['/nabh']}>
        <NABHPage />
        <TestSearchParamsExporter />
      </MemoryRouter>
    )
    expect(await screen.findByRole('heading', { name: 'Applicable Requirements' })).toBeDefined()
    expect(screen.getByTestId('current-tab').textContent).toBe('applicable')
  })

  it('calls setSearchParams with replace: true when falling back from an invalid tab', async () => {
    const fetchMock = mockApi({ profile: profileSaved, requirements: [hospitalRequirement] })
    vi.stubGlobal('fetch', fetchMock)

    const setSearchParamsSpy = vi.fn()
    const mockSearchParams = new URLSearchParams('?tab=garbage')
    
    const useSearchParamsSpy = vi.spyOn(reactRouterDom, 'useSearchParams')
    useSearchParamsSpy.mockReturnValue([mockSearchParams, setSearchParamsSpy])

    render(
      <MemoryRouter>
        <NABHPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(setSearchParamsSpy).toHaveBeenCalledWith(
        expect.objectContaining({ tab: 'applicable' }),
        expect.objectContaining({ replace: true })
      )
    })
  })

  it('updates the search query parameter when a tab is clicked', async () => {
    vi.stubGlobal('fetch', mockApi({ profile: profileSaved, requirements: [hospitalRequirement] }))

    render(
      <MemoryRouter initialEntries={['/nabh?tab=applicable']}>
        <NABHPage />
        <TestSearchParamsExporter />
      </MemoryRouter>
    )

    expect(await screen.findByRole('heading', { name: 'Applicable Requirements' })).toBeDefined()
    
    // Click on Standards Browser tab
    fireEvent.click(screen.getByText('Standards Browser'))
    
    // The tab should change and the search parameter should update to 'browser'
    expect(await screen.findByText('Official Chapters')).toBeDefined()
    expect(screen.getByTestId('current-tab').textContent).toBe('browser')
  })
})

function TestSearchParamsExporter() {
  const [searchParams] = reactRouterDom.useSearchParams()
  return <div data-testid="current-tab">{searchParams.get('tab')}</div>
}
