import { useState, useEffect } from 'react'
import { Shield, Plus, Building2, UserCheck, CheckCircle2, AlertCircle, KeyRound, RefreshCw } from 'lucide-react'

export default function SuperAdminPage() {
  // Provisioning Form
  const [name, setName] = useState('')
  const [regNumber, setRegNumber] = useState('')
  const [state, setState] = useState('')
  const [district, setDistrict] = useState('')
  const [address, setAddress] = useState('')
  const [pincode, setPincode] = useState('')
  const [adminName, setAdminName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  
  // Data State
  const [hospitals, setHospitals] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingList, setLoadingList] = useState(false)
  const [success, setSuccess] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Password Reset Modal State
  const [resetEmail, setResetEmail] = useState('')
  const [resetPassword, setResetPassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [resetLoading, setResetLoading] = useState(false)
  const [resetSuccess, setResetSuccess] = useState<string | null>(null)
  const [resetError, setResetError] = useState<string | null>(null)
  const [isResetModalOpen, setIsResetModalOpen] = useState(false)

  const token = localStorage.getItem('medguardian_token')

  async function fetchHospitals() {
    setLoadingList(true)
    try {
      const res = await fetch('/api/auth/hospitals', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setHospitals(data)
      }
    } catch (err) {
      console.error('Failed to fetch hospitals list:', err)
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => {
    fetchHospitals()
  }, [])

  async function handleOnboard(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)
    
    try {
      const res = await fetch('/api/auth/onboard-hospital', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name,
          registration_number: regNumber,
          state,
          district,
          address,
          pincode,
          admin_name: adminName,
          admin_email: adminEmail,
          admin_password: adminPassword
        })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to onboard hospital.')
      }

      setSuccess(data)
      // Reset form
      setName('')
      setRegNumber('')
      setState('')
      setDistrict('')
      setAddress('')
      setPincode('')
      setAdminName('')
      setAdminEmail('')
      setAdminPassword('')
      
      // Refresh list
      fetchHospitals()
    } catch (err: any) {
      setError(err.message || 'An unexpected connection error occurred.')
    } finally {
      setLoading(false)
    }
  }

  async function handleResetPassword(e: React.FormEvent) {
    e.preventDefault()
    setResetLoading(true)
    setResetError(null)
    setResetSuccess(null)

    try {
      const res = await fetch('/api/auth/reset-staff-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          target_email: resetEmail,
          new_password: resetPassword,
          current_password: currentPassword
        })
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Password reset failed.')
      }

      setResetSuccess(`Password for ${resetEmail} successfully updated to your selection!`)
      setResetPassword('')
      setCurrentPassword('')
    } catch (err: any) {
      setResetError(err.message || 'Failed to execute password reset.')
    } finally {
      setResetLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-brand-950 text-white rounded-2xl p-6 sm:p-8 shadow-xl border border-slate-700 relative overflow-hidden">
        <div className="relative z-10 space-y-2">
          <div className="inline-flex items-center gap-2 bg-brand-500/20 text-brand-300 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border border-brand-500/30">
            <Shield size={12} /> HQ Control Center
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">SaaS Multi-Tenant Onboarding Console</h1>
          <p className="text-slate-300 max-w-xl text-sm leading-relaxed">
            Provision new enterprise channels, manage passwords, and oversee active compliance phases across all tenants.
          </p>
        </div>
        <div className="absolute right-0 bottom-0 top-0 w-1/3 bg-[radial-gradient(circle_at_bottom_right,var(--color-brand-600),transparent_70%)] opacity-40 pointer-events-none" />
      </div>

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl p-6 shadow-sm flex flex-col md:flex-row gap-4 items-start">
          <div className="p-2 bg-emerald-100 rounded-lg text-emerald-600">
            <CheckCircle2 size={24} />
          </div>
          <div className="space-y-3 flex-1">
            <h3 className="font-bold text-emerald-900 text-lg">Hospital Tenant Provisioned Successfully!</h3>
            <p className="text-sm text-emerald-700 leading-relaxed">
              The isolated secure partition for <strong>{success.message.split("'")[1]}</strong> has been seeded.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono bg-white/60 p-4 rounded-lg border border-emerald-100">
              <div>
                <span className="text-slate-500 block font-sans">Hospital Tenant ID:</span>
                <span className="text-slate-900 font-bold select-all">{success.hospital_id}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-sans">Admin Login Account:</span>
                <span className="text-slate-900 font-bold select-all">{success.admin_user.email}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-4 shadow-sm flex gap-3 items-center">
          <AlertCircle size={20} className="text-rose-500 flex-shrink-0" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Form */}
        <div className="lg:col-span-2 space-y-6">
          <form onSubmit={handleOnboard} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Card 1: Hospital profile */}
              <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
                <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
                  <div className="p-2 bg-brand-50 rounded-lg text-brand-600">
                    <Building2 size={18} />
                  </div>
                  <h3 className="font-bold text-slate-800">Hospital Institutional Profile</h3>
                </div>

                <div className="space-y-3.5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">HOSPITAL LEGAL NAME</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Apollo Super Specialty"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">REGISTRATION LICENSE ID</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. APOLLO-REG-001"
                      value={regNumber}
                      onChange={e => setRegNumber(e.target.value)}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 mb-1">STATE</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Maharashtra"
                        value={state}
                        onChange={e => setState(e.target.value)}
                        className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 mb-1">DISTRICT</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Mumbai"
                        value={district}
                        onChange={e => setDistrict(e.target.value)}
                        className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">FULL POSTAL ADDRESS</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Bandra West, Mumbai"
                      value={address}
                      onChange={e => setAddress(e.target.value)}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">PINCODE</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. 400050"
                      value={pincode}
                      onChange={e => setPincode(e.target.value)}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                    />
                  </div>
                </div>
              </div>

              {/* Card 2: Admin profile */}
              <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
                <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
                  <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
                    <UserCheck size={18} />
                  </div>
                  <h3 className="font-bold text-slate-800">Primary Administrator Account</h3>
                </div>

                <div className="space-y-3.5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">ADMINISTRATOR FULL NAME</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Dr. Ramesh Mehta"
                      value={adminName}
                      onChange={e => setAdminName(e.target.value)}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">OFFICIAL ADMIN EMAIL</label>
                    <input
                      type="email"
                      required
                      placeholder="e.g. ramesh@apollo.org"
                      value={adminEmail}
                      onChange={e => setAdminEmail(e.target.value)}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-500 mb-1">SECURE ACCOUNT PASSWORD</label>
                    <input
                      type="password"
                      required
                      placeholder="Allocate a strong unique password"
                      value={adminPassword}
                      onChange={e => setAdminPassword(e.target.value)}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                    />
                  </div>
                </div>
                
                <div className="pt-2 text-xs text-slate-400 leading-relaxed">
                  ⚠️ <strong>Security Note:</strong> These credentials will serve as the master login for the newly provisioned tenant channel.
                </div>
              </div>
            </div>

            {/* Action Button */}
            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full sm:w-auto px-6 py-3 rounded-lg bg-gradient-to-r from-slate-900 to-brand-950 text-white font-bold text-sm shadow-md hover:from-slate-800 hover:to-brand-900 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Provisioning Tenant...
                  </>
                ) : (
                  <>
                    <Plus size={16} />
                    Provision Hospital Tenant
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Right 1 Col: Active Directory & Password Override */}
        <div className="space-y-6">
          {/* Active Tenants Directory */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
              <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <Building2 size={16} className="text-slate-400" /> Active Tenants
              </h3>
              <button 
                onClick={fetchHospitals} 
                disabled={loadingList}
                className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all disabled:opacity-50"
              >
                <RefreshCw size={14} className={loadingList ? 'animate-spin' : ''} />
              </button>
            </div>

            <div className="p-3 divide-y divide-slate-100 max-h-[400px] overflow-y-auto">
              {hospitals.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-400 font-medium">
                  No tenant channels registered yet.
                </div>
              ) : (
                hospitals.map((h: any) => (
                  <div key={h.id} className="py-3 px-2 hover:bg-slate-50/50 transition-all rounded-lg space-y-1.5">
                    <div className="flex justify-between items-start gap-2">
                      <h4 className="font-bold text-slate-800 text-xs truncate max-w-[140px]">{h.name}</h4>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wide ${
                        h.onboarding_stage === 'completed' 
                          ? 'bg-emerald-50 border-emerald-200 text-emerald-700' 
                          : 'bg-amber-50 border-amber-200 text-amber-700'
                      }`}>
                        {h.onboarding_stage}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 space-y-0.5">
                      <div><span className="font-semibold text-slate-500">ID:</span> <code className="select-all font-mono">{h.id}</code></div>
                      <div><span className="font-semibold text-slate-500">Admin:</span> {h.admin_email}</div>
                    </div>
                    <button
                      onClick={() => {
                        setResetEmail(h.admin_email)
                        setResetSuccess(null)
                        setResetError(null)
                        setIsResetModalOpen(true)
                      }}
                      className="w-full mt-2 py-1 px-2.5 border border-slate-200 hover:border-slate-300 hover:bg-slate-50 rounded-md text-[10px] font-semibold text-slate-600 transition-all flex items-center justify-center gap-1.5"
                    >
                      <KeyRound size={12} className="text-slate-400" /> Reset Password
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Password Reset Modal Overlay */}
      {isResetModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3 pb-2 border-b border-slate-100">
              <div className="p-2 bg-rose-50 text-rose-600 rounded-lg">
                <KeyRound size={20} />
              </div>
              <div>
                <h3 className="font-bold text-slate-900">Security Override</h3>
                <p className="text-xs text-slate-400 font-medium">Reset primary tenant administrator credentials.</p>
              </div>
            </div>

            {resetSuccess && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg p-3.5 text-xs font-semibold leading-relaxed">
                {resetSuccess}
              </div>
            )}

            {resetError && (
              <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-lg p-3 text-xs font-medium">
                {resetError}
              </div>
            )}

            <form onSubmit={handleResetPassword} className="space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">TARGET EMAIL ACCOUNT</label>
                <input
                  type="email"
                  readOnly
                  value={resetEmail}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 text-slate-400 font-medium select-none outline-none"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">NEW PASSWORD STRAP</label>
                <input
                  type="password"
                  required
                  placeholder="Enter a strong custom password override"
                  value={resetPassword}
                  onChange={e => setResetPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">YOUR CURRENT PASSWORD</label>
                <input
                  type="password"
                  required
                  autoComplete="current-password"
                  placeholder="Confirm your administrator password"
                  value={currentPassword}
                  onChange={e => setCurrentPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsResetModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-xs font-bold transition-all"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={resetLoading}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
                >
                  {resetLoading ? 'Saving Override...' : 'Apply Password Override'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
