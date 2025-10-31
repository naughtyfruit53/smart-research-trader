"""Smoke tests for explain API endpoint."""

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.db.models import Feature

client = TestClient(app)


def test_explain_missing_date(db_session: Session):
    """Test explain endpoint with missing date parameter."""
    response = client.get("/explain/AAPL")
    assert response.status_code == 422  # FastAPI validation error


def test_explain_invalid_date(db_session: Session):
    """Test explain endpoint with invalid date format."""
    response = client.get("/explain/AAPL?dt=invalid-date")
    assert response.status_code == 400


@patch("src.ml.explain.LGBMForecaster")
@patch("pathlib.Path.exists")
def test_explain_no_features(mock_path_exists, mock_model_class, db_session: Session):
    """Test explain endpoint when no features exist for ticker/date."""
    test_date = date.today() - timedelta(days=1)
    
    # Mock model file exists so we get past that check
    mock_path_exists.return_value = True
    
    # Mock model instance and load method
    mock_model_instance = MagicMock()
    mock_model_class.return_value = mock_model_instance
    
    response = client.get(f"/explain/AAPL?dt={test_date.isoformat()}")
    assert response.status_code == 404
    data = response.json()
    assert "No features found" in data["detail"]


@patch("src.ml.explain.LGBMForecaster")
@patch("src.ml.explain.shap")
@patch("pathlib.Path.exists")
def test_explain_with_mock_shap(
    mock_path_exists, mock_shap, mock_model_class, db_session: Session
):
    """Test explain endpoint with mocked SHAP computation."""
    # Setup test data
    ticker = "AAPL"
    test_date = date.today() - timedelta(days=1)
    
    # Insert feature
    feature = Feature(
        ticker=ticker,
        dt=test_date,
        features_json={
            "rsi14": 55.0,
            "sma20": 150.0,
            "momentum20": 0.02,
            "sent_mean_comp": 0.3,
            "quality_score": 0.7,
            "valuation_score": 0.5,
        },
        label_ret_1d=None,
    )
    db_session.add(feature)
    db_session.commit()
    
    # Mock model file exists
    mock_path_exists.return_value = True
    
    # Mock model
    mock_model_instance = MagicMock()
    mock_model_instance.feature_names = [
        "rsi14",
        "sma20",
        "momentum20",
        "sent_mean_comp",
        "quality_score",
        "valuation_score",
    ]
    mock_model_instance.predict.return_value = np.array([0.02])
    mock_model_instance.model = MagicMock()  # LightGBM model object
    
    mock_model_class.return_value = mock_model_instance
    
    # Mock SHAP
    mock_explainer = MagicMock()
    mock_explainer.expected_value = 0.001
    mock_explainer.shap_values.return_value = np.array(
        [[0.015, 0.003, 0.008, 0.002, 0.005, -0.001]]
    )
    mock_shap.TreeExplainer.return_value = mock_explainer
    
    # Test endpoint
    response = client.get(f"/explain/{ticker}?dt={test_date.isoformat()}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ticker"] == ticker
    assert data["dt"] == test_date.isoformat()
    assert data["yhat"] == 0.02
    assert "base_value" in data
    
    # Check contributions
    assert len(data["contributions"]) > 0
    
    # Check structure of first contribution
    contrib = data["contributions"][0]
    assert "feature_name" in contrib
    assert "shap_value" in contrib
    assert "feature_value" in contrib
    
    # Verify that features are ranked by absolute SHAP value
    # First contribution should be rsi14 (shap=0.015)
    assert data["contributions"][0]["feature_name"] == "rsi14"
    assert abs(data["contributions"][0]["shap_value"]) == 0.015


def test_explain_model_not_found(db_session: Session):
    """Test explain endpoint when model file doesn't exist."""
    ticker = "AAPL"
    test_date = date.today() - timedelta(days=1)
    
    # Insert feature
    feature = Feature(
        ticker=ticker,
        dt=test_date,
        features_json={"rsi14": 55.0},
        label_ret_1d=None,
    )
    db_session.add(feature)
    db_session.commit()
    
    # Test endpoint (model file won't exist in test environment)
    response = client.get(f"/explain/{ticker}?dt={test_date.isoformat()}")
    assert response.status_code == 404
    data = response.json()
    assert "Model not found" in data["detail"]
