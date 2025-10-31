"""Labeling module for computing forward returns from price data."""

import logging
from datetime import date

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.db.models import Feature, Price

logger = logging.getLogger(__name__)


def compute_forward_returns(prices_df: pd.DataFrame, horizon_days: int = 1) -> pd.DataFrame:
    """Compute forward returns from price data.

    Calculates label_ret_{horizon}d = close[t+horizon]/close[t] - 1

    Args:
        prices_df: DataFrame with columns [ticker, dt, close]
        horizon_days: Forward return horizon in days (default 1)

    Returns:
        DataFrame with columns [ticker, dt, label_ret_{horizon}d]

    Example:
        >>> prices = pd.DataFrame({
        ...     'ticker': ['AAPL', 'AAPL', 'AAPL'],
        ...     'dt': [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
        ...     'close': [100.0, 102.0, 101.0]
        ... })
        >>> labels = compute_forward_returns(prices, horizon_days=1)
        >>> labels['label_ret_1d'].iloc[0]  # (102.0/100.0 - 1) = 0.02
        0.02
    """
    if prices_df.empty:
        logger.warning("Empty prices DataFrame provided")
        return pd.DataFrame()

    # Validate required columns
    required_cols = ["ticker", "dt", "close"]
    missing_cols = [col for col in required_cols if col not in prices_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Sort by ticker and date
    df = prices_df[required_cols].copy()
    df = df.sort_values(["ticker", "dt"])

    # Compute forward returns per ticker
    label_col = f"label_ret_{horizon_days}d"
    df[label_col] = df.groupby("ticker")["close"].shift(-horizon_days) / df["close"] - 1.0

    # Drop rows without forward data (last horizon_days rows per ticker)
    df = df.dropna(subset=[label_col])

    return df[["ticker", "dt", label_col]]


def upsert_labels_to_features(
    db: Session, labels_df: pd.DataFrame, label_column: str = "label_ret_1d"
) -> int:
    """Upsert labels into features table for dates where features exist.

    Only updates rows where (ticker, dt) already exists in features table.

    Args:
        db: Database session
        labels_df: DataFrame with [ticker, dt, label_ret_*d]
        label_column: Column name to upsert (default 'label_ret_1d')

    Returns:
        Number of rows updated

    Example:
        >>> labels = compute_forward_returns(prices_df, horizon_days=1)
        >>> num_updated = upsert_labels_to_features(db, labels, 'label_ret_1d')
    """
    if labels_df.empty:
        logger.info("No labels to upsert")
        return 0

    if label_column not in labels_df.columns:
        raise ValueError(f"Label column '{label_column}' not found in DataFrame")

    # Get existing feature rows for these (ticker, dt) pairs
    tickers = labels_df["ticker"].unique().tolist()
    dates = labels_df["dt"].unique().tolist()

    stmt = select(Feature).where(Feature.ticker.in_(tickers), Feature.dt.in_(dates))
    existing_features = {(f.ticker, f.dt): f for f in db.execute(stmt).scalars()}

    if not existing_features:
        logger.info("No existing features found to update with labels")
        return 0

    # Filter labels to only those with existing features
    labels_to_update = labels_df[
        labels_df.apply(lambda row: (row["ticker"], row["dt"]) in existing_features, axis=1)
    ].copy()

    if labels_to_update.empty:
        logger.info("No matching feature rows found for labels")
        return 0

    # Update features with labels
    num_updated = 0
    for _, row in labels_to_update.iterrows():
        ticker = row["ticker"]
        dt = row["dt"]
        label_value = row[label_column]

        stmt = (
            update(Feature)
            .where(Feature.ticker == ticker, Feature.dt == dt)
            .values(label_ret_1d=label_value)
        )
        db.execute(stmt)
        num_updated += 1

    db.commit()
    logger.info(f"Updated {num_updated} feature rows with labels")

    return num_updated


def compute_and_upsert_labels(
    db: Session,
    tickers: list[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    horizon_days: int = 1,
) -> int:
    """Compute forward returns from prices and upsert to features table.

    Convenience function combining compute_forward_returns and upsert_labels_to_features.

    Args:
        db: Database session
        tickers: Optional list of tickers to process (None = all)
        start_date: Optional start date filter
        end_date: Optional end date filter
        horizon_days: Forward return horizon in days

    Returns:
        Number of feature rows updated with labels

    Example:
        >>> from datetime import date
        >>> num_updated = compute_and_upsert_labels(
        ...     db,
        ...     tickers=['AAPL', 'MSFT'],
        ...     start_date=date(2024, 1, 1),
        ...     horizon_days=1
        ... )
    """
    # Fetch prices
    stmt = select(Price)

    if tickers:
        stmt = stmt.where(Price.ticker.in_(tickers))
    if start_date:
        stmt = stmt.where(Price.dt >= start_date)
    if end_date:
        stmt = stmt.where(Price.dt <= end_date)

    prices = db.execute(stmt).scalars().all()

    if not prices:
        logger.warning("No prices found for labeling")
        return 0

    # Convert to DataFrame
    prices_df = pd.DataFrame(
        [{"ticker": p.ticker, "dt": p.dt, "close": float(p.close)} for p in prices]
    )

    logger.info(f"Computing forward returns for {len(prices_df)} price records")

    # Compute labels
    labels_df = compute_forward_returns(prices_df, horizon_days=horizon_days)

    if labels_df.empty:
        logger.warning("No labels computed")
        return 0

    # Upsert to features
    label_col = f"label_ret_{horizon_days}d"
    num_updated = upsert_labels_to_features(db, labels_df, label_column=label_col)

    return num_updated
