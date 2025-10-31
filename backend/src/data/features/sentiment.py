"""News sentiment aggregation features."""

import logging
from datetime import timedelta

import pandas as pd

logger = logging.getLogger(__name__)


def aggregate_news_sentiment(
    news_df: pd.DataFrame, trading_days_df: pd.DataFrame
) -> pd.DataFrame:
    """Aggregate news sentiment by ticker and date.
    
    Computes:
    - sent_mean_comp: Mean compound sentiment for the day
    - burst_3d: Count of headlines in last 3 days
    - burst_7d: Count of headlines in last 7 days
    - sent_ma_7d: 7-day rolling mean of compound sentiment
    
    Args:
        news_df: DataFrame with columns [ticker, dt, sent_comp, url, ...]
        trading_days_df: DataFrame with columns [ticker, dt]
        
    Returns:
        DataFrame with sentiment features keyed by [ticker, dt]
    """
    if trading_days_df.empty:
        return trading_days_df
    
    result = trading_days_df.copy()
    
    if news_df.empty:
        # No news data, fill with zeros
        result["sent_mean_comp"] = 0.0
        result["burst_3d"] = 0
        result["burst_7d"] = 0
        result["sent_ma_7d"] = 0.0
        return result
    
    # Ensure proper types
    news_df = news_df.copy()
    news_df["dt"] = pd.to_datetime(news_df["dt"])
    
    # Extract date part only (remove time)
    news_df["date"] = news_df["dt"].dt.date
    
    result["dt"] = pd.to_datetime(result["dt"])
    result["date"] = result["dt"].dt.date
    
    # Deduplicate by URL to avoid counting same news multiple times
    news_df = news_df.drop_duplicates(subset=["ticker", "url"], keep="first")
    
    # Aggregate by ticker and date
    daily_agg = (
        news_df.groupby(["ticker", "date"])
        .agg(
            sent_mean_comp=("sent_comp", "mean"),
            headline_count=("sent_comp", "count"),
        )
        .reset_index()
    )
    
    # Merge daily aggregates
    result = result.merge(
        daily_agg, on=["ticker", "date"], how="left", suffixes=("", "_news")
    )
    
    # Fill NaN with zeros for days with no news
    result["sent_mean_comp"] = result["sent_mean_comp"].fillna(0.0)
    result["headline_count"] = result["headline_count"].fillna(0)
    
    # Compute burst metrics (rolling counts)
    result = result.sort_values(["ticker", "date"])
    
    # Group by ticker and compute rolling features
    grouped_dfs = []
    for ticker, group_df in result.groupby("ticker", sort=False):
        group_df = group_df.copy()
        
        # Rolling sum of headline counts (burst metrics)
        group_df["burst_3d"] = group_df["headline_count"].rolling(window=3, min_periods=1).sum()
        group_df["burst_7d"] = group_df["headline_count"].rolling(window=7, min_periods=1).sum()
        
        # Rolling mean of sentiment
        group_df["sent_ma_7d"] = group_df["sent_mean_comp"].rolling(window=7, min_periods=1).mean()
        
        grouped_dfs.append(group_df)
    
    result = pd.concat(grouped_dfs, ignore_index=True)
    
    # Drop temporary columns
    result = result.drop(columns=["date", "headline_count"])
    
    # Ensure integer types for burst counts
    result["burst_3d"] = result["burst_3d"].astype(int)
    result["burst_7d"] = result["burst_7d"].astype(int)
    
    return result
