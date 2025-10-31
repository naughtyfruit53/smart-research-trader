"""Example workflow demonstrating the complete ML pipeline.

This script shows how to:
1. Compute labels from prices
2. Train a model with walk-forward CV
3. Run inference and populate predictions

Run this after:
- Setting up the database
- Running ETL to populate prices, fundamentals, and news
- Running compute_features to populate features table
"""

import logging
from datetime import date

from src.core.config import settings
from src.db.session import SessionLocal
from src.ml.inference import run_inference
from src.ml.labeling import compute_and_upsert_labels
from src.ml.train import train_with_walk_forward_cv

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run the complete ML workflow."""
    # Configuration
    tickers = [t.strip() for t in settings.TICKERS.split(",")][:3]  # Use first 3 tickers
    start_date = date(2023, 1, 1)  # Adjust based on your data
    output_dir = "artifacts/models"

    logger.info("=" * 80)
    logger.info("ML Pipeline Example Workflow")
    logger.info("=" * 80)
    logger.info(f"Tickers: {tickers}")
    logger.info(f"Start date: {start_date}")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # Step 1: Compute labels
        logger.info("\nStep 1: Computing forward return labels...")
        num_labeled = compute_and_upsert_labels(
            db=db, tickers=tickers, start_date=start_date, horizon_days=1
        )
        logger.info(f"✓ Labeled {num_labeled} feature rows")

        # Step 2: Train model with walk-forward CV
        logger.info("\nStep 2: Training model with walk-forward CV...")
        results = train_with_walk_forward_cv(
            db=db,
            tickers=tickers,
            start_date=start_date,
            n_splits=3,  # Small for demo
            embargo_days=2,
            test_size=0.2,
            model_params={
                "n_estimators": 50,  # Small for demo
                "learning_rate": 0.05,
                "num_leaves": 31,
                "verbose": -1,
            },
            output_dir=output_dir,
            save_importances=True,
            seed=42,
        )

        logger.info("\n✓ Training complete!")
        logger.info(f"  RMSE: {results['overall_metrics']['rmse_mean']:.4f}")
        logger.info(f"  MAE: {results['overall_metrics']['mae_mean']:.4f}")
        logger.info(f"  R2: {results['overall_metrics']['r2_mean']:.4f}")
        logger.info(
            f"  Direction Accuracy: {results['overall_metrics']['direction_accuracy_mean']:.2%}"
        )

        # Step 3: Run inference (requires manually saving model first)
        logger.info("\nStep 3: Running inference...")
        logger.info("Note: To run inference, first save a trained model to a file, then use:")
        logger.info(f"  python -m src.ml.cli_inference {output_dir}/model.txt")

        # Example of how to save a model:
        # model = LGBMForecaster()
        # model.load(f"{output_dir}/model.txt")  # If you saved it
        # num_preds = run_inference(db, model_path=f"{output_dir}/model.txt")

        logger.info("\n" + "=" * 80)
        logger.info("Workflow Complete!")
        logger.info("=" * 80)
        logger.info(f"Metrics: {output_dir}/metrics.json")
        logger.info(f"Feature importances: {output_dir}/feature_importances.csv")
        logger.info("\nNext steps:")
        logger.info("1. Review metrics and feature importances")
        logger.info("2. Tune model hyperparameters if needed")
        logger.info("3. Train on full dataset and save model")
        logger.info("4. Run inference to generate predictions")

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
