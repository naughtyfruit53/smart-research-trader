/**
 * API client for Smart Research Trader backend.
 * Provides typed fetchers for all endpoints.
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

/**
 * Base fetch wrapper with error handling
 */
async function apiFetch<T>(endpoint: string): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  const response = await fetch(url)
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }
  
  return response.json()
}

// ===== Health =====

export interface HealthResponse {
  status: string
  version: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health')
}

// ===== Signals =====

export interface SignalItem {
  ticker: string
  signal: 'LONG' | 'SHORT' | 'NEUTRAL'
  exp_return: number
  confidence: number
  quality_score?: number
  valuation_score?: number
  momentum_score?: number
  sentiment_score?: number
  composite_score?: number
  risk_adjusted_score: number
  dt: string
}

export interface SignalsResponse {
  signals: SignalItem[]
  count: number
  horizon: string
}

export interface SignalsParams {
  horizon?: string
  top?: number
  sector?: string
  min_liquidity?: number
  min_confidence?: number
  exclude_earnings?: boolean
}

export async function fetchSignals(params?: SignalsParams): Promise<SignalsResponse> {
  const searchParams = new URLSearchParams()
  
  if (params?.horizon) searchParams.append('horizon', params.horizon)
  if (params?.top !== undefined) searchParams.append('top', params.top.toString())
  if (params?.sector) searchParams.append('sector', params.sector)
  if (params?.min_liquidity !== undefined) searchParams.append('min_liquidity', params.min_liquidity.toString())
  if (params?.min_confidence !== undefined) searchParams.append('min_confidence', params.min_confidence.toString())
  if (params?.exclude_earnings !== undefined) searchParams.append('exclude_earnings', params.exclude_earnings.toString())
  
  const query = searchParams.toString()
  return apiFetch<SignalsResponse>(`/signals/daily${query ? `?${query}` : ''}`)
}

// ===== Stocks =====

export interface FundamentalsSnapshot {
  market_cap?: number
  pe_ratio?: number
  pb_ratio?: number
  roe?: number
  roce?: number
  debt_to_equity?: number
  revenue_growth?: number
  eps_growth?: number
}

export interface TechnicalsSnapshot {
  rsi_14?: number
  sma_20?: number
  sma_50?: number
  sma_200?: number
  momentum_20?: number
  momentum_60?: number
  rv_20?: number
  price?: number
}

export interface SentimentSnapshot {
  mean_compound?: number
  burst_3d?: number
  burst_7d?: number
  article_count_7d?: number
}

export interface PredictionSnapshot {
  yhat?: number
  yhat_std?: number
  dt?: string
  signal?: string
}

export interface ScoresSnapshot {
  quality_score?: number
  valuation_score?: number
  momentum_score?: number
  sentiment_score?: number
  composite_score?: number
  risk_adjusted_score?: number
}

export interface PriceSeries {
  dates: string[]
  closes: number[]
}

export interface StockSnapshot {
  ticker: string
  fundamentals: FundamentalsSnapshot
  technicals: TechnicalsSnapshot
  sentiment: SentimentSnapshot
  prediction: PredictionSnapshot
  scores: ScoresSnapshot
  price_series: PriceSeries
}

export async function fetchStock(ticker: string): Promise<StockSnapshot> {
  return apiFetch<StockSnapshot>(`/stocks/${ticker}`)
}

// ===== Backtests =====

export interface BacktestMetrics {
  total_return?: number
  annual_return?: number
  sharpe_ratio?: number
  max_drawdown?: number
  win_rate?: number
  num_trades?: number
  start_date?: string
  end_date?: string
}

export interface EquityPoint {
  date: string
  equity: number
  drawdown?: number
}

export interface BacktestResponse {
  run_id: string
  started_at: string
  finished_at: string
  params: Record<string, unknown>
  metrics: BacktestMetrics
  equity_curve: EquityPoint[]
}

export async function fetchLatestBacktest(): Promise<BacktestResponse> {
  return apiFetch<BacktestResponse>('/backtests/latest')
}

// ===== Explain =====

export interface FeatureContribution {
  feature: string
  value: number
  contribution: number
}

export interface ExplainResponse {
  ticker: string
  dt: string
  yhat: number
  base_value: number
  contributions: FeatureContribution[]
}

export async function fetchExplanation(ticker: string, dt: string): Promise<ExplainResponse> {
  return apiFetch<ExplainResponse>(`/explain/${ticker}?dt=${dt}`)
}
