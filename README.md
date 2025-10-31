Smart Research Trader (AI Stock Research + Predictive Signals)

One platform for fundamentals (Screener-style), technicals, news sentiment, and AI-driven long/short signals.
Built with FastAPI, LightGBM, and React.

Disclaimer: For research and education only. Not investment advice. Check local regulations (e.g., SEBI) before using signals for trading.

✨ Features

10y historical data (prices) with splits/dividends handling

Fundamental scoring: ROE/ROCE, growth, leverage, valuation, promoter/pledge, etc.

News sentiment with FinBERT + burstiness

Technical factors: trend, momentum, volatility, volume

Composite scores: Quality, Valuation, Momentum, Sentiment

AI model: LightGBM forecasting next-day return + uncertainty

Backtesting: costs, turnover, Sharpe, drawdown

API + UI: ranked LONG/SHORT signals with explainability (SHAP)

🧱 Architecture
backend (FastAPI, Celery/RQ, PostgreSQL)
frontend (React+Vite+TS, Tailwind, shadcn/ui, Recharts)
infra (Docker, docker-compose, GitHub Actions)
