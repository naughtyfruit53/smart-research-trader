"""Tests for feature joiner and no-leakage guarantees."""

from datetime import date

import pandas as pd
import pytest

from src.data.features.joiner import clean_features, join_features


def test_join_features_basic():
    """Test basic feature joining."""
    technicals = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 3,
            "dt": [date(2024, 1, i) for i in range(1, 4)],
            "sma_20": [100.0, 101.0, 102.0],
            "rsi_14": [50.0, 55.0, 60.0],
        }
    )
    
    fundamentals = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 3,
            "dt": [date(2024, 1, i) for i in range(1, 4)],
            "pe": [20.0, 20.0, 21.0],
            "pb": [5.0, 5.0, 5.2],
        }
    )
    
    sentiment = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 3,
            "dt": [date(2024, 1, i) for i in range(1, 4)],
            "sent_mean_comp": [0.5, 0.6, 0.4],
            "burst_3d": [1, 2, 3],
        }
    )
    
    result = join_features(technicals, fundamentals, sentiment)
    
    # Check all columns are present
    assert "sma_20" in result.columns
    assert "rsi_14" in result.columns
    assert "pe" in result.columns
    assert "pb" in result.columns
    assert "sent_mean_comp" in result.columns
    assert "burst_3d" in result.columns
    
    # Check row count
    assert len(result) == 3
    
    # Check a sample row
    row1 = result[result["dt"] == date(2024, 1, 1)].iloc[0]
    assert row1["sma_20"] == 100.0
    assert row1["pe"] == 20.0
    assert row1["sent_mean_comp"] == 0.5


def test_join_features_no_leakage():
    """Test that joining does not introduce future information leakage."""
    # Create technicals for day T
    technicals = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "dt": [date(2024, 1, 5)],
            "close": [100.0],
            "sma_20": [95.0],  # Based on prices up to day T
        }
    )
    
    # Fundamentals as-of day T (should be from before or on day T)
    fundamentals = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "dt": [date(2024, 1, 5)],
            "pe": [20.0],  # From fundamental snapshot before day T
        }
    )
    
    # Sentiment for day T (aggregated from news up to day T)
    sentiment = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "dt": [date(2024, 1, 5)],
            "sent_mean_comp": [0.5],  # From news up to day T
        }
    )
    
    result = join_features(technicals, fundamentals, sentiment)
    
    # All features for day T should use data up to and including day T only
    # This is a structural test - the functions should be called in the right order
    assert len(result) == 1
    assert result.iloc[0]["dt"] == date(2024, 1, 5)
    
    # Values should match (no shifting or future data)
    assert result.iloc[0]["sma_20"] == 95.0
    assert result.iloc[0]["pe"] == 20.0
    assert result.iloc[0]["sent_mean_comp"] == 0.5


def test_join_features_empty_fundamentals():
    """Test joining with empty fundamentals."""
    technicals = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 2,
            "dt": [date(2024, 1, 1), date(2024, 1, 2)],
            "sma_20": [100.0, 101.0],
        }
    )
    
    fundamentals = pd.DataFrame(columns=["ticker", "dt", "pe", "pb"])
    
    sentiment = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 2,
            "dt": [date(2024, 1, 1), date(2024, 1, 2)],
            "sent_mean_comp": [0.5, 0.6],
        }
    )
    
    result = join_features(technicals, fundamentals, sentiment)
    
    # Should still have technicals and sentiment
    assert len(result) == 2
    assert "sma_20" in result.columns
    assert "sent_mean_comp" in result.columns


def test_clean_features_drops_excessive_nans():
    """Test that clean_features drops columns with excessive NaNs."""
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 10,
            "dt": [date(2024, 1, i) for i in range(1, 11)],
            "good_col": [1.0] * 10,
            "bad_col": [None] * 9 + [1.0],  # 90% NaN
        }
    )
    
    result = clean_features(df, nan_threshold=0.5)
    
    # good_col should remain (0% NaN)
    assert "good_col" in result.columns
    
    # bad_col should be dropped (90% NaN > 50% threshold)
    assert "bad_col" not in result.columns
    
    # Key columns should remain
    assert "ticker" in result.columns
    assert "dt" in result.columns


def test_clean_features_fills_remaining_nans():
    """Test that clean_features fills remaining NaNs."""
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 10,
            "dt": [date(2024, 1, i) for i in range(1, 11)],
            "metric": [1.0, 2.0, None, 4.0, 5.0, None, 7.0, 8.0, 9.0, 10.0],
        }
    )
    
    result = clean_features(df, nan_threshold=0.5)
    
    # All NaNs should be filled
    assert result["metric"].notna().all()
    
    # Check forward fill worked (index 2 should be 2.0 from index 1)
    assert result.iloc[2]["metric"] == 2.0


def test_clean_features_multiple_tickers():
    """Test that clean_features handles multiple tickers correctly."""
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5 + ["MSFT"] * 5,
            "dt": [date(2024, 1, i) for i in range(1, 6)] * 2,
            "metric": [1.0, None, 3.0, 4.0, 5.0, 10.0, None, 12.0, 13.0, 14.0],
        }
    )
    
    result = clean_features(df, nan_threshold=0.5)
    
    # All NaNs should be filled
    assert result["metric"].notna().all()
    
    # Check that forward fill is per-ticker
    # AAPL index 1 should be forward-filled from index 0
    aapl_data = result[result["ticker"] == "AAPL"].sort_values("dt")
    assert aapl_data.iloc[1]["metric"] == 1.0
    
    # MSFT index 1 should be forward-filled from index 0
    msft_data = result[result["ticker"] == "MSFT"].sort_values("dt")
    assert msft_data.iloc[1]["metric"] == 10.0


def test_clean_features_preserves_key_columns():
    """Test that key columns are never dropped."""
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "dt": [date(2024, 1, i) for i in range(1, 6)],
            "bad_metric": [None] * 5,  # 100% NaN
        }
    )
    
    result = clean_features(df, nan_threshold=0.5)
    
    # Key columns should always be present
    assert "ticker" in result.columns
    assert "dt" in result.columns
    
    # Bad metric should be dropped
    assert "bad_metric" not in result.columns


def test_join_features_empty_technicals():
    """Test that empty technicals returns empty result."""
    technicals = pd.DataFrame(columns=["ticker", "dt", "sma_20"])
    
    fundamentals = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "dt": [date(2024, 1, 1)],
            "pe": [20.0],
        }
    )
    
    sentiment = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "dt": [date(2024, 1, 1)],
            "sent_mean_comp": [0.5],
        }
    )
    
    result = join_features(technicals, fundamentals, sentiment)
    
    assert result.empty
