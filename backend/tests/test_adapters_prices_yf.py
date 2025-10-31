"""Tests for yfinance price adapter."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.adapters.prices_yf import YFinancePriceAdapter


def test_yfinance_adapter_fetch_prices():
    """Test YFinance adapter fetches and normalizes data correctly."""
    # Mock yfinance response
    mock_data = pd.DataFrame(
        {
            "Date": pd.date_range(start="2024-01-01", periods=5, freq="D"),
            "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "High": [105.0, 106.0, 107.0, 108.0, 109.0],
            "Low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "Close": [104.0, 105.0, 106.0, 107.0, 108.0],
            "Volume": [1000000, 1100000, 1200000, 1300000, 1400000],
            "Adj Close": [104.0, 105.0, 106.0, 107.0, 108.0],
        }
    )
    mock_data = mock_data.set_index("Date")

    # Mock yf module
    mock_yf = MagicMock()
    mock_instance = MagicMock()
    mock_instance.history.return_value = mock_data
    mock_yf.Ticker.return_value = mock_instance

    with patch("src.data.adapters.prices_yf.yf", mock_yf):
        adapter = YFinancePriceAdapter()
        result = adapter.fetch_prices("AAPL", datetime(2024, 1, 1), datetime(2024, 1, 5))

        # Verify columns are correct
        expected_cols = ["ticker", "dt", "open", "high", "low", "close", "volume", "adj_close"]
        assert list(result.columns) == expected_cols

        # Verify ticker is added
        assert all(result["ticker"] == "AAPL")

        # Verify data types
        assert result["volume"].dtype == "int64"
        assert all(isinstance(d, date) for d in result["dt"])

        # Verify row count
        assert len(result) == 5


def test_yfinance_adapter_empty_response():
    """Test adapter handles empty response gracefully."""
    mock_data = pd.DataFrame()

    mock_yf = MagicMock()
    mock_instance = MagicMock()
    mock_instance.history.return_value = mock_data
    mock_yf.Ticker.return_value = mock_instance

    with patch("src.data.adapters.prices_yf.yf", mock_yf):
        adapter = YFinancePriceAdapter()
        result = adapter.fetch_prices("INVALID", datetime(2024, 1, 1), datetime(2024, 1, 5))

        assert result.empty


def test_yfinance_adapter_retry_on_error():
    """Test adapter retries on network errors."""
    mock_yf = MagicMock()
    mock_yf.Ticker.side_effect = ConnectionError("Network error")

    with patch("src.data.adapters.prices_yf.yf", mock_yf):
        adapter = YFinancePriceAdapter()

        with pytest.raises(ConnectionError):
            adapter.fetch_prices("AAPL", datetime(2024, 1, 1), datetime(2024, 1, 5))

        # Should attempt 3 times (initial + 2 retries)
        assert mock_yf.Ticker.call_count == 3
