# Quick Start Guide: Data Pipeline

## 🚀 5-Minute Setup

### 1. Clone and Start Services
```bash
git clone <repo-url>
cd smart-research-trader
docker compose up -d
```

### 2. Run Migrations
```bash
cd backend
alembic upgrade head
```

### 3. Validate Setup
```bash
python validate_pipeline.py
```

### 4. Import Sample Data
```bash
python -m src.data.etl.fetch_fundamentals sample_fundamentals.csv
```

## ✅ What You Get

- ✅ **Celery Worker** - Running and ready for tasks
- ✅ **Celery Beat** - Scheduled jobs configured
- ✅ **Price Adapter** - Yahoo Finance integration (requires `pip install yfinance`)
- ✅ **Fundamentals Import** - CSV-based ingestion
- ✅ **News Adapter** - RSS feed integration (requires `pip install feedparser`)
- ✅ **Sentiment Analysis** - FinBERT fallback (optional: `pip install torch transformers`)

## 📅 Scheduled Tasks

Once running, these tasks execute automatically:

| Task | Schedule | Description |
|------|----------|-------------|
| `update_prices_daily` | 22:00 UTC | Fetch last 7 days of prices |
| `update_news_daily` | 23:00 UTC | Fetch last 24 hours of news |
| `update_fundamentals_weekly` | Mon 01:00 UTC | Import fundamentals CSV |

## 🔍 Monitor

```bash
# View worker logs
docker compose logs -f worker

# View beat scheduler logs
docker compose logs -f beat

# View all services
docker compose logs -f
```

## 🛠️ Manual ETL Jobs

Run these anytime to manually fetch data:

```bash
# Install optional dependencies first
pip install yfinance feedparser

# Fetch historical prices
python -m src.data.etl.fetch_prices

# Fetch latest news
python -m src.data.etl.fetch_news

# Import fundamentals
python -m src.data.etl.fetch_fundamentals /path/to/data.csv
```

## 🧪 Test

```bash
cd backend
SKIP_NETWORK_IN_TESTS=true ENABLE_FINBERT=false pytest -v
```

Expected: **40 passed, 1 skipped**

## 📚 Documentation

- **README_DATA_PIPELINE.md** - Complete technical guide
- **IMPLEMENTATION_SUMMARY.md** - Architecture overview
- **sample_fundamentals.csv** - Example data format

## ⚙️ Configuration

Key environment variables (set in `docker-compose.yml` or `.env`):

```bash
# Required
DATABASE_URL=postgresql://trader:trader_dev_pass@postgres:5432/smart_trader
CELERY_BROKER_URL=redis://redis:6379/0
TICKERS=RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS

# Optional
ENABLE_FINBERT=false           # Enable FinBERT (requires torch)
PRICE_PROVIDER=yf              # yf or nse
NEWS_PROVIDER=rss              # rss or gdelt
```

## 🐛 Troubleshooting

**Issue**: `yfinance not found`  
**Solution**: `pip install yfinance`

**Issue**: `Celery can't connect to Redis`  
**Solution**: `docker compose up -d redis`

**Issue**: `Database connection refused`  
**Solution**: `docker compose up -d postgres`

**Issue**: Tests failing  
**Solution**: Ensure Postgres is running, then run with env flags:
```bash
SKIP_NETWORK_IN_TESTS=true ENABLE_FINBERT=false pytest
```

## 🎯 Next Steps

1. ✅ Validate setup with `python validate_pipeline.py`
2. ✅ Run tests to ensure everything works
3. ✅ Import sample fundamentals
4. ✅ Check Celery logs to see scheduled tasks
5. ✅ Customize tickers in `docker-compose.yml` or `.env`
6. ✅ Add your own fundamentals CSV
7. ✅ Monitor first scheduled task execution

## 💡 Pro Tips

- Start with the validation script to catch issues early
- Use `docker compose logs -f worker` to watch tasks execute
- The first price fetch may take a while (fetching 10 years of data)
- Keep `ENABLE_FINBERT=false` unless you need sentiment analysis
- Idempotent design means you can re-run jobs safely

## 📞 Need Help?

See **README_DATA_PIPELINE.md** for:
- Detailed architecture
- API documentation
- Advanced configuration
- Performance tuning
- Adding custom adapters
