import { useState, useEffect } from 'react'
import { Shield, Plus, ArrowUpRight, Download, AlertTriangle, CheckCircle, X, Copy, Check } from 'lucide-react'

export default function FCRAPage() {
  const [accounts, setAccounts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Modals state
  const [isTxModalOpen, setIsTxModalOpen] = useState(false)
  const [isDraftModalOpen, setIsDraftModalOpen] = useState(false)
  const [selectedDraft, setSelectedDraft] = useState<any>(null)
  const [copied, setCopied] = useState(false)

  // Transaction form state
  const [formAccountId, setFormAccountId] = useState('')
  const [formAmount, setFormAmount] = useState('')
  const [formType, setFormType] = useState('credit')
  const [formDesc, setFormDesc] = useState('')
  const [formPurpose, setFormPurpose] = useState('')
  const [formDonorName, setFormDonorName] = useState('')
  const [formDonorCountry, setFormDonorCountry] = useState('')
  const [formDonorId, setFormDonorId] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function fetchFCRAData() {
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

      const res = await fetch(`/api/fcra/accounts/${hospitalId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!res.ok) {
        throw new Error('Failed to retrieve FCRA designate ledger structures')
      }

      const data = await res.json()
      setAccounts(data.accounts || [])
      if (data.accounts && data.accounts.length > 0) {
        setFormAccountId(data.accounts[0].id)
      }
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Synchronization failure')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFCRAData()
  }, [])

  const handleTxSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      const token = localStorage.getItem('medguardian_token')
      if (!token) throw new Error('Authentication expired')

      const payload = {
        account_id: formAccountId,
        amount: parseFloat(formAmount),
        transaction_type: formType,
        description: formDesc,
        purpose: formPurpose,
        donor_name: formType === 'credit' ? formDonorName : null,
        donor_country: formType === 'credit' ? formDonorCountry : null,
        donor_passport_or_id: formType === 'credit' ? formDonorId : null
      }

      const res = await fetch('/api/fcra/transactions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to file fund transaction')
      }

      setIsTxModalOpen(false)
      // reset form
      setFormAmount('')
      setFormDesc('')
      setFormPurpose('')
      setFormDonorName('')
      setFormDonorCountry('')
      setFormDonorId('')

      setLoading(true)
      await fetchFCRAData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleGenerateRenewalDraft = async () => {
    try {
      const token = localStorage.getItem('medguardian_token')
      const userString = localStorage.getItem('medguardian_user')
      const userObj = userString ? JSON.parse(userString) : null
      const hospitalId = userObj?.hospital_id

      if (!token || !hospitalId) return

      const res = await fetch(`/api/fcra/renewal-draft/${hospitalId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!res.ok) throw new Error('Failed to generate FCRA MHA renewal draft')

      const data = await res.json()
      setSelectedDraft(data)
      setIsDraftModalOpen(true)
    } catch (err: any) {
      alert('Error drafting FCRA renewal: ' + err.message)
    }
  }

  const handleCopyDraft = () => {
    if (!selectedDraft?.draft) return
    navigator.clipboard.writeText(selectedDraft.draft)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Derive aggregates
  const totalBalance = accounts.reduce((sum, a) => sum + a.current_balance, 0)
  const totalBudget = accounts.reduce((sum, a) => sum + a.annual_budget, 0)
  const totalExpenditure = accounts.reduce((sum, a) => sum + a.ytd_expenditure, 0)

  // Accumulate all transactions across all accounts
  const allTransactions = accounts.flatMap(a => 
    a.recent_transactions.map((t: any) => ({
      ...t,
      account_name: a.account_name
    }))
  ).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())

  const complianceIssuesCount = allTransactions.filter(t => !t.is_compliant).length
  const complianceRate = allTransactions.length > 0 
    ? ((allTransactions.length - complianceIssuesCount) / allTransactions.length) * 100 
    : 100

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4 animate-pulse">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600"></div>
        <p className="text-slate-500 text-sm font-medium">Synchronizing designated foreign remittance bank nodes...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Shield size={28} className="text-brand-600" />
            FCRA Guardian
          </h2>
          <p className="text-slate-500 mt-1">Foreign fund compliance and utilization tracking</p>
        </div>
        <div className="flex gap-3">
          <button onClick={handleGenerateRenewalDraft} className="btn-secondary flex items-center gap-1.5">
            <Shield size={16} /> MHA Renewal Draft
          </button>
          <button onClick={() => setIsTxModalOpen(true)} className="btn-primary flex items-center gap-1.5">
            <Plus size={16} /> Add Transaction
          </button>
        </div>
      </div>
      
      {error && (
        <div className="p-4 border-2 border-red-200 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-3">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="stat-value text-brand-600">₹{(totalBalance / 100000).toFixed(1)}L</div>
          <div className="stat-label">Total FCRA Balance</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-green-600">₹{(totalBudget / 100000).toFixed(1)}L</div>
          <div className="stat-label">Annual Budget</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-orange-600">₹{(totalExpenditure / 100000).toFixed(1)}L</div>
          <div className="stat-label">YTD Expenditure</div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-2">
            <CheckCircle size={24} className="text-green-500" />
            <div className="stat-value text-green-600">{complianceRate.toFixed(0)}%</div>
          </div>
          <div className="stat-label">Compliance Rate</div>
        </div>
      </div>
      
      {/* Accounts */}
      <div className="card">
        <div className="px-6 py-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-900">FCRA Designated Accounts</h3>
        </div>
        <div className="divide-y divide-slate-100">
          {accounts.map((account) => (
            <div key={account.id} className="px-6 py-5">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div>
                  <h4 className="font-semibold text-slate-900">{account.account_name}</h4>
                  <p className="text-sm text-slate-500">{account.bank_name} • {account.branch} • {account.account_number}</p>
                  <p className="text-xs text-slate-400 mt-1">Utilization Purpose: {account.fcra_utilization_purpose}</p>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-sm text-slate-500">Balance</div>
                    <div className="text-lg font-bold text-slate-900">₹{(account.current_balance / 100000).toFixed(2)}L</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-slate-500">Utilization</div>
                    <div className="text-lg font-bold text-slate-900">{account.utilization_rate.toFixed(0)}%</div>
                  </div>
                  <span className={`badge ${
                    account.compliance_status === 'compliant' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {account.compliance_status}
                  </span>
                </div>
              </div>
              
              {/* Utilization bar */}
              <div className="mt-4">
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-brand-500 rounded-full"
                    style={{ width: `${account.utilization_rate}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1 text-xs text-slate-400">
                  <span>₹{(account.ytd_expenditure / 100000).toFixed(1)}L spent</span>
                  <span>₹{(account.annual_budget / 100000).toFixed(1)}L budget</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Recent Transactions */}
      <div className="card">
        <div className="px-6 py-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-900">Recent Transactions</h3>
          <p className="text-sm text-slate-500 mt-1">Every rupee tracked with FCRA compliance checks</p>
        </div>
        <div className="overflow-x-auto">
          {allTransactions.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              No transactions recorded. Click 'Add Transaction' above to record credit/debit receipts.
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-header">Date</th>
                  <th className="table-header">Account</th>
                  <th className="table-header">Description</th>
                  <th className="table-header">Purpose</th>
                  <th className="table-header">Amount</th>
                  <th className="table-header">Donor Country</th>
                  <th className="table-header">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {allTransactions.map((txn) => (
                  <tr key={txn.id} className="hover:bg-slate-50">
                    <td className="table-cell">{txn.date?.split('T')[0]}</td>
                    <td className="table-cell text-xs text-slate-500">{txn.account_name}</td>
                    <td className="table-cell font-medium">{txn.description}</td>
                    <td className="table-cell text-slate-500">{txn.purpose}</td>
                    <td className="table-cell">
                      <span className={txn.type === 'credit' ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                        {txn.type === 'credit' ? '+' : '-'}₹{txn.amount.toLocaleString('en-IN')}
                      </span>
                    </td>
                    <td className="table-cell text-slate-500">{txn.donor_country || '—'}</td>
                    <td className="table-cell">
                      {txn.is_compliant ? (
                        <span className="badge bg-green-100 text-green-800">Compliant</span>
                      ) : (
                        <span className="badge bg-red-100 text-red-800">Non-compliant</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Log Transaction Modal */}
      {isTxModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-md p-6 bg-white space-y-4 animate-scale-up relative">
            <button 
              onClick={() => setIsTxModalOpen(false)} 
              className="absolute right-4 top-4 p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <X size={20} />
            </button>
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <Shield className="text-brand-600" size={24} />
              <h3 className="text-lg font-bold text-slate-900">Record Transaction</h3>
            </div>
            
            <form onSubmit={handleTxSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Designated Bank Account</label>
                <select 
                  value={formAccountId} 
                  onChange={(e) => setFormAccountId(e.target.value)}
                  className="input-field"
                >
                  {accounts.map(acc => (
                    <option key={acc.id} value={acc.id}>{acc.account_name} ({acc.account_number})</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Amount (₹)</label>
                  <input 
                    type="number" 
                    required
                    placeholder="e.g. 50000"
                    value={formAmount}
                    onChange={(e) => setFormAmount(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Flow Type</label>
                  <select 
                    value={formType} 
                    onChange={(e) => setFormType(e.target.value)}
                    className="input-field"
                  >
                    <option value="credit">Credit (Inward Receipt)</option>
                    <option value="debit">Debit (Outward Expense)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Description</label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. ECG Machine acquisition"
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Purpose</label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. healthcare, medical equipment"
                  value={formPurpose}
                  onChange={(e) => setFormPurpose(e.target.value)}
                  className="input-field"
                />
              </div>

              {formType === 'credit' && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
                  <h4 className="text-xs font-bold text-brand-800 uppercase tracking-wide">Donor Regulatory Data</h4>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 mb-1">Donor Name</label>
                      <input 
                        type="text" 
                        required={formType === 'credit'}
                        placeholder="Caritas Intl"
                        value={formDonorName}
                        onChange={(e) => setFormDonorName(e.target.value)}
                        className="input-field py-1 text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 mb-1">Donor Country</label>
                      <input 
                        type="text" 
                        required={formType === 'credit'}
                        placeholder="Germany"
                        value={formDonorCountry}
                        onChange={(e) => setFormDonorCountry(e.target.value)}
                        className="input-field py-1 text-xs"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">Passport / Foreign Reg ID</label>
                    <input 
                      type="text" 
                      required={formType === 'credit'}
                      placeholder="DE-883294-X"
                      value={formDonorId}
                      onChange={(e) => setFormDonorId(e.target.value)}
                      className="input-field py-1 text-xs"
                    />
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button 
                  type="button" 
                  onClick={() => setIsTxModalOpen(false)} 
                  className="btn-secondary py-2 px-4"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={submitting} 
                  className="btn-primary py-2 px-4"
                >
                  {submitting ? 'Recording...' : 'Record Transaction'}
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
                <Shield className="text-brand-600" size={24} />
                <h3 className="text-lg font-bold text-slate-900">MHA FCRA Renewal Draft</h3>
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
              MedGuardian has verified the ledger balances across all designated accounts and auto-generated the formal renewal filing letter in standard Ministry of Home Affairs (MHA) template layout.
            </p>

            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono text-slate-700 overflow-y-auto max-h-[300px] whitespace-pre-line">
              {selectedDraft.draft}
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-200">
              <button 
                onClick={() => setIsDraftModalOpen(false)} 
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
