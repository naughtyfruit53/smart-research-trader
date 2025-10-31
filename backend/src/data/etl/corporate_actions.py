"""Corporate actions normalization for splits and dividends."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def normalize_splits_dividends(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize price data for splits and dividends.

    For yfinance data, adjusted close already accounts for splits/dividends.
    This function is a placeholder for more complex normalization if needed.

    Args:
        df: Price DataFrame with columns [ticker, dt, open, high, low, close, volume, adj_close]

    Returns:
        DataFrame with normalized prices
    """
    logger.info("Corporate actions normalization (noop for yfinance with adj_close)")

    # For yfinance data, we prefer using adj_close as-is
    # If needed, we could re-derive OHLC from adj_close ratios:
    # adjustment_ratio = adj_close / close
    # df['open'] = df['open'] * adjustment_ratio
    # df['high'] = df['high'] * adjustment_ratio
    # df['low'] = df['low'] * adjustment_ratio
    # df['close'] = df['adj_close']

    # For now, return as-is since yfinance handles this
    return df


def detect_splits(df: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """Detect potential stock splits in price data.

    Args:
        df: Price DataFrame sorted by date
        threshold: Price change threshold to flag potential split (0.5 = 50%)

    Returns:
        DataFrame with 'potential_split' flag column
    """
    df = df.copy()
    df = df.sort_values(["ticker", "dt"])

    # Calculate day-over-day price change
    df["price_change"] = df.groupby("ticker")["close"].pct_change()

    # Flag large negative changes as potential splits
    df["potential_split"] = (df["price_change"] < -threshold) | (df["price_change"] > threshold)

    split_count = df["potential_split"].sum()
    if split_count > 0:
        logger.info(f"Detected {split_count} potential stock splits/events")

    return df
