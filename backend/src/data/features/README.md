# Feature Engineering Pipeline

This module implements the complete feature engineering pipeline for the Smart Research Trader platform.

## Overview

The feature engineering pipeline reads raw data (prices, fundamentals, news) from PostgreSQL and computes:
- Technical indicators (SMA, EMA, RSI, MACD, ADX, ATR, Bollinger Bands, momentum, volatility)
- Fundamental metrics with as-of join and relative valuation
- News sentiment aggregates (mean compound sentiment, burst metrics, rolling averages)
- Composite scores (quality, valuation, momentum, sentiment)

## Module Structure

### `technicals.py`
Computes technical indicators using the `ta` library:
- Moving averages: SMA/EMA (20, 50, 200)
- Momentum: RSI(14), MACD(12,26,9), momentum(20,60)
- Trend: ADX(14)
- Volatility: ATR(14), Bollinger bands(20,2), realized volatility(20)

**Input**: DataFrame with columns `[ticker, dt, open, high, low, close, volume, adj_close]`

**Output**: Same DataFrame with additional indicator columns

### `fundamentals.py`
Performs as-of join of fundamental snapshots to trading days:
- Forward-fills up to `FUND_FFILL_DAYS` (default: 120 days)
- Computes relative valuation metrics (PE_vs_sector, PB_vs_sector)
- Falls back to cross-sectional z-scores if sector mapping unavailable

**Functions**:
- `asof_join_fundamentals(trading_days_df, fundamentals_df)`: Join fundamentals to trading days
- `relative_valuation(df, sector_mapping)`: Compute relative metrics

### `sentiment.py`
Aggregates news sentiment by ticker and date:
- `sent_mean_comp`: Mean compound sentiment for the day
- `burst_3d`, `burst_7d`: Headline counts in rolling windows
- `sent_ma_7d`: 7-day rolling mean of sentiment
- Deduplicates by URL to avoid double-counting

**Input**: News DataFrame with sentiment scores, trading days DataFrame

**Output**: DataFrame with sentiment features keyed by `[ticker, dt]`

### `joiner.py`
Joins all feature types ensuring no future data leakage:
- Merges technicals, fundamentals, sentiment on `[ticker, dt]`
- Cleans features by dropping columns with excessive NaNs
- Fills remaining NaNs with group-wise forward/backward fill

**Functions**:
- `join_features(technicals_df, fundamentals_df, sentiment_df)`: Combine all features
- `clean_features(df, nan_threshold)`: Clean and fill NaN values

### `composite.py`
Computes sub-scores and composite scores:
- Quality score: From ROE, ROCE, profit margins
- Valuation score: From PE_vs_sector, PB_vs_sector
- Momentum score: From momentum indicators and RSI
- Sentiment score: From sentiment metrics
- Composite score: Weighted combination using configurable weights
- Risk-adjusted score: Placeholder (currently equals composite_score)

**Weights**: Configured via `COMPOSITE_WEIGHTS` environment variable (default: equal weights)

## Usage

### Command Line

```bash
cd backend
python -m src.data.etl.compute_features --tickers AAPL,MSFT --start-date 2024-01-01 --end-date 2024-12-31
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

print(f"Generated features for {sum(result.values())} rows")
```

### Configuration

Set environment variables in `.env`:

```bash
# Feature engineering
FEATURE_LOOKBACK_DAYS=400        # Days of history to fetch for indicators
FUND_FFILL_DAYS=120              # Max days to forward-fill fundamentals
COMPOSITE_WEIGHTS='{"quality": 0.25, "valuation": 0.25, "momentum": 0.25, "sentiment": 0.25}'
SECTOR_MAP_PATH=/path/to/sector_mapping.json  # Optional
ENABLE_FEATURES_TASK=false       # Enable Celery task
```

### Celery Task (Optional)

If `ENABLE_FEATURES_TASK=true`, a daily task will run after price/news updates:

```python
from src.data.etl.tasks import compute_features_daily

# Manually trigger
compute_features_daily.delay()
```

## Database Schema

Features are stored in the `features` table with:
- Primary key: `(ticker, dt)`
- `features_json`: JSONB column with all feature values
- `label_ret_1d`: Nullable (for future use in PR5/PR6)

Upserts are idempotent using PostgreSQL `ON CONFLICT DO UPDATE`.

## Testing

Run tests with:

```bash
pytest tests/test_features*.py
pytest tests/test_compute_features_upsert_idempotent.py
```

Tests cover:
- Technical indicator shapes and warmup handling
- As-of join correctness with gaps
- Sentiment aggregation and deduplication
- Feature joining without data leakage
- Idempotent upserts

## Design Principles

1. **No Data Leakage**: Features for date T use only data available up to and including T
2. **Vectorized Operations**: Use pandas groupby and vectorized ops, avoid row loops
3. **Idempotent**: Re-running with same inputs produces same outputs
4. **Configurable**: All parameters controlled via environment variables
5. **Robust**: Handles missing data, gaps, and empty inputs gracefully

## Future Enhancements (PR5/PR6)

- Risk-adjusted score incorporating prediction uncertainty
- Label computation (forward returns)
- Feature selection and importance analysis
- Additional composite score formulations
