"""Feature engineering orchestrator and database upsert."""

import logging
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.core.config import settings
from src.data.features.composite import compute_composite_scores
from src.data.features.fundamentals import asof_join_fundamentals, relative_valuation
from src.data.features.joiner import clean_features, join_features
from src.data.features.sentiment import aggregate_news_sentiment
from src.data.features.technicals import compute_technical_indicators
from src.db.models import Feature, Fundamental, News, Price
from src.db.session import SessionLocal

logger = logging.getLogger(__name__)


def compute_and_upsert_features(
    tickers: list[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, int]:
    """Compute features and upsert to database.
    
    This orchestrator:
    1. Reads prices, fundamentals, and news from database
    2. Computes technical indicators
    3. Performs as-of join with fundamentals
    4. Aggregates news sentiment
    5. Joins all features
    6. Computes composite scores
    7. Upserts to features table
    
    Args:
        tickers: List of ticker symbols (defaults to config TICKERS)
        start_date: Start date for features (defaults to 400 days ago)
        end_date: End date for features (defaults to today)
        
    Returns:
        Dictionary with statistics: {ticker: row_count}
    """
    # Default parameters
    if tickers is None:
        tickers = [t.strip() for t in settings.TICKERS.split(",") if t.strip()]
    
    if not tickers:
        logger.warning("No tickers specified for feature computation")
        return {}
    
    if end_date is None:
        end_date = date.today()
    
    if start_date is None:
        # Use lookback days to ensure we have enough data for indicators
        start_date = end_date - timedelta(days=settings.FEATURE_LOOKBACK_DAYS)
    
    logger.info(f"Computing features for {len(tickers)} tickers from {start_date} to {end_date}")
    
    # Read data from database
    with SessionLocal() as session:
        prices_df = _read_prices(session, tickers, start_date, end_date)
        fundamentals_df = _read_fundamentals(session, tickers)
        news_df = _read_news(session, tickers, start_date, end_date)
    
    if prices_df.empty:
        logger.warning("No price data available")
        return {}
    
    logger.info(f"Loaded {len(prices_df)} price rows, {len(fundamentals_df)} fundamental rows, {len(news_df)} news rows")
    
    # Compute technical indicators
    logger.info("Computing technical indicators...")
    technicals_df = compute_technical_indicators(prices_df)
    
    # Prepare trading days for joins
    trading_days_df = technicals_df[["ticker", "dt"]].copy()
    
    # As-of join fundamentals
    logger.info("Joining fundamentals with as-of join...")
    fundamentals_joined_df = asof_join_fundamentals(trading_days_df, fundamentals_df)
    
    # Compute relative valuation
    logger.info("Computing relative valuation metrics...")
    fundamentals_joined_df = relative_valuation(fundamentals_joined_df)
    
    # Aggregate news sentiment
    logger.info("Aggregating news sentiment...")
    sentiment_df = aggregate_news_sentiment(news_df, trading_days_df)
    
    # Join all features
    logger.info("Joining all features...")
    features_df = join_features(technicals_df, fundamentals_joined_df, sentiment_df)
    
    # Clean features
    logger.info("Cleaning features...")
    features_df = clean_features(features_df, nan_threshold=0.8)
    
    # Compute composite scores
    logger.info("Computing composite scores...")
    features_df = compute_composite_scores(features_df)
    
    # Filter to requested date range (after computing indicators which need lookback)
    features_df = features_df[
        (features_df["dt"] >= pd.Timestamp(start_date))
        & (features_df["dt"] <= pd.Timestamp(end_date))
    ].copy()
    
    logger.info(f"Generated {len(features_df)} feature rows")
    
    # Upsert to database
    logger.info("Upserting to database...")
    result = _upsert_features(features_df)
    
    logger.info(f"Feature computation complete: {result}")
    
    return result


def _read_prices(
    session, tickers: list[str], start_date: date, end_date: date
) -> pd.DataFrame:
    """Read price data from database."""
    stmt = select(Price).where(
        Price.ticker.in_(tickers),
        Price.dt >= start_date,
        Price.dt <= end_date,
    )
    
    rows = session.execute(stmt).scalars().all()
    
    if not rows:
        return pd.DataFrame()
    
    data = [
        {
            "ticker": r.ticker,
            "dt": r.dt,
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": int(r.volume),
            "adj_close": float(r.adj_close),
        }
        for r in rows
    ]
    
    return pd.DataFrame(data)


def _read_fundamentals(session, tickers: list[str]) -> pd.DataFrame:
    """Read fundamental data from database."""
    stmt = select(Fundamental).where(Fundamental.ticker.in_(tickers))
    
    rows = session.execute(stmt).scalars().all()
    
    if not rows:
        return pd.DataFrame()
    
    data = []
    for r in rows:
        row_dict = {
            "ticker": r.ticker,
            "asof": r.asof,
        }
        # Add all fundamental metrics
        for col in [
            "pe", "pb", "ev_ebitda", "roe", "roce", "de_ratio",
            "eps_g3y", "rev_g3y", "profit_g3y", "opm", "npm",
            "div_yield", "promoter_hold", "pledged_pct"
        ]:
            val = getattr(r, col, None)
            row_dict[col] = float(val) if val is not None else None
        data.append(row_dict)
    
    return pd.DataFrame(data)


def _read_news(
    session, tickers: list[str], start_date: date, end_date: date
) -> pd.DataFrame:
    """Read news data from database."""
    # Convert dates to datetime for comparison with timestamp column
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    stmt = select(News).where(
        News.ticker.in_(tickers),
        News.dt >= start_dt,
        News.dt <= end_dt,
    )
    
    rows = session.execute(stmt).scalars().all()
    
    if not rows:
        return pd.DataFrame()
    
    data = [
        {
            "ticker": r.ticker,
            "dt": r.dt,
            "sent_comp": float(r.sent_comp),
            "url": r.url,
        }
        for r in rows
    ]
    
    return pd.DataFrame(data)


def _upsert_features(df: pd.DataFrame) -> dict[str, int]:
    """Upsert features to database.
    
    Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE for idempotent upserts.
    """
    if df.empty:
        return {}
    
    # Convert to records for insertion
    records = []
    ticker_counts = {}
    
    for _, row in df.iterrows():
        ticker = row["ticker"]
        dt = row["dt"]
        
        if isinstance(dt, pd.Timestamp):
            dt = dt.date()
        
        # Build features_json dict (all columns except ticker, dt)
        features_json = {}
        for col in df.columns:
            if col not in ["ticker", "dt"]:
                val = row[col]
                # Convert to native Python types
                if pd.isna(val):
                    features_json[col] = None
                elif isinstance(val, (pd.Timestamp, datetime)):
                    features_json[col] = val.isoformat()
                else:
                    features_json[col] = float(val) if isinstance(val, (int, float)) else val
        
        record = {
            "ticker": ticker,
            "dt": dt,
            "features_json": features_json,
            "label_ret_1d": None,  # Will be computed later in PR5/PR6
        }
        
        records.append(record)
        ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
    
    # Batch upsert
    with SessionLocal() as session:
        stmt = insert(Feature).values(records)
        
        # On conflict, update features_json
        stmt = stmt.on_conflict_do_update(
            index_elements=["ticker", "dt"],
            set_={"features_json": stmt.excluded.features_json},
        )
        
        session.execute(stmt)
        session.commit()
    
    logger.info(f"Upserted {len(records)} feature rows")
    
    return ticker_counts


def main():
    """CLI entry point for compute_features."""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Compute and upsert features")
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers (default: from config)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD, default: 400 days ago)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD, default: today)",
    )
    
    args = parser.parse_args()
    
    tickers = None
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    
    start_date = None
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    
    end_date = None
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    
    result = compute_and_upsert_features(tickers, start_date, end_date)
    
    print(f"\nFeature computation complete:")
    for ticker, count in result.items():
        print(f"  {ticker}: {count} rows")
    print(f"\nTotal: {sum(result.values())} rows")


if __name__ == "__main__":
    main()
