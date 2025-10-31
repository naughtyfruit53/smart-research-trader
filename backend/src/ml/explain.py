"""Model explainability using SHAP for LightGBM models."""

import logging
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap
from sqlalchemy.orm import Session

from src.core.config import settings
from src.db.repo import FeatureRepository

from .model_lgbm import LGBMForecaster

logger = logging.getLogger(__name__)


def explain_prediction(
    db: Session,
    ticker: str,
    dt: date,
    model_path: str | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    """Compute SHAP feature contributions for a prediction.
    
    Args:
        db: Database session
        ticker: Stock ticker symbol
        dt: Prediction date
        model_path: Path to trained model artifacts (default: artifacts/model_1d.pkl)
        top_k: Number of top features to return (default: from config)
        
    Returns:
        Dictionary with ticker, dt, yhat, contributions, base_value
    """
    if top_k is None:
        top_k = settings.SHAP_TOP_K
    
    if model_path is None:
        model_path = "artifacts/model_1d.pkl"
    
    # Load model
    model_file = Path(model_path)
    if not model_file.exists():
        raise FileNotFoundError(f"Model not found at {model_path}")
    
    logger.info(f"Loading model from {model_path}")
    model = LGBMForecaster.load(str(model_file))
    
    # Get features for this ticker and date
    feature_row = FeatureRepository.get_by_ticker_date(db, ticker, dt)
    if not feature_row:
        raise ValueError(f"No features found for {ticker} on {dt}")
    
    # Extract features from features_json
    features_json = feature_row.features_json or {}
    
    # Get feature names from model
    if not hasattr(model, "feature_names") or not model.feature_names:
        raise ValueError("Model does not have feature names")
    
    feature_names = model.feature_names
    
    # Build feature vector matching model's expected features
    feature_values = []
    for fname in feature_names:
        val = features_json.get(fname, np.nan)
        # Handle None values
        if val is None:
            val = np.nan
        feature_values.append(float(val))
    
    # Create DataFrame for SHAP
    X = pd.DataFrame([feature_values], columns=feature_names)
    
    # Make prediction
    yhat = model.predict(X)[0]
    
    # Compute SHAP values
    logger.info(f"Computing SHAP values for {ticker} on {dt}")
    explainer = shap.TreeExplainer(model.model)
    shap_values = explainer.shap_values(X)
    
    # Get base value (expected value)
    base_value = float(explainer.expected_value)
    
    # Extract SHAP values for the single prediction
    if isinstance(shap_values, list):
        # For classification, take first class
        shap_vals = shap_values[0][0]
    else:
        shap_vals = shap_values[0]
    
    # Create list of (feature_name, shap_value, feature_value)
    contributions = []
    for i, fname in enumerate(feature_names):
        contributions.append(
            {
                "feature_name": fname,
                "shap_value": float(shap_vals[i]),
                "feature_value": float(feature_values[i]),
            }
        )
    
    # Sort by absolute SHAP value and take top-K
    contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    top_contributions = contributions[:top_k]
    
    return {
        "ticker": ticker,
        "dt": dt,
        "yhat": float(yhat),
        "contributions": top_contributions,
        "base_value": base_value,
    }
