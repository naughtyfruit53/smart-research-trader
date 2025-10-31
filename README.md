# Smart Research Trader

AI-powered stock research and trading signals platform combining fundamentals, technicals, news sentiment, and machine learning.

**⚠️ Disclaimer: For research and education only. Not investment advice. Check local regulations before trading.**

## 📋 Overview

Smart Research Trader is a comprehensive platform for:
- Fundamental analysis (ROE/ROCE, growth, leverage, valuation)
- Technical indicators (trend, momentum, volatility, volume)
- News sentiment analysis with FinBERT
- AI-driven long/short signals using LightGBM
- Backtesting with transaction costs and risk metrics
- Interactive UI with signal explainability (SHAP)

## 🏗️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database
- **Redis** - Caching and task queue
- **Celery** - Background task processing (planned)
- **uvicorn** - ASGI server

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **shadcn/ui** - Component library

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **GitHub Actions** - CI/CD pipeline
- **nginx** - Production serving (planned)

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐             │
│  │ Signals  │  │  Stock   │  │  Backtests   │             │
│  │  Page    │  │  Page    │  │    Page      │             │
│  └──────────┘  └──────────┘  └──────────────┘             │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────────────────────┐
│                  Backend (FastAPI)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐             │
│  │ Signals  │  │  Stock   │  │  Backtests   │             │
│  │   API    │  │   API    │  │    API       │             │
│  └──────────┘  └──────────┘  └──────────────┘             │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│             Data Pipeline & ML Engine                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐             │
│  │   ETL    │  │ Features │  │   ML Train   │             │
│  │ (Prices) │  │  Engine  │  │  & Inference │             │
│  └──────────┘  └──────────┘  └──────────────┘             │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│            Database (PostgreSQL + Redis)                    │
│  • Prices  • Fundamentals  • Features  • Predictions       │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (v20.10+)
- Git
- 8GB RAM minimum (16GB recommended)
- 10GB free disk space

### Option 1: Quick Demo with Docker Compose

1. Clone the repository:
```bash
git clone https://github.com/naughtyfruit53/smart-research-trader.git
cd smart-research-trader
```

2. Start all services:
```bash
docker compose up --build
```

3. Wait for services to be healthy (2-3 minutes on first run)

4. Seed demo data (in a new terminal):
```bash
# Wait for backend to be ready
curl http://localhost:8000/health

# Run the seed script to populate data
./infra/scripts/seed_demo.sh
```

5. Access the application:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Option 2: Development Setup (Local)

For local development without Docker:

#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install ruff black mypy pytest

# Set up database (requires PostgreSQL and Redis running)
export DATABASE_URL="postgresql://trader:trader_dev_pass@localhost:5432/smart_trader"
export CELERY_BROKER_URL="redis://localhost:6379/0"

# Run migrations
alembic upgrade head

# Start the backend
uvicorn src.api.main:app --reload
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

#### Seed Demo Data (Local)
```bash
cd backend
source venv/bin/activate

# Set environment variables
export DATABASE_URL="postgresql://trader:trader_dev_pass@localhost:5432/smart_trader"
export TICKERS="RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
export PRICE_PROVIDER="yf"
export ENABLE_FINBERT="false"

# Run the seed script
../infra/scripts/seed_demo.sh
```

### Local Development (without Docker)

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install ruff black mypy pytest
uvicorn src.api.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Type Check
```bash
cd frontend
npm run type-check
npm run build
```

### Linting
```bash
# Backend
cd backend
ruff check .
black --check .
mypy src tests

# Frontend
cd frontend
npm run lint
```

## 📁 Project Structure

```
smart-research-trader/
├── backend/
│   ├── src/
│   │   ├── api/                # FastAPI routes and schemas
│   │   │   ├── routes/         # API endpoints
│   │   │   │   ├── signals.py  # Trading signals API
│   │   │   │   ├── stocks.py   # Stock details API
│   │   │   │   ├── backtests.py # Backtest results API
│   │   │   │   └── explain.py  # SHAP explainability API
│   │   │   └── schemas/        # Pydantic models
│   │   ├── core/               # Config, logging, utilities
│   │   ├── data/               # Data pipeline
│   │   │   ├── adapters/       # External data sources
│   │   │   ├── etl/            # ETL scripts
│   │   │   └── features/       # Feature engineering
│   │   ├── db/                 # Database models and repositories
│   │   └── ml/                 # ML training, inference, backtesting
│   ├── tests/                  # Backend tests
│   ├── alembic/                # Database migrations
│   ├── models/                 # Trained model artifacts
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   │   ├── Charts/         # Recharts visualizations
│   │   │   ├── Explain/        # SHAP explanations
│   │   │   ├── SignalsTable.tsx
│   │   │   ├── Filters.tsx
│   │   │   └── Navigation.tsx
│   │   ├── pages/              # Page components
│   │   │   ├── SignalsPage.tsx
│   │   │   ├── StockPage.tsx
│   │   │   ├── BacktestsPage.tsx
│   │   │   └── HomePage.tsx
│   │   ├── lib/                # Utilities and API client
│   │   │   ├── api.ts          # Typed API fetchers
│   │   │   └── utils.ts        # Helper functions
│   │   └── test/               # Frontend tests
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── vitest.config.ts
├── infra/
│   └── scripts/
│       ├── seed_demo.sh        # Demo data population
│       └── dev_up.sh           # Development startup
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD pipeline
├── docker-compose.yml
└── README.md
```

## 🎬 Seed Demo Walkthrough

The `seed_demo.sh` script orchestrates the full data pipeline for demonstration purposes. Here's what it does:

### Step-by-Step Process

1. **Fetch Historical Prices** (~10 years of data)
   - Uses yfinance to download OHLCV data
   - Handles splits and dividends
   - Stores in `prices` table

2. **Import Fundamentals** (optional, requires CSV)
   - Imports fundamental metrics (ROE, ROCE, P/E, etc.)
   - Stores in `fundamentals` table with as-of dates
   - Sample CSV format provided in `backend/sample_fundamentals.csv`

3. **Fetch News** (RSS-based sentiment)
   - Collects recent news articles (~90 days)
   - Computes sentiment scores
   - Stores in `news` table

4. **Compute Features** (Technical + Fundamental + Sentiment)
   - Technical: RSI, SMA, momentum, volatility
   - Fundamental: As-of join with latest metrics
   - Sentiment: Aggregated scores from news
   - Stores in `features` table

5. **Compute Labels** (Forward returns)
   - Calculates 1-day forward returns
   - Updates `features` table with labels
   - Required for training

6. **Train ML Model** (LightGBM)
   - Walk-forward cross-validation
   - 3 folds with 2-day embargo
   - Saves model to `backend/models/`

7. **Run Inference** (Latest predictions)
   - Loads trained model
   - Predicts for latest date
   - Stores in `predictions` table

8. **Run Backtest** (Performance metrics)
   - Simulates long/short strategy
   - Computes Sharpe, drawdown, win rate
   - Stores in `backtests` table

### Usage Examples

```bash
# Basic usage (NIFTY large caps)
./infra/scripts/seed_demo.sh

# With custom fundamentals CSV
./infra/scripts/seed_demo.sh /path/to/fundamentals.csv

# With custom tickers (environment variable)
TICKERS="AAPL,MSFT,GOOGL,AMZN" ./infra/scripts/seed_demo.sh

# Re-run safely (idempotent)
./infra/scripts/seed_demo.sh  # Safe to run multiple times
```

### Expected Runtime
- **First run**: 15-30 minutes (depends on data volume and network speed)
- **Subsequent runs**: 5-10 minutes (incremental updates)

### Troubleshooting

**Issue**: Prices not downloading
- **Solution**: Check network connectivity, verify tickers are valid

**Issue**: Model training fails
- **Solution**: Ensure sufficient data (at least 200 days), check labels are computed

**Issue**: Database connection error
- **Solution**: Verify PostgreSQL is running, check DATABASE_URL

## 🔌 API Endpoints

### Health Check
```
GET /health
Response: {"status": "ok", "version": "0.1.0"}
```

### Trading Signals
```
GET /signals/daily?horizon=1d&top=50&min_confidence=0.5
Response: {
  "signals": [
    {
      "ticker": "RELIANCE.NS",
      "signal": "LONG",
      "exp_return": 0.0234,
      "confidence": 0.87,
      "quality_score": 0.75,
      "valuation_score": 0.68,
      "momentum_score": 0.82,
      "sentiment_score": 0.71,
      "composite_score": 0.74,
      "risk_adjusted_score": 1.42,
      "dt": "2024-01-15"
    }
  ],
  "count": 50,
  "horizon": "1d"
}
```

### Stock Details
```
GET /stocks/{ticker}
Response: {
  "ticker": "RELIANCE.NS",
  "fundamentals": {...},
  "technicals": {...},
  "sentiment": {...},
  "prediction": {...},
  "scores": {...},
  "price_series": {...}
}
```

### Backtest Results
```
GET /backtests/latest
Response: {
  "run_id": "uuid",
  "metrics": {
    "total_return": 0.45,
    "sharpe_ratio": 1.82,
    "max_drawdown": -0.12,
    "win_rate": 0.58
  },
  "equity_curve": [...]
}
```

### SHAP Explanations
```
GET /explain/{ticker}?dt=2024-01-15
Response: {
  "ticker": "RELIANCE.NS",
  "dt": "2024-01-15",
  "yhat": 0.0234,
  "base_value": 0.01,
  "contributions": [
    {"feature": "momentum_20", "value": 0.045, "contribution": 0.012},
    {"feature": "rsi_14", "value": 68.5, "contribution": 0.008}
  ]
}
```

## 🖼️ Screenshots

### Signals Page
![Signals Page](docs/screenshots/signals-page.png)
*Trading signals with filtering and sorting*

### Stock Details Page
![Stock Page](docs/screenshots/stock-page.png)
*Comprehensive stock analysis with fundamentals, technicals, and SHAP*

### Backtests Page
![Backtests Page](docs/screenshots/backtests-page.png)
*Backtest results with equity curve and performance metrics*

> **Note**: Screenshots will be added after UI verification

## 🔧 Configuration

### Environment Variables

Backend (`.env` in `backend/` or via docker-compose):
```bash
# App settings
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://trader:trader_dev_pass@postgres:5432/smart_trader

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Data sources
PRICE_PROVIDER=yf              # yf (yfinance) or nse
NEWS_PROVIDER=rss              # rss or newsapi
ENABLE_FINBERT=false           # Enable FinBERT for sentiment (slow)

# Tickers
TICKERS=RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

Frontend (environment variable):
```bash
VITE_API_BASE=http://localhost:8000
```

## 🚦 CI/CD

The project uses GitHub Actions for continuous integration:
1. **Python Lint & Test** - Runs ruff, black, mypy, and pytest
2. **Frontend TypeCheck & Build** - Validates TypeScript and builds
3. **Docker Build** - Builds backend and frontend images

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## ⚠️ Important Disclaimers

- This software is for **research and educational purposes only**
- **Not financial or investment advice**
- Past performance does not guarantee future results
- Trading involves substantial risk of loss
- Consult with licensed financial advisors before making investment decisions
- Check and comply with local regulations (e.g., SEBI in India)

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure CI passes
5. Submit a pull request

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review API docs at `/docs` endpoint
