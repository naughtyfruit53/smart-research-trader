"""CLI for running inference and populating preds table."""

import argparse
import logging
from datetime import date
from pathlib import Path

from src.core.config import settings
from src.db.session import SessionLocal

from .inference import run_inference

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run inference and populate preds table")

    parser.add_argument("model_path", type=str, help="Path to trained model file (.txt)")
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated list of tickers (default: all from TICKERS env)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date in YYYY-MM-DD format (default: latest available)",
    )
    parser.add_argument(
        "--horizon", type=str, default="1d", help="Prediction horizon label (default: 1d)"
    )

    return parser.parse_args()


def main():
    """Main CLI entrypoint."""
    args = parse_args()

    # Validate model path
    model_path = Path(args.model_path)
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return

    # Parse tickers
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",")]
    else:
        tickers = [t.strip() for t in settings.TICKERS.split(",")]

    # Parse date
    target_date = date.fromisoformat(args.date) if args.date else None

    logger.info("=" * 80)
    logger.info("Running Inference Pipeline")
    logger.info("=" * 80)
    logger.info(f"Model: {model_path}")
    logger.info(f"Tickers: {tickers}")
    logger.info(f"Date: {target_date or 'latest'}")
    logger.info(f"Horizon: {args.horizon}")
    logger.info("=" * 80)

    # Run inference
    db = SessionLocal()
    try:
        num_preds = run_inference(
            db=db,
            model_path=model_path,
            tickers=tickers,
            target_date=target_date,
            horizon=args.horizon,
        )

        logger.info("\n" + "=" * 80)
        logger.info("Inference Complete!")
        logger.info("=" * 80)
        logger.info(f"Generated {num_preds} predictions")

    except Exception as e:
        logger.error(f"Inference failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
