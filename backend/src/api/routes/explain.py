"""Explainability API endpoints."""

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.ml.explain import explain_prediction

from ..schemas.explain import ExplainResponse, FeatureContribution

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{ticker}", response_model=ExplainResponse)
def get_explanation(
    ticker: Annotated[str, Path(description="Stock ticker symbol")],
    db: Annotated[Session, Depends(get_db)],
    dt: str = Query(..., description="Prediction date in YYYY-MM-DD format"),
) -> ExplainResponse:
    """Get SHAP feature contributions for a prediction.
    
    Computes top-K SHAP feature contributions for the model prediction
    of the given ticker on the specified date. This is an on-demand
    computation to keep runtime reasonable.
    
    Args:
        ticker: Stock ticker symbol
        dt: Prediction date (YYYY-MM-DD)
        
    Returns:
        Top-K feature contributions ranked by absolute SHAP value
        
    Examples:
        GET /explain/AAPL?dt=2024-01-15
        GET /explain/RELIANCE.NS?dt=2024-06-01
    """
    logger.info(f"Getting explanation for {ticker} on {dt}")
    
    # Parse date
    try:
        pred_date = date.fromisoformat(dt)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {dt}")
    
    # Compute SHAP values
    try:
        result = explain_prediction(db, ticker, pred_date)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing explanation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error computing explanation: {e}")
    
    # Build response
    contributions = [FeatureContribution(**c) for c in result["contributions"]]
    
    return ExplainResponse(
        ticker=result["ticker"],
        dt=result["dt"],
        yhat=result["yhat"],
        contributions=contributions,
        base_value=result["base_value"],
    )
