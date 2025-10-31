"""Training pipeline with walk-forward cross-validation."""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Feature

from .model_lgbm import LGBMForecaster
from .timesplit import expanding_window_split, get_train_test_dates

logger = logging.getLogger(__name__)


def load_features_with_labels(
    db: Session,
    tickers: list[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    min_feature_count: int = 10,
) -> pd.DataFrame:
    """Load features with labels from database.

    Args:
        db: Database session
        tickers: Optional list of tickers to load
        start_date: Optional start date filter
        end_date: Optional end date filter
        min_feature_count: Minimum number of non-null features required

    Returns:
        DataFrame with columns [ticker, dt, label_ret_1d, feature1, feature2, ...]
    """
    stmt = select(Feature).where(Feature.label_ret_1d.isnot(None))

    if tickers:
        stmt = stmt.where(Feature.ticker.in_(tickers))
    if start_date:
        stmt = stmt.where(Feature.dt >= start_date)
    if end_date:
        stmt = stmt.where(Feature.dt <= end_date)

    features = db.execute(stmt).scalars().all()

    if not features:
        logger.warning("No features with labels found")
        return pd.DataFrame()

    # Convert to DataFrame
    rows = []
    for f in features:
        row = {"ticker": f.ticker, "dt": f.dt, "label_ret_1d": f.label_ret_1d}
        # Unpack features_json
        if f.features_json:
            row.update(f.features_json)
        rows.append(row)

    df = pd.DataFrame(rows)

    # Filter rows with sufficient non-null features
    feature_cols = [c for c in df.columns if c not in ["ticker", "dt", "label_ret_1d"]]
    if feature_cols:
        non_null_counts = df[feature_cols].notna().sum(axis=1)
        df = df[non_null_counts >= min_feature_count].copy()

    logger.info(
        f"Loaded {len(df)} feature rows with labels "
        f"({len(df['ticker'].unique())} tickers, "
        f"{len(feature_cols)} features)"
    )

    return df


def prepare_train_test_data(
    df: pd.DataFrame,
    train_indices: np.ndarray,
    test_indices: np.ndarray,
    target_col: str = "label_ret_1d",
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """Prepare train/test split from DataFrame.

    Args:
        df: DataFrame with features and labels
        train_indices: Training indices
        test_indices: Test indices
        target_col: Target column name

    Returns:
        (X_train, y_train, X_test, y_test)
    """
    # Get feature columns (exclude ticker, dt, and target)
    feature_cols = [c for c in df.columns if c not in ["ticker", "dt", target_col]]

    # Split data
    X_train = df.iloc[train_indices][feature_cols].copy()
    y_train = df.iloc[train_indices][target_col].copy()
    X_test = df.iloc[test_indices][feature_cols].copy()
    y_test = df.iloc[test_indices][target_col].copy()

    # Fill NaNs with 0 (safer than dropping for time-series)
    X_train = X_train.fillna(0)
    X_test = X_test.fillna(0)

    return X_train, y_train, X_test, y_test


def evaluate_predictions(y_true: np.ndarray | pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    """Evaluate predictions with multiple metrics.

    Args:
        y_true: True values
        y_pred: Predicted values

    Returns:
        Dictionary with metrics (rmse, mae, r2, direction_accuracy)
    """
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    # Direction accuracy: % of times sign is correct
    y_true_arr = np.array(y_true)
    direction_accuracy = np.mean(np.sign(y_true_arr) == np.sign(y_pred))

    return {
        "rmse": float(rmse),
        "mae": float(mae),
        "r2": float(r2),
        "direction_accuracy": float(direction_accuracy),
        "n_samples": len(y_true),
    }


def train_with_walk_forward_cv(
    db: Session,
    tickers: list[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    n_splits: int = 5,
    embargo_days: int = 2,
    test_size: float = 0.2,
    model_params: dict[str, Any] | None = None,
    output_dir: str | Path = "artifacts/models",
    save_importances: bool = True,
    seed: int = 42,
) -> dict[str, Any]:
    """Train model with walk-forward cross-validation.

    Args:
        db: Database session
        tickers: Optional list of tickers
        start_date: Optional start date
        end_date: Optional end date
        n_splits: Number of CV folds
        embargo_days: Embargo days between train and test
        test_size: Fraction for test set
        model_params: Optional model parameters
        output_dir: Directory to save artifacts
        save_importances: Whether to save feature importances
        seed: Random seed

    Returns:
        Dictionary with metrics and metadata
    """
    # Load data
    logger.info("Loading features with labels...")
    df = load_features_with_labels(db=db, tickers=tickers, start_date=start_date, end_date=end_date)

    if df.empty:
        raise ValueError("No data loaded. Cannot train model.")

    # Sort by date for time-series CV
    df = df.sort_values("dt").reset_index(drop=True)

    # Generate CV splits
    logger.info(f"Generating {n_splits} CV splits with {embargo_days}d embargo...")
    splits = expanding_window_split(
        dates=df["dt"], n_splits=n_splits, embargo_days=embargo_days, test_size=test_size, seed=seed
    )

    # Train on each fold
    fold_metrics = []
    all_importances = []

    for fold_idx, (train_idx, test_idx) in enumerate(splits):
        logger.info(f"\nFold {fold_idx + 1}/{len(splits)}")

        # Get date ranges
        train_start, train_end, test_start, test_end = get_train_test_dates(
            train_idx, test_idx, df["dt"]
        )
        logger.info(f"  Train: {train_start} to {train_end} ({len(train_idx)} samples)")
        logger.info(f"  Test:  {test_start} to {test_end} ({len(test_idx)} samples)")

        # Prepare data
        X_train, y_train, X_test, y_test = prepare_train_test_data(df, train_idx, test_idx)

        # Train model
        model = LGBMForecaster(random_state=seed, **(model_params or {}))

        # Use 20% of train as validation for early stopping
        val_size = int(len(X_train) * 0.2)
        if val_size > 0:
            X_train_fit = X_train.iloc[:-val_size]
            y_train_fit = y_train.iloc[:-val_size]
            X_val = X_train.iloc[-val_size:]
            y_val = y_train.iloc[-val_size:]
        else:
            X_train_fit = X_train
            y_train_fit = y_train
            X_val = None
            y_val = None

        model.fit(X_train_fit, y_train_fit, X_val=X_val, y_val=y_val, early_stopping_rounds=10)

        # Predict
        y_pred = model.predict(X_test)

        # Evaluate
        metrics = evaluate_predictions(y_test, y_pred)
        metrics["fold"] = fold_idx
        metrics["train_start"] = str(train_start)
        metrics["train_end"] = str(train_end)
        metrics["test_start"] = str(test_start)
        metrics["test_end"] = str(test_end)
        metrics["n_train"] = len(train_idx)
        metrics["n_test"] = len(test_idx)

        fold_metrics.append(metrics)

        logger.info(
            f"  RMSE: {metrics['rmse']:.4f}, MAE: {metrics['mae']:.4f}, "
            f"R2: {metrics['r2']:.4f}, Dir Acc: {metrics['direction_accuracy']:.2%}"
        )

        # Get feature importances
        if save_importances:
            importances = model.get_feature_importance()
            importances["fold"] = fold_idx
            all_importances.append(importances)

    # Aggregate metrics
    overall_metrics = {
        "rmse_mean": np.mean([m["rmse"] for m in fold_metrics]),
        "rmse_std": np.std([m["rmse"] for m in fold_metrics]),
        "mae_mean": np.mean([m["mae"] for m in fold_metrics]),
        "mae_std": np.std([m["mae"] for m in fold_metrics]),
        "r2_mean": np.mean([m["r2"] for m in fold_metrics]),
        "r2_std": np.std([m["r2"] for m in fold_metrics]),
        "direction_accuracy_mean": np.mean([m["direction_accuracy"] for m in fold_metrics]),
        "direction_accuracy_std": np.std([m["direction_accuracy"] for m in fold_metrics]),
        "n_folds": len(fold_metrics),
        "n_total_samples": len(df),
    }

    logger.info("\n=== Overall Metrics ===")
    logger.info(f"RMSE: {overall_metrics['rmse_mean']:.4f} ± {overall_metrics['rmse_std']:.4f}")
    logger.info(f"MAE: {overall_metrics['mae_mean']:.4f} ± {overall_metrics['mae_std']:.4f}")
    logger.info(f"R2: {overall_metrics['r2_mean']:.4f} ± {overall_metrics['r2_std']:.4f}")
    logger.info(
        f"Direction Accuracy: {overall_metrics['direction_accuracy_mean']:.2%} ± "
        f"{overall_metrics['direction_accuracy_std']:.2%}"
    )

    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {
        "overall_metrics": overall_metrics,
        "fold_metrics": fold_metrics,
        "config": {
            "n_splits": n_splits,
            "embargo_days": embargo_days,
            "test_size": test_size,
            "seed": seed,
            "model_params": model_params or {},
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "tickers": tickers,
        },
    }

    # Save metrics
    metrics_path = output_path / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved metrics to {metrics_path}")

    # Save feature importances
    if save_importances and all_importances:
        importances_df = pd.concat(all_importances, ignore_index=True)

        # Aggregate across folds
        avg_importances = (
            importances_df.groupby("feature")["importance"]
            .mean()
            .sort_values(ascending=False)
            .reset_index()
        )

        importances_path = output_path / "feature_importances.csv"
        avg_importances.to_csv(importances_path, index=False)
        logger.info(f"Saved feature importances to {importances_path}")

        # Log top 10 features
        logger.info("\n=== Top 10 Features ===")
        for _, row in avg_importances.head(10).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.2f}")

    return results
