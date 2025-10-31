# Database Layer Documentation

This document describes the database layer implementation using SQLAlchemy 2.0 and Alembic migrations.

## Overview

The database layer provides:
- **SQLAlchemy 2.0** ORM with type-safe models
- **Alembic** migrations for schema management
- **Repository pattern** for common queries
- **FastAPI integration** with dependency injection
- **Health checks** for monitoring

## Database Schema

### Tables

1. **prices** - Historical OHLCV price data
   - Primary Key: (ticker, dt)
   - Columns: ticker, dt, open, high, low, close, volume, adj_close
   - Indexes: ticker, dt

2. **news** - News articles with sentiment analysis
   - Primary Key: id (bigserial)
   - Columns: id, dt, ticker, source, headline, summary, url, sent_pos, sent_neg, sent_comp
   - Indexes: ticker, dt, (ticker, dt)

3. **fundamentals** - Fundamental analysis metrics
   - Primary Key: (ticker, asof)
   - Columns: ticker, asof, pe, pb, ev_ebitda, roe, roce, de_ratio, eps_g3y, rev_g3y, profit_g3y, opm, npm, div_yield, promoter_hold, pledged_pct
   - Indexes: ticker, asof

4. **features** - Engineered features for ML models
   - Primary Key: (ticker, dt)
   - Columns: ticker, dt, features_json (JSONB), label_ret_1d
   - Indexes: ticker, dt

5. **preds** - Model predictions
   - Primary Key: (ticker, dt, horizon)
   - Columns: ticker, dt, horizon, yhat, yhat_std, prob_up
   - Indexes: ticker, dt, (ticker, dt)

6. **backtests** - Backtest results
   - Primary Key: run_id (UUID)
   - Columns: run_id, started_at, finished_at, params (JSONB), metrics (JSONB)
   - Indexes: started_at

## Configuration

### Environment Variables

Set `DATABASE_URL` to connect to your PostgreSQL database:

```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

Default for local development (if not set):
```
postgresql://trader:trader_dev_pass@localhost:5432/smart_trader
```

### Docker Compose

The docker-compose.yml includes PostgreSQL service configuration:

```bash
# Start PostgreSQL
docker compose up postgres -d

# Start backend with migrations
docker compose up backend
```

## Alembic Migrations

### Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration (auto-generate from model changes)
alembic revision --autogenerate -m "Add new column"

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# Check current migration version
alembic current

# View migration history
alembic history
```

### Migration Files

Migrations are stored in `alembic/versions/`. Each migration has:
- `upgrade()` - Apply changes
- `downgrade()` - Revert changes

## Usage Examples

### Using the Database Session

```python
from src.db import get_db, Price

# In FastAPI route
@app.get("/prices/{ticker}")
def get_prices(ticker: str, db: Session = Depends(get_db)):
    from src.db.repo import PriceRepository
    prices = PriceRepository.get_latest_by_ticker(db, ticker, limit=100)
    return prices
```

### Using Context Manager

```python
from src.db.session import get_session
from src.db.models import Backtest

with get_session() as db:
    backtests = db.query(Backtest).limit(10).all()
    for bt in backtests:
        print(bt.params)
```

### Using Repositories

```python
from src.db.session import get_session
from src.db.repo import PriceRepository, BacktestRepository

with get_session() as db:
    # Get latest prices for a ticker
    prices = PriceRepository.get_latest_by_ticker(db, "AAPL", limit=30)
    
    # Get latest backtests
    backtests = BacktestRepository.get_latest(db, limit=5)
    
    # Create a new backtest
    from datetime import datetime, UTC
    from uuid import uuid4
    
    backtest = BacktestRepository.create(
        db,
        run_id=uuid4(),
        started_at=datetime.now(UTC),
        params={"strategy": "momentum", "lookback": 20},
        metrics={"sharpe": 1.5, "returns": 0.25}
    )
```

## Testing

Run all database tests:

```bash
pytest tests/test_db*.py -v
```

Run specific test files:

```bash
# Test models
pytest tests/test_db_models.py -v

# Test repositories
pytest tests/test_db_repo.py -v

# Test migrations
pytest tests/test_migrations.py -v

# Test session management
pytest tests/test_db_session.py -v
```

## Health Check

The `/health` endpoint includes database connectivity status:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "database": "connected"
}
```

## Development Workflow

1. **Make model changes** in `src/db/models.py`
2. **Generate migration**: `alembic revision --autogenerate -m "description"`
3. **Review migration** in `alembic/versions/`
4. **Apply migration**: `alembic upgrade head`
5. **Test changes**: `pytest tests/`
6. **Commit** both model changes and migration file

## Troubleshooting

### Database Connection Issues

```python
from src.db.session import check_db_health

if not check_db_health():
    print("Database connection failed")
    # Check DATABASE_URL environment variable
    # Check PostgreSQL is running
    # Check network connectivity
```

### Migration Conflicts

If you have uncommitted changes and need to pull:
1. Stash your changes: `git stash`
2. Pull latest: `git pull`
3. Apply stashed changes: `git stash pop`
4. Resolve conflicts in migration files
5. Test: `alembic upgrade head`

### Reset Database

To completely reset the database:

```bash
# Drop all tables
alembic downgrade base

# Recreate tables
alembic upgrade head
```

Or use SQLAlchemy directly:

```python
from src.db.models import Base
from src.db.session import engine

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
```
