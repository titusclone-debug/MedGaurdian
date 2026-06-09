import { useState, useEffect, useCallback } from 'react'
import { Award, CheckCircle, AlertTriangle, Clock, ChevronRight, Target, Plus, X, Zap, Download, FileText, Activity, RefreshCw, Shield, TrendingUp } from 'lucide-react'

// ============================================================
// TYPES
// ============================================================

interface DailyAction {
  priority: number
  standard_code: string
  standard_name: string
  chapter_code: string
  severity: string
  maturity_level: number
  maturity_label: string
  task: string
  deadline: string | null
}

interface FeedEvent {
  id: string
  agent: string
  action: string
  standard_code: string
  severity: string
  timestamp: string | null
  status: string
  recommended_action: string
}

interface SOPData {
  standard_code: string
  title: string
  customized_content: string
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function timeAgo(isoString: string | null): string {
  if (!isoString) return 'Unknown'
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'text-red-600 bg-red-50 border-red-200'
    case 'high': return 'text-orange-600 bg-orange-50 border-orange-200'
    case 'major': return 'text-orange-600 bg-orange-50 border-orange-200'
    case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    case 'minor': return 'text-blue-600 bg-blue-50 border-blue-200'
    default: return 'text-slate-600 bg-slate-50 border-slate-200'
  }
}

function severityDot(severity: string): string {
  switch (severity) {
    case 'critical': return '🔴'
    case 'high': return '🟠'
    case 'major': return '🟠'
    case 'medium': return '🟡'
    case 'minor': return '🟢'
    default: return '⚪'
  }
}

function agentIcon(agent: string): string {
  if (agent.toLowerCase().includes('inspector')) return '🔍'
  if (agent.toLowerCase().includes('consultant')) return '📋'
  return '🤖'
}

// ============================================================
// CHAPTER MAPPING
// ============================================================

const CHAPTER_NAMES: Record<string, string> = {
  'ACC': 'Access, Assessment & Continuity',
  'PC': 'Patient Care',
  'FMS': 'Facility Management & Safety',
  'QMS': 'Quality Management System',
  'IS': 'Information Management',
  'HR': 'Human Resource Management'
}

// ============================================================
// MAIN COMPONENT
// ============================================================

export default function LegacyNABHDashboard() {
  // Core data
  const [complianceSummary, setComplianceSummary] = useState<any>(null)
  const [gapAnalysis, setGapAnalysis] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Agentic data
  const [dailyBrief, setDailyBrief] = useState<any>(null)
  const [activityFeed, setActivityFeed] = useState<any>(null)
  const [feedLoading, setFeedLoading] = useState(false)
  const [roadmap, setRoadmap] = useState<any>(null)
  const [generatingRoadmap, setGeneratingRoadmap] = useState(false)

  // Agent actions
  const [assessing, setAssessing] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [assessmentResult, setAssessmentResult] = useState<any>(null)

  // SOP Modal
  const [sopModalOpen, setSopModalOpen] = useState(false)
  const [sopData, setSopData] = useState<SOPData | null>(null)
  const [sopLoading, setSopLoading] = useState(false)

  // Update Assessment Modal
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false)
  const [selectedStandardCode, setSelectedStandardCode] = useState('')
  const [formStatus, setFormStatus] = useState('compliant')
  const [formScore, setFormScore] = useState('100')
  const [formEvidence, setFormEvidence] = useState('')
  const [formPlan, setFormPlan] = useState('')
  const [formDeadline, setFormDeadline] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Toast notifications
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null)

  // ============================================================
  // HELPERS
  // ============================================================

  function getAuthHeaders() {
    const token = localStorage.getItem('medguardian_token')
    return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
  }

  function getHospitalId(): string | null {
    const userString = localStorage.getItem('medguardian_user')
    const userObj = userString ? JSON.parse(userString) : null
    return userObj?.hospital_id || null
  }

  function showToast(message: string, type: 'success' | 'error' | 'info') {
    setToast({ message, type })
    setTimeout(() => setToast(null), 5000)
  }

  // ============================================================
  // DATA FETCHING
  // ============================================================

  const fetchCoreData = useCallback(async () => {
    try {
      const hospitalId = getHospitalId()
      const headers = getAuthHeaders()
      if (!hospitalId) { setError('Session or hospital identifier missing'); setLoading(false); return }

      const [compRes, gapRes] = await Promise.all([
        fetch(`/api/nabh/compliance/${hospitalId}`, { headers }),
        fetch(`/api/nabh/gap-analysis/${hospitalId}`, { headers })
      ])

      if (!compRes.ok || !gapRes.ok) throw new Error('Failed to retrieve NABH accreditation indices')

      setComplianceSummary(await compRes.json())
      setGapAnalysis(await gapRes.json())
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Synchronization failure')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchAgenticData = useCallback(async () => {
    try {
      const hospitalId = getHospitalId()
      const headers = getAuthHeaders()
      if (!hospitalId) return

      setFeedLoading(true)
      const [briefRes, feedRes, roadmapRes] = await Promise.all([
        fetch(`/api/nabh/agent/daily-brief/${hospitalId}`, { headers }),
        fetch(`/api/nabh/agent/activity-feed/${hospitalId}`, { headers }),
        fetch(`/api/nabh/agent/generate-roadmap/${hospitalId}?target_months=16`, { method: 'POST', headers })
      ])

      if (briefRes.ok) setDailyBrief(await briefRes.json())
      if (feedRes.ok) setActivityFeed(await feedRes.json())
      if (roadmapRes.ok) setRoadmap(await roadmapRes.json())
    } catch (err: any) {
      console.error('Agentic data fetch error:', err)
    } finally {
      setFeedLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCoreData()
    fetchAgenticData()
    // Auto-refresh activity feed every 60 seconds
    const interval = setInterval(fetchAgenticData, 60000)
    return () => clearInterval(interval)
  }, [fetchCoreData, fetchAgenticData])

  // ============================================================
  // AGENT ACTIONS
  // ============================================================

  async function handleRunAssessment() {
    setAssessing(true)
    setError('')
    try {
      const hospitalId = getHospitalId()
      const res = await fetch(`/api/nabh/agent/assess/${hospitalId}`, {
        method: 'POST',
        headers: getAuthHeaders()
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Agent assessment failed')
      }
      const result = await res.json()
      setAssessmentResult(result)
      showToast(
        `Assessment complete: ${result.assessment?.gaps_count || 0} gaps found, ${result.remediation?.capa_created_count || 0} CAPA tasks created.`,
        'success'
      )
      // Refresh all data
      setLoading(true)
      await Promise.all([fetchCoreData(), fetchAgenticData()])
    } catch (err: any) {
      showToast(err.message || 'Assessment failed', 'error')
      setError(err.message)
    } finally {
      setAssessing(false)
    }
  }

  async function handleGenerateRoadmap() {
    setGeneratingRoadmap(true)
    try {
      const hospitalId = getHospitalId()
      const res = await fetch(`/api/nabh/agent/generate-roadmap/${hospitalId}?target_months=16`, {
        method: 'POST',
        headers: getAuthHeaders()
      })
      if (!res.ok) {
        throw new Error('Failed to generate roadmap')
      }
      const data = await res.json()
      setRoadmap(data)
      showToast('NABH Accreditation Roadmap regenerated successfully.', 'success')
    } catch (err: any) {
      showToast(err.message || 'Roadmap generation failed', 'error')
    } finally {
      setGeneratingRoadmap(false)
    }
  }

  async function handleExportBinder() {
    setExporting(true)
    try {
      const hospitalId = getHospitalId()
      const token = localStorage.getItem('medguardian_token')
      const res = await fetch(`/api/nabh/agent/export-binder/${hospitalId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || 'Export failed')
      }
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Surveyor_Binder_${hospitalId}.zip`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      showToast('Surveyor Binder downloaded successfully.', 'success')
    } catch (err: any) {
      showToast(err.message || 'Export failed. Check network and permissions.', 'error')
    } finally {
      setExporting(false)
    }
  }

  async function handleDraftSOP(standardCode: string) {
    setSopLoading(true)
    setSopModalOpen(true)
    setSopData(null)
    try {
      const hospitalId = getHospitalId()
      const res = await fetch(`/api/nabh/agent/sop/${hospitalId}/${standardCode}`, {
        headers: getAuthHeaders()
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || 'SOP generation failed')
      }
      setSopData(await res.json())
    } catch (err: any) {
      showToast(err.message || 'SOP generation failed', 'error')
      setSopModalOpen(false)
    } finally {
      setSopLoading(false)
    }
  }

  // ============================================================
  // COMPLIANCE UPDATE MODAL
  // ============================================================

  const handleOpenUpdateModal = (code: string) => {
    setSelectedStandardCode(code)
    setFormStatus('compliant')
    setFormScore('100')
    setFormEvidence('')
    setFormPlan('')
    setFormDeadline('')
    setIsUpdateModalOpen(true)
  }

  const handleUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const hospitalId = getHospitalId()
      if (!hospitalId) throw new Error('Authentication expired')
      const payload = {
        standard_code: selectedStandardCode,
        status: formStatus,
        current_score: parseFloat(formScore),
        evidence_description: formEvidence || null,
        remediation_plan: formPlan || null,
        remediation_deadline: formDeadline || null
      }
      const res = await fetch(`/api/nabh/update/${hospitalId}`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Compliance update failed')
      }
      setIsUpdateModalOpen(false)
      showToast(`Standard ${selectedStandardCode} updated successfully.`, 'success')
      setLoading(true)
      await Promise.all([fetchCoreData(), fetchAgenticData()])
    } catch (err: any) {
      showToast(err.message || 'Update failed', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  // ============================================================
  // LOADING STATE
  // ============================================================

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4 animate-pulse">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
        <p className="text-slate-500 text-sm font-medium">Synchronizing QCI NABH accreditation tracking nodes...</p>
      </div>
    )
  }

  // ============================================================
  // DERIVED DATA
  // ============================================================

  const overallScore = complianceSummary?.overall_compliance_rate || 0
  const chaptersList = complianceSummary?.chapters
    ? Object.entries(complianceSummary.chapters).map(([code, chObj]: [string, any]) => ({
        code,
        name: CHAPTER_NAMES[code] || chObj.name || code,
        total: chObj.total || 0,
        compliant: chObj.compliant || 0,
        partial: chObj.partial || 0,
        score: Math.round(chObj.compliance_rate || 0)
      }))
    : []

  const gaps = gapAnalysis?.gaps || []
  const missingStandards = gapAnalysis?.missing_standards || []
  const dailyActions: DailyAction[] = dailyBrief?.daily_actions || []
  const feedEvents: FeedEvent[] = activityFeed?.feed || []
  const lastAssessment = activityFeed?.last_assessment
  const assessedBy = activityFeed?.assessed_by

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="space-y-6 animate-fade-in">

      {/* ============ TOAST NOTIFICATION ============ */}
      {toast && (
        <div className={`fixed top-4 right-4 z-[100] max-w-sm p-4 rounded-xl shadow-lg border-2 transition-all animate-scale-up ${
          toast.type === 'success' ? 'bg-emerald-50 border-emerald-300 text-emerald-800' :
          toast.type === 'error' ? 'bg-red-50 border-red-300 text-red-800' :
          'bg-blue-50 border-blue-300 text-blue-800'
        }`}>
          <div className="flex items-start gap-2">
            <span className="text-lg">{toast.type === 'success' ? '✅' : toast.type === 'error' ? '❌' : 'ℹ️'}</span>
            <p className="text-sm font-medium flex-1">{toast.message}</p>
            <button onClick={() => setToast(null)} className="text-slate-400 hover:text-slate-600">
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ============ SECTION 1: HEADER + AGENTIC ACTION BAR ============ */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Award size={28} className="text-brand-600" />
            NABH Agentic Compliance
          </h2>
          <p className="text-slate-500 mt-1">6th Edition • Dual-Agent Autonomous Audit System</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAssessment}
            disabled={assessing}
            id="btn-run-assessment"
            className="btn-primary py-2.5 px-5 flex items-center gap-2 text-sm font-semibold disabled:opacity-60"
          >
            {assessing ? (
              <RefreshCw size={16} className="animate-spin" />
            ) : (
              <Zap size={16} />
            )}
            {assessing ? 'Running Agent Assessment...' : 'Run Agent Assessment'}
          </button>
          <button
            onClick={handleExportBinder}
            disabled={exporting}
            id="btn-export-binder"
            className="btn-secondary py-2.5 px-5 flex items-center gap-2 text-sm font-semibold border-brand-300 text-brand-700 hover:bg-brand-50 disabled:opacity-60"
          >
            {exporting ? (
              <RefreshCw size={16} className="animate-spin" />
            ) : (
              <Download size={16} />
            )}
            {exporting ? 'Generating...' : 'Export Surveyor Binder'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 border-2 border-red-200 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-3">
          <AlertTriangle size={20} />
          <span>{error}</span>
          <button onClick={() => setError('')} className="ml-auto"><X size={16} /></button>
        </div>
      )}

      {/* ============ SECTION 2: DAILY BRIEF — TODAY'S 3 PRIORITY ACTIONS ============ */}
      <div className="card border-2 border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50">
        <div className="px-6 py-4 border-b border-amber-200">
          <div className="flex items-center gap-2">
            <Shield size={20} className="text-amber-600" />
            <h3 className="text-lg font-semibold text-slate-900">Today's Priority Actions</h3>
            {dailyBrief && (
              <span className="ml-auto text-xs font-medium text-amber-700 bg-amber-100 px-2.5 py-1 rounded-full">
                {dailyBrief.gaps_remaining} gaps remaining • {dailyBrief.readiness_pct}% ready
              </span>
            )}
          </div>
        </div>
        <div className="p-6">
          {dailyActions.length === 0 ? (
            <div className="text-center py-4 text-slate-400">
              <Shield size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">No gaps detected or agent assessment has not been run yet.</p>
              <p className="text-xs mt-1">Click <strong>"Run Agent Assessment"</strong> to populate today's actions.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {dailyActions.map((action) => (
                <div key={action.standard_code} className="bg-white rounded-xl border border-slate-200 p-4 space-y-3 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white bg-amber-500 w-6 h-6 rounded-full flex items-center justify-center">
                      {action.priority}
                    </span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${severityColor(action.severity)}`}>
                      {action.severity.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <span className="font-mono text-xs font-bold text-brand-600">{action.standard_code}</span>
                    <h4 className="font-semibold text-slate-900 text-sm mt-0.5 leading-snug">{action.standard_name}</h4>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed line-clamp-3">{action.task}</p>
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-xs text-slate-400">
                      Maturity: <span className="font-medium">{action.maturity_label}</span>
                    </span>
                    <button
                      onClick={() => handleDraftSOP(action.standard_code)}
                      className="text-xs font-semibold text-brand-600 hover:text-brand-800 flex items-center gap-1"
                    >
                      <FileText size={12} /> Draft SOP →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ============ SECTION 3: LIVE AGENT ACTIVITY FEED ============ */}
      <div className="card">
        <div className="px-6 py-4 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <Activity size={20} className="text-brand-600" />
            <h3 className="text-lg font-semibold text-slate-900">Live Agent Activity Feed</h3>
            {feedLoading && <RefreshCw size={14} className="animate-spin text-slate-400 ml-2" />}
            <span className="ml-auto text-xs text-slate-400">
              {lastAssessment
                ? `Last assessed: ${timeAgo(lastAssessment)} by ${assessedBy || 'Agent'}`
                : 'Never assessed — Run Assessment to begin'}
            </span>
          </div>
        </div>
        <div className="divide-y divide-slate-100 max-h-[320px] overflow-y-auto">
          {feedEvents.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <Activity size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">No agent activity yet.</p>
              <p className="text-xs mt-1">Click <strong>"Run Agent Assessment"</strong> to start the compliance audit engine.</p>
            </div>
          ) : (
            feedEvents.map((event) => (
              <div key={event.id} className="px-6 py-3 flex items-center gap-4 hover:bg-slate-50 transition-colors">
                <span className="text-lg shrink-0">{agentIcon(event.agent)}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-semibold text-slate-700">{event.agent}</span>
                    <span className="font-mono text-xs font-bold text-brand-600">{event.standard_code}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded border ${event.status === 'resolved' ? 'text-green-600 bg-green-50 border-green-200' : 'text-orange-600 bg-orange-50 border-orange-200'}`}>
                      {event.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 truncate">{event.action}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-sm">{severityDot(event.severity)}</span>
                  <span className="text-xs text-slate-400 whitespace-nowrap">{timeAgo(event.timestamp)}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ============ ACCREDITATION REMEDIATION ROADMAP ============ */}
      {roadmap && (
        <div className="card border-2 border-brand-200 bg-white p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Clock className="text-brand-600" size={22} />
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Accreditation Remediation Roadmap</h3>
                <p className="text-xs text-slate-500">Target Survey Date: {new Date(roadmap.target_survey_date).toLocaleDateString()}</p>
              </div>
            </div>
            <button
              onClick={handleGenerateRoadmap}
              disabled={generatingRoadmap}
              className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1 border-brand-300 text-brand-700 hover:bg-brand-50"
            >
              {generatingRoadmap ? <RefreshCw size={12} className="animate-spin" /> : <RefreshCw size={12} />}
              Recalibrate Roadmap
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Object.entries(roadmap.roadmap).map(([phaseName, phaseData]: [string, any], index: number) => (
              <div key={phaseName} className="bg-slate-50 rounded-xl border border-slate-200 p-4 flex flex-col justify-between space-y-3 relative hover:shadow-sm transition-shadow">
                {/* Number badge on top right */}
                <div className="absolute top-3 right-3 text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-100 text-brand-700">
                  Phase {index + 1}
                </div>
                
                <div className="space-y-2">
                  <div>
                    <h4 className="font-bold text-slate-800 text-sm">{phaseName}</h4>
                    <span className="text-[10px] font-semibold text-slate-400 block mt-0.5">{phaseData.window} • Due by {new Date(phaseData.due_by).toLocaleDateString()}</span>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">{phaseData.focus}</p>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-200">
                  <div className="flex justify-between items-center text-[10px] text-slate-400 font-semibold">
                    <span>Gaps to address:</span>
                    <span>{phaseData.count} standards</span>
                  </div>
                  
                  {/* Standards list */}
                  <div className="flex flex-wrap gap-1 max-h-[60px] overflow-y-auto pr-1">
                    {phaseData.standards.length === 0 ? (
                      <span className="text-[10px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded font-medium border border-emerald-100">
                        ✅ Clear
                      </span>
                    ) : (
                      phaseData.standards.map((std: any) => (
                        <span 
                          key={typeof std === 'string' ? std : std.code} 
                          className="text-[9px] font-mono font-bold text-slate-600 bg-slate-200 px-1.5 py-0.5 rounded"
                          title={typeof std === 'string' ? std : std.name}
                        >
                          {typeof std === 'string' ? std : std.code}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ============ SECTION 4: ACCREDITATION READINESS GAUGE ============ */}
      <div className="card p-6 border-2 border-brand-200 bg-brand-50">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-brand-900">Accreditation Readiness</h3>
            <p className="text-sm text-brand-700 mt-1">
              {complianceSummary?.readiness_level === 'Assessment Ready' ? 'Assessment Ready — Schedule NABH audit' :
               complianceSummary?.readiness_level === 'Near Ready' ? 'Near Ready — Focus on remaining gaps' :
               'In Progress — Continue systematic remediation'}
            </p>
            <p className="text-xs text-brand-600 mt-2 flex items-center gap-1">
              <TrendingUp size={12} />
              {lastAssessment
                ? `Last assessed: ${timeAgo(lastAssessment)} by ${assessedBy || 'System'}`
                : 'Never assessed — Run Agent Assessment to populate metrics'}
            </p>
          </div>
          <div className="text-center">
            <div className="text-5xl font-bold text-brand-700">{overallScore}%</div>
            <div className="text-sm text-brand-600">Overall Compliance</div>
          </div>
        </div>
        <div className="mt-4 w-full h-3 bg-brand-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000 bg-brand-500"
            style={{ width: `${overallScore}%` }}
          />
        </div>
      </div>

      {/* Chapter Scores Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {chaptersList.map((ch) => (
          <div key={ch.code} className="card-hover p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <span className="text-xs font-bold text-brand-600">{ch.code}</span>
                <h4 className="font-semibold text-slate-900 text-sm">{ch.name}</h4>
              </div>
              <div className={`text-2xl font-bold ${
                ch.score >= 80 ? 'text-green-600' : ch.score >= 60 ? 'text-yellow-600' : 'text-red-600'
              }`}>
                {ch.score}%
              </div>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden mb-2">
              <div
                className={`h-full rounded-full ${
                  ch.score >= 80 ? 'bg-green-500' : ch.score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${ch.score}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-500">
              <span>{ch.compliant}/{ch.total} compliant</span>
              <span>{ch.partial} partial</span>
            </div>
          </div>
        ))}
      </div>

      {/* ============ SECTION 5: GAP ANALYSIS + SOP GENERATOR ============ */}
      <div className="card">
        <div className="px-6 py-4 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <Target size={20} className="text-orange-500" />
            <h3 className="text-lg font-semibold text-slate-900">Gap Analysis — Priority Remediation</h3>
          </div>
          <p className="text-sm text-slate-500 mt-1">Standards requiring immediate attention • Agent-generated SOPs available</p>
        </div>
        <div className="divide-y divide-slate-100">
          {gaps.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <CheckCircle size={32} className="mx-auto mb-2 text-green-400" />
              <p>Excellent! No compliance gaps recorded.</p>
            </div>
          ) : (
            gaps.map((gap: any) => (
              <div key={gap.standard_code} className="px-6 py-5">
                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="font-mono text-sm font-bold text-brand-600">{gap.standard_code}</span>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                        gap.priority === 'critical' ? 'text-red-600 bg-red-50 border-red-200' :
                        gap.priority === 'high' ? 'text-orange-600 bg-orange-50 border-orange-200' :
                        'text-yellow-600 bg-yellow-50 border-yellow-200'
                      }`}>
                        {gap.priority}
                      </span>
                    </div>
                    <h4 className="font-semibold text-slate-900">{gap.standard_name}</h4>
                    <p className="text-sm text-slate-500 mt-1">Chapter: {gap.chapter}</p>
                    <p className="text-sm text-slate-600 mt-2 p-3 bg-slate-50 rounded-lg">
                      <span className="font-medium">Remediation Plan:</span> {gap.remediation_plan || 'No plan drafted.'}
                    </p>
                    <div className="mt-2 text-xs text-slate-400">
                      <span>Deadline: {gap.remediation_deadline?.split('T')[0] || 'Unscheduled'}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-center lg:items-end shrink-0 gap-3">
                    <div className="text-center lg:text-right">
                      <div className="text-3xl font-bold text-orange-600">{gap.gap_percentage}%</div>
                      <div className="text-xs text-slate-500">Deficit</div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleDraftSOP(gap.standard_code)}
                        className="btn-secondary text-xs px-3 py-1.5 border-emerald-300 text-emerald-700 hover:bg-emerald-50 flex items-center gap-1"
                      >
                        <FileText size={12} /> Draft SOP
                      </button>
                      <button
                        onClick={() => handleOpenUpdateModal(gap.standard_code)}
                        className="btn-secondary text-xs px-3 py-1.5 border-brand-300 text-brand-700 hover:bg-brand-50"
                      >
                        Update Assessment
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Unassessed Reference Standards */}
      {missingStandards.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Clock size={20} className="text-brand-600" />
            Unassessed Reference Chapters ({missingStandards.length})
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto pr-2">
            {missingStandards.map((std: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                <div>
                  <span className="font-mono text-xs font-bold text-brand-600 block">{std.code}</span>
                  <span className="text-sm text-slate-700">{std.name}</span>
                </div>
                <button
                  onClick={() => handleOpenUpdateModal(std.code)}
                  className="btn-secondary text-xs px-2.5 py-1 border-brand-300 text-brand-700 hover:bg-brand-50 flex items-center gap-1"
                >
                  <Plus size={12} /> Assess
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ============ SOP MODAL ============ */}
      {sopModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-2xl max-h-[80vh] bg-white relative animate-scale-up flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center gap-2 shrink-0">
              <FileText className="text-emerald-600" size={24} />
              <h3 className="text-lg font-bold text-slate-900">
                {sopData ? `SOP: ${sopData.title}` : 'Generating SOP...'}
              </h3>
              <button
                onClick={() => setSopModalOpen(false)}
                className="ml-auto p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 overflow-y-auto flex-1">
              {sopLoading ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-3">
                  <RefreshCw size={24} className="animate-spin text-brand-600" />
                  <p className="text-sm text-slate-500">Consultant Agent is drafting your SOP...</p>
                </div>
              ) : sopData ? (
                <pre className="whitespace-pre-wrap text-sm text-slate-800 font-mono leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-200">
                  {sopData.customized_content}
                </pre>
              ) : (
                <p className="text-slate-400 text-center">No SOP data available.</p>
              )}
            </div>
            <div className="px-6 py-3 border-t border-slate-200 flex justify-end shrink-0">
              <button onClick={() => setSopModalOpen(false)} className="btn-secondary py-2 px-4">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* ============ COMPLIANCE UPDATE MODAL ============ */}
      {isUpdateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-md p-6 bg-white space-y-4 animate-scale-up relative">
            <button
              onClick={() => setIsUpdateModalOpen(false)}
              className="absolute right-4 top-4 p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <X size={20} />
            </button>
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <Award className="text-brand-600" size={24} />
              <h3 className="text-lg font-bold text-slate-900">Assess Standard: {selectedStandardCode}</h3>
            </div>

            <form onSubmit={handleUpdateSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Compliance Level</label>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value)}
                    className="input-field"
                  >
                    <option value="compliant">Fully Compliant</option>
                    <option value="partially_compliant">Partially Compliant</option>
                    <option value="non_compliant">Non Compliant</option>
                    <option value="under_review">Under Review</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Score (0 - 100)</label>
                  <input
                    type="number"
                    required
                    placeholder="e.g. 80"
                    value={formScore}
                    onChange={(e) => setFormScore(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Evidence Description</label>
                <input
                  type="text"
                  placeholder="e.g. surgical safety checklists reviewed and certified"
                  value={formEvidence}
                  onChange={(e) => setFormEvidence(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Remediation Action Plan</label>
                <textarea
                  placeholder="Draft remediation protocols..."
                  value={formPlan}
                  onChange={(e) => setFormPlan(e.target.value)}
                  className="input-field h-20"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Remediation Target Deadline</label>
                <input
                  type="date"
                  value={formDeadline}
                  onChange={(e) => setFormDeadline(e.target.value)}
                  className="input-field"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsUpdateModalOpen(false)}
                  className="btn-secondary py-2 px-4"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary py-2 px-4"
                >
                  {submitting ? 'Submitting...' : 'Record Assessment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
