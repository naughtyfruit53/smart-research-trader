"""Tests for fundamentals CSV import."""

import tempfile
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from src.data.etl.fetch_fundamentals import fetch_and_upsert_fundamentals
from src.db.models import Fundamental


def test_fundamentals_csv_parse_and_upsert(db_session: Session):
    """Test CSV import and upsert to database."""
    # Create temp CSV file
    csv_data = """Ticker,As Of,P/E,P/B,ROE,ROCE,D/E
AAPL,2024-01-01,25.5,5.2,0.35,0.28,1.5
GOOGL,2024-01-01,22.3,4.8,0.32,0.25,1.2
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_data)
        csv_path = f.name

    try:
        # Import data
        count = fetch_and_upsert_fundamentals(csv_path)

        assert count == 2

        # Verify data in database
        aapl = (
            db_session.query(Fundamental)
            .filter(Fundamental.ticker == "AAPL", Fundamental.asof == date(2024, 1, 1))
            .first()
        )
        assert aapl is not None
        assert aapl.pe == 25.5
        assert aapl.pb == 5.2
        assert aapl.roe == 0.35

        googl = (
            db_session.query(Fundamental)
            .filter(Fundamental.ticker == "GOOGL", Fundamental.asof == date(2024, 1, 1))
            .first()
        )
        assert googl is not None
        assert googl.pe == 22.3

    finally:
        # Cleanup
        Path(csv_path).unlink()


def test_fundamentals_idempotent_upsert(db_session: Session):
    """Test that re-running import is idempotent."""
    csv_data = """Ticker,As Of,P/E,P/B
MSFT,2024-01-01,30.0,6.0
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_data)
        csv_path = f.name

    try:
        # First import
        count1 = fetch_and_upsert_fundamentals(csv_path)
        assert count1 == 1

        # Check count in DB
        count_db1 = (
            db_session.query(Fundamental)
            .filter(Fundamental.ticker == "MSFT", Fundamental.asof == date(2024, 1, 1))
            .count()
        )
        assert count_db1 == 1

        # Second import (should update, not duplicate)
        count2 = fetch_and_upsert_fundamentals(csv_path)
        assert count2 == 1

        # Check count in DB (should still be 1)
        count_db2 = (
            db_session.query(Fundamental)
            .filter(Fundamental.ticker == "MSFT", Fundamental.asof == date(2024, 1, 1))
            .count()
        )
        assert count_db2 == 1

    finally:
        Path(csv_path).unlink()


def test_fundamentals_csv_missing_file():
    """Test handling of missing CSV file."""
    result = fetch_and_upsert_fundamentals("/nonexistent/file.csv")
    assert result == 0
