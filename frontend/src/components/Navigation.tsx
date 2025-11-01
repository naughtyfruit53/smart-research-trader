import { Link, useLocation } from 'react-router-dom'
import { Moon, Sun, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavigationProps {
  theme: string
  toggleTheme: () => void
}

export function Navigation({ theme, toggleTheme }: NavigationProps) {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Home' },
    { path: '/signals', label: 'Signals' },
    { path: '/backtests', label: 'Backtests' },
  ]

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">Smart Research Trader</span>
          </div>
          
          <div className="flex items-center gap-6">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "text-sm font-medium transition-colors hover:text-primary",
                  location.pathname === item.path
                    ? "text-foreground"
                    : "text-muted-foreground"
                )}
              >
                {item.label}
              </Link>
            ))}
            
            <button
              onClick={toggleTheme}
              className="rounded-md p-2 hover:bg-accent"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? (
                <Sun className="h-5 w-5" />
              ) : (
                <Moon className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}
