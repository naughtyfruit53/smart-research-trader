import { useEffect, useState } from 'react'
import { fetchHealth, type HealthResponse } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/Card'

export default function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        setLoading(true)
        const data = await fetchHealth()
        setHealth(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch health status')
        setHealth(null)
      } finally {
        setLoading(false)
      }
    }

    checkHealth()
  }, [])

  return (
    <div className="container mx-auto p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight">
            Smart Research Trader
          </h1>
          <p className="text-lg text-muted-foreground">
            AI-powered stock research and trading signals platform
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Backend Health Status</CardTitle>
          </CardHeader>
          <CardContent>
            {loading && (
              <p className="text-muted-foreground">Checking backend status...</p>
            )}
            {error && (
              <div className="text-destructive">
                <p className="font-semibold">Error:</p>
                <p>{error}</p>
              </div>
            )}
            {health && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">Status:</span>
                  <span className={health.status === 'ok' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                    {health.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">Version:</span>
                  <span className="text-muted-foreground">{health.version}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="text-center text-sm text-muted-foreground">
          <p>⚠️ For research and education only. Not investment advice.</p>
        </div>
      </div>
    </div>
  )
}
