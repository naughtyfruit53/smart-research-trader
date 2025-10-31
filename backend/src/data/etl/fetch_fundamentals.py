"""Fundamentals data import and loading ETL."""

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from src.core.config import settings
from src.data.adapters.fund_screener import FundamentalScreenerAdapter
from src.data.etl.normalize import batch_dataframe, deduplicate_by_key, validate_required_columns
from src.db.models import Fundamental

logger = logging.getLogger(__name__)


def fetch_and_upsert_fundamentals(csv_path: str | None = None) -> int:
    """Import fundamentals from CSV and upsert to database.

    Args:
        csv_path: Path to CSV file (defaults to config FUND_CSV_PATH)

    Returns:
        Number of records upserted
    """
    if csv_path is None:
        csv_path = settings.FUND_CSV_PATH

    if not csv_path or not Path(csv_path).exists():
        logger.error(f"CSV file not found: {csv_path}")
        return 0

    logger.info(f"Importing fundamentals from {csv_path}")

    try:
        adapter = FundamentalScreenerAdapter()
        df = adapter.parse_csv(csv_path)

        if df.empty:
            logger.warning("No data in CSV")
            return 0

        # Validate required columns
        validate_required_columns(df, ["ticker", "asof"])

        # Deduplicate by primary key
        df = deduplicate_by_key(df, key_columns=["ticker", "asof"])

        # Batch upsert
        engine = create_engine(settings.DATABASE_URL)
        total_upserted = 0

        for batch in batch_dataframe(df, settings.FUNDAMENTAL_FETCH_BATCH_SIZE):
            records = batch.to_dict(orient="records")

            # Upsert using PostgreSQL INSERT ... ON CONFLICT
            stmt = insert(Fundamental).values(records)

            # Build set_ dict dynamically for all non-key columns
            update_cols = {
                col: getattr(stmt.excluded, col)
                for col in df.columns
                if col not in ["ticker", "asof"]
            }

            stmt = stmt.on_conflict_do_update(index_elements=["ticker", "asof"], set_=update_cols)

            with engine.begin() as conn:
                conn.execute(stmt)

            total_upserted += len(records)

        logger.info(f"Upserted {total_upserted} fundamental records")
        return total_upserted

    except Exception as e:
        logger.error(f"Error importing fundamentals: {e}")
        raise


if __name__ == "__main__":
    # Allow running as standalone script
    import sys

    logging.basicConfig(level=logging.INFO)

    csv_file = sys.argv[1] if len(sys.argv) > 1 else None
    result = fetch_and_upsert_fundamentals(csv_file)
    print(f"Fundamentals import completed: {result} records")
