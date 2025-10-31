"""Tests for LightGBM model wrapper."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ml.model_lgbm import LGBMForecaster


@pytest.fixture
def sample_data():
    """Create sample regression data."""
    np.random.seed(42)
    n_samples = 100
    n_features = 5

    X = np.random.randn(n_samples, n_features)
    # Simple linear relationship with noise
    y = X[:, 0] * 2 + X[:, 1] * -1 + np.random.randn(n_samples) * 0.1

    # Split into train/val
    split = 80
    X_train = X[:split]
    y_train = y[:split]
    X_val = X[split:]
    y_val = y[split:]

    return X_train, y_train, X_val, y_val


def test_lgbm_forecaster_init():
    """Test model initialization."""
    model = LGBMForecaster(n_estimators=50, learning_rate=0.1)

    assert model.n_estimators == 50
    assert model.learning_rate == 0.1
    assert model.model is None


def test_lgbm_forecaster_get_params():
    """Test getting model parameters."""
    model = LGBMForecaster(n_estimators=50, learning_rate=0.1, num_leaves=20)

    params = model.get_params()

    assert params["n_estimators"] == 50
    assert params["learning_rate"] == 0.1
    assert params["num_leaves"] == 20
    assert params["objective"] == "regression"


def test_lgbm_forecaster_fit_basic(sample_data):
    """Test basic model fitting."""
    X_train, y_train, X_val, y_val = sample_data

    model = LGBMForecaster(n_estimators=10, verbose=-1)
    model.fit(X_train, y_train)

    assert model.model is not None
    assert model.best_iteration > 0


def test_lgbm_forecaster_fit_with_validation(sample_data):
    """Test fitting with validation set."""
    X_train, y_train, X_val, y_val = sample_data

    model = LGBMForecaster(n_estimators=20, verbose=-1)
    model.fit(X_train, y_train, X_val=X_val, y_val=y_val, early_stopping_rounds=5)

    assert model.model is not None
    # Early stopping should kick in before max iterations
    assert model.best_iteration <= 20


def test_lgbm_forecaster_fit_with_dataframe(sample_data):
    """Test fitting with pandas DataFrame."""
    X_train, y_train, X_val, y_val = sample_data

    # Convert to DataFrame
    X_train_df = pd.DataFrame(X_train, columns=[f"feat_{i}" for i in range(X_train.shape[1])])
    y_train_series = pd.Series(y_train)

    model = LGBMForecaster(n_estimators=10, verbose=-1)
    model.fit(X_train_df, y_train_series)

    assert model.model is not None
    assert len(model.feature_names) == X_train.shape[1]
    assert "feat_0" in model.feature_names


def test_lgbm_forecaster_predict(sample_data):
    """Test making predictions."""
    X_train, y_train, X_val, y_val = sample_data

    model = LGBMForecaster(n_estimators=10, verbose=-1)
    model.fit(X_train, y_train)

    predictions = model.predict(X_val)

    assert len(predictions) == len(y_val)
    assert isinstance(predictions, np.ndarray)

    # Predictions should be somewhat correlated with true values
    correlation = np.corrcoef(predictions, y_val)[0, 1]
    assert correlation > 0.5  # Reasonable correlation


def test_lgbm_forecaster_predict_not_fitted():
    """Test error when predicting without fitting."""
    model = LGBMForecaster()
    X = np.random.randn(10, 5)

    with pytest.raises(ValueError, match="Model not trained"):
        model.predict(X)


def test_lgbm_forecaster_predict_with_std(sample_data):
    """Test predictions with uncertainty estimates."""
    X_train, y_train, X_val, y_val = sample_data

    model = LGBMForecaster(n_estimators=20, verbose=-1)
    model.fit(X_train, y_train)

    yhat, yhat_std = model.predict_with_std(X_val, n_trees=10)

    assert len(yhat) == len(y_val)
    assert len(yhat_std) == len(y_val)
    # Standard deviation should be non-negative
    assert np.all(yhat_std >= 0)


def test_lgbm_forecaster_feature_importance(sample_data):
    """Test feature importance extraction."""
    X_train, y_train, _, _ = sample_data

    # Use DataFrame with feature names
    X_train_df = pd.DataFrame(X_train, columns=[f"feat_{i}" for i in range(X_train.shape[1])])

    model = LGBMForecaster(n_estimators=10, verbose=-1)
    model.fit(X_train_df, y_train)

    importance_df = model.get_feature_importance()

    assert len(importance_df) == X_train.shape[1]
    assert "feature" in importance_df.columns
    assert "importance" in importance_df.columns
    # Importances should be sorted descending
    assert importance_df["importance"].is_monotonic_decreasing


def test_lgbm_forecaster_save_load(sample_data):
    """Test saving and loading model."""
    X_train, y_train, X_val, y_val = sample_data

    # Train model
    model = LGBMForecaster(n_estimators=10, verbose=-1)
    model.fit(X_train, y_train)

    # Make predictions
    pred_before = model.predict(X_val)

    # Save model
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "model.txt"
        model.save(model_path)

        # Load model
        model_loaded = LGBMForecaster(verbose=-1)
        model_loaded.load(model_path)

        # Predictions should match
        pred_after = model_loaded.predict(X_val)

        np.testing.assert_array_almost_equal(pred_before, pred_after)


def test_lgbm_forecaster_small_model_for_ci():
    """Test that default parameters are suitable for fast CI."""
    # Default parameters should be small
    model = LGBMForecaster()

    assert model.n_estimators <= 100  # Fast training
    assert model.learning_rate <= 0.1  # Reasonable learning rate
    assert model.num_leaves <= 31  # Small tree

    # Model should train quickly
    X = np.random.randn(50, 10)
    y = np.random.randn(50)

    model.fit(X, y)

    assert model.model is not None
    assert model.best_iteration <= 100
