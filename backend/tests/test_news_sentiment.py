"""Tests for news fetching and sentiment analysis."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from src.data.etl.fetch_news import fetch_and_upsert_news
from src.data.features.sentiment_model import analyze_sentiment
from src.db.models import News


def test_sentiment_model_fallback():
    """Test sentiment model fallback when ENABLE_FINBERT=false."""
    # Should return neutral sentiment
    result = analyze_sentiment("This is a positive news headline")

    assert "sent_pos" in result
    assert "sent_neg" in result
    assert "sent_comp" in result

    # With ENABLE_FINBERT=false, should return zeros
    assert result["sent_pos"] == 0.0
    assert result["sent_neg"] == 0.0
    assert result["sent_comp"] == 0.0


@pytest.mark.skipif(True, reason="FinBERT test skipped in CI - requires model download")
def test_sentiment_model_with_finbert():
    """Test sentiment model with FinBERT enabled (skip in CI)."""
    # This test would require ENABLE_FINBERT=true
    from src.core.config import settings

    settings.ENABLE_FINBERT = True

    result = analyze_sentiment("Stock prices surge on strong earnings report")

    # Should have some sentiment scores
    assert "sent_pos" in result
    assert "sent_neg" in result
    assert "sent_comp" in result


def test_news_fetch_and_upsert_mock(db_session: Session):
    """Test news fetching with mocked adapter."""
    mock_news_df = pd.DataFrame(
        [
            {
                "dt": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                "ticker": "AAPL",
                "source": "test_rss",
                "headline": "Apple announces new product",
                "summary": "Apple has launched a new device",
                "url": "https://example.com/news1",
            },
            {
                "dt": datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
                "ticker": "GOOGL",
                "source": "test_rss",
                "headline": "Google unveils AI breakthrough",
                "summary": "Google demonstrates new AI capabilities",
                "url": "https://example.com/news2",
            },
        ]
    )

    with patch("src.data.etl.fetch_news.get_news_adapter") as mock_adapter:
        mock_instance = MagicMock()
        mock_instance.fetch_news.return_value = mock_news_df
        mock_adapter.return_value = mock_instance

        # Fetch and upsert news
        count = fetch_and_upsert_news(tickers=["AAPL", "GOOGL"])

        assert count == 2

        # Verify data in database
        news_items = db_session.query(News).all()
        assert len(news_items) == 2

        # Check that sentiment fields exist
        for item in news_items:
            assert item.sent_pos is not None
            assert item.sent_neg is not None
            assert item.sent_comp is not None


def test_news_fetch_empty_result():
    """Test news fetching with empty results."""
    empty_df = pd.DataFrame()

    with patch("src.data.etl.fetch_news.get_news_adapter") as mock_adapter:
        mock_instance = MagicMock()
        mock_instance.fetch_news.return_value = empty_df
        mock_adapter.return_value = mock_instance

        count = fetch_and_upsert_news(tickers=["AAPL"])

        assert count == 0
