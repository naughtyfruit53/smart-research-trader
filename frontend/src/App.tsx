import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from '@/components/ThemeProvider'
import { Navigation } from '@/components/Navigation'
import HomePage from '@/pages/HomePage'
import SignalsPage from '@/pages/SignalsPage'
import StockPage from '@/pages/StockPage'
import BacktestsPage from '@/pages/BacktestsPage'

function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')

  useEffect(() => {
    const stored = localStorage.getItem('smart-trader-theme') as 'dark' | 'light' | null
    if (stored) {
      setTheme(stored)
    }
  }, [])

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    localStorage.setItem('smart-trader-theme', newTheme)
  }

  return (
    <ThemeProvider defaultTheme={theme as 'dark' | 'light' | 'system'} storageKey="smart-trader-theme">
      <Router>
        <div className="min-h-screen bg-background">
          <Navigation theme={theme} toggleTheme={toggleTheme} />
          <main className="container mx-auto px-4 py-8">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/signals" element={<SignalsPage />} />
              <Route path="/stock/:ticker" element={<StockPage />} />
              <Route path="/backtests" element={<BacktestsPage />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App
