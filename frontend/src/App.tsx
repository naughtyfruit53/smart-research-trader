import { ThemeProvider } from '@/components/ThemeProvider'
import HomePage from '@/pages/HomePage'

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="smart-trader-theme">
      <div className="min-h-screen bg-background">
        <HomePage />
      </div>
    </ThemeProvider>
  )
}

export default App
