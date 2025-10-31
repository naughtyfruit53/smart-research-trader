# PR: Implement Feature Engineering Pipeline

## Summary

This PR implements the complete feature engineering pipeline that reads prices, fundamentals, and news from Postgres; computes technical, fundamentals-asof, and sentiment aggregates; derives relative valuation and composite scores; and upserts daily feature rows into the features table.

## Changes Overview

### New Modules

#### `backend/src/data/features/`

1. **`technicals.py`**: Computes technical indicators using `ta` library
   - SMA/EMA (20, 50, 200)
   - RSI(14), MACD(12,26,9)
   - ADX(14), ATR(14)
   - Bollinger band width(20,2)
   - Momentum(20,60), realized volatility(20)
   - Handles minimal lookback warmup per ticker

2. **`fundamentals.py`**: As-of join and relative valuation
   - `asof_join_fundamentals()`: Joins fundamental snapshots to trading days
   - Forward-fills up to `FUND_FFILL_DAYS` (120 days)
   - `relative_valuation()`: Computes PE_vs_sector, PB_vs_sector
   - Falls back to cross-sectional z-scores if no sector mapping

3. **`sentiment.py`**: News sentiment aggregation
   - Aggregates by ticker/date
   - Produces: `sent_mean_comp`, `burst_3d`, `burst_7d`, `sent_ma_7d`
   - Deduplicates by URL to avoid counting same news twice
   - Handles days with no news (fills with 0s)

4. **`joiner.py`**: Feature joining with no-leakage guarantee
   - Joins technicals, fundamentals, sentiment on `[ticker, dt]`
   - `clean_features()`: Drops columns with excessive NaNs
   - Fills remaining NaNs with group-wise forward/backward fill

5. **`composite.py`**: Composite score computation
   - Quality score (from ROE, ROCE, margins)
   - Valuation score (from PE_vs_sector, PB_vs_sector)
   - Momentum score (from momentum indicators, RSI)
   - Sentiment score (from sentiment metrics)
   - Composite score (weighted combination)
   - Risk-adjusted score (placeholder, equals composite for now)

6. **`README.md`**: Module documentation

#### `backend/src/data/etl/`

1. **`compute_features.py`**: Main orchestrator
   - Reads data from DB (prices, fundamentals, news)
   - Runs feature pipeline in correct order
   - Upserts to `features` table using `ON CONFLICT DO UPDATE`
   - Callable as script or Python function
   - CLI: `python -m src.data.etl.compute_features --tickers AAPL,MSFT --start-date 2024-01-01 --end-date 2024-12-31`

#### `backend/src/core/`

1. **`config.py`**: Extended with feature settings
   - `FEATURE_LOOKBACK_DAYS` (default: 400)
   - `FUND_FFILL_DAYS` (default: 120)
   - `COMPOSITE_WEIGHTS` (JSON string, default: equal weights)
   - `SECTOR_MAP_PATH` (optional)
   - `ENABLE_FEATURES_TASK` (default: false)
   - Helper functions: `get_composite_weights()`, `load_sector_mapping()`

#### `backend/src/data/etl/tasks.py`

1. **`compute_features_daily()`**: Optional Celery task
   - Runs after price/news ETLs
   - Only enabled if `ENABLE_FEATURES_TASK=true`
   - Scheduled at 11:30 PM UTC (after news at 11:00 PM)

### Tests

#### `backend/tests/`

1. **`test_features_technicals_shapes.py`**
   - Validates indicator columns exist
   - Tests NaN warmup handling
   - Tests shapes across multiple tickers
   - Tests insufficient data handling

2. **`test_features_fundamentals_asof.py`**
   - Tests as-of join correctness with gaps
   - Tests forward-fill cap (120 days)
   - Tests relative valuation with/without sectors
   - Tests cross-sectional z-score fallback

3. **`test_features_sentiment_aggregates.py`**
   - Tests sentiment mean and burst counts
   - Tests URL deduplication
   - Tests rolling mean computation
   - Tests handling of days with no news

4. **`test_features_joiner_no_leakage.py`**
   - Tests feature joining
   - Validates no future data leakage
   - Tests NaN cleaning and filling
   - Tests group-wise operations per ticker

5. **`test_compute_features_upsert_idempotent.py`**
   - Tests full pipeline with fixture data
   - Tests idempotent upserts (no duplicates)
   - Tests PK constraint (`ticker`, `dt`)
   - Tests multiple tickers

### Dependencies

Added to `requirements.txt`:
- `ta==0.11.0` - Technical analysis indicators
- `scikit-learn==1.4.0` - For potential future use (RobustScaler)

## Database Interactions

### Read Operations
- `prices`: OHLCV data for technical indicators
- `fundamentals`: Fundamental snapshots for as-of join
- `news`: News articles with sentiment for aggregation

### Write Operations
- `features`: Upsert with `ON CONFLICT (ticker, dt) DO UPDATE`
- Primary key: `(ticker, dt)`
- `features_json`: JSONB containing all feature values
- `label_ret_1d`: Nullable (for future use)

## How to Run

### Prerequisites
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Ensure database is populated with prices, fundamentals, news
# (from previous PRs)
```

### Run Locally
```bash
# Full pipeline for demo tickers
python -m src.data.etl.compute_features

# Specific tickers and date range
python -m src.data.etl.compute_features \
  --tickers AAPL,MSFT,GOOGL \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

### Python API
```python
from datetime import date
from src.data.etl.compute_features import compute_and_upsert_features

result = compute_and_upsert_features(
    tickers=["AAPL", "MSFT"],
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31)
)
```

### Run Tests
```bash
cd backend
pytest tests/test_features*.py
pytest tests/test_compute_features_upsert_idempotent.py
```

## Acceptance Criteria

✅ **Feature Computation**
- Running `compute_features.py` against a DB populated with PR3 ETLs produces non-empty features rows
- Composite score is populated for all generated rows
- All technical indicators are computed correctly with proper warmup handling

✅ **Data Integrity**
- Upserts are idempotent (re-running produces same results, no duplicates)
- Primary key `(ticker, dt)` is respected
- No future data leakage (features for day T use only data up to T)

✅ **Tests**
- All 5 new test files pass locally and in CI
- Tests cover shapes, warmup, as-of join, sentiment aggregation, no-leakage, idempotency
- Tests use fixture data and mock where appropriate

✅ **Configuration**
- All parameters are configurable via environment variables
- Sensible defaults are provided
- Optional Celery task can be enabled via config

## Design Decisions

1. **Vectorized Operations**: Use pandas groupby and vectorized ops throughout, avoid row-level loops for performance

2. **No Data Leakage**: Strict ordering ensures features for date T only use data available up to T:
   - Technical indicators computed from historical prices
   - Fundamentals use as-of join (backward-looking)
   - Sentiment aggregated from news up to T

3. **Robust Handling**: Gracefully handles:
   - Missing data (NaNs)
   - Gaps in fundamental snapshots
   - Days with no news
   - Insufficient history for indicators

4. **Idempotent Upserts**: Uses PostgreSQL `ON CONFLICT DO UPDATE` for safe re-runs

5. **Modular Design**: Each feature type (technical, fundamental, sentiment) in separate module for maintainability

6. **Configurable Weights**: Composite score weights loaded from environment for easy experimentation

## Future Work (PR5/PR6)

- Compute forward returns as labels (`label_ret_1d`)
- Incorporate prediction uncertainty into risk-adjusted score
- Feature selection and importance analysis
- Additional composite score formulations
- Performance optimization for large ticker universes

## CI Compatibility

- Tests reuse PostgreSQL from PR2 CI setup
- Tests respect `SKIP_NETWORK_IN_TESTS=true`
- Fixture data created programmatically (no external files needed)
- No new services required

## Breaking Changes

None. This is a new feature that doesn't modify existing functionality.

## Rollback Plan

If issues arise, this feature can be safely disabled by:
1. Not calling `compute_and_upsert_features()`
2. Setting `ENABLE_FEATURES_TASK=false` to disable Celery task
3. The `features` table will remain empty but won't affect other ETLs
