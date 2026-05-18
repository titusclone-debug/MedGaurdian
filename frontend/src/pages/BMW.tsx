import { useState, useEffect } from 'react'
import { Recycle, Plus, Download, AlertTriangle, CheckCircle, X } from 'lucide-react'

const BMW_CATEGORIES = {
  yellow: { name: 'Yellow', desc: 'Human anatomical, soiled waste', color: 'bg-yellow-400', treatment: 'Incineration' },
  red: { name: 'Red', desc: 'Contaminated recyclable', color: 'bg-red-500', treatment: 'Autoclaving' },
  white: { name: 'White', desc: 'Sharps waste', color: 'bg-white border border-slate-300', treatment: 'Autoclaving/Shredding' },
  blue: { name: 'Blue', desc: 'Medicines, cytotoxic', color: 'bg-blue-500', treatment: 'Incineration' },
  black: { name: 'Black', desc: 'General municipal', color: 'bg-gray-800', treatment: 'Secured landfill' },
}

export default function BMWPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [summary, setSummary] = useState<any>({
    total_entries: 0,
    total_weight_kg: 0,
    overall_compliance_rate: 100,
    compliance_status: 'audit_ready'
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [formCategory, setFormCategory] = useState('yellow')
  const [formWeight, setFormWeight] = useState('')
  const [formDept, setFormDept] = useState('Surgery')
  const [formWard, setFormWard] = useState('')
  const [formTreatment, setFormTreatment] = useState('Incineration')

  async function fetchBMWData() {
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

      const res = await fetch(`/api/bmw/dashboard/${hospitalId}?days=30`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!res.ok) {
        throw new Error('Failed to retrieve SPCB bio-medical waste metrics')
      }

      const data = await res.json()
      setLogs(data.logs || [])
      setSummary({
        total_entries: data.summary?.total_entries || 0,
        total_weight_kg: data.summary?.total_weight_kg || 0,
        overall_compliance_rate: data.summary?.overall_compliance_rate || 100,
        compliance_status: data.compliance_status || 'audit_ready'
      })
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Synchronization failure')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBMWData()
  }, [])

  const handleDownloadReport = async () => {
    try {
      const token = localStorage.getItem('medguardian_token')
      const userString = localStorage.getItem('medguardian_user')
      const userObj = userString ? JSON.parse(userString) : null
      const hospitalId = userObj?.hospital_id

      if (!token || !hospitalId) return

      const month = new Date().getMonth() + 1
      const year = new Date().getFullYear()

      const res = await fetch(`/api/bmw/audit-report/${hospitalId}?month=${month}&year=${year}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!res.ok) throw new Error('Report generation failed')

      const data = await res.json()
      // Generate virtual JSON download to browser
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `medguardian_spcb_report_${month}_${year}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err: any) {
      alert('Error generating audit report: ' + err.message)
    }
  }

  const handleLogSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      const token = localStorage.getItem('medguardian_token')
      const userString = localStorage.getItem('medguardian_user')
      const userObj = userString ? JSON.parse(userString) : null
      const hospitalId = userObj?.hospital_id

      if (!token || !hospitalId) throw new Error('Authentication parameters expired')

      const payload = {
        hospital_id: hospitalId,
        category: formCategory,
        weight_kg: parseFloat(formWeight),
        source_department: formDept,
        source_ward: formWard || null,
        treatment_method: formTreatment
      }

      const res = await fetch('/api/bmw/log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to submit bio-waste entry')
      }

      setIsModalOpen(false)
      setFormWeight('')
      setFormWard('')
      // Refresh Dashboard metrics
      setLoading(true)
      await fetchBMWData()
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
        <p className="text-slate-500 text-sm font-medium">Synchronizing SPCB Bio-Medical Ledgers...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Recycle size={28} className="text-brand-600" />
            BMW Sentinel
          </h2>
          <p className="text-slate-500 mt-1">Bio-Medical Waste tracking and audit readiness</p>
        </div>
        <div className="flex gap-3">
          <button onClick={handleDownloadReport} className="btn-secondary">
            <Download size={16} /> Audit Report
          </button>
          <button onClick={() => setIsModalOpen(true)} className="btn-primary">
            <Plus size={16} /> Log Waste Entry
          </button>
        </div>
      </div>
      
      {error && (
        <div className="p-4 border-2 border-red-200 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-3">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="stat-value text-slate-900">{summary.total_weight_kg.toFixed(1)} kg</div>
          <div className="stat-label">Total Waste (30 days)</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-slate-900">{summary.total_entries}</div>
          <div className="stat-label">Total Entries</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-green-600">{summary.overall_compliance_rate.toFixed(0)}%</div>
          <div className="stat-label">Compliance Rate</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-brand-600">5</div>
          <div className="stat-label">Categories Tracked</div>
        </div>
      </div>
      
      {/* Category Legend */}
      <div className="card p-5">
        <h3 className="font-semibold text-slate-900 mb-3">BMW Categories (as per Rules, 2016)</h3>
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {Object.entries(BMW_CATEGORIES).map(([key, cat]) => (
            <div key={key} className="flex items-center gap-3 p-3 rounded-lg bg-slate-50">
              <div className={`w-8 h-8 rounded-lg ${cat.color}`} />
              <div>
                <div className="text-sm font-semibold text-slate-900">{cat.name}</div>
                <div className="text-xs text-slate-500">{cat.treatment}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Waste Log Table */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-900">Waste Log (Recent Entries)</h3>
        </div>
        <div className="overflow-x-auto">
          {logs.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              No waste entries logged for this period. Click 'Log Waste Entry' above.
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-header">Date</th>
                  <th className="table-header">Category</th>
                  <th className="table-header">Weight</th>
                  <th className="table-header">Department</th>
                  <th className="table-header">Ward</th>
                  <th className="table-header">Treatment</th>
                  <th className="table-header">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="table-cell">{log.date}</td>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <div className={`w-4 h-4 rounded ${BMW_CATEGORIES[log.category as keyof typeof BMW_CATEGORIES]?.color}`} />
                        <span className="capitalize font-medium">{log.category}</span>
                      </div>
                    </td>
                    <td className="table-cell font-semibold">{log.weight} kg</td>
                    <td className="table-cell">{log.dept}</td>
                    <td className="table-cell text-slate-500">{log.ward}</td>
                    <td className="table-cell text-slate-500">{log.treatment}</td>
                    <td className="table-cell">
                      {log.compliant ? (
                        <span className="badge bg-green-100 text-green-800">Compliant</span>
                      ) : (
                        <span className="badge bg-red-100 text-red-800">Review Required</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      
      {/* Audit Readiness badge */}
      {summary.overall_compliance_rate >= 95 ? (
        <div className="card border-green-200 bg-green-50 p-5">
          <div className="flex items-center gap-3">
            <CheckCircle size={24} className="text-green-600" />
            <div>
              <h4 className="font-semibold text-green-900">Audit Status: Ready</h4>
              <p className="text-sm text-green-700">SPCB compliance threshold reached ({summary.overall_compliance_rate.toFixed(0)}%). Institutional waste matrices are chain-hashed and fully auditable.</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="card border-yellow-200 bg-yellow-50 p-5">
          <div className="flex items-center gap-3">
            <AlertTriangle size={24} className="text-yellow-600" />
            <div>
              <h4 className="font-semibold text-yellow-900">Audit Status: Needs Attention</h4>
              <p className="text-sm text-yellow-700">Compliance is currently below standard ({summary.overall_compliance_rate.toFixed(0)}%). Perform spot-checks on yellow anatomical disposal chains.</p>
            </div>
          </div>
        </div>
      )}

      {/* Log Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-md p-6 bg-white space-y-4 animate-scale-up relative">
            <button 
              onClick={() => setIsModalOpen(false)} 
              className="absolute right-4 top-4 p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <X size={20} />
            </button>
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <Recycle className="text-brand-600" size={24} />
              <h3 className="text-lg font-bold text-slate-900">Log Waste Disposal</h3>
            </div>
            
            <form onSubmit={handleLogSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Category Color</label>
                <select 
                  value={formCategory} 
                  onChange={(e) => {
                    setFormCategory(e.target.value)
                    setFormTreatment(BMW_CATEGORIES[e.target.value as keyof typeof BMW_CATEGORIES]?.treatment || 'Incineration')
                  }}
                  className="input-field"
                >
                  <option value="yellow">Yellow (Anatomical/Soiled)</option>
                  <option value="red">Red (Recyclable Plastic)</option>
                  <option value="white">White (Sharps/Needles)</option>
                  <option value="blue">Blue (Medicines/Cytotoxic)</option>
                  <option value="black">Black (General Municipal)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Weight (in kg)</label>
                <input 
                  type="number" 
                  step="0.01"
                  required
                  placeholder="e.g. 12.45"
                  value={formWeight}
                  onChange={(e) => setFormWeight(e.target.value)}
                  className="input-field"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Source Department</label>
                  <select 
                    value={formDept} 
                    onChange={(e) => setFormDept(e.target.value)}
                    className="input-field"
                  >
                    <option value="Surgery">Surgery</option>
                    <option value="ICU">ICU</option>
                    <option value="Emergency">Emergency</option>
                    <option value="Laboratory">Laboratory</option>
                    <option value="Pharmacy">Pharmacy</option>
                    <option value="Maternity">Maternity</option>
                    <option value="Outpatient">Outpatient</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Ward / Room</label>
                  <input 
                    type="text" 
                    placeholder="e.g. Ward 3B"
                    value={formWard}
                    onChange={(e) => setFormWard(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Treatment Method</label>
                <input 
                  type="text" 
                  readOnly
                  disabled
                  value={formTreatment}
                  className="input-field bg-slate-50 text-slate-500 cursor-not-allowed"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button 
                  type="button" 
                  onClick={() => setIsModalOpen(false)} 
                  className="btn-secondary py-2 px-4"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={submitting} 
                  className="btn-primary py-2 px-4"
                >
                  {submitting ? 'Logging...' : 'Save Entry'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
