import { useState, useEffect } from 'react'
import { 
  CloudLightning, CloudRain, CloudSun, Sun, Cloud,
  Shield, FileCheck, Recycle, Award, FileText, Users,
  AlertTriangle, TrendingUp, TrendingDown, Minus,
  ChevronRight, Clock, ArrowUpRight, ArrowRight, Save, CheckCircle
} from 'lucide-react'
import { Link } from 'react-router-dom'

const RISK_WEATHER = {
  critical: { icon: CloudLightning, label: 'Storm Warning', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
  high: { icon: CloudRain, label: 'Heavy Clouds', color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
  medium: { icon: CloudSun, label: 'Partly Cloudy', color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200' },
  low: { icon: Cloud, label: 'Mostly Clear', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  minimal: { icon: Sun, label: 'Clear Skies', color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' },
}

const MOCK_DASHBOARD = {
  risk_weather: { overall_score: 0.0, level: 'minimal', forecast: '☀️ Clear Skies', trend: 'stable' },
  domain_scores: {
    licenses: { score: 100, status: 'good' },
    nabh: { score: 100, status: 'good' },
    fcra: { score: 100, status: 'good' },
    dpdp_consent: { score: 100, status: 'good' },
    bmw: { score: 100, status: 'good' },
    staffing: { score: 100, status: 'good' },
  },
  quick_stats: {
    total_licenses: 0, expiring_soon: 0, expired_licenses: 0,
    nabh_readiness: '100%', bmw_compliance: '100%',
    active_consents: 0, expired_consents: 0,
    fcra_accounts: 0, active_alerts: 0, critical_alerts: 0,
  },
  alerts: { total_active: 0, critical: 0 },
}

export default function Dashboard() {
  const [dashboard, setDashboard] = useState<any>(MOCK_DASHBOARD)
  const [actions, setActions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  
  // Onboarding Stepper State
  const [onboardingStage, setOnboardingStage] = useState('profile') // 'profile', 'compliance', 'completed'
  const [bedCount, setBedCount] = useState<number>(50)
  const [hospitalType, setHospitalType] = useState('private')
  const [hasEmergency, setHasEmergency] = useState(true)
  const [hasIcu, setHasIcu] = useState(true)
  const [hasOt, setHasOt] = useState(true)
  
  const [hasFcra, setHasFcra] = useState(false)
  const [fcraNumber, setFcraNumber] = useState('')
  
  const [savingOnboard, setSavingOnboard] = useState(false)
  const [userRole, setUserRole] = useState('')

  const token = localStorage.getItem('medguardian_token')

  async function fetchDashboardData() {
    try {
      const userString = localStorage.getItem('medguardian_user')
      const userObj = userString ? JSON.parse(userString) : null
      const hospitalId = userObj?.hospital_id
      setUserRole(userObj?.role || '')

      if (!token || !hospitalId) {
        setError('Session or hospital identifier missing')
        setLoading(false)
        return
      }

      const headers = { 'Authorization': `Bearer ${token}` }

      // Fetch dashboard overview and actions
      const [overviewRes, actionsRes] = await Promise.all([
        fetch(`/api/dashboard/overview/${hospitalId}`, { headers }),
        fetch(`/api/dashboard/action-items/${hospitalId}`, { headers })
      ])

      if (overviewRes.status === 401 || actionsRes.status === 401) {
        localStorage.removeItem('medguardian_token')
        localStorage.removeItem('medguardian_user')
        window.location.reload()
        return
      }

      if (overviewRes.ok && actionsRes.ok) {
        const overviewData = await overviewRes.json()
        const actionsData = await actionsRes.json()

        setDashboard(overviewData)
        setActions(actionsData.actions || [])
        
        // Sync stage from backend if hospital info has onboarding_stage
        if (overviewData.hospital?.onboarding_stage) {
          setOnboardingStage(overviewData.hospital.onboarding_stage)
        }
      }
    } catch (err: any) {
      console.error('Dashboard synchronization error:', err)
      // If it's a new database partition, it might have empty values.
      // We will read onboardingStage from user object if backend fails
      const userString = localStorage.getItem('medguardian_user')
      const userObj = userString ? JSON.parse(userString) : null
      if (userObj?.role === 'super_admin') {
        setOnboardingStage('completed')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboardData()
  }, [])

  async function saveOnboardingStage(nextStage: string) {
    setSavingOnboard(true)
    try {
      const res = await fetch('/api/auth/hospitals/onboard', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          onboarding_stage: nextStage,
          bed_count: bedCount,
          hospital_type: hospitalType,
          has_emergency: hasEmergency,
          has_icu: hasIcu,
          has_operation_theatre: hasOt,
          fcra_number: hasFcra ? fcraNumber : null
        })
      })

      if (res.ok) {
        setOnboardingStage(nextStage)
        if (nextStage === 'completed') {
          // Hard reload to refresh layout sidebar visibility or dashboard charts
          window.location.reload()
        }
      } else {
        const data = await res.json()
        alert(data.detail || 'Failed to update onboarding progress.')
      }
    } catch (err) {
      console.error('Failed to post onboarding stepper metrics:', err)
    } finally {
      setSavingOnboard(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4 animate-pulse">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
        <p className="text-slate-500 text-sm font-medium">Synchronizing with MedGuardian Nerval Center...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-6 border-red-200 border-2 bg-red-50/50 flex flex-col items-center justify-center min-h-[200px] text-center">
        <AlertTriangle size={48} className="text-red-500 mb-3" />
        <h3 className="text-lg font-semibold text-slate-900">Synchronicity Failure</h3>
        <p className="text-sm text-red-700 mt-2 max-w-md">{error}</p>
        <button onClick={() => window.location.reload()} className="btn-primary mt-4 py-2 px-4 text-sm">
          Re-establish Connection
        </button>
      </div>
    )
  }

  // GUIDED ONBOARDING INTERACTIVE VIEW
  if (onboardingStage !== 'completed' && userRole === 'hospital_admin') {
    return (
      <div className="max-w-3xl mx-auto space-y-8 py-6">
        {/* Onboarding Stepper Indicator */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Configure Your Secure Node</h2>
              <p className="text-xs text-slate-500">Welcome to MedGuardian. Let's customize your compliance channels.</p>
            </div>
            <span className="text-xs font-bold text-brand-600 bg-brand-50 px-3 py-1 rounded-full uppercase tracking-wider">
              Setup Phase
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className={`flex-1 h-2 rounded-full transition-all duration-300 ${onboardingStage === 'profile' ? 'bg-brand-500' : 'bg-slate-200'}`} />
            <div className={`flex-1 h-2 rounded-full transition-all duration-300 ${onboardingStage === 'compliance' ? 'bg-brand-500' : 'bg-slate-200'}`} />
          </div>

          <div className="flex justify-between text-xs font-bold text-slate-400">
            <span className={onboardingStage === 'profile' ? 'text-brand-700 font-bold' : ''}>1. Hospital Profile</span>
            <span className={onboardingStage === 'compliance' ? 'text-brand-700 font-bold' : ''}>2. Compliance Setup</span>
          </div>
        </div>

        {/* STEP 1: Profile customization */}
        {onboardingStage === 'profile' && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6 animate-fade-in">
            <div className="space-y-1">
              <h3 className="font-extrabold text-slate-900 text-lg">Stage 1: Operational Scale & Capacity</h3>
              <p className="text-xs text-slate-500">Provide details to calibrate the risk monitoring filters.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">TOTAL SANCTIONED BED COUNT</label>
                <input
                  type="number"
                  value={bedCount}
                  onChange={e => setBedCount(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white outline-none"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">INSTITUTION TYPE</label>
                <select
                  value={hospitalType}
                  onChange={e => setHospitalType(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white outline-none"
                >
                  <option value="private">Private / Corporate Hospital</option>
                  <option value="trust">Charitable Trust Clinic</option>
                  <option value="government">Government Medical College</option>
                  <option value="mission">Missionary Clinic</option>
                </select>
              </div>
            </div>

            <div className="space-y-4 pt-2">
              <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wider">Active Clinical Departments</h4>
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <label className="flex items-center gap-3 p-3.5 border border-slate-100 rounded-xl hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasEmergency}
                    onChange={e => setHasEmergency(e.target.checked)}
                    className="w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500"
                  />
                  <div>
                    <span className="block text-xs font-bold text-slate-800">Emergency Unit</span>
                    <span className="block text-[10px] text-slate-400">Casualty and Trauma</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3.5 border border-slate-100 rounded-xl hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasIcu}
                    onChange={e => setHasIcu(e.target.checked)}
                    className="w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500"
                  />
                  <div>
                    <span className="block text-xs font-bold text-slate-800">ICU</span>
                    <span className="block text-[10px] text-slate-400">Intensive Care Facilities</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3.5 border border-slate-100 rounded-xl hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasOt}
                    onChange={e => setHasOt(e.target.checked)}
                    className="w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500"
                  />
                  <div>
                    <span className="block text-xs font-bold text-slate-800">Operation Theatre</span>
                    <span className="block text-[10px] text-slate-400">Major Surgical Rooms</span>
                  </div>
                </label>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-100">
              <button
                onClick={() => saveOnboardingStage('compliance')}
                disabled={savingOnboard}
                className="px-5 py-2.5 bg-slate-900 text-white rounded-lg text-xs font-bold shadow-md hover:bg-slate-800 transition-all flex items-center gap-1.5"
              >
                {savingOnboard ? 'Saving...' : 'Next Step'} <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: Compliance Setup */}
        {onboardingStage === 'compliance' && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6 animate-fade-in">
            <div className="space-y-1">
              <h3 className="font-extrabold text-slate-900 text-lg">Stage 2: Critical Compliance Setup</h3>
              <p className="text-xs text-slate-500">Upload key licenses and configure your foreign funding status.</p>
            </div>

            <div className="space-y-4">
              <label className="flex items-start gap-4 p-4 border border-slate-200 rounded-xl bg-slate-50/50 hover:bg-slate-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={hasFcra}
                  onChange={e => setHasFcra(e.target.checked)}
                  className="w-4 h-4 mt-0.5 text-brand-600 border-slate-300 rounded focus:ring-brand-500"
                />
                <div className="space-y-1.5 flex-1">
                  <span className="block text-xs font-bold text-slate-800">We receive foreign funds or grants</span>
                  <span className="block text-[11px] text-slate-500 leading-relaxed">
                    Checking this unlocks the <strong>FCRA Guardian</strong> module to monitor utilization certificates, track bank transactions, and draft audit-ready filings.
                  </span>
                </div>
              </label>

              {hasFcra && (
                <div className="p-4 border border-slate-100 rounded-xl space-y-3 animate-fade-in">
                  <label className="block text-[10px] font-bold text-slate-500 mb-1">FCRA REGISTRATION ID</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. FCRA/05284019"
                    value={fcraNumber}
                    onChange={e => setFcraNumber(e.target.value)}
                    className="w-full max-w-md px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white outline-none"
                  />
                  <p className="text-[10px] text-slate-400">
                    💡 You can upload your utilization certificate later in the FCRA tab.
                  </p>
                </div>
              )}
            </div>

            <div className="flex justify-between pt-4 border-t border-slate-100">
              <button
                onClick={() => setOnboardingStage('profile')}
                disabled={savingOnboard}
                className="px-5 py-2.5 border border-slate-200 hover:bg-slate-50 rounded-lg text-xs font-bold transition-all"
              >
                Back
              </button>
              <button
                onClick={() => saveOnboardingStage('completed')}
                disabled={savingOnboard}
                className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-bold shadow-md transition-all flex items-center gap-1.5"
              >
                {savingOnboard ? 'Configuring Node...' : 'Complete Setup & Unlock'} <CheckCircle size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  const weather = RISK_WEATHER[dashboard.risk_weather.level as keyof typeof RISK_WEATHER] || RISK_WEATHER.medium
  const WeatherIcon = weather.icon

  const getDomainIcon = (domain: string) => {
    const icons: Record<string, any> = {
      licenses: FileText, nabh: Award, fcra: Shield,
      dpdp_consent: FileCheck, bmw: Recycle, staffing: Users,
    }
    return icons[domain] || Shield
  }
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good': return 'text-green-600 bg-green-50'
      case 'warning': return 'text-yellow-600 bg-yellow-50'
      case 'critical': return 'text-red-600 bg-red-50'
      default: return 'text-slate-600 bg-slate-50'
    }
  }
  
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical': return 'badge-critical'
      case 'high': return 'badge-high'
      case 'medium': return 'badge-medium'
      case 'low': return 'badge-low'
      default: return 'badge bg-slate-100 text-slate-700'
    }
  }
  
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return <TrendingDown size={16} className="text-green-500" />
      case 'worsening': return <TrendingUp size={16} className="text-red-500" />
      default: return <Minus size={16} className="text-slate-400" />
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Risk Weather Hero */}
      <div className={`card p-6 ${weather.border} border-2`}>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className={`w-20 h-20 rounded-2xl ${weather.bg} flex items-center justify-center risk-weather-pulse`}>
              <WeatherIcon size={40} className={weather.color} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold text-slate-900">Risk Weather</h2>
                {getTrendIcon(dashboard.risk_weather.trend)}
              </div>
              <p className={`text-xl font-semibold ${weather.color} mt-1`}>
                {dashboard.risk_weather.forecast}
              </p>
              <p className="text-sm text-slate-500 mt-1">
                Overall Risk Score: <span className="font-semibold text-slate-700">{dashboard.risk_weather.overall_score}/100</span>
                <span className="text-slate-400 mx-2">•</span>
                Trend: <span className="font-medium capitalize">{dashboard.risk_weather.trend}</span>
              </p>
            </div>
          </div>
          
          {/* Quick Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{dashboard.alerts?.critical || 0}</div>
              <div className="text-xs text-slate-500">Critical Alerts</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{dashboard.quick_stats?.expiring_soon || 0}</div>
              <div className="text-xs text-slate-500">Licenses Expiring</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-brand-600">{dashboard.quick_stats?.nabh_readiness || '100%'}</div>
              <div className="text-xs text-slate-500">NABH Ready</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{dashboard.quick_stats?.bmw_compliance || '100%'}</div>
              <div className="text-xs text-slate-500">BMW Compliant</div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Domain Scores Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(dashboard.domain_scores || {}).map(([domain, data]: any) => {
          const Icon = getDomainIcon(domain)
          const label = domain.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
          
          return (
            <Link key={domain} to={`/${domain.split('_')[0]}`} className="card-hover p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg ${getStatusColor(data.status)} flex items-center justify-center`}>
                    <Icon size={20} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900">{label}</h3>
                    <p className="text-xs text-slate-500 capitalize">{data.status}</p>
                  </div>
                </div>
                <ChevronRight size={16} className="text-slate-400" />
              </div>
              
              {/* Score bar */}
              <div className="mt-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm text-slate-500">Compliance Score</span>
                  <span className="text-sm font-semibold text-slate-900">{data.score}%</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-500 ${
                      data.score >= 80 ? 'bg-green-500' :
                      data.score >= 60 ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${data.score}%` }}
                  />
                </div>
              </div>
            </Link>
          )
        })}
      </div>
      
      {/* Priority Actions */}
      <div className="card">
        <div className="px-6 py-4 border-b border-slate-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle size={20} className="text-orange-500" />
              <h3 className="text-lg font-semibold text-slate-900">Priority Actions</h3>
            </div>
            <span className="badge bg-slate-100 text-slate-700">{actions.length} items</span>
          </div>
          <p className="text-sm text-slate-500 mt-1">What needs your attention right now</p>
        </div>
        
        <div className="divide-y divide-slate-100">
          {actions.length === 0 ? (
            <div className="text-center py-12 text-slate-400 font-medium text-sm">
              No priority actions currently active.
            </div>
          ) : (
            actions.map((action) => (
              <div key={action.id} className="px-6 py-4 hover:bg-slate-50 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="mt-0.5">
                    <span className={getSeverityBadge(action.severity)}>
                      {action.severity}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-slate-900">{action.title}</h4>
                    <p className="text-sm text-slate-500 mt-1">{action.recommended_action}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <Clock size={12} />
                        Due: {action.due_date}
                      </span>
                      <span className="text-xs text-slate-400 capitalize">
                        {action.domain}
                      </span>
                    </div>
                  </div>
                  <button className="btn-secondary text-xs py-1.5 px-3">
                    <ArrowUpRight size={14} />
                    Act
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      
      {/* Recent Activity Timeline */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Recent Activity</h3>
        <div className="space-y-4">
          {[
            { time: '2 hours ago', event: 'BMW waste log verified for Ward 2', type: 'bmw', status: 'success' },
            { time: '5 hours ago', event: 'Patient consent renewed (ID: P-2847)', type: 'dpdp', status: 'success' },
            { time: '1 day ago', event: 'FCRA quarterly reconciliation completed', type: 'fcra', status: 'success' },
            { time: '2 days ago', event: 'NABH gap identified: PSG-3 Medication Reconciliation', type: 'nabh', status: 'warning' },
            { time: '3 days ago', event: 'Regulatory update: BMW Amendment 2026 ingested', type: 'regulatory', status: 'info' },
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className={`w-2 h-2 rounded-full mt-2 ${
                item.status === 'success' ? 'bg-green-500' :
                item.status === 'warning' ? 'bg-yellow-500' :
                'bg-blue-500'
              }`} />
              <div>
                <p className="text-sm text-slate-700">{item.event}</p>
                <p className="text-xs text-slate-400 mt-0.5">{item.time}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
