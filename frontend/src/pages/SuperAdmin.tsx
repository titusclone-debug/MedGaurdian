import { useState } from 'react'
import { Shield, Plus, Building2, UserCheck, CheckCircle2, AlertCircle } from 'lucide-react'

export default function SuperAdminPage() {
  const [name, setName] = useState('')
  const [regNumber, setRegNumber] = useState('')
  const [state, setState] = useState('')
  const [district, setDistrict] = useState('')
  const [address, setAddress] = useState('')
  const [pincode, setPincode] = useState('')
  
  const [adminName, setAdminName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleOnboard(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)

    const token = localStorage.getItem('medguardian_token')
    
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
      
    } catch (err: any) {
      setError(err.message || 'An unexpected connection error occurred.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-brand-950 text-white rounded-2xl p-6 sm:p-8 shadow-xl border border-slate-700 relative overflow-hidden">
        <div className="relative z-10 space-y-2">
          <div className="inline-flex items-center gap-2 bg-brand-500/20 text-brand-300 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border border-brand-500/30">
            <Shield size={12} /> HQ Control Center
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">SaaS Multi-Tenant Onboarding Console</h1>
          <p className="text-slate-300 max-w-xl text-sm leading-relaxed">
            Provision new enterprise hospital channels and allocate isolated administrative credentials securely onto our global cloud network.
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
              The isolated secure partition for <strong>{success.message.split("'")[1]}</strong> has been successfully seeded. The credentials are now active!
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
            <p className="text-xs text-emerald-600 font-medium">
              💡 Your client can now log in securely from any device at your primary site.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-4 shadow-sm flex gap-3 items-center">
          <AlertCircle size={20} className="text-rose-500 flex-shrink-0" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

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
              ⚠️ <strong>Security Note:</strong> These credentials will serve as the master login for the newly provisioned tenant channel. Ensure they are delivered securely.
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
  )
}
