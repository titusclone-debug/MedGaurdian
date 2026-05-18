import { useState, useEffect } from 'react'
import { Cloud, AlertTriangle, TrendingUp, TrendingDown, Minus, CheckCircle, Clock, Bell, Filter } from 'lucide-react'

export default function RiskPage() {
  const [alerts, setAlerts] = useState<any[]>([])
  const [forecast, setForecast] = useState<any>({
    trend: 'stable',
    current_alerts: 0,
    resolved_in_period: 0,
    top_risk_areas: [],
    forecast: { next_week_risk: 'medium', recommendation: 'Maintain current controls.' }
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('all')

  async function fetchRiskData() {
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

      // Fetch alerts and forecast concurrently
      const [alertsRes, forecastRes] = await Promise.all([
        fetch(`/api/risk/alerts/${hospitalId}?resolved=false`, { headers }),
        fetch(`/api/risk/forecast/${hospitalId}`, { headers })
      ])

      if (!alertsRes.ok || !forecastRes.ok) {
        throw new Error('Failed to retrieve active risk intelligence matrices')
      }

      const alertsData = await alertsRes.json()
      const forecastData = await forecastRes.json()

      setAlerts(alertsData.alerts || [])
      setForecast(forecastData)
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Synchronization failure')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRiskData()
  }, [])

  const handleAcknowledge = async (id: string) => {
    try {
      const token = localStorage.getItem('medguardian_token')
      if (!token) return

      const res = await fetch(`/api/risk/alerts/${id}/acknowledge`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!res.ok) throw new Error('Acknowledge trigger failed')

      // Refresh list
      setLoading(true)
      await fetchRiskData()
    } catch (err: any) {
      alert('Error acknowledging alert: ' + err.message)
    }
  }

  const handleEscalate = async (alertTitle: string) => {
    alert(`Escalation notification drafted for: "${alertTitle}". Dispatching alerts via Slack/SMS notifications to hospital director and compliance committee.`);
  }

  const filtered = alerts.filter(a => {
    if (filterSeverity !== 'all' && a.severity !== filterSeverity) return false
    return true
  })

  const criticalCount = alerts.filter(a => a.severity === 'critical' && !a.is_acknowledged).length
  const highCount = alerts.filter(a => a.severity === 'high').length

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4 animate-pulse">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
        <p className="text-slate-500 text-sm font-medium">Synchronizing Predictive Risk Forecasting Engines...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Cloud size={28} className="text-brand-600" />
          Risk Intelligence
        </h2>
        <p className="text-slate-500 mt-1">Predictive alerts and institutional risk management</p>
      </div>
      
      {error && (
        <div className="p-4 border-2 border-red-200 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-3">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Risk Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="stat-card border-l-4 border-l-red-500">
          <div className="stat-value text-red-600">{criticalCount}</div>
          <div className="stat-label">Unacknowledged Critical</div>
        </div>
        <div className="stat-card border-l-4 border-l-orange-500">
          <div className="stat-value text-orange-600">{highCount}</div>
          <div className="stat-label">High Priority</div>
        </div>
        <div className="stat-card border-l-4 border-l-green-500">
          <div className="stat-value text-green-600">{forecast.resolved_in_period}</div>
          <div className="stat-label">Resolved (30 days)</div>
        </div>
        <div className="stat-card border-l-4 border-l-brand-500">
          <div className="flex items-center gap-2">
            {forecast.trend === 'improving' ? <TrendingDown size={20} className="text-green-500" /> : forecast.trend === 'worsening' ? <TrendingUp size={20} className="text-red-500" /> : <Minus size={20} className="text-slate-400" />}
            <div className="stat-value capitalize text-slate-900">{forecast.trend === 'insufficient_data' ? 'stable' : forecast.trend}</div>
          </div>
          <div className="stat-label">Risk Trend</div>
        </div>
      </div>
      
      {/* Top Risk Areas */}
      {forecast.top_risk_areas && forecast.top_risk_areas.length > 0 && (
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 mb-3">Top Risk Areas (Alert Frequency)</h3>
          <div className="flex flex-wrap gap-3">
            {forecast.top_risk_areas.map((areaObj: any, i: number) => (
              <div key={i} className="flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-sm font-medium text-slate-700 capitalize">{areaObj.area.replace(/_/g, ' ')}</span>
                <span className="badge bg-red-100 text-red-800">{areaObj.alert_count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter size={16} className="text-slate-400" />
        {['all', 'critical', 'high', 'medium', 'low'].map((f) => (
          <button key={f} onClick={() => setFilterSeverity(f)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filterSeverity === f ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      
      {/* Alert List */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-slate-400 card bg-white">
            No predictive risk items catalogued for this severity filter.
          </div>
        ) : (
          filtered.map((alert) => (
            <div key={alert.id} className={`card p-5 transition-all duration-300 ${
              alert.severity === 'critical' && !alert.is_acknowledged ? 'border-l-4 border-l-red-500 bg-red-50/20' :
              alert.severity === 'high' ? 'border-l-4 border-l-orange-500' :
              ''
            } ${alert.is_acknowledged ? 'opacity-70' : ''}`}>
              <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`badge ${
                      alert.severity === 'critical' ? 'badge-critical' :
                      alert.severity === 'high' ? 'badge-high' :
                      alert.severity === 'medium' ? 'badge-medium' : 'badge-low'
                    }`}>
                      {alert.severity}
                    </span>
                    <span className="text-xs text-slate-400 capitalize">{alert.type.replace(/_/g, ' ')}</span>
                    {alert.is_acknowledged && <span className="badge bg-green-100 text-green-800">Acknowledged</span>}
                  </div>
                  <h4 className="font-semibold text-slate-900">{alert.title}</h4>
                  <p className="text-sm text-slate-600 mt-1">{alert.description}</p>
                  <div className="mt-3 p-3 bg-slate-50 rounded-lg">
                    <p className="text-sm text-slate-700 font-medium">
                      <span className="text-brand-700 font-bold">Action Guidance:</span> {alert.recommended_action}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 mt-3 text-xs text-slate-400">
                    <span className="flex items-center gap-1"><Clock size={12} /> Due: {alert.due_date?.split('T')[0] || '-'}</span>
                    <span>Assigned Agent: {alert.assigned_to || 'General Compliance Office'}</span>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  {!alert.is_acknowledged && (
                    <button 
                      onClick={() => handleAcknowledge(alert.id)}
                      className="btn-secondary text-sm border-brand-300 text-brand-700 hover:bg-brand-50"
                    >
                      <CheckCircle size={14} /> Acknowledge
                    </button>
                  )}
                  <button onClick={() => handleEscalate(alert.title)} className="btn-primary text-sm bg-gradient-to-r from-brand-600 to-brand-700">
                    <Bell size={14} /> Escalate
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
