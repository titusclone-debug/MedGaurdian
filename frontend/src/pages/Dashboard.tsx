import { useState, useEffect } from 'react'
import { 
  CloudLightning, CloudRain, CloudSun, Sun, Cloud,
  Shield, FileCheck, Recycle, Award, FileText, Users,
  AlertTriangle, TrendingUp, TrendingDown, Minus,
  ChevronRight, Clock, ArrowUpRight
} from 'lucide-react'
import { Link } from 'react-router-dom'

const RISK_WEATHER = {
  critical: { icon: CloudLightning, label: 'Storm Warning', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
  high: { icon: CloudRain, label: 'Heavy Clouds', color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
  medium: { icon: CloudSun, label: 'Partly Cloudy', color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200' },
  low: { icon: Cloud, label: 'Mostly Clear', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  minimal: { icon: Sun, label: 'Clear Skies', color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' },
}

// Mock data — replace with API calls
const MOCK_DASHBOARD = {
  risk_weather: { overall_score: 35.2, level: 'medium', forecast: '⛅ Partly Cloudy', trend: 'improving' },
  domain_scores: {
    licenses: { score: 72, status: 'warning' },
    nabh: { score: 65, status: 'warning' },
    fcra: { score: 90, status: 'good' },
    dpdp_consent: { score: 85, status: 'good' },
    bmw: { score: 95, status: 'good' },
    staffing: { score: 85, status: 'good' },
  },
  quick_stats: {
    total_licenses: 24, expiring_soon: 3, expired_licenses: 0,
    nabh_readiness: '65%', bmw_compliance: '95%',
    active_consents: 1247, expired_consents: 12,
    fcra_accounts: 2, active_alerts: 8, critical_alerts: 1,
  },
  alerts: { total_active: 8, critical: 1 },
}

const MOCK_ACTIONS = [
  { type: 'alert', id: '1', title: 'Fire Safety NOC expires in 5 days', severity: 'critical', domain: 'license', due_date: '2026-05-22', recommended_action: 'File renewal application immediately' },
  { type: 'alert', id: '2', title: 'NABH gap: Patient Safety Goals (PSG-3)', severity: 'high', domain: 'nabh', due_date: '2026-06-01', recommended_action: 'Complete medication reconciliation documentation' },
  { type: 'alert', id: '3', title: '12 patient consents expiring this month', severity: 'medium', domain: 'dpdp', due_date: '2026-05-31', recommended_action: 'Initiate consent renewal outreach' },
  { type: 'alert', id: '4', title: 'BMW: Ward 3 waste segregation review needed', severity: 'medium', domain: 'bmw', due_date: '2026-05-25', recommended_action: 'Schedule spot check for Ward 3' },
  { type: 'alert', id: '5', title: 'FCRA quarterly utilization report due', severity: 'high', domain: 'fcra', due_date: '2026-05-30', recommended_action: 'Prepare and submit Q4 utilization certificate' },
]

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(MOCK_DASHBOARD)
  const [actions, setActions] = useState(MOCK_ACTIONS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function fetchDashboardData() {
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

        // Fetch overview and actions concurrently
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

        if (!overviewRes.ok || !actionsRes.ok) {
          throw new Error('Failed to retrieve live administrative intelligence')
        }

        const overviewData = await overviewRes.json()
        const actionsData = await actionsRes.json()

        setDashboard(overviewData)
        setActions(actionsData.actions || [])
      } catch (err: any) {
        console.error('Dashboard synchronization error:', err)
        setError(err.message || 'Synchronization failure')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])
  
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
        <button 
          onClick={() => window.location.reload()} 
          className="btn-primary mt-4 py-2 px-4 text-sm"
        >
          Re-establish Connection
        </button>
      </div>
    )
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
              <div className="text-2xl font-bold text-red-600">{dashboard.alerts.critical}</div>
              <div className="text-xs text-slate-500">Critical Alerts</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{dashboard.quick_stats.expiring_soon}</div>
              <div className="text-xs text-slate-500">Licenses Expiring</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-brand-600">{dashboard.quick_stats.nabh_readiness}</div>
              <div className="text-xs text-slate-500">NABH Ready</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{dashboard.quick_stats.bmw_compliance}</div>
              <div className="text-xs text-slate-500">BMW Compliant</div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Domain Scores Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(dashboard.domain_scores).map(([domain, data]) => {
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
          {actions.map((action) => (
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
          ))}
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
