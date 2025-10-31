"""CLI for computing and upserting labels."""

import argparse
import logging
from datetime import date

from src.core.config import settings
from src.db.session import SessionLocal

from .labeling import compute_and_upsert_labels

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compute forward returns and upsert labels to features table"
    )

    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated list of tickers (default: all from TICKERS env)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date in YYYY-MM-DD format (default: all available)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date in YYYY-MM-DD format (default: all available)",
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=1,
        help="Forward return horizon in days (default: 1)",
    )

    return parser.parse_args()


def main():
    """Main CLI entrypoint."""
    args = parse_args()

    # Parse tickers
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",")]
    else:
        tickers = [t.strip() for t in settings.TICKERS.split(",")]

    # Parse dates
    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None

    logger.info("=" * 80)
    logger.info("Computing Forward Return Labels")
    logger.info("=" * 80)
    logger.info(f"Tickers: {tickers}")
    logger.info(f"Date range: {start_date or 'earliest'} to {end_date or 'latest'}")
    logger.info(f"Horizon: {args.horizon_days} day(s)")
    logger.info("=" * 80)

    # Compute labels
    db = SessionLocal()
    try:
        num_updated = compute_and_upsert_labels(
            db=db,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            horizon_days=args.horizon_days,
        )

        logger.info("\n" + "=" * 80)
        logger.info("Labeling Complete!")
        logger.info("=" * 80)
        logger.info(f"Updated {num_updated} feature rows with labels")

    except Exception as e:
        logger.error(f"Labeling failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
