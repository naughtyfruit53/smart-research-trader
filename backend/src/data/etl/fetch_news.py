"""News data fetching and sentiment analysis ETL."""

import logging
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from src.core.config import settings
from src.data.adapters.news_gdelt import GDELTNewsAdapter, RSSNewsAdapter
from src.data.etl.normalize import batch_dataframe, normalize_dates
from src.data.features.sentiment_model import analyze_sentiment
from src.db.models import News

logger = logging.getLogger(__name__)


def get_news_adapter():
    """Get news adapter based on configuration."""
    if settings.NEWS_PROVIDER == "rss":
        return RSSNewsAdapter()
    elif settings.NEWS_PROVIDER == "gdelt":
        return GDELTNewsAdapter()
    else:
        raise ValueError(f"Unknown news provider: {settings.NEWS_PROVIDER}")


def fetch_and_upsert_news(
    tickers: list[str] | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """Fetch news and perform sentiment analysis, then upsert to database.

    Args:
        tickers: List of ticker symbols (defaults to config TICKERS)
        start_date: Start date for fetching
        end_date: End date for fetching

    Returns:
        Number of records upserted
    """
    if tickers is None:
        tickers = [t.strip() for t in settings.TICKERS.split(",") if t.strip()]

    if not tickers:
        logger.warning("No tickers specified for news fetch")
        return 0

    logger.info(f"Fetching news for {len(tickers)} tickers")

    try:
        adapter = get_news_adapter()
        df = adapter.fetch_news(tickers, start_date, end_date)

        if df.empty:
            logger.warning("No news articles fetched")
            return 0

        # Normalize dates
        df = normalize_dates(df, "dt")

        # Perform sentiment analysis
        logger.info("Analyzing sentiment...")
        sentiments = []
        for text in df["headline"] + " " + df["summary"]:
            sentiment = analyze_sentiment(text)
            sentiments.append(sentiment)

        # Add sentiment columns
        df["sent_pos"] = [s["sent_pos"] for s in sentiments]
        df["sent_neg"] = [s["sent_neg"] for s in sentiments]
        df["sent_comp"] = [s["sent_comp"] for s in sentiments]

        # Batch upsert
        engine = create_engine(settings.DATABASE_URL)
        total_upserted = 0

        for batch in batch_dataframe(df, settings.NEWS_FETCH_BATCH_SIZE):
            records = batch.to_dict(orient="records")

            # Insert without ON CONFLICT since news has auto-incrementing ID
            # We don't deduplicate news articles - each fetch is new
            stmt = insert(News).values(records)

            with engine.begin() as conn:
                conn.execute(stmt)

            total_upserted += len(records)

        logger.info(f"Upserted {total_upserted} news records")
        return total_upserted

    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise


if __name__ == "__main__":
    # Allow running as standalone script
    logging.basicConfig(level=logging.INFO)
    result = fetch_and_upsert_news()
    print(f"News fetch completed: {result} records")
