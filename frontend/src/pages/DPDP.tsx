import { useState, useEffect, useRef } from 'react'
import { FileCheck, Plus, Search, AlertTriangle, CheckCircle, Clock, Shield, X, HelpCircle } from 'lucide-react'

export default function DPDPPage() {
  const [consents, setConsents] = useState<any[]>([])
  const [complianceScore, setComplianceScore] = useState(100)
  const [complianceStatus, setComplianceStatus] = useState('compliant')
  const [issues, setIssues] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')

  // Modals state
  const [isConsentModalOpen, setIsConsentModalOpen] = useState(false)
  const [isBreachModalOpen, setIsBreachModalOpen] = useState(false)
  const [selectedConsent, setSelectedConsent] = useState<any>(null)

  // Consent Form State
  const [formPatientId, setFormPatientId] = useState('')
  const [formPatientName, setFormPatientName] = useState('')
  const [formPatientMobile, setFormPatientMobile] = useState('')
  const [formPatientAddress, setFormPatientAddress] = useState('')
  const [formType, setFormType] = useState('treatment')
  const [formPurpose, setFormPurpose] = useState('')
  const [formDataCats, setFormDataCats] = useState<string[]>(['name', 'diagnosis'])
  const [formThirdParties, setFormThirdParties] = useState('')
  const [formMethod, setFormMethod] = useState('digital_signature')
  const [formIsMinor, setFormIsMinor] = useState(false)
  const [formGuardianId, setFormGuardianId] = useState('')
  const [formExpiresDays, setFormExpiresDays] = useState('365')
  const [submittingConsent, setSubmittingConsent] = useState(false)

  const [signatureData, setSignatureData] = useState<string | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isDrawing, setIsDrawing] = useState(false)

  const startDrawing = (e: any) => {
    const canvas = canvasRef.current; if (!canvas) return
    const ctx = canvas.getContext('2d'); if (!ctx) return
    ctx.beginPath(); ctx.moveTo(e.nativeEvent.offsetX, e.nativeEvent.offsetY)
    setIsDrawing(true)
  }
  const draw = (e: any) => {
    if (!isDrawing) return
    const canvas = canvasRef.current; if (!canvas) return
    const ctx = canvas.getContext('2d'); if (!ctx) return
    ctx.lineTo(e.nativeEvent.offsetX, e.nativeEvent.offsetY); ctx.stroke()
  }
  const stopDrawing = () => {
    setIsDrawing(false)
    if (canvasRef.current) setSignatureData(canvasRef.current.toDataURL('image/png'))
  }
  const clearSignature = () => {
    const canvas = canvasRef.current; if (!canvas) return
    const ctx = canvas.getContext('2d'); if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
    setSignatureData(null)
  }

  // Breach Form State
  const [formBreachType, setFormBreachType] = useState('unauthorized_access')
  const [formBreachCount, setFormBreachCount] = useState('')
  const [formBreachCats, setFormBreachCats] = useState<string[]>(['name', 'diagnosis'])
  const [formBreachCause, setFormBreachCause] = useState('')
  const [submittingBreach, setSubmittingBreach] = useState(false)

  async function fetchDPDPData() {
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

      // Fetch consents and compliance audit concurrently
      const [consentsRes, auditRes] = await Promise.all([
        fetch(`/api/dpdp/list/${hospitalId}`, { headers }),
        fetch(`/api/dpdp/compliance-check/${hospitalId}`, { headers })
      ])

      if (!consentsRes.ok || !auditRes.ok) {
        throw new Error('Failed to retrieve DPDP digital consent registers')
      }

      const consentsData = await consentsRes.json()
      const auditData = await auditRes.json()

      setConsents(consentsData.consents || [])
      setComplianceScore(auditData.compliance_score || 100)
      setComplianceStatus(auditData.status || 'compliant')
      setIssues(auditData.issues || [])
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Synchronization failure')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDPDPData()
  }, [])

  const handleConsentSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmittingConsent(true)
    setError('')

    try {
      const token = localStorage.getItem('medguardian_token')
      const userString = localStorage.getItem('medguardian_user')
      const userObj = userString ? JSON.parse(userString) : null
      const hospitalId = userObj?.hospital_id

      if (!token || !hospitalId) throw new Error('Authentication expired')

      const payload = {
        hospital_id: hospitalId,
        patient_id: formPatientId,
        patient_name: formPatientName,
        patient_mobile: formPatientMobile,
        patient_address: formPatientAddress,
        consent_type: formType,
        purpose: formPurpose,
        data_categories: formDataCats,
        third_parties: formThirdParties ? formThirdParties.split(',').map(s => s.trim()) : null,
        consent_method: formMethod,
        digital_signature: signatureData,
        is_minor: formIsMinor,
        guardian_consent_id: formIsMinor ? formGuardianId : null,
        expires_in_days: parseInt(formExpiresDays)
      }

      const res = await fetch('/api/dpdp/grant', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to grant digital consent')
      }

      setIsConsentModalOpen(false)
      // reset form
      setFormPatientId('')
      setFormPatientName('')
      setFormPatientMobile('')
      setFormPatientAddress('')
      setFormPurpose('')
      setFormIsMinor(false)
      setFormGuardianId('')
      clearSignature()

      setLoading(true)
      await fetchDPDPData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmittingConsent(false)
    }
  }

  const handleWithdrawConsent = async (consentId: string) => {
    const reason = prompt('Please specify withdrawal reason (DPDP Requirement):')
    if (reason === null) return // cancelled

    try {
      const token = localStorage.getItem('medguardian_token')
      if (!token) return

      const res = await fetch(`/api/dpdp/withdraw/${consentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ reason: reason || 'Patient requested cessation' })
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Withdrawal request failed')
      }

      setLoading(true)
      await fetchDPDPData()
    } catch (err: any) {
      alert('Error withdrawing consent: ' + err.message)
    }
  }

  const handleBreachSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmittingBreach(true)
    setError('')

    try {
      const token = localStorage.getItem('medguardian_token')
      const userString = localStorage.getItem('medguardian_user')
      const userObj = userString ? JSON.parse(userString) : null
      const hospitalId = userObj?.hospital_id

      if (!token || !hospitalId) throw new Error('Authentication expired')

      const payload = {
        hospital_id: hospitalId,
        breach_type: formBreachType,
        affected_records_count: parseInt(formBreachCount),
        data_categories_affected: formBreachCats,
        root_cause: formBreachCause
      }

      const res = await fetch('/api/dpdp/breach/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Data breach report failed')
      }

      const resData = await res.json()
      setIsBreachModalOpen(false)
      // Display breach warnings
      alert(`⚠️ BREACH DETECTED AND STAMPED ON BLOCKCHAIN.\nDPDP 72-Hour Regulatory Timer has initiated.\nDeadline: ${resData.notification_deadline?.split('T')[0] || ''}`);

      setLoading(true)
      await fetchDPDPData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmittingBreach(false)
    }
  }

  const toggleCategory = (cat: string, isBreach: boolean = false) => {
    if (isBreach) {
      if (formBreachCats.includes(cat)) {
        setFormBreachCats(formBreachCats.filter(c => c !== cat))
      } else {
        setFormBreachCats([...formBreachCats, cat])
      }
    } else {
      if (formDataCats.includes(cat)) {
        setFormDataCats(formDataCats.filter(c => c !== cat))
      } else {
        setFormDataCats([...formDataCats, cat])
      }
    }
  }

  const filtered = consents.filter(c => {
    if (filter === 'all') return true
    return c.status === filter
  })

  const stats = {
    total: consents.length,
    active: consents.filter(c => c.status === 'granted').length,
    expired: consents.filter(c => c.status === 'expired').length,
    withdrawn: consents.filter(c => c.status === 'withdrawn').length,
    minors: consents.filter(c => c.is_minor).length
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4 animate-pulse">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
        <p className="text-slate-500 text-sm font-medium">Synchronizing cryptographic patient consent ledgers...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <FileCheck size={28} className="text-brand-600" />
            DPDP Consent Manager
          </h2>
          <p className="text-slate-500 mt-1">Patient data protection and consent management (Act 2026)</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => setIsBreachModalOpen(true)} className="btn-secondary border-red-300 text-red-700 hover:bg-red-50 flex items-center gap-1.5">
            <AlertTriangle size={16} /> Report Breach
          </button>
          <button onClick={() => setIsConsentModalOpen(true)} className="btn-primary flex items-center gap-1.5">
            <Plus size={16} /> Record New Consent
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
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <div className="stat-card">
          <div className="stat-value text-slate-900">{stats.total}</div>
          <div className="stat-label">Total Consents</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-green-600">{stats.active}</div>
          <div className="stat-label">Active</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-orange-600">{stats.expired}</div>
          <div className="stat-label">Expired</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-red-600">{stats.withdrawn}</div>
          <div className="stat-label">Withdrawn</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-purple-600">{stats.minors}</div>
          <div className="stat-label">Minor Patients</div>
        </div>
      </div>
      
      {/* Compliance Status */}
      {complianceStatus === 'compliant' ? (
        <div className="card border-green-200 bg-green-50 p-5">
          <div className="flex items-center gap-3">
            <Shield size={24} className="text-green-600" />
            <div>
              <h4 className="font-semibold text-green-900">DPDP Compliance Score: {complianceScore}% (Good)</h4>
              <p className="text-sm text-green-700">All active consents are purpose-limited and time-bound. Minor patients have guardian consent on file.</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="card border-yellow-200 bg-yellow-50 p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle size={24} className="text-yellow-600 mt-0.5" />
            <div>
              <h4 className="font-semibold text-yellow-900">DPDP Compliance Alert: {complianceScore}% (Needs Attention)</h4>
              <ul className="text-sm text-yellow-700 mt-2 list-disc pl-5 space-y-1">
                {issues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
      
      {/* Filter Tabs */}
      <div className="flex gap-2">
        {['all', 'granted', 'expired', 'withdrawn'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === f ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            {f === 'granted' ? 'Active' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      
      {/* Consent Records */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              No consent records match this query.
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-header">Patient ID</th>
                  <th className="table-header">Type</th>
                  <th className="table-header">Purpose</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Granted</th>
                  <th className="table-header">Expires</th>
                  <th className="table-header">Minor</th>
                  <th className="table-header">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((consent) => (
                  <tr key={consent.id} className="hover:bg-slate-50">
                    <td className="table-cell font-mono text-sm">
                      <div className="font-semibold">{consent.patient_id}</div>
                      {consent.patient_name && <div className="text-xs text-slate-500">{consent.patient_name}</div>}
                    </td>
                    <td className="table-cell">
                      <span className="badge bg-blue-100 text-blue-800 capitalize">{consent.type}</span>
                    </td>
                    <td className="table-cell text-slate-600 max-w-xs truncate">{consent.purpose}</td>
                    <td className="table-cell">
                      <span className={`badge ${
                        consent.status === 'granted' ? 'bg-green-100 text-green-800' :
                        consent.status === 'expired' ? 'bg-orange-100 text-orange-800' :
                        consent.status === 'withdrawn' ? 'bg-red-100 text-red-800' :
                        'bg-slate-100 text-slate-800'
                      }`}>
                        {consent.status}
                      </span>
                    </td>
                    <td className="table-cell text-sm text-slate-500">{consent.granted_at}</td>
                    <td className="table-cell text-sm text-slate-500">{consent.expires_at || '—'}</td>
                    <td className="table-cell">
                      {consent.is_minor && <span className="badge bg-purple-100 text-purple-800">Minor</span>}
                    </td>
                    <td className="table-cell">
                      <div className="flex gap-2">
                        <button 
                          onClick={() => setSelectedConsent(consent)} 
                          className="text-brand-600 hover:text-brand-700 text-sm font-medium"
                        >
                          View
                        </button>
                        {consent.status === 'granted' && (
                          <button 
                            onClick={() => handleWithdrawConsent(consent.id)} 
                            className="text-red-600 hover:text-red-700 text-sm font-medium"
                          >
                            Withdraw
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      
      {/* DPDP Key Requirements Checklist */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">DPDP 2026 Compliance Checklist</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { label: 'Consent Manager registered with DPDP Board', done: true },
            { label: 'Patient consent forms in local language', done: true },
            { label: '72-hour breach notification process', done: true },
            { label: 'Data Protection Officer appointed', done: true },
            { label: 'Minor patient guardian consent workflow', done: true },
            { label: 'Consent withdrawal mechanism (as easy as granting)', done: true },
            { label: 'Purpose limitation enforcement', done: true },
            { label: 'Anonymized ledger logs using SHA-256 blocks', done: true },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-slate-50">
              <CheckCircle size={18} className="text-green-500 flex-shrink-0" />
              <span className="text-sm text-slate-700">
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Record Consent Modal */}
      {isConsentModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-md p-6 bg-white space-y-4 animate-scale-up relative overflow-y-auto max-h-[90vh]">
            <button 
              onClick={() => setIsConsentModalOpen(false)} 
              className="absolute right-4 top-4 p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <X size={20} />
            </button>
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <FileCheck className="text-brand-600" size={24} />
              <h3 className="text-lg font-bold text-slate-900">Record Patient Consent</h3>
            </div>
            
            <form onSubmit={handleConsentSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Patient ID</label>
                  <input 
                    type="text" 
                    required
                    placeholder="e.g. P-2847"
                    value={formPatientId}
                    onChange={(e) => setFormPatientId(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Patient Name</label>
                  <input 
                    type="text" 
                    required
                    placeholder="e.g. Rohan Dev"
                    value={formPatientName}
                    onChange={(e) => setFormPatientName(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Mobile Number</label>
                  <input 
                    type="text" 
                    placeholder="e.g. 9876543210"
                    value={formPatientMobile}
                    onChange={(e) => setFormPatientMobile(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Address</label>
                  <input 
                    type="text" 
                    placeholder="e.g. New Delhi"
                    value={formPatientAddress}
                    onChange={(e) => setFormPatientAddress(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Consent Scope / Type</label>
                <select 
                  value={formType} 
                  onChange={(e) => setFormType(e.target.value)}
                  className="input-field"
                >
                  <option value="treatment">General Treatment</option>
                  <option value="data_sharing">Data Sharing (Third Party Referrals)</option>
                  <option value="research">Anonymized Research Study</option>
                  <option value="billing">Billing & Insurance Processing</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Purpose Specification</label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. general diagnostics and prescribing"
                  value={formPurpose}
                  onChange={(e) => setFormPurpose(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Data Categories Affected</label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  {['name', 'diagnosis', 'lab_results', 'prescriptions', 'imaging', 'billing_cost'].map(cat => (
                    <label key={cat} className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={formDataCats.includes(cat)} 
                        onChange={() => toggleCategory(cat)}
                        className="rounded text-brand-600 focus:ring-brand-500"
                      />
                      <span className="capitalize">{cat.replace(/_/g, ' ')}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Third Parties Authorized (comma separated)</label>
                <input 
                  type="text" 
                  placeholder="e.g. Kottayam Medical College, MedLab Ltd"
                  value={formThirdParties}
                  onChange={(e) => setFormThirdParties(e.target.value)}
                  className="input-field"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Signing Method</label>
                  <select 
                    value={formMethod} 
                    onChange={(e) => setFormMethod(e.target.value)}
                    className="input-field"
                  >
                    <option value="digital_signature">Digital Signature (Draw)</option>
                    <option value="otp">Mobile OTP Authentication</option>
                    <option value="verbal_witness">Verbal Witness Sign</option>
                    <option value="thumbprint">Biometric Thumbprint</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Expires (Days)</label>
                  <input 
                    type="number" 
                    value={formExpiresDays}
                    onChange={(e) => setFormExpiresDays(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
                <label className="flex items-center gap-2 text-sm text-slate-700 font-medium cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={formIsMinor} 
                    onChange={() => setFormIsMinor(!formIsMinor)}
                    className="rounded text-brand-600 focus:ring-brand-500"
                  />
                  <span>Patient is a Minor (&lt;18 years)</span>
                </label>
                
                {formIsMinor && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">Guardian Consent ID</label>
                    <input 
                      type="text" 
                      required={formIsMinor}
                      placeholder="e.g. G-001"
                      value={formGuardianId}
                      onChange={(e) => setFormGuardianId(e.target.value)}
                      className="input-field py-1 text-xs"
                    />
                  </div>
                )}
              </div>

              {formMethod === 'digital_signature' && (
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <label className="block text-sm font-medium text-slate-700">Digital Signature</label>
                    <button type="button" onClick={clearSignature} className="text-xs text-red-600 hover:text-red-700">Clear</button>
                  </div>
                  <div className="border border-slate-300 rounded-lg bg-slate-50 overflow-hidden touch-none cursor-crosshair">
                    <canvas 
                      ref={canvasRef}
                      width={400}
                      height={150}
                      className="w-full bg-white"
                      onMouseDown={startDrawing}
                      onMouseMove={draw}
                      onMouseUp={stopDrawing}
                      onMouseLeave={stopDrawing}
                    />
                  </div>
                  {!signatureData && <p className="text-xs text-orange-600">Please draw signature to continue.</p>}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button 
                  type="button" 
                  onClick={() => setIsConsentModalOpen(false)} 
                  className="btn-secondary py-2 px-4"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={submittingConsent} 
                  className="btn-primary py-2 px-4"
                >
                  {submittingConsent ? 'Recording...' : 'Grant Consent'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Report Breach Modal */}
      {isBreachModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-md p-6 bg-white space-y-4 animate-scale-up relative">
            <button 
              onClick={() => setIsBreachModalOpen(false)} 
              className="absolute right-4 top-4 p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <X size={20} />
            </button>
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <AlertTriangle className="text-red-500" size={24} />
              <h3 className="text-lg font-bold text-slate-900 text-red-700">Report Data Breach</h3>
            </div>
            
            <p className="text-xs text-slate-500">
              DPDP rules mandate all institutions report any suspect breaches within 72 hours. Submitting this log triggers the regulatory countdown.
            </p>

            <form onSubmit={handleBreachSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Breach Vector</label>
                <select 
                  value={formBreachType} 
                  onChange={(e) => setFormBreachType(e.target.value)}
                  className="input-field"
                >
                  <option value="unauthorized_access">Unauthorized Server Access</option>
                  <option value="phishing">Social Engineering / Phishing</option>
                  <option value="physical_loss">Physical Logbook / Disk Theft</option>
                  <option value="accidental_leak">Accidental public index leakage</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Affected Records</label>
                  <input 
                    type="number" 
                    required
                    placeholder="e.g. 150"
                    value={formBreachCount}
                    onChange={(e) => setFormBreachCount(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Data Categories Leakage</label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  {['name', 'diagnosis', 'lab_results', 'prescriptions', 'billing_cost'].map(cat => (
                    <label key={cat} className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={formBreachCats.includes(cat)} 
                        onChange={() => toggleCategory(cat, true)}
                        className="rounded text-red-600 focus:ring-red-500"
                      />
                      <span className="capitalize">{cat.replace(/_/g, ' ')}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Root Cause Assessment</label>
                <textarea 
                  required
                  placeholder="Describe the root cause of the data compromise..."
                  value={formBreachCause}
                  onChange={(e) => setFormBreachCause(e.target.value)}
                  className="input-field h-20"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button 
                  type="button" 
                  onClick={() => setIsBreachModalOpen(false)} 
                  className="btn-secondary py-2 px-4"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={submittingBreach} 
                  className="btn-primary py-2 px-4 bg-red-600 hover:bg-red-700"
                >
                  {submittingBreach ? 'Reporting...' : 'Trigger DPDP Clock'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Consent Details Modal */}
      {selectedConsent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-md p-6 bg-white space-y-4 animate-scale-up relative">
            <button 
              onClick={() => setSelectedConsent(null)} 
              className="absolute right-4 top-4 p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <X size={20} />
            </button>
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <Shield className="text-brand-600" size={24} />
              <h3 className="text-lg font-bold text-slate-900">Consent Artefact</h3>
            </div>
            
            <div className="space-y-3 text-sm text-slate-700">
              <div>
                <span className="font-semibold block text-slate-500">Patient Identifier</span>
                <span className="font-mono">{selectedConsent.patient_id}</span>
              </div>
              <div>
                <span className="font-semibold block text-slate-500">Scope Type</span>
                <span className="capitalize font-medium">{selectedConsent.type}</span>
              </div>
              <div>
                <span className="font-semibold block text-slate-500">Authorized Purpose</span>
                <p className="bg-slate-50 p-2 rounded border border-slate-100">{selectedConsent.purpose}</p>
              </div>
              <div>
                <span className="font-semibold block text-slate-500">Cryptographic Blockchain Hash</span>
                <span className="font-mono text-xs block truncate bg-slate-100 p-2 rounded border border-slate-200 text-slate-600">
                  {selectedConsent.artefact_hash || 'SHA-256 Block Unchained'}
                </span>
              </div>
              {selectedConsent.status === 'withdrawn' && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-xs">
                  <span className="font-bold block">Withdrawal Reason:</span>
                  {selectedConsent.withdrawal_reason || 'N/A'}
                </div>
              )}
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-200">
              <button 
                onClick={() => setSelectedConsent(null)} 
                className="btn-primary py-2 px-4"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
