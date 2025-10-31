"""Fundamentals as-of join and relative valuation metrics."""

import logging
from datetime import timedelta

import pandas as pd

from src.core.config import load_sector_mapping, settings

logger = logging.getLogger(__name__)


def asof_join_fundamentals(
    trading_days_df: pd.DataFrame, fundamentals_df: pd.DataFrame
) -> pd.DataFrame:
    """Perform as-of join of fundamentals to trading days with forward-fill cap.
    
    Args:
        trading_days_df: DataFrame with columns [ticker, dt]
        fundamentals_df: DataFrame with columns [ticker, asof, pe, pb, ...]
        
    Returns:
        DataFrame with fundamentals joined to trading days, forward-filled up to FUND_FFILL_DAYS
    """
    if trading_days_df.empty:
        return trading_days_df
    
    if fundamentals_df.empty:
        # Return trading days with NaN fundamentals columns
        # Define standard fundamental columns
        fundamental_cols = [
            "pe", "pb", "ev_ebitda", "roe", "roce", "de_ratio",
            "eps_g3y", "rev_g3y", "profit_g3y", "opm", "npm",
            "div_yield", "promoter_hold", "pledged_pct"
        ]
        result = trading_days_df.copy()
        for col in fundamental_cols:
            result[col] = float("nan")
        return result
    
    # Ensure proper types and sorting
    trading_days_df = trading_days_df.copy()
    fundamentals_df = fundamentals_df.copy()
    
    trading_days_df["dt"] = pd.to_datetime(trading_days_df["dt"])
    fundamentals_df["asof"] = pd.to_datetime(fundamentals_df["asof"])
    
    trading_days_df = trading_days_df.sort_values(["ticker", "dt"])
    fundamentals_df = fundamentals_df.sort_values(["ticker", "asof"])
    
    # Perform as-of merge
    result = pd.merge_asof(
        trading_days_df,
        fundamentals_df,
        left_on="dt",
        right_on="asof",
        by="ticker",
        direction="backward",
        tolerance=pd.Timedelta(days=settings.FUND_FFILL_DAYS),
    )
    
    # Drop the asof column as it's redundant
    if "asof" in result.columns:
        result = result.drop(columns=["asof"])
    
    return result


def relative_valuation(
    df: pd.DataFrame, sector_mapping: dict[str, str] | None = None
) -> pd.DataFrame:
    """Compute relative valuation metrics (PE_vs_sector, PB_vs_sector).
    
    If sector mapping is available, compute metrics relative to sector.
    Otherwise, compute cross-sectional z-scores per date as a fallback.
    
    Args:
        df: DataFrame with columns [ticker, dt, pe, pb, ...]
        sector_mapping: Optional dictionary mapping ticker to sector
        
    Returns:
        DataFrame with relative valuation columns added
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Load sector mapping if not provided
    if sector_mapping is None:
        sector_mapping = load_sector_mapping()
    
    if sector_mapping is not None:
        # Add sector column
        df["sector"] = df["ticker"].map(sector_mapping)
        
        # Compute sector-relative metrics
        df = _compute_sector_relative(df)
        
        # Drop sector column
        df = df.drop(columns=["sector"])
    else:
        # Fallback: compute cross-sectional z-scores per date
        logger.info("No sector mapping available, using cross-sectional z-scores")
        df = _compute_cross_sectional_zscores(df)
    
    return df


def _compute_sector_relative(df: pd.DataFrame) -> pd.DataFrame:
    """Compute sector-relative metrics."""
    # Group by date and sector
    for metric in ["pe", "pb"]:
        if metric not in df.columns:
            df[f"{metric}_vs_sector"] = float("nan")
            continue
        
        # Compute sector mean for each date
        sector_means = df.groupby(["dt", "sector"])[metric].transform("mean")
        
        # Compute relative metric (stock value / sector mean)
        df[f"{metric}_vs_sector"] = df[metric] / sector_means
        
        # Replace inf with NaN
        df[f"{metric}_vs_sector"] = df[f"{metric}_vs_sector"].replace([float("inf"), -float("inf")], float("nan"))
    
    return df


def _compute_cross_sectional_zscores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute cross-sectional z-scores per date as fallback."""
    for metric in ["pe", "pb"]:
        if metric not in df.columns:
            df[f"{metric}_vs_sector"] = float("nan")
            continue
        
        # Compute z-score per date
        grouped = df.groupby("dt")[metric]
        mean = grouped.transform("mean")
        std = grouped.transform("std")
        
        # Z-score: (value - mean) / std
        # Use negative z-score for PE/PB (lower is better for valuation)
        df[f"{metric}_vs_sector"] = -(df[metric] - mean) / std
        
        # Replace inf with NaN
        df[f"{metric}_vs_sector"] = df[f"{metric}_vs_sector"].replace([float("inf"), -float("inf")], float("nan"))
    
    return df
