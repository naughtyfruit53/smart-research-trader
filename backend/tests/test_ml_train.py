"""Tests for ML training pipeline."""

import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.db.models import Feature
from src.ml.train import (
    evaluate_predictions,
    load_features_with_labels,
    prepare_train_test_data,
    train_with_walk_forward_cv,
)


@pytest.fixture
def sample_features_with_labels(db_session):
    """Create sample features with labels for testing."""
    features = []

    # Create features for 2 tickers over 60 days
    for ticker in ["AAPL", "MSFT"]:
        for day in range(1, 61):
            dt = date(2024, 1, 1) + pd.Timedelta(days=day - 1)

            # Simple synthetic features
            features_json = {
                "sma_20": 100.0 + day * 0.5,
                "rsi_14": 50.0 + (day % 10) * 2,
                "momentum_20": 0.01 * (day % 20),
                "volatility": 0.02,
                "composite_score": 0.5 + 0.01 * day,
            }

            # Label: small positive trend with noise
            label = 0.001 * day + 0.0001 * (day % 5)

            feat = Feature(ticker=ticker, dt=dt, features_json=features_json, label_ret_1d=label)
            features.append(feat)

    db_session.add_all(features)
    db_session.commit()

    return features


def test_load_features_with_labels(sample_features_with_labels, db_session):
    """Test loading features with labels."""
    df = load_features_with_labels(db_session)

    # Should have 2 tickers * 60 days = 120 rows
    assert len(df) == 120

    # Should have key columns
    assert "ticker" in df.columns
    assert "dt" in df.columns
    assert "label_ret_1d" in df.columns

    # Should have feature columns
    assert "sma_20" in df.columns
    assert "rsi_14" in df.columns

    # Check no missing labels
    assert df["label_ret_1d"].notna().all()


def test_load_features_with_labels_filtered(sample_features_with_labels, db_session):
    """Test loading features with filters."""
    df = load_features_with_labels(
        db_session, tickers=["AAPL"], start_date=date(2024, 1, 10), end_date=date(2024, 1, 20)
    )

    # Should have only AAPL
    assert (df["ticker"] == "AAPL").all()

    # Should be within date range
    assert df["dt"].min() >= date(2024, 1, 10)
    assert df["dt"].max() <= date(2024, 1, 20)


def test_load_features_no_labels(db_session):
    """Test loading when no features have labels."""
    # Add feature without label
    feat = Feature(
        ticker="TEST", dt=date(2024, 1, 1), features_json={"value": 1.0}, label_ret_1d=None
    )
    db_session.add(feat)
    db_session.commit()

    df = load_features_with_labels(db_session, tickers=["TEST"])

    assert df.empty


def test_prepare_train_test_data():
    """Test preparing train/test splits."""
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 10,
            "dt": pd.date_range("2024-01-01", periods=10),
            "label_ret_1d": [0.01] * 10,
            "feat1": range(10),
            "feat2": range(10, 20),
        }
    )

    train_idx = [0, 1, 2, 3, 4, 5]
    test_idx = [7, 8, 9]

    X_train, y_train, X_test, y_test = prepare_train_test_data(df, train_idx, test_idx)

    # Check shapes
    assert len(X_train) == 6
    assert len(y_train) == 6
    assert len(X_test) == 3
    assert len(y_test) == 3

    # Check columns
    assert "feat1" in X_train.columns
    assert "feat2" in X_train.columns
    assert "ticker" not in X_train.columns
    assert "label_ret_1d" not in X_train.columns


def test_evaluate_predictions():
    """Test prediction evaluation."""
    y_true = [0.01, -0.02, 0.03, -0.01, 0.02]
    y_pred = [0.011, -0.018, 0.028, -0.012, 0.019]

    metrics = evaluate_predictions(y_true, y_pred)

    assert "rmse" in metrics
    assert "mae" in metrics
    assert "r2" in metrics
    assert "direction_accuracy" in metrics
    assert "n_samples" in metrics

    # Check reasonable values
    assert metrics["rmse"] > 0
    assert metrics["mae"] > 0
    assert -1 <= metrics["r2"] <= 1
    assert 0 <= metrics["direction_accuracy"] <= 1
    assert metrics["n_samples"] == 5

    # Direction accuracy should be perfect for this example
    assert metrics["direction_accuracy"] == 1.0


def test_train_with_walk_forward_cv(sample_features_with_labels, db_session):
    """Test full training pipeline with walk-forward CV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        results = train_with_walk_forward_cv(
            db_session,
            tickers=["AAPL"],
            n_splits=3,
            embargo_days=1,
            test_size=0.2,
            model_params={"n_estimators": 10, "verbose": -1},
            output_dir=tmpdir,
            save_importances=True,
            seed=42,
        )

        # Check results structure
        assert "overall_metrics" in results
        assert "fold_metrics" in results
        assert "config" in results

        # Check overall metrics
        overall = results["overall_metrics"]
        assert "rmse_mean" in overall
        assert "mae_mean" in overall
        assert "r2_mean" in overall
        assert "direction_accuracy_mean" in overall
        assert "n_folds" in overall

        # Should have 3 folds
        assert overall["n_folds"] == 3
        assert len(results["fold_metrics"]) == 3

        # Check fold metrics
        for fold_metrics in results["fold_metrics"]:
            assert "rmse" in fold_metrics
            assert "mae" in fold_metrics
            assert "r2" in fold_metrics
            assert "fold" in fold_metrics
            assert "n_train" in fold_metrics
            assert "n_test" in fold_metrics

        # Check artifacts were saved
        output_path = Path(tmpdir)
        assert (output_path / "metrics.json").exists()
        assert (output_path / "feature_importances.csv").exists()


def test_train_with_walk_forward_cv_insufficient_data(db_session):
    """Test training with insufficient data."""
    # Add only a few features
    features = [
        Feature(ticker="TEST", dt=date(2024, 1, i), features_json={"value": 1.0}, label_ret_1d=0.01)
        for i in range(1, 6)
    ]
    db_session.add_all(features)
    db_session.commit()

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError):
            train_with_walk_forward_cv(
                db_session,
                tickers=["TEST"],
                n_splits=5,  # Too many splits for 5 samples
                output_dir=tmpdir,
            )


def test_train_with_walk_forward_cv_no_data(db_session):
    """Test training with no data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="No data loaded"):
            train_with_walk_forward_cv(db_session, tickers=["NONEXISTENT"], output_dir=tmpdir)
