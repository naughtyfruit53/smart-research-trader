"""Tests for news sentiment aggregation."""

from datetime import date, datetime, timedelta, UTC

import pandas as pd
import pytest

from src.data.features.sentiment import aggregate_news_sentiment


def test_sentiment_aggregation_basic():
    """Test basic sentiment aggregation."""
    trading_days = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "dt": [date(2024, 1, i) for i in range(1, 6)],
        }
    )
    
    news = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "dt": [
                datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
                datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 4, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 4, 15, 0, tzinfo=UTC),
            ],
            "sent_comp": [0.5, 0.7, -0.3, 0.8, 0.6],
            "url": [f"http://news.com/{i}" for i in range(5)],
        }
    )
    
    result = aggregate_news_sentiment(news, trading_days)
    
    # Check columns exist
    assert "sent_mean_comp" in result.columns
    assert "burst_3d" in result.columns
    assert "burst_7d" in result.columns
    assert "sent_ma_7d" in result.columns
    
    # Day 1 should have mean of 0.5 and 0.7 = 0.6
    day1 = result[result["dt"] == pd.Timestamp("2024-01-01")]
    assert len(day1) == 1
    assert abs(day1["sent_mean_comp"].values[0] - 0.6) < 0.01
    
    # Day 3 should have 0 sentiment (no news)
    day3 = result[result["dt"] == pd.Timestamp("2024-01-03")]
    assert day3["sent_mean_comp"].values[0] == 0.0


def test_sentiment_burst_counts():
    """Test burst count computation."""
    trading_days = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 10,
            "dt": [date(2024, 1, i) for i in range(1, 11)],
        }
    )
    
    # Create news with varying counts per day
    news_data = []
    for day in range(1, 11):
        count = min(day, 3)  # 1, 2, 3, 3, 3, ...
        for i in range(count):
            news_data.append(
                {
                    "ticker": "AAPL",
                    "dt": datetime(2024, 1, day, 10 + i, 0, tzinfo=UTC),
                    "sent_comp": 0.5,
                    "url": f"http://news.com/day{day}_{i}",
                }
            )
    
    news = pd.DataFrame(news_data)
    
    result = aggregate_news_sentiment(news, trading_days)
    
    # Day 1: 1 headline, burst_3d=1, burst_7d=1
    day1 = result[result["dt"] == pd.Timestamp("2024-01-01")]
    assert day1["burst_3d"].values[0] == 1
    assert day1["burst_7d"].values[0] == 1
    
    # Day 3: 3 headlines, burst_3d=1+2+3=6
    day3 = result[result["dt"] == pd.Timestamp("2024-01-03")]
    assert day3["burst_3d"].values[0] == 6
    
    # Day 7: burst_7d should be sum of days 1-7 = 1+2+3+3+3+3+3 = 18
    day7 = result[result["dt"] == pd.Timestamp("2024-01-07")]
    assert day7["burst_7d"].values[0] == 18


def test_sentiment_duplicates_ignored():
    """Test that duplicate URLs are ignored."""
    trading_days = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 2,
            "dt": [date(2024, 1, 1), date(2024, 1, 2)],
        }
    )
    
    # Same URL appears twice (duplicate)
    news = pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "dt": [
                datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
            ],
            "sent_comp": [0.5, 0.7],
            "url": ["http://news.com/same", "http://news.com/same"],
        }
    )
    
    result = aggregate_news_sentiment(news, trading_days)
    
    # Should only count the URL once
    day1 = result[result["dt"] == pd.Timestamp("2024-01-01")]
    assert day1["burst_3d"].values[0] == 1  # Only 1, not 2


def test_sentiment_no_news():
    """Test handling of days with no news."""
    trading_days = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "dt": [date(2024, 1, i) for i in range(1, 6)],
        }
    )
    
    # Empty news DataFrame
    news = pd.DataFrame(columns=["ticker", "dt", "sent_comp", "url"])
    
    result = aggregate_news_sentiment(news, trading_days)
    
    # All sentiment metrics should be 0 or 0.0
    assert (result["sent_mean_comp"] == 0.0).all()
    assert (result["burst_3d"] == 0).all()
    assert (result["burst_7d"] == 0).all()
    assert (result["sent_ma_7d"] == 0.0).all()


def test_sentiment_rolling_mean():
    """Test 7-day rolling mean computation."""
    trading_days = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 10,
            "dt": [date(2024, 1, i) for i in range(1, 11)],
        }
    )
    
    # Create news with consistent sentiment
    news_data = []
    for day in range(1, 11):
        news_data.append(
            {
                "ticker": "AAPL",
                "dt": datetime(2024, 1, day, 10, 0, tzinfo=UTC),
                "sent_comp": float(day) / 10.0,  # 0.1, 0.2, 0.3, ...
                "url": f"http://news.com/day{day}",
            }
        )
    
    news = pd.DataFrame(news_data)
    
    result = aggregate_news_sentiment(news, trading_days)
    
    # Day 1: ma_7d = 0.1 (only 1 value)
    day1 = result[result["dt"] == pd.Timestamp("2024-01-01")]
    assert abs(day1["sent_ma_7d"].values[0] - 0.1) < 0.01
    
    # Day 7: ma_7d = mean(0.1, 0.2, ..., 0.7) = 0.4
    day7 = result[result["dt"] == pd.Timestamp("2024-01-07")]
    expected_mean = sum(i / 10.0 for i in range(1, 8)) / 7
    assert abs(day7["sent_ma_7d"].values[0] - expected_mean) < 0.01


def test_sentiment_multiple_tickers():
    """Test sentiment aggregation for multiple tickers."""
    trading_days = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 3 + ["MSFT"] * 3,
            "dt": [date(2024, 1, i) for i in range(1, 4)] * 2,
        }
    )
    
    news = pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "dt": [
                datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
            ],
            "sent_comp": [0.5, 0.7, -0.3, -0.5],
            "url": [f"http://news.com/{i}" for i in range(4)],
        }
    )
    
    result = aggregate_news_sentiment(news, trading_days)
    
    # Check AAPL day 1
    aapl_day1 = result[(result["ticker"] == "AAPL") & (result["dt"] == pd.Timestamp("2024-01-01"))]
    assert abs(aapl_day1["sent_mean_comp"].values[0] - 0.5) < 0.01
    
    # Check MSFT day 1
    msft_day1 = result[(result["ticker"] == "MSFT") & (result["dt"] == pd.Timestamp("2024-01-01"))]
    assert abs(msft_day1["sent_mean_comp"].values[0] - (-0.3)) < 0.01
