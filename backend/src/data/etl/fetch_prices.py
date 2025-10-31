"""Price data fetching and loading ETL."""

import logging
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from src.core.config import settings
from src.data.adapters.prices_nse import NSEPriceAdapter
from src.data.adapters.prices_yf import YFinancePriceAdapter
from src.data.etl.corporate_actions import normalize_splits_dividends
from src.data.etl.normalize import batch_dataframe, deduplicate_by_key
from src.db.models import Price

logger = logging.getLogger(__name__)


def get_price_adapter():
    """Get price adapter based on configuration."""
    if settings.PRICE_PROVIDER == "yf":
        return YFinancePriceAdapter()
    elif settings.PRICE_PROVIDER == "nse":
        return NSEPriceAdapter()
    else:
        raise ValueError(f"Unknown price provider: {settings.PRICE_PROVIDER}")


def fetch_and_upsert_prices(
    tickers: list[str] | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, int]:
    """Fetch prices for tickers and upsert to database.

    Args:
        tickers: List of ticker symbols (defaults to config TICKERS)
        start_date: Start date for fetching
        end_date: End date for fetching

    Returns:
        Dictionary with statistics: {ticker: row_count}
    """
    if tickers is None:
        tickers = [t.strip() for t in settings.TICKERS.split(",") if t.strip()]

    if not tickers:
        logger.warning("No tickers specified for price fetch")
        return {}

    logger.info(f"Fetching prices for {len(tickers)} tickers")

    adapter = get_price_adapter()
    engine = create_engine(settings.DATABASE_URL)
    stats = {}

    for ticker in tickers:
        try:
            # Fetch data
            df = adapter.fetch_prices(ticker, start_date, end_date)

            if df.empty:
                logger.warning(f"No data fetched for {ticker}")
                stats[ticker] = 0
                continue

            # Normalize corporate actions
            df = normalize_splits_dividends(df)

            # Deduplicate by primary key
            df = deduplicate_by_key(df, key_columns=["ticker", "dt"])

            # Batch upsert
            total_upserted = 0
            for batch in batch_dataframe(df, settings.PRICE_FETCH_BATCH_SIZE):
                records = batch.to_dict(orient="records")

                # Upsert using PostgreSQL INSERT ... ON CONFLICT
                stmt = insert(Price).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["ticker", "dt"],
                    set_={
                        "open": stmt.excluded.open,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                        "close": stmt.excluded.close,
                        "volume": stmt.excluded.volume,
                        "adj_close": stmt.excluded.adj_close,
                    },
                )

                with engine.begin() as conn:
                    conn.execute(stmt)

                total_upserted += len(records)

            logger.info(f"Upserted {total_upserted} price records for {ticker}")
            stats[ticker] = total_upserted

        except Exception as e:
            logger.error(f"Error processing prices for {ticker}: {e}")
            stats[ticker] = -1

    return stats


if __name__ == "__main__":
    # Allow running as standalone script
    logging.basicConfig(level=logging.INFO)
    result = fetch_and_upsert_prices()
    print(f"Price fetch completed: {result}")
