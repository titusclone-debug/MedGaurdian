import { useState, useEffect } from 'react'
import { Award, CheckCircle, AlertTriangle, Clock, ChevronRight, Target, Plus, X } from 'lucide-react'

export default function NABHPage() {
  const [complianceSummary, setComplianceSummary] = useState<any>(null)
  const [gapAnalysis, setGapAnalysis] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Modals state
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false)
  const [selectedStandardCode, setSelectedStandardCode] = useState('')
  const [formStatus, setFormStatus] = useState('compliant')
  const [formScore, setFormScore] = useState('100')
  const [formEvidence, setFormEvidence] = useState('')
  const [formPlan, setFormPlan] = useState('')
  const [formDeadline, setFormDeadline] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Full chapter mapping names for aesthetic rendering
  const CHAPTER_NAMES: Record<string, string> = {
    'ACC': 'Access, Assessment & Continuity',
    'PC': 'Patient Care',
    'FMS': 'Facility Management & Safety',
    'QMS': 'Quality Management System',
    'IS': 'Information Management',
    'HR': 'Human Resource Management'
  }

  async function fetchNABHData() {
    try {
      const token = localStorage.getItem('medguardian_token')
      const userString = localStorage.getItem('medguardian_user')
      const userObj = userString ? JSON.parse(userString) : null
      const hospitalId = userObj?.hospital_id

      if (!token || !hospitalId) {
        setError('Session or hospital identifier missing')
        setLoading(false)
        return
      }

      const headers = { 'Authorization': `Bearer ${token}` }

      // Fetch compliance overview and gaps concurrently
      const [compRes, gapRes] = await Promise.all([
        fetch(`/api/nabh/compliance/${hospitalId}`, { headers }),
        fetch(`/api/nabh/gap-analysis/${hospitalId}`, { headers })
      ])

      if (!compRes.ok || !gapRes.ok) {
        throw new Error('Failed to retrieve NABH accreditation indices')
      }

      const compData = await compRes.json()
      const gapData = await gapRes.json()

      setComplianceSummary(compData)
      setGapAnalysis(gapData)
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Synchronization failure')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNABHData()
  }, [])

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
      const token = localStorage.getItem('medguardian_token')
      const userString = localStorage.getItem('medguardian_user')
      const userObj = userString ? JSON.parse(userString) : null
      const hospitalId = userObj?.hospital_id

      if (!token || !hospitalId) throw new Error('Authentication expired')

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
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Compliance update failed')
      }

      setIsUpdateModalOpen(false)
      setLoading(true)
      await fetchNABHData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4 animate-pulse">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
        <p className="text-slate-500 text-sm font-medium">Synchronizing QCI NABH accreditation tracking nodes...</p>
      </div>
    )
  }

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

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Award size={28} className="text-brand-600" />
          NABH Compliance Tracker
        </h2>
        <p className="text-slate-500 mt-1">6th Edition Accreditation Standards • Effective January 2025</p>
      </div>
      
      {error && (
        <div className="p-4 border-2 border-red-200 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-3">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Overall Readiness */}
      <div className="card p-6 border-2 border-brand-200 bg-brand-50">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-brand-900">Accreditation Readiness</h3>
            <p className="text-sm text-brand-700 mt-1">
              {complianceSummary?.readiness_level === 'Assessment Ready' ? 'Assessment Ready — Schedule NABH audit' :
               complianceSummary?.readiness_level === 'Near Ready' ? 'Near Ready — Focus on remaining gaps' :
               'In Progress — Continue systematic remediation'}
            </p>
          </div>
          <div className="text-center">
            <div className="text-5xl font-bold text-brand-700">{overallScore}%</div>
            <div className="text-sm text-brand-600">Overall Compliance</div>
          </div>
        </div>
        <div className="mt-4 w-full h-3 bg-brand-100 rounded-full overflow-hidden">
          <div 
            className={`h-full rounded-full transition-all duration-1000 bg-brand-500`}
            style={{ width: `${overallScore}%` }}
          />
        </div>
      </div>
      
      {/* Chapter Scores */}
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
      
      {/* Gap Analysis */}
      <div className="card">
        <div className="px-6 py-4 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <Target size={20} className="text-orange-500" />
            <h3 className="text-lg font-semibold text-slate-900">Gap Analysis — Priority Remediation</h3>
          </div>
          <p className="text-sm text-slate-500 mt-1">Standards requiring immediate attention</p>
        </div>
        <div className="divide-y divide-slate-100">
          {gaps.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              Excellent! No compliance gaps recorded.
            </div>
          ) : (
            gaps.map((gap: any) => (
              <div key={gap.standard_code} className="px-6 py-5">
                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="font-mono text-sm font-bold text-brand-600">{gap.standard_code}</span>
                      <span className={`badge ${
                        gap.priority === 'critical' ? 'badge-critical' :
                        gap.priority === 'high' ? 'badge-high' : 'badge-medium'
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
                      <span>Remediation Deadline: {gap.remediation_deadline?.split('T')[0] || 'Unscheduled'}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-center lg:items-end shrink-0 gap-3">
                    <div className="text-center lg:text-right">
                      <div className="text-3xl font-bold text-orange-600">{gap.gap_percentage}%</div>
                      <div className="text-xs text-slate-500">Deficit</div>
                    </div>
                    <button 
                      onClick={() => handleOpenUpdateModal(gap.standard_code)}
                      className="btn-secondary text-xs px-3 py-1.5 border-brand-300 text-brand-700 hover:bg-brand-50"
                    >
                      Update Assessment
                    </button>
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

      {/* Compliance Update Assessment Modal */}
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
