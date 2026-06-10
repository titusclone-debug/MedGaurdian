import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  Award,
  BookOpen,
  CheckCircle,
  ChevronRight,
  ClipboardCheck,
  FileSearch,
  FileText,
  Info,
  Loader2,
  RefreshCw,
  Save,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react'
import LegacyNABHDashboard from '../components/nabh/LegacyNABHDashboard'

type TabId = 'start' | 'profile' | 'applicable' | 'browser' | 'evidence' | 'dashboard'

type ApiError = {
  message: string
  status?: number
}

type UserSession = {
  hospital_id?: string
  role?: string
  name?: string
}

type HospitalProfile = {
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

type CoverageChapter = {
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

type Coverage = {
  ontology_status: string
  seeded_total_standards: number
  seeded_total_elements: number
  global_standards_coverage_percent: number
  global_elements_coverage_percent: number
  citation_complete: boolean
  chapters: CoverageChapter[]
}

type OntologyChapter = {
  id: string
  code: string
  canonical_code: string
  title: string
  display_order: number
  official_standards_count: number
  official_measurable_elements_count: number
  is_fully_seeded: boolean
}

type OntologyRequirement = {
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

type HospitalRequirement = {
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

type Readiness = {
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

type EvidenceItem = {
  evidence_code: string
  evidence_type: string
  description: string
  suggested_documentation?: string | null
  is_mandatory: boolean
  evidence_frequency?: string | null
  minimum_lookback_days: number
  default_owner_role?: string | null
}

type RequirementExplanation = {
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
  applicability: {
    status: string
    reason: string
  }
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

const TABS: Array<{ id: TabId; label: string; icon: any }> = [
  { id: 'start', label: 'Start Here', icon: Info },
  { id: 'profile', label: 'Hospital Profile', icon: SlidersHorizontal },
  { id: 'applicable', label: 'Applicable Requirements', icon: ClipboardCheck },
  { id: 'browser', label: 'Standards Browser', icon: BookOpen },
  { id: 'evidence', label: 'Evidence Needed', icon: FileSearch },
  { id: 'dashboard', label: 'Dashboard', icon: Award },
]

const PROFILE_FLAGS = [
  ['has_emergency', 'Emergency'],
  ['has_icu', 'ICU'],
  ['has_operation_theatre', 'Operation Theatre'],
  ['has_pharmacy', 'Pharmacy'],
  ['has_lab', 'Laboratory'],
  ['has_blood_bank', 'Blood Bank'],
  ['has_ambulance', 'Ambulance'],
  ['has_maternity', 'Maternity'],
  ['has_dialysis', 'Dialysis'],
  ['has_imaging', 'Imaging'],
  ['has_cssd', 'CSSD'],
] as const

const emptyProfile = (hospitalId: string): HospitalProfile => ({
  hospital_id: hospitalId,
  bed_count: 0,
  hospital_type: 'mission',
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
  annual_patient_volume: null,
  avg_monthly_opd: null,
  exists: false,
})

function getStoredUser(): UserSession | null {
  const savedUser = localStorage.getItem('medguardian_user')
  if (!savedUser) return null
  try {
    return JSON.parse(savedUser)
  } catch {
    return null
  }
}

function getAuthHeaders() {
  const token = localStorage.getItem('medguardian_token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    'Content-Type': 'application/json',
  }
}

async function apiFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  })

  if (response.status === 401) {
    localStorage.removeItem('medguardian_token')
    localStorage.removeItem('medguardian_user')
    window.location.reload()
    throw { message: 'Session expired', status: 401 } satisfies ApiError
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw {
      message: body.detail || `Request failed with status ${response.status}`,
      status: response.status,
    } satisfies ApiError
  }

  return response.json()
}

function sentenceCase(value: string | undefined | null) {
  if (!value) return 'Not set'
  return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function statusBadgeClass(value: string) {
  switch (value) {
    case 'applicable':
    case 'compliant':
    case 'verified':
    case 'ready':
      return 'bg-green-50 text-green-700 border-green-200'
    case 'conditional':
    case 'partially_compliant':
    case 'pending_verification':
    case 'in_progress':
      return 'bg-amber-50 text-amber-700 border-amber-200'
    case 'manual_review':
    case 'under_review':
    case 'draft':
      return 'bg-blue-50 text-blue-700 border-blue-200'
    case 'not_applicable':
    case 'missing':
    case 'non_compliant':
      return 'bg-red-50 text-red-700 border-red-200'
    default:
      return 'bg-slate-50 text-slate-700 border-slate-200'
  }
}

function StatusBadge({ value }: { value: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${statusBadgeClass(value)}`}>
      {sentenceCase(value)}
    </span>
  )
}

function SplitListInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string[]
  onChange: (items: string[]) => void
  placeholder: string
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase text-slate-500">{label}</span>
      <input
        className="input-field"
        value={value.join(', ')}
        onChange={(event) => {
          const items = event.target.value
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean)
          onChange(items)
        }}
        placeholder={placeholder}
      />
    </label>
  )
}

export default function NABHPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') as TabId | null
  const isValidTab = useMemo(() => {
    return tabParam && ['start', 'profile', 'applicable', 'browser', 'evidence', 'dashboard'].includes(tabParam)
  }, [tabParam])

  const activeTab = isValidTab ? (tabParam as TabId) : 'start'

  const [user] = useState<UserSession | null>(() => getStoredUser())
  const hospitalId = user?.hospital_id

  const [profile, setProfile] = useState<HospitalProfile | null>(null)
  const [coverage, setCoverage] = useState<Coverage | null>(null)
  const [chapters, setChapters] = useState<OntologyChapter[]>([])
  const [ontologyRequirements, setOntologyRequirements] = useState<OntologyRequirement[]>([])
  const [hospitalRequirements, setHospitalRequirements] = useState<HospitalRequirement[]>([])
  const [readiness, setReadiness] = useState<Readiness | null>(null)
  const [loading, setLoading] = useState(true)
  const [savingProfile, setSavingProfile] = useState(false)
  const [computingScope, setComputingScope] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [selectedRequirementId, setSelectedRequirementId] = useState<string | null>(null)
  const [selectedExplanation, setSelectedExplanation] = useState<RequirementExplanation | null>(null)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [evidenceExplanations, setEvidenceExplanations] = useState<RequirementExplanation[]>([])
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const hasChosenTabRef = useRef(false)

  const scopedRequirements = useMemo(
    () => hospitalRequirements.filter((req) => req.applicability_status !== 'not_applicable'),
    [hospitalRequirements]
  )
  const hasComputedScope = hospitalRequirements.length > 0

  const fetchHospitalData = useCallback(async () => {
    if (!hospitalId) {
      setError('Session or hospital identifier missing')
      setLoading(false)
      return
    }

    setLoading(true)
    setError('')
    try {
      const [profileData, requirementsData, readinessData] = await Promise.all([
        apiFetch<HospitalProfile>(`/api/nabh/profile/${hospitalId}`),
        apiFetch<{ total: number; items: HospitalRequirement[] }>(`/api/nabh/requirements/${hospitalId}?limit=1000`),
        apiFetch<Readiness>(`/api/nabh/readiness/${hospitalId}`),
      ])

      setProfile(profileData.exists ? profileData : emptyProfile(hospitalId))
      setHospitalRequirements(requirementsData.items || [])
      setReadiness(readinessData)

      if (!hasChosenTabRef.current) {
        if (!isValidTab) {
          let defaultTab: TabId = 'start'
          if (!profileData.exists) defaultTab = 'start'
          else if ((requirementsData.items || []).length === 0) defaultTab = 'profile'
          else defaultTab = 'applicable'
          setSearchParams({ tab: defaultTab }, { replace: true })
        }
        hasChosenTabRef.current = true
      }
    } catch (err: any) {
      setError(err.message || 'Unable to load NABH workspace')
    } finally {
      setLoading(false)
    }
  }, [hospitalId])

  const fetchOntologyData = useCallback(async () => {
    try {
      const [coverageData, chapterData, requirementData] = await Promise.all([
        apiFetch<Coverage>('/api/nabh/ontology/coverage'),
        apiFetch<OntologyChapter[]>('/api/nabh/ontology/chapters'),
        apiFetch<{ total: number; items: OntologyRequirement[] }>('/api/nabh/ontology/requirements?limit=1000'),
      ])
      setCoverage(coverageData)
      setChapters(chapterData)
      setOntologyRequirements(requirementData.items || [])
    } catch (err: any) {
      setError(err.message || 'Unable to load NABH ontology')
    }
  }, [])

  useEffect(() => {
    fetchOntologyData()
    fetchHospitalData()
  }, [fetchHospitalData, fetchOntologyData])

  useEffect(() => {
    if (activeTab !== 'evidence' || !hospitalId || scopedRequirements.length === 0 || evidenceExplanations.length > 0) {
      return
    }

    async function loadEvidencePlan() {
      setEvidenceLoading(true)
      try {
        const explanations = await Promise.all(
          scopedRequirements.map((req) =>
            apiFetch<RequirementExplanation>(
              `/api/nabh/ontology/requirements/${req.requirement_id}/explanation?hospital_id=${hospitalId}`
            )
          )
        )
        setEvidenceExplanations(explanations)
      } catch (err: any) {
        setError(err.message || 'Unable to load evidence expectations')
      } finally {
        setEvidenceLoading(false)
      }
    }

    loadEvidencePlan()
  }, [activeTab, evidenceExplanations.length, hospitalId, scopedRequirements])

  async function saveProfile() {
    if (!hospitalId || !profile) return
    setSavingProfile(true)
    setError('')
    setNotice('')
    try {
      const payload = {
        bed_count: profile.bed_count,
        hospital_type: profile.hospital_type,
        profile_status: profile.profile_status,
        services_offered: profile.services_offered,
        specialty_services: profile.specialty_services,
        has_icu: profile.has_icu,
        has_operation_theatre: profile.has_operation_theatre,
        has_emergency: profile.has_emergency,
        has_pharmacy: profile.has_pharmacy,
        has_lab: profile.has_lab,
        has_blood_bank: profile.has_blood_bank,
        has_ambulance: profile.has_ambulance,
        has_maternity: profile.has_maternity,
        has_dialysis: profile.has_dialysis,
        has_imaging: profile.has_imaging,
        has_cssd: profile.has_cssd,
        scope_exclusions: profile.scope_exclusions,
        annual_patient_volume: profile.annual_patient_volume,
        avg_monthly_opd: profile.avg_monthly_opd,
      }
      const saved = await apiFetch<HospitalProfile>(`/api/nabh/profile/${hospitalId}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      })
      setProfile(saved)
      setNotice('Hospital accreditation profile saved.')
    } catch (err: any) {
      setError(err.message || 'Unable to save profile')
    } finally {
      setSavingProfile(false)
    }
  }

  async function computeScope() {
    if (!hospitalId) return
    setComputingScope(true)
    setError('')
    setNotice('')
    try {
      const result = await apiFetch<{ total_requirements_evaluated: number; status_counts: Record<string, number> }>(
        `/api/nabh/profile/${hospitalId}/compute-applicability`,
        { method: 'POST' }
      )
      hasChosenTabRef.current = true
      await fetchHospitalData()
      setEvidenceExplanations([])
      setSearchParams({ tab: 'applicable' })
      setNotice(`Scope computed across ${result.total_requirements_evaluated} seeded requirements.`)
    } catch (err: any) {
      setError(err.message || 'Unable to compute applicability')
    } finally {
      setComputingScope(false)
    }
  }

  async function openExplanation(requirementId: string) {
    setSelectedRequirementId(requirementId)
    setSelectedExplanation(null)
    setDrawerLoading(true)
    setError('')
    try {
      const suffix = hospitalId ? `?hospital_id=${hospitalId}` : ''
      const explanation = await apiFetch<RequirementExplanation>(
        `/api/nabh/ontology/requirements/${requirementId}/explanation${suffix}`
      )
      setSelectedExplanation(explanation)
    } catch (err: any) {
      setError(err.message || 'Unable to load requirement explanation')
    } finally {
      setDrawerLoading(false)
    }
  }

  function chooseTab(tab: TabId) {
    hasChosenTabRef.current = true
    setSearchParams({ tab })
  }

  if (loading) {
    return (
      <div className="flex min-h-[360px] items-center justify-center">
        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-600">
          <Loader2 size={18} className="animate-spin text-brand-600" />
          Loading NABH accreditation workspace
        </div>
      </div>
    )
  }

  if (!hospitalId) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Hospital context missing"
        body="This session does not include a hospital identifier. Sign in again with a hospital-linked account."
      />
    )
  }

  return (
    <div className="space-y-5">
      <WorkspaceHeader
        coverage={coverage}
        readiness={readiness}
        profile={profile}
        hasComputedScope={hasComputedScope}
      />

      {error && <Alert type="error" message={error} onDismiss={() => setError('')} />}
      {notice && <Alert type="success" message={notice} onDismiss={() => setNotice('')} />}

      <div className="overflow-x-auto border-b border-slate-200">
        <div className="flex min-w-max gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon
            const active = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => chooseTab(tab.id)}
                className={`flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-semibold transition-colors ${
                  active
                    ? 'border-brand-600 text-brand-700'
                    : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
                }`}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {activeTab === 'start' && (
        <StartHere
          profile={profile}
          coverage={coverage}
          readiness={readiness}
          hasComputedScope={hasComputedScope}
          onGoProfile={() => chooseTab('profile')}
          onGoApplicable={() => chooseTab('applicable')}
          onGoBrowser={() => chooseTab('browser')}
        />
      )}

      {activeTab === 'profile' && profile && (
        <HospitalProfileView
          profile={profile}
          setProfile={setProfile}
          onSave={saveProfile}
          onCompute={computeScope}
          saving={savingProfile}
          computing={computingScope}
          hasComputedScope={hasComputedScope}
        />
      )}

      {activeTab === 'applicable' && (
        <ApplicableRequirementsView
          requirements={hospitalRequirements}
          chapters={chapters}
          hasComputedScope={hasComputedScope}
          onOpenExplanation={openExplanation}
          onGoProfile={() => chooseTab('profile')}
          onCompute={computeScope}
          computing={computingScope}
        />
      )}

      {activeTab === 'browser' && (
        <StandardsBrowserView
          coverage={coverage}
          chapters={chapters}
          requirements={ontologyRequirements}
          onOpenExplanation={openExplanation}
        />
      )}

      {activeTab === 'evidence' && (
        <EvidenceNeededView
          explanations={evidenceExplanations}
          loading={evidenceLoading}
          requirementCount={scopedRequirements.length}
          hasComputedScope={hasComputedScope}
          onGoApplicable={() => chooseTab('applicable')}
        />
      )}

      {activeTab === 'dashboard' && (
        <div className="space-y-4">
          <ReadinessStrip readiness={readiness} />
          <LegacyNABHDashboard />
        </div>
      )}

      <RequirementExplanationDrawer
        requirementId={selectedRequirementId}
        explanation={selectedExplanation}
        loading={drawerLoading}
        onClose={() => {
          setSelectedRequirementId(null)
          setSelectedExplanation(null)
        }}
      />
    </div>
  )
}

function WorkspaceHeader({
  coverage,
  readiness,
  profile,
  hasComputedScope,
}: {
  coverage: Coverage | null
  readiness: Readiness | null
  profile: HospitalProfile | null
  hasComputedScope: boolean
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Award size={24} className="text-brand-600" />
            <h2 className="text-xl font-bold text-slate-900">NABH Accreditation Workspace</h2>
          </div>
          <p className="max-w-3xl text-sm text-slate-500">
            Build the hospital scope first, then review applicable requirements, evidence expectations, and readiness.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <HeaderMetric label="Profile" value={profile?.exists ? 'Saved' : 'Missing'} tone={profile?.exists ? 'good' : 'warn'} />
          <HeaderMetric label="Scope" value={hasComputedScope ? 'Computed' : 'Pending'} tone={hasComputedScope ? 'good' : 'warn'} />
          <HeaderMetric label="Seeded" value={`${coverage?.seeded_total_elements || 0} reqs`} tone="info" />
          <HeaderMetric label="Ready" value={readiness?.readiness_score_percent == null ? 'Not scoped' : `${readiness.readiness_score_percent}%`} tone="info" />
        </div>
      </div>
      {coverage && !coverage.citation_complete && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <span>
            Ontology is intentionally partial: {coverage.seeded_total_standards} seeded standards and {coverage.seeded_total_elements} seeded requirements are available for Phase 1 validation.
          </span>
        </div>
      )}
    </div>
  )
}

function HeaderMetric({ label, value, tone }: { label: string; value: string; tone: 'good' | 'warn' | 'info' }) {
  const toneClass = tone === 'good' ? 'text-green-700' : tone === 'warn' ? 'text-amber-700' : 'text-brand-700'
  return (
    <div className="min-w-[105px] rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</div>
      <div className={`mt-0.5 text-sm font-bold ${toneClass}`}>{value}</div>
    </div>
  )
}

function Alert({ type, message, onDismiss }: { type: 'error' | 'success'; message: string; onDismiss: () => void }) {
  const styles = type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-green-200 bg-green-50 text-green-700'
  return (
    <div className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-sm ${styles}`}>
      {type === 'error' ? <AlertTriangle size={18} /> : <CheckCircle size={18} />}
      <span className="flex-1">{message}</span>
      <button onClick={onDismiss} className="rounded p-1 hover:bg-white/50" aria-label="Dismiss message">
        <X size={16} />
      </button>
    </div>
  )
}

function StartHere({
  profile,
  coverage,
  readiness,
  hasComputedScope,
  onGoProfile,
  onGoApplicable,
  onGoBrowser,
}: {
  profile: HospitalProfile | null
  coverage: Coverage | null
  readiness: Readiness | null
  hasComputedScope: boolean
  onGoProfile: () => void
  onGoApplicable: () => void
  onGoBrowser: () => void
}) {
  const nextAction = !profile?.exists
    ? { label: 'Complete Hospital Profile', action: onGoProfile }
    : !hasComputedScope
      ? { label: 'Compute Applicable Scope', action: onGoProfile }
      : { label: 'Review Applicable Requirements', action: onGoApplicable }

  const steps = [
    { label: 'Hospital profile saved', done: !!profile?.exists },
    { label: 'Applicability scope computed', done: hasComputedScope },
    { label: 'Applicable requirements ready', done: (readiness?.total_state_rows || 0) > 0 },
    { label: 'Evidence expectations available', done: (coverage?.seeded_total_elements || 0) > 0 },
  ]

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.8fr)]">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Start Here</h3>
            <p className="mt-1 max-w-2xl text-sm text-slate-500">
              This workspace starts by defining which NABH requirements apply to this hospital. Readiness scores stay secondary until the scope is defensible.
            </p>
          </div>
          <button onClick={nextAction.action} className="btn-primary shrink-0">
            {nextAction.label}
            <ChevronRight size={16} />
          </button>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {steps.map((step) => (
            <div key={step.label} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
              {step.done ? <CheckCircle size={20} className="text-green-600" /> : <Info size={20} className="text-amber-600" />}
              <span className="text-sm font-medium text-slate-700">{step.label}</span>
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <ProcessPanel
            title="1. Scope"
            body="Capture hospital capabilities such as beds, ICU, OT, blood bank, lab, imaging, and exclusions."
          />
          <ProcessPanel
            title="2. Requirements"
            body="Compute applicable, conditional, manual-review, and not-applicable requirement states."
          />
          <ProcessPanel
            title="3. Evidence"
            body="Review source-cited explanations and the proof burden before reading the readiness score."
          />
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">Current Scope Snapshot</h3>
        <div className="mt-4 space-y-3">
          <SnapshotRow label="Profile status" value={profile?.exists ? sentenceCase(profile.profile_status) : 'Not created'} />
          <SnapshotRow label="Last scoped" value={profile?.last_scoped_at ? new Date(profile.last_scoped_at).toLocaleDateString() : 'Never'} />
          <SnapshotRow label="State rows" value={`${readiness?.total_state_rows || 0}`} />
          <SnapshotRow label="Applicable denominator" value={`${readiness?.denominator || 0}`} />
          <SnapshotRow label="Ontology coverage" value={`${coverage?.global_elements_coverage_percent || 0}%`} />
        </div>
        <button onClick={onGoBrowser} className="btn-secondary mt-5 w-full">
          Browse Official Structure
          <BookOpen size={16} />
        </button>
      </section>
    </div>
  )
}

function ProcessPanel({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <h4 className="text-sm font-bold text-slate-900">{title}</h4>
      <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
    </div>
  )
}

function SnapshotRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-2 text-sm last:border-0">
      <span className="text-slate-500">{label}</span>
      <span className="font-semibold text-slate-800">{value}</span>
    </div>
  )
}

function HospitalProfileView({
  profile,
  setProfile,
  onSave,
  onCompute,
  saving,
  computing,
  hasComputedScope,
}: {
  profile: HospitalProfile
  setProfile: (profile: HospitalProfile) => void
  onSave: () => void
  onCompute: () => void
  saving: boolean
  computing: boolean
  hasComputedScope: boolean
}) {
  function update<K extends keyof HospitalProfile>(key: K, value: HospitalProfile[K]) {
    setProfile({ ...profile, [key]: value })
  }

  return (
    <section className="space-y-5">
      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Hospital Accreditation Profile</h3>
            <p className="mt-1 text-sm text-slate-500">
              These details determine the hospital-specific NABH scope. Save the profile before computing applicability.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={onSave} disabled={saving} className="btn-secondary">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              Save Profile
            </button>
            <button onClick={onCompute} disabled={computing} className="btn-primary">
              {computing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
              {hasComputedScope ? 'Recompute Scope' : 'Compute Scope'}
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase text-slate-500">Bed Count</span>
              <input
                className="input-field"
                type="number"
                value={profile.bed_count}
                onChange={(event) => update('bed_count', Number(event.target.value) || 0)}
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase text-slate-500">Hospital Type</span>
              <select
                className="input-field"
                value={profile.hospital_type || ''}
                onChange={(event) => update('hospital_type', event.target.value)}
              >
                <option value="mission">Mission Hospital</option>
                <option value="trust">Charitable Trust</option>
                <option value="private">Private Hospital</option>
                <option value="government">Government Hospital</option>
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase text-slate-500">Annual Patient Volume</span>
              <input
                className="input-field"
                type="number"
                value={profile.annual_patient_volume || ''}
                onChange={(event) => update('annual_patient_volume', event.target.value ? Number(event.target.value) : null)}
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase text-slate-500">Average Monthly OPD</span>
              <input
                className="input-field"
                type="number"
                value={profile.avg_monthly_opd || ''}
                onChange={(event) => update('avg_monthly_opd', event.target.value ? Number(event.target.value) : null)}
              />
            </label>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {PROFILE_FLAGS.map(([key, label]) => (
              <label key={key} className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={Boolean(profile[key])}
                  onChange={(event) => update(key, event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                {label}
              </label>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h4 className="text-sm font-bold uppercase tracking-wide text-slate-500">Scope Lists</h4>
          <div className="mt-4 space-y-4">
            <SplitListInput
              label="Services Offered"
              value={profile.services_offered || []}
              onChange={(items) => update('services_offered', items)}
              placeholder="OPD, IPD, ICU"
            />
            <SplitListInput
              label="Specialty Services"
              value={profile.specialty_services || []}
              onChange={(items) => update('specialty_services', items)}
              placeholder="Dialysis, maternity, imaging"
            />
            <SplitListInput
              label="Scope Exclusions"
              value={profile.scope_exclusions || []}
              onChange={(items) => update('scope_exclusions', items)}
              placeholder="Blood bank, dialysis"
            />
          </div>
        </div>
      </div>
    </section>
  )
}

function ApplicableRequirementsView({
  requirements,
  chapters,
  hasComputedScope,
  onOpenExplanation,
  onGoProfile,
  onCompute,
  computing,
}: {
  requirements: HospitalRequirement[]
  chapters: OntologyChapter[]
  hasComputedScope: boolean
  onOpenExplanation: (id: string) => void
  onGoProfile: () => void
  onCompute: () => void
  computing: boolean
}) {
  const [chapterFilter, setChapterFilter] = useState('')
  const [appFilter, setAppFilter] = useState('')
  const [readinessFilter, setReadinessFilter] = useState('')
  const [evidenceFilter, setEvidenceFilter] = useState('')
  const [query, setQuery] = useState('')

  const filtered = requirements.filter((req) => {
    if (chapterFilter && req.chapter_code !== chapterFilter) return false
    if (appFilter && req.applicability_status !== appFilter) return false
    if (readinessFilter && req.readiness_status !== readinessFilter) return false
    if (evidenceFilter && req.evidence_status !== evidenceFilter) return false
    if (query) {
      const text = `${req.requirement_code} ${req.requirement_description} ${req.standard_code}`.toLowerCase()
      if (!text.includes(query.toLowerCase())) return false
    }
    return true
  })

  if (!hasComputedScope) {
    return (
      <EmptyState
        icon={ClipboardCheck}
        title="Applicability scope has not been computed"
        body="Complete the accreditation profile and compute scope before reviewing applicable requirements."
        actionLabel="Open Hospital Profile"
        onAction={onGoProfile}
      />
    )
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Applicable Requirements</h3>
            <p className="text-sm text-slate-500">{filtered.length} of {requirements.length} hospital-scoped rows shown</p>
          </div>
          <button onClick={onCompute} disabled={computing} className="btn-secondary">
            {computing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
            Recompute Scope
          </button>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-5">
          <FilterSelect label="Chapter" value={chapterFilter} onChange={setChapterFilter} options={chapters.map((c) => c.canonical_code)} />
          <FilterSelect label="Applicability" value={appFilter} onChange={setAppFilter} options={['applicable', 'conditional', 'manual_review', 'not_applicable']} />
          <FilterSelect label="Readiness" value={readinessFilter} onChange={setReadinessFilter} options={['compliant', 'partially_compliant', 'non_compliant', 'under_review']} />
          <FilterSelect label="Evidence" value={evidenceFilter} onChange={setEvidenceFilter} options={['missing', 'draft', 'pending_verification', 'verified', 'expired']} />
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold uppercase text-slate-500">Search</span>
            <div className="relative">
              <Search size={15} className="absolute left-3 top-3 text-slate-400" />
              <input className="input-field pl-9" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Code or text" />
            </div>
          </label>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-100">
          <thead className="bg-slate-50">
            <tr>
              <th className="table-header">Requirement</th>
              <th className="table-header">Applicability</th>
              <th className="table-header">Evidence</th>
              <th className="table-header">Readiness</th>
              <th className="table-header">Owner</th>
              <th className="table-header">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {filtered.map((req) => (
              <tr key={req.id} className="align-top">
                <td className="table-cell min-w-[340px]">
                  <div className="font-mono text-xs font-bold text-brand-700">{req.requirement_code}</div>
                  <div className="mt-1 font-semibold text-slate-900">{req.requirement_description}</div>
                  <div className="mt-1 text-xs text-slate-400">{req.chapter_code} / {req.standard_code} / {req.objective_element_code}</div>
                </td>
                <td className="table-cell min-w-[220px]">
                  <StatusBadge value={req.applicability_status} />
                  <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-500">{req.applicability_reason || 'No rule reason recorded.'}</p>
                </td>
                <td className="table-cell"><StatusBadge value={req.evidence_status} /></td>
                <td className="table-cell"><StatusBadge value={req.readiness_status} /></td>
                <td className="table-cell text-xs text-slate-500">{req.owner_id || 'Unassigned'}</td>
                <td className="table-cell">
                  <button onClick={() => onOpenExplanation(req.requirement_id)} className="btn-secondary px-3 py-1.5 text-xs">
                    Explain
                    <FileText size={13} />
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-400">No requirements match the selected filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  options: string[]
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase text-slate-500">{label}</span>
      <select className="input-field" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>{sentenceCase(option)}</option>
        ))}
      </select>
    </label>
  )
}

function StandardsBrowserView({
  coverage,
  chapters,
  requirements,
  onOpenExplanation,
}: {
  coverage: Coverage | null
  chapters: OntologyChapter[]
  requirements: OntologyRequirement[]
  onOpenExplanation: (id: string) => void
}) {
  const [selectedChapter, setSelectedChapter] = useState(chapters[0]?.canonical_code || '')
  const activeChapter = selectedChapter || chapters[0]?.canonical_code || ''
  const chapterRequirements = requirements.filter((req) => !activeChapter || req.chapter_code === activeChapter)
  const coverageByCode = useMemo(
    () => new Map((coverage?.chapters || []).map((chapter) => [chapter.chapter_code, chapter])),
    [coverage]
  )

  useEffect(() => {
    if (!selectedChapter && chapters.length > 0) setSelectedChapter(chapters[0].canonical_code)
  }, [chapters, selectedChapter])

  return (
    <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 p-4">
          <h3 className="font-bold text-slate-900">Official Chapters</h3>
          <p className="mt-1 text-xs text-slate-500">Browse the NABH 6th Edition structure independent of hospital progress.</p>
        </div>
        <div className="divide-y divide-slate-100">
          {chapters.map((chapter) => {
            const stats = coverageByCode.get(chapter.canonical_code)
            const active = chapter.canonical_code === activeChapter
            return (
              <button
                key={chapter.id}
                onClick={() => setSelectedChapter(chapter.canonical_code)}
                className={`block w-full px-4 py-3 text-left transition-colors ${active ? 'bg-brand-50' : 'hover:bg-slate-50'}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className={`text-sm font-bold ${active ? 'text-brand-700' : 'text-slate-800'}`}>{chapter.canonical_code}</span>
                  <span className="text-xs text-slate-400">{stats?.seeded_objective_elements_count || 0} seeded</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">{chapter.title}</div>
              </button>
            )
          })}
        </div>
      </aside>

      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h3 className="text-lg font-bold text-slate-900">{activeChapter || 'All Chapters'}</h3>
              <p className="text-sm text-slate-500">
                {chapterRequirements.length} seeded requirements available in this browser.
              </p>
            </div>
            {coverage && (
              <div className="flex flex-wrap gap-2">
                <StatusBadge value={coverage.ontology_status} />
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-semibold text-slate-600">
                  {coverage.global_elements_coverage_percent}% global element coverage
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="divide-y divide-slate-100">
          {chapterRequirements.map((req) => (
            <div key={req.id} className="p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="font-mono text-xs font-bold text-brand-700">{req.canonical_code}</div>
                  <h4 className="mt-1 font-semibold text-slate-900">{req.description}</h4>
                  <p className="mt-1 text-xs text-slate-500">{req.standard_code}: {req.standard_title}</p>
                </div>
                <button onClick={() => onOpenExplanation(req.id)} className="btn-secondary px-3 py-1.5 text-xs">
                  Explain Requirement
                  <ChevronRight size={13} />
                </button>
              </div>
            </div>
          ))}
          {chapterRequirements.length === 0 && (
            <div className="p-10 text-center text-sm text-slate-400">No seeded requirements are available for this chapter yet.</div>
          )}
        </div>
      </section>
    </div>
  )
}

function EvidenceNeededView({
  explanations,
  loading,
  requirementCount,
  hasComputedScope,
  onGoApplicable,
}: {
  explanations: RequirementExplanation[]
  loading: boolean
  requirementCount: number
  hasComputedScope: boolean
  onGoApplicable: () => void
}) {
  const evidenceRows = explanations.flatMap((explanation) =>
    explanation.required_evidence.map((evidence) => ({
      ...evidence,
      requirement_code: explanation.requirement_code,
      responsible_role: evidence.default_owner_role || explanation.responsible_role,
      confidence: explanation.confidence,
    }))
  )

  const groupedByType = evidenceRows.reduce<Record<string, typeof evidenceRows>>((groups, row) => {
    const key = row.evidence_type || 'other'
    groups[key] = groups[key] || []
    groups[key].push(row)
    return groups
  }, {})

  if (!hasComputedScope) {
    return (
      <EmptyState
        icon={FileSearch}
        title="Evidence plan needs computed scope"
        body="Compute applicability first so this view can aggregate evidence only for applicable requirements."
        actionLabel="Review Applicable Requirements"
        onAction={onGoApplicable}
      />
    )
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
        <Loader2 size={22} className="mx-auto mb-3 animate-spin text-brand-600" />
        Loading source-cited evidence expectations
      </div>
    )
  }

  return (
    <section className="space-y-5">
      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <h3 className="text-lg font-bold text-slate-900">Evidence Needed</h3>
        <p className="mt-1 text-sm text-slate-500">
          Aggregated proof expectations across {requirementCount} applicable, conditional, or manual-review requirements. Uploads are intentionally deferred.
        </p>
      </div>

      {Object.entries(groupedByType).map(([type, rows]) => (
        <div key={type} className="rounded-lg border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div className="flex items-center gap-2">
              <FileText size={18} className="text-brand-600" />
              <h4 className="font-bold text-slate-900">{sentenceCase(type)}</h4>
            </div>
            <span className="text-xs font-semibold text-slate-500">{rows.length} item(s)</span>
          </div>
          <div className="divide-y divide-slate-100">
            {rows.map((row) => (
              <div key={`${row.requirement_code}-${row.evidence_code}`} className="grid gap-3 p-4 lg:grid-cols-[150px_minmax(0,1fr)_180px]">
                <div className="font-mono text-xs font-bold text-brand-700">{row.requirement_code}</div>
                <div>
                  <div className="text-sm font-semibold text-slate-900">{row.description}</div>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{row.suggested_documentation || 'No suggested documentation recorded.'}</p>
                  {row.confidence === 'missing_citation' && (
                    <p className="mt-2 text-xs font-semibold text-red-600">Citation missing for this requirement.</p>
                  )}
                </div>
                <div className="text-xs text-slate-500">
                  <div><span className="font-semibold text-slate-700">Owner:</span> {sentenceCase(row.responsible_role)}</div>
                  <div><span className="font-semibold text-slate-700">Frequency:</span> {sentenceCase(row.evidence_frequency)}</div>
                  <div><span className="font-semibold text-slate-700">Lookback:</span> {row.minimum_lookback_days} days</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {evidenceRows.length === 0 && (
        <EmptyState
          icon={FileSearch}
          title="No evidence expectations found"
          body="The applicable scope exists, but no evidence requirements were returned for these seeded requirements."
        />
      )}
    </section>
  )
}

function ReadinessStrip({ readiness }: { readiness: Readiness | null }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Readiness Summary</h3>
          <p className="text-sm text-slate-500">This score is shown after scope because it depends on applicable requirements.</p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <HeaderMetric label="Score" value={readiness?.readiness_score_percent == null ? 'N/A' : `${readiness.readiness_score_percent}%`} tone="info" />
          <HeaderMetric label="Denominator" value={`${readiness?.denominator || 0}`} tone="info" />
          <HeaderMetric label="Ready" value={`${readiness?.ready_count || 0}`} tone="good" />
          <HeaderMetric label="Excluded" value={`${readiness?.not_applicable_count || 0}`} tone="warn" />
        </div>
      </div>
    </div>
  )
}

function RequirementExplanationDrawer({
  requirementId,
  explanation,
  loading,
  onClose,
}: {
  requirementId: string | null
  explanation: RequirementExplanation | null
  loading: boolean
  onClose: () => void
}) {
  if (!requirementId) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
      <aside className="h-full w-full max-w-3xl overflow-y-auto bg-white shadow-xl">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Requirement Explanation</h3>
            <p className="text-xs text-slate-500">Source-cited deterministic guidance</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Close explanation">
            <X size={20} />
          </button>
        </div>

        {loading && (
          <div className="flex min-h-[320px] items-center justify-center text-sm text-slate-500">
            <Loader2 size={22} className="mr-2 animate-spin text-brand-600" />
            Loading explanation
          </div>
        )}

        {!loading && explanation && (
          <div className="space-y-5 p-5">
            <div>
              <div className="font-mono text-xs font-bold text-brand-700">{explanation.requirement_code}</div>
              <h4 className="mt-1 text-xl font-bold text-slate-900">{explanation.title}</h4>
              <div className="mt-3 flex flex-wrap gap-2">
                <StatusBadge value={explanation.confidence} />
                <StatusBadge value={explanation.applicability.status} />
              </div>
            </div>

            {explanation.limitations.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <div className="mb-1 font-semibold">Limitations</div>
                <ul className="list-disc space-y-1 pl-5">
                  {explanation.limitations.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            )}

            <DrawerSection title="What This Means">
              <p>{explanation.plain_language_explanation || 'A source-cited explanation is unavailable for this requirement.'}</p>
            </DrawerSection>

            <DrawerSection title="Why It Matters">
              <p>{explanation.why_it_matters || 'Why-it-matters guidance is withheld until a citation is available.'}</p>
            </DrawerSection>

            <DrawerSection title="Ownership">
              <div className="grid gap-3 sm:grid-cols-2">
                <SnapshotRow label="Responsible role" value={sentenceCase(explanation.responsible_role)} />
                <SnapshotRow label="Owner" value={explanation.responsible_owner_name || 'Unassigned'} />
              </div>
              {explanation.responsible_roles.length > 0 && (
                <p className="mt-2 text-xs text-slate-500">Roles involved: {explanation.responsible_roles.map(sentenceCase).join(', ')}</p>
              )}
            </DrawerSection>

            <DrawerSection title="Proof Burden">
              <div className="grid gap-3 sm:grid-cols-4">
                <HeaderMetric label="Mandatory" value={`${explanation.proof_burden_summary.mandatory_evidence_count}`} tone="info" />
                <HeaderMetric label="Optional" value={`${explanation.proof_burden_summary.optional_evidence_count}`} tone="info" />
                <HeaderMetric label="Lookback" value={`${explanation.proof_burden_summary.lookback_days_required} days`} tone="warn" />
                <HeaderMetric label="Types" value={`${explanation.proof_burden_summary.evidence_types_required.length}`} tone="good" />
              </div>
            </DrawerSection>

            <DrawerSection title="Evidence Needed">
              <div className="space-y-3">
                {explanation.required_evidence.map((evidence) => (
                  <div key={evidence.evidence_code} className="rounded-lg border border-slate-200 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-brand-700">{evidence.evidence_code}</span>
                      <StatusBadge value={evidence.is_mandatory ? 'mandatory' : 'optional'} />
                      <StatusBadge value={evidence.evidence_type} />
                    </div>
                    <p className="mt-2 text-sm font-medium text-slate-800">{evidence.description}</p>
                    <p className="mt-1 text-sm text-slate-500">{evidence.suggested_documentation || 'No suggested documentation recorded.'}</p>
                  </div>
                ))}
              </div>
            </DrawerSection>

            <DrawerSection title="Citations">
              <div className="space-y-3">
                {explanation.citations.map((citation, index) => (
                  <div key={`${citation.document_title}-${index}`} className="rounded-lg border border-slate-200 p-3 text-sm">
                    <div className="font-semibold text-slate-900">{citation.document_title}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {citation.publisher} / Edition {citation.edition_version} / Section {citation.section || 'N/A'} / Page {citation.page_number || 'N/A'}
                    </div>
                    <p className="mt-2 text-slate-600">{citation.clause_text_summary || 'No clause summary recorded.'}</p>
                  </div>
                ))}
                {explanation.citations.length === 0 && (
                  <p className="text-sm text-slate-500">No citation records are available.</p>
                )}
              </div>
            </DrawerSection>
          </div>
        )}
      </aside>
    </div>
  )
}

function DrawerSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 p-4">
      <h5 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">{title}</h5>
      <div className="text-sm leading-6 text-slate-600">{children}</div>
    </section>
  )
}

function EmptyState({
  icon: Icon,
  title,
  body,
  actionLabel,
  onAction,
}: {
  icon: any
  title: string
  body: string
  actionLabel?: string
  onAction?: () => void
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-10 text-center">
      <Icon size={36} className="mx-auto text-slate-300" />
      <h3 className="mt-3 text-lg font-bold text-slate-900">{title}</h3>
      <p className="mx-auto mt-2 max-w-lg text-sm text-slate-500">{body}</p>
      {actionLabel && onAction && (
        <button onClick={onAction} className="btn-primary mt-5">
          {actionLabel}
          <ChevronRight size={16} />
        </button>
      )}
    </div>
  )
}
