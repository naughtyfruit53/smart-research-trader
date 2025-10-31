import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchStock, fetchExplanation, StockSnapshot, ExplainResponse } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/Card'
import { PriceWithSignals } from '@/components/Charts/PriceWithSignals'
import { ShapBar } from '@/components/Explain/ShapBar'

export default function StockPage() {
  const { ticker } = useParams<{ ticker: string }>()
  const [stock, setStock] = useState<StockSnapshot | null>(null)
  const [explain, setExplain] = useState<ExplainResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [loadingExplain, setLoadingExplain] = useState(false)

  useEffect(() => {
    const loadStock = async () => {
      if (!ticker) return

      try {
        setLoading(true)
        const data = await fetchStock(ticker)
        setStock(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch stock data')
        setStock(null)
      } finally {
        setLoading(false)
      }
    }

    loadStock()
  }, [ticker])

  const handleLoadExplanation = async () => {
    if (!ticker || !stock?.prediction?.dt) return

    try {
      setLoadingExplain(true)
      const data = await fetchExplanation(ticker, stock.prediction.dt)
      setExplain(data)
    } catch (err) {
      console.error('Failed to load explanation:', err)
    } finally {
      setLoadingExplain(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Loading stock data...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !stock) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-destructive">
              <p className="font-semibold">Error:</p>
              <p>{error || 'Stock not found'}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{ticker}</h1>
        <p className="text-muted-foreground mt-2">Comprehensive stock analysis</p>
      </div>

      {/* Fundamentals */}
      <Card>
        <CardHeader>
          <CardTitle>Fundamentals</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricItem label="Market Cap" value={stock.fundamentals.market_cap?.toFixed(2)} />
            <MetricItem label="P/E Ratio" value={stock.fundamentals.pe_ratio?.toFixed(2)} />
            <MetricItem label="P/B Ratio" value={stock.fundamentals.pb_ratio?.toFixed(2)} />
            <MetricItem label="ROE" value={stock.fundamentals.roe ? `${(stock.fundamentals.roe * 100).toFixed(2)}%` : undefined} />
            <MetricItem label="ROCE" value={stock.fundamentals.roce ? `${(stock.fundamentals.roce * 100).toFixed(2)}%` : undefined} />
            <MetricItem label="Debt/Equity" value={stock.fundamentals.debt_to_equity?.toFixed(2)} />
            <MetricItem label="Revenue Growth" value={stock.fundamentals.revenue_growth ? `${(stock.fundamentals.revenue_growth * 100).toFixed(2)}%` : undefined} />
            <MetricItem label="EPS Growth" value={stock.fundamentals.eps_growth ? `${(stock.fundamentals.eps_growth * 100).toFixed(2)}%` : undefined} />
          </div>
        </CardContent>
      </Card>

      {/* Technicals */}
      <Card>
        <CardHeader>
          <CardTitle>Technicals</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricItem label="Price" value={stock.technicals.price?.toFixed(2)} prefix="₹" />
            <MetricItem label="RSI-14" value={stock.technicals.rsi_14?.toFixed(2)} />
            <MetricItem label="SMA-20" value={stock.technicals.sma_20?.toFixed(2)} prefix="₹" />
            <MetricItem label="SMA-50" value={stock.technicals.sma_50?.toFixed(2)} prefix="₹" />
            <MetricItem label="SMA-200" value={stock.technicals.sma_200?.toFixed(2)} prefix="₹" />
            <MetricItem label="Momentum-20" value={stock.technicals.momentum_20 ? `${(stock.technicals.momentum_20 * 100).toFixed(2)}%` : undefined} />
            <MetricItem label="Momentum-60" value={stock.technicals.momentum_60 ? `${(stock.technicals.momentum_60 * 100).toFixed(2)}%` : undefined} />
            <MetricItem label="RV-20" value={stock.technicals.rv_20?.toFixed(4)} />
          </div>
        </CardContent>
      </Card>

      {/* Sentiment */}
      <Card>
        <CardHeader>
          <CardTitle>Sentiment</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricItem label="Mean Compound" value={stock.sentiment.mean_compound?.toFixed(3)} />
            <MetricItem label="Burst 3D" value={stock.sentiment.burst_3d?.toFixed(3)} />
            <MetricItem label="Burst 7D" value={stock.sentiment.burst_7d?.toFixed(3)} />
            <MetricItem label="Articles (7D)" value={stock.sentiment.article_count_7d?.toString()} />
          </div>
        </CardContent>
      </Card>

      {/* Prediction & Scores */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Latest Prediction</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <MetricItem label="Signal" value={stock.prediction.signal} />
              <MetricItem label="Expected Return" value={stock.prediction.yhat ? `${(stock.prediction.yhat * 100).toFixed(2)}%` : undefined} />
              <MetricItem label="Uncertainty" value={stock.prediction.yhat_std?.toFixed(4)} />
              <MetricItem label="Date" value={stock.prediction.dt} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Scores</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <MetricItem label="Quality" value={stock.scores.quality_score?.toFixed(3)} />
              <MetricItem label="Valuation" value={stock.scores.valuation_score?.toFixed(3)} />
              <MetricItem label="Momentum" value={stock.scores.momentum_score?.toFixed(3)} />
              <MetricItem label="Sentiment" value={stock.scores.sentiment_score?.toFixed(3)} />
              <MetricItem label="Composite" value={stock.scores.composite_score?.toFixed(3)} />
              <MetricItem label="Risk-Adjusted" value={stock.scores.risk_adjusted_score?.toFixed(3)} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Price Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Price History (200 days)</CardTitle>
        </CardHeader>
        <CardContent>
          <PriceWithSignals priceSeries={stock.price_series} />
        </CardContent>
      </Card>

      {/* SHAP Explanation */}
      <Card>
        <CardHeader>
          <CardTitle>Feature Importance (SHAP)</CardTitle>
        </CardHeader>
        <CardContent>
          {!explain && (
            <div className="text-center py-8">
              <button
                onClick={handleLoadExplanation}
                disabled={loadingExplain || !stock.prediction.dt}
                className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {loadingExplain ? 'Loading...' : 'Load Explanation'}
              </button>
              <p className="text-sm text-muted-foreground mt-2">
                Click to compute SHAP values for this prediction
              </p>
            </div>
          )}
          {explain && <ShapBar contributions={explain.contributions} />}
        </CardContent>
      </Card>

      <div className="text-sm text-muted-foreground text-center">
        <p>⚠️ For research and education only. Not investment advice.</p>
      </div>
    </div>
  )
}

interface MetricItemProps {
  label: string
  value?: string
  prefix?: string
}

function MetricItem({ label, value, prefix = '' }: MetricItemProps) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">
        {value !== undefined ? `${prefix}${value}` : 'N/A'}
      </p>
    </div>
  )
}
