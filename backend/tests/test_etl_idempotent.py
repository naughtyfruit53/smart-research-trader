"""Tests for ETL idempotency."""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
from sqlalchemy.orm import Session

from src.data.etl.fetch_prices import fetch_and_upsert_prices
from src.db.models import Price


def test_price_fetch_idempotent(db_session: Session):
    """Test that price fetching is idempotent - no duplicate records."""
    # Mock price data
    mock_data = pd.DataFrame(
        {
            "Date": pd.date_range(start="2024-01-01", periods=3, freq="D"),
            "Open": [100.0, 101.0, 102.0],
            "High": [105.0, 106.0, 107.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [104.0, 105.0, 106.0],
            "Volume": [1000000, 1100000, 1200000],
            "Adj Close": [104.0, 105.0, 106.0],
        }
    )
    mock_data = mock_data.set_index("Date")

    with patch("src.data.etl.fetch_prices.get_price_adapter") as mock_adapter:
        mock_instance = MagicMock()
        mock_instance.fetch_prices.return_value = pd.DataFrame(
            {
                "ticker": ["AAPL"] * 3,
                "dt": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
                "open": [100.0, 101.0, 102.0],
                "high": [105.0, 106.0, 107.0],
                "low": [99.0, 100.0, 101.0],
                "close": [104.0, 105.0, 106.0],
                "volume": [1000000, 1100000, 1200000],
                "adj_close": [104.0, 105.0, 106.0],
            }
        )
        mock_adapter.return_value = mock_instance

        # First fetch
        result1 = fetch_and_upsert_prices(tickers=["AAPL"])
        assert result1["AAPL"] == 3

        # Check count in DB
        count1 = db_session.query(Price).filter(Price.ticker == "AAPL").count()
        assert count1 == 3

        # Second fetch (should update, not duplicate)
        result2 = fetch_and_upsert_prices(tickers=["AAPL"])
        assert result2["AAPL"] == 3

        # Check count in DB (should still be 3)
        count2 = db_session.query(Price).filter(Price.ticker == "AAPL").count()
        assert count2 == 3


def test_price_fetch_updates_existing(db_session: Session):
    """Test that price fetching updates existing records."""
    # Insert initial data
    initial_price = Price(
        ticker="MSFT",
        dt=date(2024, 1, 1),
        open=200.0,
        high=205.0,
        low=199.0,
        close=204.0,
        volume=2000000,
        adj_close=204.0,
    )
    db_session.add(initial_price)
    db_session.commit()

    # Mock updated data
    with patch("src.data.etl.fetch_prices.get_price_adapter") as mock_adapter:
        mock_instance = MagicMock()
        mock_instance.fetch_prices.return_value = pd.DataFrame(
            {
                "ticker": ["MSFT"],
                "dt": [date(2024, 1, 1)],
                "open": [201.0],  # Updated
                "high": [206.0],  # Updated
                "low": [200.0],  # Updated
                "close": [205.0],  # Updated
                "volume": [2100000],  # Updated
                "adj_close": [205.0],  # Updated
            }
        )
        mock_adapter.return_value = mock_instance

        # Fetch again
        result = fetch_and_upsert_prices(tickers=["MSFT"])
        assert result["MSFT"] == 1

        # Verify update
        updated_price = (
            db_session.query(Price)
            .filter(Price.ticker == "MSFT", Price.dt == date(2024, 1, 1))
            .first()
        )
        assert updated_price.close == 205.0
        assert updated_price.volume == 2100000

        # Ensure only one record exists
        count = db_session.query(Price).filter(Price.ticker == "MSFT").count()
        assert count == 1
