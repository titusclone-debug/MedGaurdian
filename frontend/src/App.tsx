import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import FCRAPage from './pages/FCRA'
import DPDPPage from './pages/DPDP'
import BMWPage from './pages/BMW'
import NABHPage from './pages/NABH'
import LicensesPage from './pages/Licenses'
import RiskPage from './pages/Risk'
import LoginPage from './pages/Login'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  
  useEffect(() => {
    const token = localStorage.getItem('medguardian_token')
    const savedUser = localStorage.getItem('medguardian_user')
    if (token && savedUser) {
      setIsAuthenticated(true)
      setUser(JSON.parse(savedUser))
    }
  }, [])
  
  const handleLogin = (token: string, userData: any) => {
    localStorage.setItem('medguardian_token', token)
    localStorage.setItem('medguardian_user', JSON.stringify(userData))
    setIsAuthenticated(true)
    setUser(userData)
  }
  
  const handleLogout = () => {
    localStorage.removeItem('medguardian_token')
    localStorage.removeItem('medguardian_user')
    setIsAuthenticated(false)
    setUser(null)
  }
  
  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />
  }
  
  return (
    <Router>
      <Layout user={user} onLogout={handleLogout}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/fcra" element={<FCRAPage />} />
          <Route path="/dpdp" element={<DPDPPage />} />
          <Route path="/bmw" element={<BMWPage />} />
          <Route path="/nabh" element={<NABHPage />} />
          <Route path="/licenses" element={<LicensesPage />} />
          <Route path="/risk" element={<RiskPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
