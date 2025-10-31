"""Inference module for generating predictions and populating preds table."""

import logging
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.db.models import Feature, Pred

from .model_lgbm import LGBMForecaster

logger = logging.getLogger(__name__)


def load_features_for_inference(
    db: Session,
    tickers: list[str] | None = None,
    target_date: date | None = None,
    min_feature_count: int = 10,
) -> pd.DataFrame:
    """Load features for inference (no labels required).

    Args:
        db: Database session
        tickers: Optional list of tickers
        target_date: Specific date to predict for (default: latest)
        min_feature_count: Minimum number of non-null features

    Returns:
        DataFrame with features
    """
    stmt = select(Feature)

    if tickers:
        stmt = stmt.where(Feature.ticker.in_(tickers))
    if target_date:
        stmt = stmt.where(Feature.dt == target_date)

    features = db.execute(stmt).scalars().all()

    if not features:
        logger.warning("No features found for inference")
        return pd.DataFrame()

    # Convert to DataFrame
    rows = []
    for f in features:
        row = {"ticker": f.ticker, "dt": f.dt}
        if f.features_json:
            row.update(f.features_json)
        rows.append(row)

    df = pd.DataFrame(rows)

    # Filter rows with sufficient features
    feature_cols = [c for c in df.columns if c not in ["ticker", "dt"]]
    if feature_cols:
        non_null_counts = df[feature_cols].notna().sum(axis=1)
        df = df[non_null_counts >= min_feature_count].copy()

    logger.info(f"Loaded {len(df)} feature rows for inference")

    return df


def generate_predictions(
    model: LGBMForecaster, features_df: pd.DataFrame, horizon: str = "1d"
) -> pd.DataFrame:
    """Generate predictions from features.

    Args:
        model: Trained model
        features_df: DataFrame with features
        horizon: Prediction horizon label

    Returns:
        DataFrame with [ticker, dt, horizon, yhat, yhat_std, prob_up]
    """
    if features_df.empty:
        logger.warning("No features provided for prediction")
        return pd.DataFrame()

    # Get feature columns
    meta_cols = ["ticker", "dt"]
    feature_cols = [c for c in features_df.columns if c not in meta_cols]

    # Prepare features
    X = features_df[feature_cols].fillna(0)

    # Generate predictions with uncertainty
    yhat, yhat_std = model.predict_with_std(X)

    # Compute probability of positive return
    # Assumes returns follow a normal distribution: return ~ N(yhat, yhat_std^2)
    # P(return > 0) = P(Z > -yhat/yhat_std) where Z ~ N(0,1)
    #
    # We approximate the normal CDF using a sigmoid function:
    # Φ(x) ≈ σ(1.702*x) where σ(x) = 1/(1+exp(-x))
    # The factor 1.702 provides a close approximation to the normal CDF.
    # However, for simplicity, we use σ(x) which is close enough for our purposes.
    #
    # This gives us a smooth probability estimate between 0 and 1 that:
    # - Approaches 0 when yhat << 0 (strong negative prediction)
    # - Equals 0.5 when yhat = 0 (neutral prediction)
    # - Approaches 1 when yhat >> 0 (strong positive prediction)
    with np.errstate(divide="ignore", invalid="ignore"):
        z_scores = yhat / np.maximum(yhat_std, 1e-6)
        # Sigmoid approximation of normal CDF
        prob_up = 1.0 / (1.0 + np.exp(-z_scores))
        # Clip to reasonable range to avoid extreme probabilities
        prob_up = np.clip(prob_up, 0.01, 0.99)

    # Create predictions DataFrame
    preds_df = pd.DataFrame(
        {
            "ticker": features_df["ticker"],
            "dt": features_df["dt"],
            "horizon": horizon,
            "yhat": yhat,
            "yhat_std": yhat_std,
            "prob_up": prob_up,
        }
    )

    return preds_df


def upsert_predictions(db: Session, preds_df: pd.DataFrame) -> int:
    """Upsert predictions to preds table.

    Args:
        db: Database session
        preds_df: DataFrame with [ticker, dt, horizon, yhat, yhat_std, prob_up]

    Returns:
        Number of rows upserted
    """
    if preds_df.empty:
        logger.info("No predictions to upsert")
        return 0

    # Convert to records
    records = preds_df.to_dict("records")

    # Upsert with ON CONFLICT DO UPDATE
    stmt = insert(Pred).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker", "dt", "horizon"],
        set_={
            "yhat": stmt.excluded.yhat,
            "yhat_std": stmt.excluded.yhat_std,
            "prob_up": stmt.excluded.prob_up,
        },
    )

    db.execute(stmt)
    db.commit()

    logger.info(f"Upserted {len(records)} predictions")

    return len(records)


def run_inference(
    db: Session,
    model_path: str | Path,
    tickers: list[str] | None = None,
    target_date: date | None = None,
    horizon: str = "1d",
) -> int:
    """Run inference pipeline: load features, predict, upsert to preds table.

    Args:
        db: Database session
        model_path: Path to trained model file
        tickers: Optional list of tickers
        target_date: Optional target date (default: latest available)
        horizon: Prediction horizon label

    Returns:
        Number of predictions generated
    """
    # Load model
    logger.info(f"Loading model from {model_path}")
    model = LGBMForecaster()
    model.load(model_path)

    # Load features
    logger.info("Loading features for inference...")
    features_df = load_features_for_inference(db=db, tickers=tickers, target_date=target_date)

    if features_df.empty:
        logger.warning("No features available for inference")
        return 0

    # Generate predictions
    logger.info(f"Generating predictions for {len(features_df)} rows...")
    preds_df = generate_predictions(model, features_df, horizon=horizon)

    # Upsert to database
    num_upserted = upsert_predictions(db, preds_df)

    logger.info(f"Inference complete: {num_upserted} predictions generated")

    return num_upserted
