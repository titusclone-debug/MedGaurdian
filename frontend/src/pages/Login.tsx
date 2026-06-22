import { useState } from 'react'
import { Lock, Mail, Eye, EyeOff, Hospital } from 'lucide-react'
import type { SessionUser } from '../types/session'

interface LoginPageProps {
  onLogin: (token: string, user: SessionUser) => void
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)
      
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      })
      
      if (!response.ok) {
        throw new Error('Invalid credentials')
      }
      
      const data = await response.json()
      onLogin(data.access_token, data.user)
    } catch (err: any) {
      setError('Invalid credentials or authentication service unavailable')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 via-white to-blue-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Hospital size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">MedGuardian</h1>
          <p className="text-slate-500 mt-2">The Institutional Nervous System</p>
          <p className="text-sm text-slate-400 mt-1">Hospital Administration & Compliance Tracking</p>
        </div>
        
        {/* Login Form */}
        <div className="card p-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Welcome back</h2>
          <p className="text-sm text-slate-500 mb-6">Sign in to your compliance dashboard</p>
          
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
              <div className="relative">
                <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field pl-10"
                  placeholder="admin@hospital.org"
                  required
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pl-10 pr-10"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-3"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          
          <p className="text-xs text-slate-400 text-center mt-6">
            Use credentials issued by your MedGuardian administrator.
          </p>
        </div>
        
        {/* Footer */}
        <p className="text-center text-xs text-slate-400 mt-6">
          Built for Christian Mission Hospitals • FCRA • DPDP • NABH 6th Edition
        </p>
      </div>
    </div>
  )
}
