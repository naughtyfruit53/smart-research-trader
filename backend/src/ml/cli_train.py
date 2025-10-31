"""CLI for training ML models."""

import argparse
import logging
from datetime import date

from src.core.config import settings
from src.db.session import SessionLocal

from .train import train_with_walk_forward_cv

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Train LightGBM forecasting model")

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
    parser.add_argument("--n-splits", type=int, default=5, help="Number of CV folds (default: 5)")
    parser.add_argument(
        "--embargo-days",
        type=int,
        default=2,
        help="Embargo days between train and test (default: 2)",
    )
    parser.add_argument(
        "--test-size", type=float, default=0.2, help="Test set size as fraction (default: 0.2)"
    )
    parser.add_argument(
        "--n-estimators", type=int, default=100, help="Number of boosting rounds (default: 100)"
    )
    parser.add_argument(
        "--learning-rate", type=float, default=0.05, help="Learning rate (default: 0.05)"
    )
    parser.add_argument(
        "--num-leaves", type=int, default=31, help="Max number of leaves (default: 31)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/models",
        help="Output directory for artifacts (default: artifacts/models)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--no-importances", action="store_true", help="Don't save feature importances"
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

    # Model parameters
    model_params = {
        "n_estimators": args.n_estimators,
        "learning_rate": args.learning_rate,
        "num_leaves": args.num_leaves,
    }

    logger.info("=" * 80)
    logger.info("Training LightGBM Forecasting Model")
    logger.info("=" * 80)
    logger.info(f"Tickers: {tickers}")
    logger.info(f"Date range: {start_date or 'earliest'} to {end_date or 'latest'}")
    logger.info(
        f"CV: {args.n_splits} folds, {args.embargo_days}d embargo, {args.test_size:.0%} test"
    )
    logger.info(
        f"Model: {args.n_estimators} estimators, lr={args.learning_rate}, leaves={args.num_leaves}"
    )
    logger.info(f"Output: {args.output_dir}")
    logger.info("=" * 80)

    # Train
    db = SessionLocal()
    try:
        results = train_with_walk_forward_cv(
            db=db,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            n_splits=args.n_splits,
            embargo_days=args.embargo_days,
            test_size=args.test_size,
            model_params=model_params,
            output_dir=args.output_dir,
            save_importances=not args.no_importances,
            seed=args.seed,
        )

        logger.info("\n" + "=" * 80)
        logger.info("Training Complete!")
        logger.info("=" * 80)
        logger.info(f"Overall RMSE: {results['overall_metrics']['rmse_mean']:.4f}")
        logger.info(f"Overall MAE: {results['overall_metrics']['mae_mean']:.4f}")
        logger.info(f"Overall R2: {results['overall_metrics']['r2_mean']:.4f}")
        logger.info(
            f"Direction Accuracy: {results['overall_metrics']['direction_accuracy_mean']:.2%}"
        )

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
