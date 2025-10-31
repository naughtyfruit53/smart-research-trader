"""Tests for technical indicators computation."""

from datetime import date, timedelta

import pandas as pd
import pytest

from src.data.features.technicals import compute_technical_indicators


def test_technical_indicators_columns():
    """Test that all expected indicator columns are present."""
    # Create sample data with enough rows for indicators
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(250)]
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 250,
            "dt": dates,
            "open": [100.0 + i * 0.1 for i in range(250)],
            "high": [105.0 + i * 0.1 for i in range(250)],
            "low": [99.0 + i * 0.1 for i in range(250)],
            "close": [104.0 + i * 0.1 for i in range(250)],
            "volume": [1000000 + i * 100 for i in range(250)],
            "adj_close": [104.0 + i * 0.1 for i in range(250)],
        }
    )
    
    result = compute_technical_indicators(df)
    
    # Check expected columns exist
    expected_cols = [
        "sma_20", "sma_50", "sma_200",
        "ema_20", "ema_50", "ema_200",
        "rsi_14",
        "macd", "macd_signal", "macd_diff",
        "adx_14", "atr_14",
        "bb_high", "bb_low", "bb_mid", "bb_width",
        "momentum_20", "momentum_60",
        "rv_20"
    ]
    
    for col in expected_cols:
        assert col in result.columns, f"Missing column: {col}"


def test_technical_indicators_warmup():
    """Test that indicators handle warmup period correctly."""
    # Create sample data with just enough rows for shortest indicator
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(30)]
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 30,
            "dt": dates,
            "open": [100.0] * 30,
            "high": [105.0] * 30,
            "low": [99.0] * 30,
            "close": [104.0] * 30,
            "volume": [1000000] * 30,
            "adj_close": [104.0] * 30,
        }
    )
    
    result = compute_technical_indicators(df)
    
    # First rows should have NaN for indicators with warmup
    # SMA_20 should have values starting from row 19 (0-indexed)
    assert pd.isna(result.iloc[0]["sma_20"])
    assert not pd.isna(result.iloc[-1]["sma_20"])
    
    # SMA_200 should be NaN for all rows (not enough data)
    assert result["sma_200"].isna().all()


def test_technical_indicators_multiple_tickers():
    """Test that indicators are computed separately for each ticker."""
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(100)]
    
    # Create data for two tickers
    df = pd.concat([
        pd.DataFrame(
            {
                "ticker": ["AAPL"] * 100,
                "dt": dates,
                "open": [100.0 + i * 0.2 for i in range(100)],
                "high": [105.0 + i * 0.2 for i in range(100)],
                "low": [99.0 + i * 0.2 for i in range(100)],
                "close": [104.0 + i * 0.2 for i in range(100)],
                "volume": [1000000] * 100,
                "adj_close": [104.0 + i * 0.2 for i in range(100)],
            }
        ),
        pd.DataFrame(
            {
                "ticker": ["MSFT"] * 100,
                "dt": dates,
                "open": [200.0 + i * 0.1 for i in range(100)],
                "high": [205.0 + i * 0.1 for i in range(100)],
                "low": [199.0 + i * 0.1 for i in range(100)],
                "close": [204.0 + i * 0.1 for i in range(100)],
                "volume": [2000000] * 100,
                "adj_close": [204.0 + i * 0.1 for i in range(100)],
            }
        ),
    ], ignore_index=True)
    
    result = compute_technical_indicators(df)
    
    # Check that both tickers are present
    assert set(result["ticker"].unique()) == {"AAPL", "MSFT"}
    
    # Check that each ticker has 100 rows
    assert len(result[result["ticker"] == "AAPL"]) == 100
    assert len(result[result["ticker"] == "MSFT"]) == 100
    
    # Check that SMA values differ between tickers (different price levels)
    aapl_sma = result[result["ticker"] == "AAPL"]["sma_20"].dropna().mean()
    msft_sma = result[result["ticker"] == "MSFT"]["sma_20"].dropna().mean()
    assert aapl_sma != msft_sma


def test_technical_indicators_insufficient_data():
    """Test handling of insufficient data."""
    # Create data with very few rows
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(5)]
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "dt": dates,
            "open": [100.0] * 5,
            "high": [105.0] * 5,
            "low": [99.0] * 5,
            "close": [104.0] * 5,
            "volume": [1000000] * 5,
            "adj_close": [104.0] * 5,
        }
    )
    
    result = compute_technical_indicators(df)
    
    # Should still return a DataFrame with the same shape
    assert len(result) == 5
    assert set(result["ticker"]) == {"AAPL"}
    
    # All indicators should be NaN
    assert result["sma_20"].isna().all()
    assert result["rsi_14"].isna().all()


def test_technical_indicators_empty_dataframe():
    """Test handling of empty DataFrame."""
    df = pd.DataFrame(
        columns=["ticker", "dt", "open", "high", "low", "close", "volume", "adj_close"]
    )
    
    result = compute_technical_indicators(df)
    
    # Should maintain consistent schema with indicator columns
    assert result.empty
    assert "sma_20" in result.columns
    assert "rsi_14" in result.columns
