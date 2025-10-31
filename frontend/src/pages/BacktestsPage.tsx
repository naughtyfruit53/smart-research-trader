import { useEffect, useState } from 'react'
import { fetchLatestBacktest, BacktestResponse } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/Card'
import { EquityCurve } from '@/components/Charts/EquityCurve'
import { DrawdownChart } from '@/components/Charts/DrawdownChart'

export default function BacktestsPage() {
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadBacktest = async () => {
      try {
        setLoading(true)
        const data = await fetchLatestBacktest()
        setBacktest(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch backtest data')
        setBacktest(null)
      } finally {
        setLoading(false)
      }
    }

    loadBacktest()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Loading backtest results...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !backtest) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-destructive">
              <p className="font-semibold">Error:</p>
              <p>{error || 'No backtest data available'}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Backtest Results</h1>
        <p className="text-muted-foreground mt-2">
          Performance metrics and equity curve from the latest backtest
        </p>
      </div>

      {/* Metrics Cards */}
      <div className="grid md:grid-cols-3 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Return"
          value={backtest.metrics.total_return ? `${(backtest.metrics.total_return * 100).toFixed(2)}%` : 'N/A'}
        />
        <MetricCard
          title="Annual Return"
          value={backtest.metrics.annual_return ? `${(backtest.metrics.annual_return * 100).toFixed(2)}%` : 'N/A'}
        />
        <MetricCard
          title="Sharpe Ratio"
          value={backtest.metrics.sharpe_ratio?.toFixed(2)}
        />
        <MetricCard
          title="Max Drawdown"
          value={backtest.metrics.max_drawdown ? `${(backtest.metrics.max_drawdown * 100).toFixed(2)}%` : 'N/A'}
        />
        <MetricCard
          title="Win Rate"
          value={backtest.metrics.win_rate ? `${(backtest.metrics.win_rate * 100).toFixed(2)}%` : 'N/A'}
        />
        <MetricCard
          title="Number of Trades"
          value={backtest.metrics.num_trades?.toString()}
        />
        <MetricCard
          title="Start Date"
          value={backtest.metrics.start_date ? new Date(backtest.metrics.start_date).toLocaleDateString() : 'N/A'}
        />
        <MetricCard
          title="End Date"
          value={backtest.metrics.end_date ? new Date(backtest.metrics.end_date).toLocaleDateString() : 'N/A'}
        />
      </div>

      {/* Equity Curve */}
      <Card>
        <CardHeader>
          <CardTitle>Equity Curve</CardTitle>
        </CardHeader>
        <CardContent>
          {backtest.equity_curve.length > 0 ? (
            <EquityCurve data={backtest.equity_curve} />
          ) : (
            <p className="text-muted-foreground">No equity curve data available</p>
          )}
        </CardContent>
      </Card>

      {/* Drawdown Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Drawdown</CardTitle>
        </CardHeader>
        <CardContent>
          {backtest.equity_curve.length > 0 ? (
            <DrawdownChart data={backtest.equity_curve} />
          ) : (
            <p className="text-muted-foreground">No drawdown data available</p>
          )}
        </CardContent>
      </Card>

      {/* Backtest Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Backtest Info</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Run ID</p>
              <p className="text-lg font-mono">{backtest.run_id}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Started At</p>
              <p className="text-lg">
                {new Date(backtest.started_at).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Finished At</p>
              <p className="text-lg">
                {new Date(backtest.finished_at).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Parameters</p>
              <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-auto">
                {JSON.stringify(backtest.params, null, 2)}
              </pre>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="text-sm text-muted-foreground text-center">
        <p>⚠️ For research and education only. Not investment advice.</p>
        <p>Past performance does not guarantee future results.</p>
      </div>
    </div>
  )
}

interface MetricCardProps {
  title: string
  value?: string
}

function MetricCard({ title, value }: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{value || 'N/A'}</p>
      </CardContent>
    </Card>
  )
}
