import { useState } from 'react'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'

function App() {
  const [token, setToken] = useState(null)

  if (!token) return <LoginPage onLogin={setToken} />
  return <DashboardPage token={token} />
}

export default App