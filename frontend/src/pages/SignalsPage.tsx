import { useEffect, useState } from 'react'
import { SortingState } from '@tanstack/react-table'
import { fetchSignals, SignalsResponse } from '@/lib/api'
import { SignalsTable } from '@/components/SignalsTable'
import { Filters, FilterValues } from '@/components/Filters'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/Card'

export default function SignalsPage() {
  const [data, setData] = useState<SignalsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'risk_adjusted_score', desc: true },
  ])
  const [filters, setFilters] = useState<FilterValues>({
    sector: '',
    min_liquidity: 0,
    min_confidence: 0,
    exclude_earnings: false,
  })

  useEffect(() => {
    const loadSignals = async () => {
      try {
        setLoading(true)
        const result = await fetchSignals({
          horizon: '1d',
          top: 100,
          sector: filters.sector || undefined,
          min_liquidity: filters.min_liquidity || undefined,
          min_confidence: filters.min_confidence || undefined,
          exclude_earnings: filters.exclude_earnings,
        })
        setData(result)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch signals')
        setData(null)
      } finally {
        setLoading(false)
      }
    }

    loadSignals()
  }, [filters])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Trading Signals</h1>
        <p className="text-muted-foreground mt-2">
          Ranked trading signals based on AI predictions and risk-adjusted scores
        </p>
      </div>

      <Filters filters={filters} onChange={setFilters} />

      {loading && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Loading signals...</p>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-destructive">
              <p className="font-semibold">Error:</p>
              <p>{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {data && !loading && (
        <Card>
          <CardHeader>
            <CardTitle>
              {data.count} Signal{data.count !== 1 ? 's' : ''} Found
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.signals.length > 0 ? (
              <SignalsTable
                signals={data.signals}
                sorting={sorting}
                onSortingChange={setSorting}
              />
            ) : (
              <p className="text-muted-foreground">
                No signals found matching your filters.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="text-sm text-muted-foreground text-center">
        <p>⚠️ For research and education only. Not investment advice.</p>
      </div>
    </div>
  )
}
