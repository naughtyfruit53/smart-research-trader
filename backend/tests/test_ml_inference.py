"""Tests for ML inference pipeline."""

import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.db.models import Feature, Pred
from src.ml.inference import (
    generate_predictions,
    load_features_for_inference,
    run_inference,
    upsert_predictions,
)
from src.ml.model_lgbm import LGBMForecaster


@pytest.fixture
def sample_features_for_inference(db_session):
    """Create sample features for inference testing."""
    features = []

    for ticker in ["AAPL", "MSFT"]:
        for day in range(1, 6):
            dt = date(2024, 1, day)

            features_json = {
                "sma_20": 100.0 + day,
                "rsi_14": 50.0 + day,
                "momentum_20": 0.01 * day,
                "volatility": 0.02,
            }

            feat = Feature(
                ticker=ticker,
                dt=dt,
                features_json=features_json,
                label_ret_1d=None,  # No label needed for inference
            )
            features.append(feat)

    db_session.add_all(features)
    db_session.commit()

    return features


@pytest.fixture
def trained_model():
    """Create and train a simple model for testing."""
    # Create synthetic training data
    np.random.seed(42)
    X = np.random.randn(100, 4)
    y = X[:, 0] * 0.5 + np.random.randn(100) * 0.1

    X_df = pd.DataFrame(X, columns=["sma_20", "rsi_14", "momentum_20", "volatility"])

    model = LGBMForecaster(n_estimators=10, verbose=-1)
    model.fit(X_df, y)

    return model


def test_load_features_for_inference(sample_features_for_inference, db_session):
    """Test loading features for inference."""
    df = load_features_for_inference(db_session)

    # Should have 2 tickers * 5 days = 10 rows
    assert len(df) == 10

    # Should have key columns
    assert "ticker" in df.columns
    assert "dt" in df.columns

    # Should have feature columns
    assert "sma_20" in df.columns
    assert "rsi_14" in df.columns


def test_load_features_for_inference_filtered(sample_features_for_inference, db_session):
    """Test loading features with filters."""
    df = load_features_for_inference(db_session, tickers=["AAPL"], target_date=date(2024, 1, 3))

    # Should have only AAPL on 2024-01-03
    assert len(df) == 1
    assert df.iloc[0]["ticker"] == "AAPL"
    assert df.iloc[0]["dt"] == date(2024, 1, 3)


def test_load_features_for_inference_no_data(db_session):
    """Test loading when no features exist."""
    df = load_features_for_inference(db_session, tickers=["NONEXISTENT"])

    assert df.empty


def test_generate_predictions(trained_model):
    """Test generating predictions."""
    features_df = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "dt": [date(2024, 1, 1), date(2024, 1, 1)],
            "sma_20": [100.0, 105.0],
            "rsi_14": [50.0, 55.0],
            "momentum_20": [0.01, 0.02],
            "volatility": [0.02, 0.03],
        }
    )

    preds_df = generate_predictions(trained_model, features_df, horizon="1d")

    # Check structure
    assert len(preds_df) == 2
    assert "ticker" in preds_df.columns
    assert "dt" in preds_df.columns
    assert "horizon" in preds_df.columns
    assert "yhat" in preds_df.columns
    assert "yhat_std" in preds_df.columns
    assert "prob_up" in preds_df.columns

    # Check values
    assert (preds_df["horizon"] == "1d").all()
    assert preds_df["yhat_std"].min() >= 0
    assert preds_df["prob_up"].min() >= 0.01
    assert preds_df["prob_up"].max() <= 0.99


def test_generate_predictions_empty_features(trained_model):
    """Test generating predictions with empty DataFrame."""
    features_df = pd.DataFrame()

    preds_df = generate_predictions(trained_model, features_df)

    assert preds_df.empty


def test_upsert_predictions(db_session):
    """Test upserting predictions to database."""
    preds_df = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "dt": [date(2024, 1, 1), date(2024, 1, 1)],
            "horizon": ["1d", "1d"],
            "yhat": [0.01, 0.02],
            "yhat_std": [0.005, 0.008],
            "prob_up": [0.65, 0.70],
        }
    )

    num_upserted = upsert_predictions(db_session, preds_df)

    assert num_upserted == 2

    # Verify predictions were saved
    pred = (
        db_session.query(Pred).filter_by(ticker="AAPL", dt=date(2024, 1, 1), horizon="1d").first()
    )

    assert pred is not None
    assert pred.yhat == 0.01
    assert pred.yhat_std == 0.005
    assert pred.prob_up == 0.65


def test_upsert_predictions_updates_existing(db_session):
    """Test that upsert updates existing predictions."""
    # Insert initial prediction
    pred = Pred(
        ticker="AAPL", dt=date(2024, 1, 1), horizon="1d", yhat=0.01, yhat_std=0.005, prob_up=0.60
    )
    db_session.add(pred)
    db_session.commit()

    # Upsert with new values
    preds_df = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "dt": [date(2024, 1, 1)],
            "horizon": ["1d"],
            "yhat": [0.02],
            "yhat_std": [0.008],
            "prob_up": [0.70],
        }
    )

    num_upserted = upsert_predictions(db_session, preds_df)

    assert num_upserted == 1

    # Verify values were updated
    pred_updated = (
        db_session.query(Pred).filter_by(ticker="AAPL", dt=date(2024, 1, 1), horizon="1d").first()
    )

    assert pred_updated.yhat == 0.02
    assert pred_updated.yhat_std == 0.008
    assert pred_updated.prob_up == 0.70


def test_upsert_predictions_empty(db_session):
    """Test upserting empty DataFrame."""
    preds_df = pd.DataFrame()

    num_upserted = upsert_predictions(db_session, preds_df)

    assert num_upserted == 0


def test_run_inference_integration(sample_features_for_inference, db_session, trained_model):
    """Test full inference pipeline."""
    # Save model to temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "model.txt"
        trained_model.save(model_path)

        # Run inference
        num_preds = run_inference(db_session, model_path=model_path, tickers=["AAPL"], horizon="1d")

        # Should generate 5 predictions (5 days for AAPL)
        assert num_preds == 5

        # Verify predictions were saved to database
        preds = db_session.query(Pred).filter_by(ticker="AAPL", horizon="1d").all()
        assert len(preds) == 5

        # Check prediction values are reasonable
        for pred in preds:
            assert pred.yhat is not None
            assert pred.yhat_std >= 0
            assert 0.01 <= pred.prob_up <= 0.99


def test_run_inference_specific_date(sample_features_for_inference, db_session, trained_model):
    """Test inference for specific date."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "model.txt"
        trained_model.save(model_path)

        # Run inference for specific date
        num_preds = run_inference(
            db_session,
            model_path=model_path,
            tickers=["AAPL", "MSFT"],
            target_date=date(2024, 1, 3),
            horizon="1d",
        )

        # Should generate 2 predictions (2 tickers on same date)
        assert num_preds == 2


def test_run_inference_no_features(db_session, trained_model):
    """Test inference when no features available."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "model.txt"
        trained_model.save(model_path)

        num_preds = run_inference(db_session, model_path=model_path, tickers=["NONEXISTENT"])

        assert num_preds == 0
