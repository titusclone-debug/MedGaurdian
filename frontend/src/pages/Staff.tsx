import { useState, useEffect } from 'react'
import { UserPlus, ShieldAlert, KeyRound, CheckCircle2, AlertCircle, RefreshCw, Users, Shield } from 'lucide-react'

export default function StaffPage() {
  const [staff, setStaff] = useState<any[]>([])
  
  // Create Staff Form State
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [role, setRole] = useState('doctor')
  const [department, setDepartment] = useState('')
  const [employeeId, setEmployeeId] = useState('')
  const [qualification, setQualification] = useState('')
  const [password, setPassword] = useState('')

  // Control State
  const [loading, setLoading] = useState(false)
  const [loadingList, setLoadingList] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Password Reset Overlay State
  const [resetEmail, setResetEmail] = useState('')
  const [resetPassword, setResetPassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [resetLoading, setResetLoading] = useState(false)
  const [resetSuccess, setResetSuccess] = useState<string | null>(null)
  const [resetError, setResetError] = useState<string | null>(null)
  const [isResetModalOpen, setIsResetModalOpen] = useState(false)

  const token = localStorage.getItem('medguardian_token')

  async function fetchStaff() {
    setLoadingList(true)
    try {
      const res = await fetch('/api/auth/staff', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setStaff(data)
      }
    } catch (err) {
      console.error('Failed to load staff list:', err)
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => {
    fetchStaff()
  }, [])

  async function handleCreateStaff(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const res = await fetch('/api/auth/staff', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name,
          email,
          phone,
          role,
          department,
          employee_id: employeeId,
          qualification,
          password
        })
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to register staff member.')
      }

      setSuccess(`Staff member '${name}' successfully onboarded with temporary credentials!`)
      
      // Reset fields
      setName('')
      setEmail('')
      setPhone('')
      setDepartment('')
      setEmployeeId('')
      setQualification('')
      setPassword('')
      
      fetchStaff()
    } catch (err: any) {
      setError(err.message || 'Failed to complete registration.')
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
        throw new Error(data.detail || 'Password override failed.')
      }

      setResetSuccess(`Password for ${resetEmail} successfully updated!`)
      setResetPassword('')
      setCurrentPassword('')
    } catch (err: any) {
      setResetError(err.message || 'Failed to execute credentials update.')
    } finally {
      setResetLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 text-white rounded-2xl p-6 sm:p-8 shadow-xl border border-slate-700 relative overflow-hidden">
        <div className="relative z-10 space-y-2">
          <div className="inline-flex items-center gap-2 bg-indigo-500/20 text-indigo-300 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border border-indigo-500/30">
            <Users size={12} /> Staff Administration
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Hospital Staff Directory & Roles</h1>
          <p className="text-slate-300 max-w-xl text-sm leading-relaxed">
            Manage roles, issue delegation credentials, and execute administrative password overrides for clinical and compliance teams.
          </p>
        </div>
        <div className="absolute right-0 bottom-0 top-0 w-1/3 bg-[radial-gradient(circle_at_bottom_right,var(--color-indigo-600),transparent_70%)] opacity-40 pointer-events-none" />
      </div>

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl p-4 shadow-sm flex gap-3 items-center">
          <CheckCircle2 size={20} className="text-emerald-500 flex-shrink-0" />
          <p className="text-sm font-medium">{success}</p>
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-4 shadow-sm flex gap-3 items-center">
          <AlertCircle size={20} className="text-rose-500 flex-shrink-0" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Form to invite new staff */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
            <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
              <UserPlus size={18} />
            </div>
            <h3 className="font-bold text-slate-800">Add New Staff Member</h3>
          </div>

          <form onSubmit={handleCreateStaff} className="space-y-3.5">
            <div>
              <label className="block text-[10px] font-bold text-slate-500 mb-1">EMPLOYEE ID / BADGE</label>
              <input
                type="text"
                required
                placeholder="e.g. EMP-908"
                value={employeeId}
                onChange={e => setEmployeeId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-500 mb-1">FULL LEGAL NAME</label>
              <input
                type="text"
                required
                placeholder="e.g. Dr. Ramesh Mehta"
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-500 mb-1">OFFICIAL EMAIL</label>
              <input
                type="email"
                required
                placeholder="e.g. name@hospital.org"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">PHONE NUMBER</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. +91-99999"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">DEPARTMENT</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Surgery"
                  value={department}
                  onChange={e => setDepartment(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">SYSTEM ASSIGNED ROLE</label>
                <select
                  value={role}
                  onChange={e => setRole(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all"
                >
                  <option value="doctor">Doctor</option>
                  <option value="nurse">Nurse</option>
                  <option value="compliance_officer">Compliance Officer</option>
                  <option value="accountant">Accountant / Finance</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">QUALIFICATION</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. MBBS, MD"
                  value={qualification}
                  onChange={e => setQualification(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
                />
              </div>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-500 mb-1">TEMPORARY PASSWORD</label>
              <input
                type="password"
                required
                placeholder="Assign a secure temp password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none transition-all placeholder:text-slate-400"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-lg text-xs font-bold shadow-md hover:from-slate-800 hover:to-indigo-900 transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              {loading ? 'Registering...' : 'Register Active Staff'}
            </button>
          </form>
        </div>

        {/* Right 2 Columns: Directory List */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
              <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <Users size={16} className="text-slate-400" /> Active Staff Roster
              </h3>
              <button 
                onClick={fetchStaff} 
                disabled={loadingList}
                className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all disabled:opacity-50"
              >
                <RefreshCw size={14} className={loadingList ? 'animate-spin' : ''} />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-slate-100 text-[10px] font-bold text-slate-400 bg-slate-50/50">
                    <th className="px-6 py-3">NAME & ROLE</th>
                    <th className="px-6 py-3">EMPLOYEE DETAILS</th>
                    <th className="px-6 py-3">CONTACT INFO</th>
                    <th className="px-6 py-3 text-right">CREDENTIALS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                  {staff.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="text-center py-12 text-slate-400 font-medium">
                        No team members registered under this hospital channel yet.
                      </td>
                    </tr>
                  ) : (
                    staff.map((s: any) => (
                      <tr key={s.id} className="hover:bg-slate-50/50 transition-all">
                        <td className="px-6 py-4">
                          <div>
                            <div className="font-bold text-slate-900">{s.name}</div>
                            <div className="text-[10px] text-slate-400 font-medium tracking-wide uppercase mt-0.5 inline-flex items-center gap-1">
                              <Shield size={10} className="text-slate-400" /> {s.role}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="font-medium text-slate-800">{s.department}</div>
                          <div className="text-[10px] text-slate-400 font-mono mt-0.5">ID: {s.employee_id}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div>{s.email}</div>
                          <div className="text-[10px] text-slate-400 font-medium mt-0.5">{s.phone}</div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => {
                              setResetEmail(s.email)
                              setResetSuccess(null)
                              setResetError(null)
                              setIsResetModalOpen(true)
                            }}
                            className="inline-flex items-center gap-1.5 py-1 px-2.5 border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-[10px] font-bold text-slate-600 rounded-md transition-all"
                          >
                            <KeyRound size={11} className="text-slate-400" /> Override Pass
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Password Override Modal Overlay */}
      {isResetModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3 pb-2 border-b border-slate-100">
              <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                <KeyRound size={20} />
              </div>
              <div>
                <h3 className="font-bold text-slate-900">Credential Override</h3>
                <p className="text-xs text-slate-400 font-medium">Instantly override login password for your team member.</p>
              </div>
            </div>

            {resetSuccess && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg p-3.5 text-xs font-semibold">
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
                <label className="block text-[10px] font-bold text-slate-500 mb-1">MEMBER EMAIL</label>
                <input
                  type="email"
                  readOnly
                  value={resetEmail}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 text-slate-400 font-medium select-none outline-none"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-1">NEW SECURE PASSWORD</label>
                <input
                  type="password"
                  required
                  placeholder="Enter a new strong credential override"
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
                  {resetLoading ? 'Overriding...' : 'Apply Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
