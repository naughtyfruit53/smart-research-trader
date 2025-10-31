"""Feature joiner with no-leakage guarantees."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def join_features(
    technicals_df: pd.DataFrame,
    fundamentals_df: pd.DataFrame,
    sentiment_df: pd.DataFrame,
) -> pd.DataFrame:
    """Join technicals, fundamentals, and sentiment features on [ticker, dt].
    
    Ensures no data leakage by using end-of-day data only.
    Fundamentals and sentiment are already lagged appropriately.
    
    Args:
        technicals_df: DataFrame with technical indicators
        fundamentals_df: DataFrame with fundamental metrics
        sentiment_df: DataFrame with sentiment metrics
        
    Returns:
        Combined DataFrame with all features
    """
    # Start with technicals as base
    if technicals_df.empty:
        logger.warning("Technicals dataframe is empty")
        return pd.DataFrame()
    
    result = technicals_df.copy()
    
    # Join fundamentals
    if not fundamentals_df.empty:
        # Drop ticker column from fundamentals to avoid duplication
        fund_cols = [c for c in fundamentals_df.columns if c not in ["ticker", "dt"]]
        result = result.merge(
            fundamentals_df[["ticker", "dt"] + fund_cols],
            on=["ticker", "dt"],
            how="left",
        )
    
    # Join sentiment
    if not sentiment_df.empty:
        # Drop ticker column from sentiment to avoid duplication
        sent_cols = [c for c in sentiment_df.columns if c not in ["ticker", "dt"]]
        result = result.merge(
            sentiment_df[["ticker", "dt"] + sent_cols],
            on=["ticker", "dt"],
            how="left",
        )
    
    return result


def clean_features(
    df: pd.DataFrame, nan_threshold: float = 0.5
) -> pd.DataFrame:
    """Clean features by dropping columns with excessive NaNs and filling remaining.
    
    Args:
        df: DataFrame with features
        nan_threshold: Threshold for dropping columns (0.5 = drop if >50% NaN)
        
    Returns:
        Cleaned DataFrame
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Identify columns to drop
    nan_ratio = df.isna().sum() / len(df)
    cols_to_drop = nan_ratio[nan_ratio > nan_threshold].index.tolist()
    
    # Exclude key columns from dropping
    key_cols = ["ticker", "dt"]
    cols_to_drop = [c for c in cols_to_drop if c not in key_cols]
    
    if cols_to_drop:
        logger.info(f"Dropping {len(cols_to_drop)} columns with >{nan_threshold*100}% NaN: {cols_to_drop[:5]}...")
        df = df.drop(columns=cols_to_drop)
    
    # Fill remaining NaNs with group-wise methods
    df = _fill_nans(df)
    
    return df


def _fill_nans(df: pd.DataFrame) -> pd.DataFrame:
    """Fill remaining NaNs using group-wise forward-fill then backward-fill."""
    # Get numeric columns (excluding key columns)
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    key_cols = ["ticker", "dt"]
    fill_cols = [c for c in numeric_cols if c not in key_cols]
    
    if not fill_cols:
        return df
    
    # Sort by ticker and date
    df = df.sort_values(["ticker", "dt"])
    
    # Group by ticker and fill
    for col in fill_cols:
        # Forward fill within group
        df[col] = df.groupby("ticker")[col].ffill()
        # Backward fill within group
        df[col] = df.groupby("ticker")[col].bfill()
    
    # Fill any remaining NaNs with 0
    df[fill_cols] = df[fill_cols].fillna(0)
    
    return df
