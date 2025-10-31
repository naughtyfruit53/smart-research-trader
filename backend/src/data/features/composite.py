"""Composite score computation from sub-scores."""

import logging

import pandas as pd
from sklearn.preprocessing import RobustScaler

from src.core.config import get_composite_weights

logger = logging.getLogger(__name__)


def compute_composite_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute composite scores from sub-scores.
    
    Computes:
    - quality_score: From ROE, ROCE, profit margins
    - valuation_score: From PE_vs_sector, PB_vs_sector
    - momentum_score: From momentum indicators and RSI
    - sentiment_score: From sentiment metrics
    - composite_score: Weighted combination of above
    - risk_adjusted_score: Placeholder (equals composite_score for now)
    
    Args:
        df: DataFrame with all features
        
    Returns:
        DataFrame with composite scores added
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Compute sub-scores
    df = _compute_quality_score(df)
    df = _compute_valuation_score(df)
    df = _compute_momentum_score(df)
    df = _compute_sentiment_score(df)
    
    # Combine into composite score
    weights = get_composite_weights()
    
    df["composite_score"] = (
        weights["quality"] * df["quality_score"]
        + weights["valuation"] * df["valuation_score"]
        + weights["momentum"] * df["momentum_score"]
        + weights["sentiment"] * df["sentiment_score"]
    )
    
    # Risk-adjusted score (placeholder for now)
    df["risk_adjusted_score"] = df["composite_score"]
    
    return df


def _compute_quality_score(df: pd.DataFrame) -> pd.DataFrame:
    """Compute quality score from fundamental metrics."""
    quality_cols = []
    
    # Identify available quality metrics
    if "roe" in df.columns:
        quality_cols.append("roe")
    if "roce" in df.columns:
        quality_cols.append("roce")
    if "opm" in df.columns:
        quality_cols.append("opm")
    if "npm" in df.columns:
        quality_cols.append("npm")
    
    if not quality_cols:
        logger.warning("No quality metrics available, setting quality_score to 0.5")
        df["quality_score"] = 0.5
        return df
    
    # Scale each metric to [0, 1] using robust z-score per date
    scaled_scores = []
    for col in quality_cols:
        scaled = _scale_to_01(df, col)
        scaled_scores.append(scaled)
    
    # Average scaled scores
    df["quality_score"] = pd.concat(scaled_scores, axis=1).mean(axis=1)
    
    return df


def _compute_valuation_score(df: pd.DataFrame) -> pd.DataFrame:
    """Compute valuation score from relative valuation metrics."""
    valuation_cols = []
    
    if "pe_vs_sector" in df.columns:
        valuation_cols.append("pe_vs_sector")
    if "pb_vs_sector" in df.columns:
        valuation_cols.append("pb_vs_sector")
    
    if not valuation_cols:
        logger.warning("No valuation metrics available, setting valuation_score to 0.5")
        df["valuation_score"] = 0.5
        return df
    
    # For valuation, negative values are good (already z-scored in fundamentals.py)
    # Scale to [0, 1]
    scaled_scores = []
    for col in valuation_cols:
        scaled = _scale_to_01(df, col)
        scaled_scores.append(scaled)
    
    df["valuation_score"] = pd.concat(scaled_scores, axis=1).mean(axis=1)
    
    return df


def _compute_momentum_score(df: pd.DataFrame) -> pd.DataFrame:
    """Compute momentum score from technical indicators."""
    momentum_cols = []
    
    if "momentum_20" in df.columns:
        momentum_cols.append("momentum_20")
    if "momentum_60" in df.columns:
        momentum_cols.append("momentum_60")
    if "rsi_14" in df.columns:
        # RSI is already in [0, 100] range, normalize to [0, 1]
        df["rsi_normalized"] = df["rsi_14"] / 100.0
        momentum_cols.append("rsi_normalized")
    
    if not momentum_cols:
        logger.warning("No momentum metrics available, setting momentum_score to 0.5")
        df["momentum_score"] = 0.5
        return df
    
    scaled_scores = []
    for col in momentum_cols:
        scaled = _scale_to_01(df, col)
        scaled_scores.append(scaled)
    
    df["momentum_score"] = pd.concat(scaled_scores, axis=1).mean(axis=1)
    
    # Clean up temporary column
    if "rsi_normalized" in df.columns:
        df = df.drop(columns=["rsi_normalized"])
    
    return df


def _compute_sentiment_score(df: pd.DataFrame) -> pd.DataFrame:
    """Compute sentiment score from news sentiment metrics."""
    sentiment_cols = []
    
    if "sent_mean_comp" in df.columns:
        sentiment_cols.append("sent_mean_comp")
    if "sent_ma_7d" in df.columns:
        sentiment_cols.append("sent_ma_7d")
    
    if not sentiment_cols:
        logger.warning("No sentiment metrics available, setting sentiment_score to 0.5")
        df["sentiment_score"] = 0.5
        return df
    
    scaled_scores = []
    for col in sentiment_cols:
        scaled = _scale_to_01(df, col)
        scaled_scores.append(scaled)
    
    df["sentiment_score"] = pd.concat(scaled_scores, axis=1).mean(axis=1)
    
    return df


def _scale_to_01(df: pd.DataFrame, col: str) -> pd.Series:
    """Scale a column to [0, 1] using robust z-score per date.
    
    Uses cross-sectional ranking percentile for each date.
    
    Args:
        df: DataFrame with column to scale
        col: Column name
        
    Returns:
        Series with scaled values
    """
    # Group by date and compute percentile rank
    scaled = df.groupby("dt")[col].rank(pct=True)
    
    # Fill NaN with 0.5 (neutral)
    scaled = scaled.fillna(0.5)
    
    # Clip to [0, 1]
    scaled = scaled.clip(0, 1)
    
    return scaled
