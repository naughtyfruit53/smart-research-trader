"""News adapter for RSS feeds and GDELT (stub)."""

import logging
from datetime import UTC, datetime

import pandas as pd

try:
    import feedparser
except ImportError:
    feedparser = None

logger = logging.getLogger(__name__)


class RSSNewsAdapter:
    """Simple RSS feed adapter for news ingestion."""

    def __init__(self, feed_urls: list[str] | None = None):
        """Initialize RSS adapter.

        Args:
            feed_urls: List of RSS feed URLs (defaults to sample feeds)
        """
        self.feed_urls = feed_urls or [
            "https://feeds.finance.yahoo.com/rss/2.0/headline",
        ]

    def fetch_news(
        self,
        tickers: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch news articles from RSS feeds.

        Args:
            tickers: List of ticker symbols to filter for (best-effort matching)
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)

        Returns:
            DataFrame with columns: [dt, ticker, source, headline, summary, url]
        """
        if feedparser is None:
            raise ImportError(
                "feedparser package not installed. Install with: pip install feedparser"
            )

        logger.info(f"Fetching news for tickers: {tickers}")

        articles = []

        for feed_url in self.feed_urls:
            try:
                feed = feedparser.parse(feed_url)

                for entry in feed.entries:
                    # Extract timestamp
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        dt = datetime(*entry.published_parsed[:6], tzinfo=UTC)
                    else:
                        dt = datetime.now(UTC)

                    # Filter by date range if specified
                    if start_date and dt < start_date:
                        continue
                    if end_date and dt > end_date:
                        continue

                    # Extract article details
                    headline = entry.get("title", "")
                    summary = entry.get("summary", "") or entry.get("description", "")
                    url = entry.get("link", "")

                    # Match ticker in title or summary (simple keyword search)
                    matched_ticker = None
                    for ticker in tickers:
                        ticker_base = ticker.split(".")[0]  # Remove exchange suffix
                        if (
                            ticker_base.upper() in headline.upper()
                            or ticker_base.upper() in summary.upper()
                        ):
                            matched_ticker = ticker
                            break

                    # If no ticker matched, assign to first ticker (or skip)
                    if not matched_ticker:
                        matched_ticker = tickers[0] if tickers else "UNKNOWN"

                    articles.append(
                        {
                            "dt": dt,
                            "ticker": matched_ticker,
                            "source": feed_url,
                            "headline": headline,
                            "summary": summary,
                            "url": url,
                        }
                    )

            except Exception as e:
                logger.error(f"Error fetching feed {feed_url}: {e}")
                continue

        df = pd.DataFrame(articles)
        logger.info(f"Fetched {len(df)} news articles")
        return df


class GDELTNewsAdapter:
    """GDELT adapter stub for future implementation."""

    def fetch_news(
        self,
        tickers: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch news from GDELT.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with columns: [dt, ticker, source, headline, summary, url]

        Raises:
            NotImplementedError: This is a placeholder adapter
        """
        raise NotImplementedError("GDELT adapter not yet implemented. Use 'rss' provider.")
