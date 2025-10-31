# Data Pipeline Documentation

This document describes the data ingestion and transformation pipelines for the Smart Research Trader platform.

## Overview

The data pipeline consists of:
- **Adapters**: Pluggable data sources for prices, fundamentals, and news
- **ETL Modules**: Extract, Transform, Load scripts with idempotent upserts
- **Celery Tasks**: Scheduled jobs for periodic data updates
- **Sentiment Analysis**: FinBERT-based sentiment scoring for news

## Architecture

```
backend/src/data/
├── adapters/          # Data source adapters
│   ├── prices_yf.py   # Yahoo Finance price adapter
│   ├── prices_nse.py  # NSE stub (future)
│   ├── fund_screener.py  # Fundamentals CSV importer
│   └── news_gdelt.py  # RSS/GDELT news adapter
├── etl/               # ETL pipelines
│   ├── normalize.py   # Data normalization utilities
│   ├── fetch_prices.py       # Price data ingestion
│   ├── fetch_fundamentals.py # Fundamentals ingestion
│   ├── fetch_news.py         # News ingestion + sentiment
│   ├── corporate_actions.py  # Splits/dividends handling
│   └── tasks.py       # Celery scheduled tasks
└── features/
    └── sentiment_model.py  # FinBERT sentiment analysis
```

## Environment Variables

### Required Variables
```bash
# Database
DATABASE_URL=postgresql://trader:trader_dev_pass@localhost:5432/smart_trader

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Data Providers
PRICE_PROVIDER=yf        # yf (Yahoo Finance) or nse (future)
NEWS_PROVIDER=rss        # rss or gdelt (future)
FUND_CSV_PATH=/path/to/fundamentals.csv

# Tickers (comma-separated)
TICKERS=RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS
```

### Optional Variables
```bash
# Feature Flags
ENABLE_FINBERT=false     # Enable FinBERT sentiment analysis (requires torch+transformers)
SKIP_NETWORK_IN_TESTS=true  # Skip network calls in tests

# Batch Sizes
PRICE_FETCH_BATCH_SIZE=5
NEWS_FETCH_BATCH_SIZE=10
FUNDAMENTAL_FETCH_BATCH_SIZE=10
```

## Installation

### Base Requirements
```bash
pip install -r requirements.txt
```

### Optional: FinBERT Support
To enable FinBERT sentiment analysis:
```bash
pip install torch transformers
export ENABLE_FINBERT=true
```

## Running ETL Jobs

### 1. Fetch Price Data
Fetches historical OHLCV data from Yahoo Finance:
```bash
cd backend
python -m src.data.etl.fetch_prices
```

This will:
- Fetch ~10 years of historical prices
- Normalize data to schema format
- Upsert to `prices` table (idempotent)
- Handle corporate actions via adjusted close

### 2. Import Fundamentals
Import fundamentals from CSV:
```bash
python -m src.data.etl.fetch_fundamentals sample_fundamentals.csv
```

CSV Format:
```csv
Ticker,As Of,P/E,P/B,EV/EBITDA,ROE,ROCE,D/E,...
RELIANCE.NS,2024-01-01,27.5,2.8,15.2,0.12,0.09,0.55,...
```

### 3. Fetch News with Sentiment
Fetch news articles and perform sentiment analysis:
```bash
python -m src.data.etl.fetch_news
```

## Celery Scheduled Tasks

### Starting Workers
```bash
# Start Celery worker
celery -A src.core.celery_app.celery_app worker -l info

# Start Celery beat (scheduler)
celery -A src.core.celery_app.celery_app beat -l info
```

### Docker Compose
The docker-compose.yml includes worker and beat services:
```bash
docker compose up -d worker beat
```

### Task Schedules
- **update_prices_daily**: Runs daily at 10 PM UTC
- **update_news_daily**: Runs daily at 11 PM UTC  
- **update_fundamentals_weekly**: Runs Mondays at 1 AM UTC

## Adapter Interface

### Price Adapter
```python
class PriceAdapter:
    def fetch_prices(
        self, 
        ticker: str, 
        start_date: datetime | None, 
        end_date: datetime | None
    ) -> pd.DataFrame:
        """
        Returns DataFrame with columns:
        [ticker, dt, open, high, low, close, volume, adj_close]
        """
```

### News Adapter
```python
class NewsAdapter:
    def fetch_news(
        self, 
        tickers: list[str], 
        start_date: datetime | None, 
        end_date: datetime | None
    ) -> pd.DataFrame:
        """
        Returns DataFrame with columns:
        [dt, ticker, source, headline, summary, url]
        """
```

### Fundamentals Adapter
```python
class FundamentalsAdapter:
    def parse_csv(self, csv_path: str) -> pd.DataFrame:
        """
        Returns DataFrame with columns:
        [ticker, asof, pe, pb, ev_ebitda, roe, roce, de_ratio, ...]
        """
```

## Data Schema

### Prices Table
```sql
CREATE TABLE prices (
    ticker TEXT PRIMARY KEY,
    dt DATE PRIMARY KEY,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    adj_close NUMERIC
);
```

### Fundamentals Table
```sql
CREATE TABLE fundamentals (
    ticker TEXT PRIMARY KEY,
    asof DATE PRIMARY KEY,
    pe FLOAT,
    pb FLOAT,
    ev_ebitda FLOAT,
    roe FLOAT,
    roce FLOAT,
    de_ratio FLOAT,
    eps_g3y FLOAT,
    rev_g3y FLOAT,
    profit_g3y FLOAT,
    opm FLOAT,
    npm FLOAT,
    div_yield FLOAT,
    promoter_hold FLOAT,
    pledged_pct FLOAT
);
```

### News Table
```sql
CREATE TABLE news (
    id BIGSERIAL PRIMARY KEY,
    dt TIMESTAMP WITH TIME ZONE,
    ticker TEXT,
    source TEXT,
    headline TEXT,
    summary TEXT,
    url TEXT,
    sent_pos FLOAT,
    sent_neg FLOAT,
    sent_comp FLOAT
);
```

## Idempotency

All ETL jobs are idempotent using PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE`:

```python
stmt = insert(Price).values(records)
stmt = stmt.on_conflict_do_update(
    index_elements=["ticker", "dt"],
    set_={
        "open": stmt.excluded.open,
        "high": stmt.excluded.high,
        # ... other fields
    }
)
```

Running the same job multiple times will:
- Not create duplicates
- Update existing records with latest data
- Maintain primary key constraints

## Testing

### Run All Tests
```bash
cd backend
SKIP_NETWORK_IN_TESTS=true ENABLE_FINBERT=false pytest
```

### Test Coverage
- `test_adapters_prices_yf.py`: Tests price adapter with mocked yfinance
- `test_fund_csv_import.py`: Tests CSV import and idempotency
- `test_news_sentiment.py`: Tests news fetch and sentiment (with/without FinBERT)
- `test_etl_idempotent.py`: Tests idempotent upserts

## CI/CD

The GitHub Actions CI workflow:
1. Sets up Postgres and Redis services
2. Installs dependencies
3. Runs linting (ruff, black, mypy)
4. Runs tests with `SKIP_NETWORK_IN_TESTS=true`

No external API calls are made during CI to keep builds fast and reliable.

## Adding New Adapters

### Example: Adding BSE Price Adapter

1. Create adapter file:
```python
# backend/src/data/adapters/prices_bse.py
class BSEPriceAdapter:
    def fetch_prices(self, ticker, start_date, end_date):
        # Implementation
        return df  # With required columns
```

2. Update config:
```python
# backend/src/core/config.py
PRICE_PROVIDER: str = "bse"  # Add new option
```

3. Update factory:
```python
# backend/src/data/etl/fetch_prices.py
def get_price_adapter():
    if settings.PRICE_PROVIDER == "bse":
        return BSEPriceAdapter()
    # ... existing providers
```

## Troubleshooting

### Issue: yfinance not installed
```
ImportError: yfinance package not installed
```
Solution: `pip install yfinance`

### Issue: Celery can't connect to Redis
```
ConnectionError: Error 111 connecting to localhost:6379
```
Solution: Start Redis with `docker compose up -d redis` or `redis-server`

### Issue: FinBERT model download timeout
```
Error: Failed to load FinBERT model
```
Solution: Set `ENABLE_FINBERT=false` or ensure stable internet connection for first run

### Issue: Database connection refused
```
OperationalError: could not connect to server
```
Solution: Start Postgres with `docker compose up -d postgres`

## Performance Considerations

- **Batch Sizes**: Adjust `*_FETCH_BATCH_SIZE` variables for optimal performance
- **Retry Logic**: Price adapter has exponential backoff (max 3 retries)
- **Rate Limiting**: Respect API rate limits; add delays if needed
- **Database Indexes**: Composite indexes on (ticker, dt) for fast queries

## Next Steps

1. **Add NSE/BSE Adapters**: Implement real Indian exchange adapters
2. **GDELT Integration**: Replace RSS with GDELT for comprehensive news
3. **Real-time Streaming**: Add WebSocket support for live price updates
4. **Data Quality Checks**: Add validation and anomaly detection
5. **Monitoring**: Integrate with monitoring tools (Prometheus, Grafana)

## References

- [Celery Documentation](https://docs.celeryq.dev/)
- [yfinance Documentation](https://pypi.org/project/yfinance/)
- [FinBERT Paper](https://arxiv.org/abs/1908.10063)
- [SQLAlchemy Upsert Documentation](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict-upsert)
