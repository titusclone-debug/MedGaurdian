import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, Shield, FileCheck, Recycle, Award, 
  FileText, Cloud, LogOut, Bell, Search, Menu, X
} from 'lucide-react'
import { useState } from 'react'
import type { SessionUser } from '../types/session'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, description: 'Risk Weather Forecast' },
  { name: 'FCRA Guardian', href: '/fcra', icon: Shield, description: 'Foreign Fund Compliance' },
  { name: 'DPDP Consent', href: '/dpdp', icon: FileCheck, description: 'Patient Data Protection' },
  { name: 'BMW Sentinel', href: '/bmw', icon: Recycle, description: 'Bio-Medical Waste' },
  { name: 'NABH Compliance', href: '/nabh', icon: Award, description: '6th Edition Standards' },
  { name: 'Licenses', href: '/licenses', icon: FileText, description: 'License Tracker' },
  { name: 'Risk Intelligence', href: '/risk', icon: Cloud, description: 'Predictive Alerts' },
]

interface LayoutProps {
  children: ReactNode
  user: SessionUser
  onLogout: () => void
}

export default function Layout({ children, user, onLogout }: LayoutProps) {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  
  const visibleNavigation = [
    ...navigation,
    ...(user?.role === 'super_admin' ? [
      { name: 'HQ Command Center', href: '/hq', icon: Shield, description: 'SaaS Onboarding Portal' }
    ] : []),
    ...(user?.role === 'hospital_admin' ? [
      { name: 'Staff Directory', href: '/staff', icon: FileText, description: 'Team Management' }
    ] : [])
  ]
  
  const currentPage = visibleNavigation.find(n => n.href === location.pathname)
  
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-72 bg-white border-r border-slate-200 
        transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0
      `}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-200">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
            <span className="text-white text-xl font-bold">M</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900">MedGuardian</h1>
            <p className="text-xs text-slate-500">Institutional Nervous System</p>
          </div>
          <button 
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden ml-auto p-1.5 rounded-lg hover:bg-slate-100"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* Navigation */}
        <nav className="px-3 py-4 space-y-1 overflow-y-auto max-h-[calc(100vh-160px)] pb-12">
          {visibleNavigation.map((item) => {
            const isActive = location.pathname === item.href
            const Icon = item.icon
            
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setSidebarOpen(false)}
                className={isActive ? 'nav-link-active' : 'nav-link'}
              >
                <Icon size={20} className={isActive ? 'text-brand-600' : 'text-slate-400'} />
                <div>
                  <div className={isActive ? 'text-brand-700' : 'text-slate-700'}>{item.name}</div>
                  <div className="text-xs text-slate-400">{item.description}</div>
                </div>
              </Link>
            )
          })}
        </nav>
        
        {/* User section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-brand-100 flex items-center justify-center">
              <span className="text-brand-700 font-semibold text-sm">
                {user?.name?.charAt(0) || 'U'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">{user?.name || 'User'}</p>
              <p className="text-xs text-slate-500 truncate">{user?.role || 'Staff'}</p>
            </div>
            <button
              onClick={onLogout}
              className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600"
              title="Sign out"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      
      {/* Main content */}
      <div className="lg:pl-72">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-sm border-b border-slate-200">
          <div className="flex items-center justify-between px-4 sm:px-6 py-3">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-2 rounded-lg hover:bg-slate-100"
              >
                <Menu size={20} />
              </button>
              
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  {currentPage?.name || 'Dashboard'}
                </h2>
                <p className="text-sm text-slate-500 hidden sm:block">
                  {currentPage?.description || 'Overview'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Search */}
              <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-slate-100 rounded-lg">
                <Search size={16} className="text-slate-400" />
                <input
                  type="text"
                  placeholder="Search regulations..."
                  className="bg-transparent border-none outline-none text-sm w-48 placeholder:text-slate-400"
                />
              </div>
              
              {/* Notifications */}
              <button className="relative p-2 rounded-lg hover:bg-slate-100 text-slate-500">
                <Bell size={20} />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
              </button>
            </div>
          </div>
        </header>
        
        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
