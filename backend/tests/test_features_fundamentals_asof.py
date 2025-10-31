"""Tests for fundamentals as-of join and relative valuation."""

from datetime import date

import pandas as pd
import pytest

from src.data.features.fundamentals import asof_join_fundamentals, relative_valuation


def test_asof_join_basic():
    """Test basic as-of join functionality."""
    trading_days = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "dt": [date(2024, 1, i) for i in range(1, 6)],
        }
    )
    
    fundamentals = pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "asof": [date(2024, 1, 1), date(2024, 1, 4)],
            "pe": [20.0, 22.0],
            "pb": [5.0, 5.5],
        }
    )
    
    result = asof_join_fundamentals(trading_days, fundamentals)
    
    # Check that fundamentals are joined correctly
    assert len(result) == 5
    
    # Days 1-3 should have first fundamental snapshot
    assert result.loc[result["dt"] == pd.Timestamp("2024-01-01"), "pe"].values[0] == 20.0
    assert result.loc[result["dt"] == pd.Timestamp("2024-01-02"), "pe"].values[0] == 20.0
    assert result.loc[result["dt"] == pd.Timestamp("2024-01-03"), "pe"].values[0] == 20.0
    
    # Days 4-5 should have second fundamental snapshot
    assert result.loc[result["dt"] == pd.Timestamp("2024-01-04"), "pe"].values[0] == 22.0
    assert result.loc[result["dt"] == pd.Timestamp("2024-01-05"), "pe"].values[0] == 22.0


def test_asof_join_with_gap():
    """Test as-of join with gap larger than forward-fill cap."""
    trading_days = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 150,
            "dt": [date(2024, 1, 1) + pd.Timedelta(days=i) for i in range(150)],
        }
    )
    
    # Only one fundamental snapshot at the beginning
    fundamentals = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "asof": [date(2024, 1, 1)],
            "pe": [20.0],
            "pb": [5.0],
        }
    )
    
    result = asof_join_fundamentals(trading_days, fundamentals)
    
    # First 120 days should have the fundamental (within FUND_FFILL_DAYS=120)
    first_120 = result.iloc[:120]
    assert first_120["pe"].notna().all()
    
    # Days beyond 120 should be NaN (beyond tolerance)
    beyond_120 = result.iloc[120:]
    assert beyond_120["pe"].isna().all()


def test_asof_join_empty_fundamentals():
    """Test as-of join with empty fundamentals."""
    trading_days = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "dt": [date(2024, 1, i) for i in range(1, 6)],
        }
    )
    
    fundamentals = pd.DataFrame(columns=["ticker", "asof", "pe", "pb"])
    
    result = asof_join_fundamentals(trading_days, fundamentals)
    
    # Should return trading days with NaN fundamentals
    assert len(result) == 5
    assert "pe" in result.columns
    assert "pb" in result.columns
    assert result["pe"].isna().all()
    assert result["pb"].isna().all()


def test_relative_valuation_with_sectors():
    """Test relative valuation with sector mapping."""
    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "XOM", "CVX"],
            "dt": [date(2024, 1, 1)] * 4,
            "pe": [20.0, 25.0, 10.0, 12.0],
            "pb": [5.0, 6.0, 2.0, 2.5],
        }
    )
    
    sector_mapping = {
        "AAPL": "Technology",
        "MSFT": "Technology",
        "XOM": "Energy",
        "CVX": "Energy",
    }
    
    result = relative_valuation(df, sector_mapping)
    
    # Check that relative metrics are computed
    assert "pe_vs_sector" in result.columns
    assert "pb_vs_sector" in result.columns
    
    # Technology stocks (PE 20, 25) vs Tech mean (22.5)
    aapl_pe_rel = result.loc[result["ticker"] == "AAPL", "pe_vs_sector"].values[0]
    msft_pe_rel = result.loc[result["ticker"] == "MSFT", "pe_vs_sector"].values[0]
    
    # AAPL should have lower relative PE (20/22.5 < 1)
    assert aapl_pe_rel < 1.0
    # MSFT should have higher relative PE (25/22.5 > 1)
    assert msft_pe_rel > 1.0


def test_relative_valuation_cross_sectional():
    """Test relative valuation fallback to cross-sectional z-scores."""
    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "XOM", "CVX"],
            "dt": [date(2024, 1, 1)] * 4,
            "pe": [20.0, 25.0, 10.0, 15.0],  # mean=17.5, std~6.45
            "pb": [5.0, 6.0, 2.0, 3.0],  # mean=4.0, std~1.83
        }
    )
    
    # No sector mapping provided
    result = relative_valuation(df, sector_mapping=None)
    
    # Check that relative metrics are computed as z-scores
    assert "pe_vs_sector" in result.columns
    assert "pb_vs_sector" in result.columns
    
    # All values should be finite
    assert result["pe_vs_sector"].notna().all()
    assert result["pb_vs_sector"].notna().all()
    
    # Lower PE should have positive z-score (better valuation)
    xom_pe_z = result.loc[result["ticker"] == "XOM", "pe_vs_sector"].values[0]
    msft_pe_z = result.loc[result["ticker"] == "MSFT", "pe_vs_sector"].values[0]
    assert xom_pe_z > msft_pe_z  # XOM has lower PE, so higher (better) z-score


def test_relative_valuation_handles_nans():
    """Test that relative valuation handles NaN values correctly."""
    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "XOM"],
            "dt": [date(2024, 1, 1)] * 3,
            "pe": [20.0, None, 10.0],
            "pb": [5.0, 6.0, None],
        }
    )
    
    result = relative_valuation(df, sector_mapping=None)
    
    # Result should have same number of rows
    assert len(result) == 3
    
    # Rows with NaN input should have NaN output
    assert pd.isna(result.loc[result["ticker"] == "MSFT", "pe_vs_sector"].values[0])
    assert pd.isna(result.loc[result["ticker"] == "XOM", "pb_vs_sector"].values[0])


def test_relative_valuation_empty_dataframe():
    """Test relative valuation with empty DataFrame."""
    df = pd.DataFrame(columns=["ticker", "dt", "pe", "pb"])
    
    result = relative_valuation(df)
    
    assert result.empty
