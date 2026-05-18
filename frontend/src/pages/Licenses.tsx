import { useState, useEffect } from 'react'
import { FileText, Plus, AlertTriangle, CheckCircle, Clock, RefreshCw, X, Copy, Check } from 'lucide-react'

export default function LicensesPage() {
  const [licenses, setLicenses] = useState<any[]>([])
  const [summary, setSummary] = useState<any>({
    expired: 0,
    critical: 0,
    high: 0,
    ok: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isDraftModalOpen, setIsDraftModalOpen] = useState(false)
  const [selectedDraft, setSelectedDraft] = useState<any>(null)
  const [copied, setCopied] = useState(false)

  // Add License Form State
  const [formName, setFormName] = useState('')
  const [formNumber, setFormNumber] = useState('')
  const [formAuthority, setFormAuthority] = useState('')
  const [formType, setFormType] = useState('clinical_establishment')
  const [formIssued, setFormIssued] = useState('')
  const [formExpiry, setFormExpiry] = useState('')
  const [formRemind, setFormRemind] = useState('90')
  const [submitting, setSubmitting] = useState(false)

  async function fetchLicensesData() {
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

      const res = await fetch(`/api/licenses/${hospitalId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!res.ok) {
        throw new Error('Failed to retrieve license/accreditation directories')
      }

      const data = await res.json()
      setLicenses(data.licenses || [])
      setSummary(data.summary || { expired: 0, critical: 0, high: 0, ok: 0 })
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Synchronization failure')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLicensesData()
  }, [])

  const handleAddSubmit = async (e: React.FormEvent) => {
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
        hospital_id: hospitalId,
        license_name: formName,
        license_number: formNumber,
        issuing_authority: formAuthority,
        license_type: formType,
        issued_date: formIssued,
        expiry_date: formExpiry || null,
        renewal_reminder_days: parseInt(formRemind)
      }

      const res = await fetch('/api/licenses/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to register license')
      }

      setIsAddModalOpen(false)
      // reset form
      setFormName('')
      setFormNumber('')
      setFormAuthority('')
      setFormIssued('')
      setFormExpiry('')
      setFormRemind('90')

      setLoading(true)
      await fetchLicensesData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleRenew = async (licenseId: string) => {
    try {
      const token = localStorage.getItem('medguardian_token')
      if (!token) return

      // File renewal
      const renewRes = await fetch(`/api/licenses/renewal/${licenseId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!renewRes.ok) throw new Error('Failed to file renewal trigger')

      // Get auto-draft letter
      const draftRes = await fetch(`/api/licenses/renewal-draft/${licenseId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!draftRes.ok) throw new Error('Failed to generate bureaucracy engine draft')

      const draftData = await draftRes.json()
      setSelectedDraft(draftData)
      setIsDraftModalOpen(true)

      // Refresh list
      await fetchLicensesData()
    } catch (err: any) {
      alert('Error triggering license renewal: ' + err.message)
    }
  }

  const handleCopyDraft = () => {
    if (!selectedDraft?.draft) return
    navigator.clipboard.writeText(selectedDraft.draft)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'expired': return 'bg-red-50/50 border-red-200 border-2'
      case 'critical':
      case 'high': return 'bg-orange-50/50 border-orange-200 border-2'
      default: return 'bg-white'
    }
  }

  const filtered = licenses.filter(l => {
    if (filter === 'all') return true
    if (filter === 'expired') return l.urgency === 'expired'
    if (filter === 'expiring') return l.urgency === 'critical' || l.urgency === 'high' || l.urgency === 'medium'
    return l.status === 'active'
  })

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4 animate-pulse">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
        <p className="text-slate-500 text-sm font-medium">Synchronizing License and NOC Ledgers...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <FileText size={28} className="text-brand-600" />
            License Tracker
          </h2>
          <p className="text-slate-500 mt-1">Every license, registration, and accreditation</p>
        </div>
        <button onClick={() => setIsAddModalOpen(true)} className="btn-primary">
          <Plus size={16} /> Add License
        </button>
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
          <div className="stat-value text-slate-900">{licenses.length}</div>
          <div className="stat-label">Total Licenses</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-green-600">{summary.ok}</div>
          <div className="stat-label">Active & Valid</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-orange-600">{summary.critical + summary.high}</div>
          <div className="stat-label">Expiring Soon</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-red-600">{summary.expired}</div>
          <div className="stat-label">Expired</div>
        </div>
      </div>
      
      {/* Critical Alert */}
      {summary.expired > 0 && (
        <div className="card border-red-200 bg-red-50 p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle size={24} className="text-red-600 mt-0.5" />
            <div>
              <h4 className="font-semibold text-red-900">Urgent: Expired License Detected</h4>
              <p className="text-sm text-red-700 mt-1">
                Your facility has expired regulatory compliance items. Operating under an expired license is a direct 
                violation of the Clinical Establishments Act and State pollution boards. Click "Renew" to instantly generate SPCB drafts.
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Filter */}
      <div className="flex gap-2">
        {['all', 'active', 'expiring', 'expired'].map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === f ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            {f === 'expiring' ? 'Expiring Soon' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      
      {/* License List */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-slate-400 card">
            No registrations found matching the selected filter.
          </div>
        ) : (
          filtered.map((lic) => {
            const hasExpired = lic.days_to_expiry !== null && lic.days_to_expiry < 0
            return (
              <div key={lic.id} className={`card-hover p-5 transition-all duration-300 ${getUrgencyColor(lic.urgency)}`}>
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <h4 className="font-semibold text-slate-900">{lic.name}</h4>
                      <span className={`badge ${
                        lic.status === 'active' ? 'bg-green-100 text-green-800' :
                        lic.status === 'renewal_in_progress' ? 'bg-blue-100 text-blue-800' :
                        lic.status === 'expiring_soon' ? 'bg-orange-100 text-orange-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {lic.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500">No: {lic.number} • Issued by: {lic.authority}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Issued: {lic.issued_date?.split('T')[0] || '-'} • Expires: {lic.expiry_date?.split('T')[0] || 'Perpetual'}
                    </p>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-center min-w-[80px]">
                      <div className={`text-2xl font-bold ${
                        hasExpired ? 'text-red-600' : (lic.days_to_expiry !== null && lic.days_to_expiry <= 90) ? 'text-orange-600' : 'text-green-600'
                      }`}>
                        {lic.days_to_expiry === null ? '∞' : hasExpired ? `${Math.abs(lic.days_to_expiry)}d ago` : `${lic.days_to_expiry}d`}
                      </div>
                      <div className="text-xs text-slate-500">{lic.days_to_expiry === null ? 'No Expiry' : hasExpired ? 'Expired' : 'Remaining'}</div>
                    </div>
                    
                    {lic.status !== 'renewal_in_progress' && (
                      <button 
                        onClick={() => handleRenew(lic.id)} 
                        className="btn-secondary text-sm border-brand-300 text-brand-700 hover:bg-brand-50"
                      >
                        <RefreshCw size={14} className="animate-spin-slow" /> Renew
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Add Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-md p-6 bg-white space-y-4 animate-scale-up relative">
            <button 
              onClick={() => setIsAddModalOpen(false)} 
              className="absolute right-4 top-4 p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <X size={20} />
            </button>
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <FileText className="text-brand-600" size={24} />
              <h3 className="text-lg font-bold text-slate-900">Add License / NOC</h3>
            </div>
            
            <form onSubmit={handleAddSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">License Name</label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. Fire Safety NOC"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="input-field"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">License Number</label>
                  <input 
                    type="text" 
                    required
                    placeholder="e.g. FS/KTM/2026"
                    value={formNumber}
                    onChange={(e) => setFormNumber(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">License Type</label>
                  <select 
                    value={formType} 
                    onChange={(e) => setFormType(e.target.value)}
                    className="input-field"
                  >
                    <option value="clinical_establishment">Clinical Establishment</option>
                    <option value="fire">Fire Safety</option>
                    <option value="pollution">Pollution Control</option>
                    <option value="pharmacy">Pharmacy</option>
                    <option value="blood_bank">Blood Bank</option>
                    <option value="bmw">BMW Authorization</option>
                    <option value="fcra">FCRA Registry</option>
                    <option value="nabh">NABH Accreditation</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Issuing Authority</label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. District Fire Officer"
                  value={formAuthority}
                  onChange={(e) => setFormAuthority(e.target.value)}
                  className="input-field"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Issued Date</label>
                  <input 
                    type="date" 
                    required
                    value={formIssued}
                    onChange={(e) => setFormIssued(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Expiry Date</label>
                  <input 
                    type="date" 
                    value={formExpiry}
                    onChange={(e) => setFormExpiry(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Renewal Reminder (days before)</label>
                <input 
                  type="number" 
                  value={formRemind}
                  onChange={(e) => setFormRemind(e.target.value)}
                  className="input-field"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button 
                  type="button" 
                  onClick={() => setIsAddModalOpen(false)} 
                  className="btn-secondary py-2 px-4"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={submitting} 
                  className="btn-primary py-2 px-4"
                >
                  {submitting ? 'Registering...' : 'Add License'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bureaucracy Engine Draft Modal */}
      {isDraftModalOpen && selectedDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-2xl p-6 bg-white space-y-4 animate-scale-up relative">
            <button 
              onClick={() => setIsDraftModalOpen(false)} 
              className="absolute right-4 top-4 p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <X size={20} />
            </button>
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <RefreshCw className="text-brand-600 animate-spin-slow" size={24} />
                <h3 className="text-lg font-bold text-slate-900">Renewal Bureaucracy Engine</h3>
              </div>
              <button 
                onClick={handleCopyDraft} 
                className="btn-secondary text-xs flex items-center gap-1.5 py-1.5 px-3"
              >
                {copied ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
                {copied ? 'Copied!' : 'Copy Letter'}
              </button>
            </div>
            
            <p className="text-xs text-slate-500">
              MedGuardian has automatically logged your renewal request in the database and pre-compiled the formal SPCB / municipal renewal filing draft letter below. Customize as needed.
            </p>

            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono text-slate-700 overflow-y-auto max-h-[300px] whitespace-pre-line">
              {selectedDraft.draft}
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-200">
              <button 
                onClick={() => setIsDraftModalOpen(false)} 
                className="btn-primary py-2 px-4"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
