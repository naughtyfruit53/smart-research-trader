"""Signals API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.config import settings
from src.db.repo import FeatureRepository
from src.db.session import get_db

from ..schemas.signals import SignalItem, SignalsResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/daily", response_model=SignalsResponse)
def get_daily_signals(
    db: Annotated[Session, Depends(get_db)],
    horizon: str = Query(default="1d", description="Prediction horizon"),
    top: int = Query(default=None, description="Number of top signals to return"),
    sector: str = Query(default="", description="Filter by sector (optional)"),
    min_liquidity: float = Query(default=0.0, description="Minimum liquidity filter (optional)"),
    min_confidence: float = Query(
        default=0.0, description="Minimum confidence score filter (optional)"
    ),
    exclude_earnings: bool = Query(
        default=False, description="Exclude stocks with upcoming earnings (optional)"
    ),
) -> SignalsResponse:
    """Get daily trading signals ranked by risk-adjusted score.
    
    Returns latest predictions joined with features for scoring and filtering.
    Signals are ranked by risk_adjusted_score computed as a blend of:
    - base_score = yhat / (yhat_std + 1e-6)
    - composite_score from features
    
    Examples:
        GET /signals/daily?horizon=1d&top=50
        GET /signals/daily?horizon=1d&top=20&min_confidence=0.5
    """
    if top is None:
        top = settings.SIGNAL_TOP_DEFAULT
    
    logger.info(
        f"Getting daily signals: horizon={horizon}, top={top}, "
        f"sector={sector}, min_liquidity={min_liquidity}, "
        f"min_confidence={min_confidence}, exclude_earnings={exclude_earnings}"
    )
    
    # Get latest predictions with features
    preds_with_features = FeatureRepository.get_latest_features_for_preds(db, horizon=horizon)
    
    if not preds_with_features:
        logger.warning(f"No predictions found for horizon={horizon}")
        return SignalsResponse(signals=[], count=0, horizon=horizon)
    
    # Build signal items
    signal_items = []
    for pred, feature in preds_with_features:
        fj = feature.features_json or {}
        
        # Compute base score from prediction
        base_score = pred.yhat / (pred.yhat_std + 1e-6)
        
        # Get composite score from features
        composite_score = fj.get("composite_score", 0.0)
        if composite_score is None:
            composite_score = 0.0
        
        # Blend scores using configured weight
        risk_adjusted_score = (
            settings.RISK_SCORE_WEIGHT * base_score
            + (1 - settings.RISK_SCORE_WEIGHT) * composite_score
        )
        
        # Determine signal
        if risk_adjusted_score > 0.5:
            signal = "LONG"
        elif risk_adjusted_score < -0.5:
            signal = "SHORT"
        else:
            signal = "NEUTRAL"
        
        # Compute confidence (inverse of uncertainty)
        confidence = 1.0 / (pred.yhat_std + 1e-6)
        
        # Apply filters
        if min_confidence > 0 and confidence < min_confidence:
            continue
        
        # TODO: Implement sector, liquidity, and earnings filters when data available
        
        signal_item = SignalItem(
            ticker=pred.ticker,
            signal=signal,
            exp_return=pred.yhat,
            confidence=confidence,
            quality_score=fj.get("quality_score"),
            valuation_score=fj.get("valuation_score"),
            momentum_score=fj.get("momentum_score"),
            sentiment_score=fj.get("sentiment_score"),
            composite_score=composite_score,
            risk_adjusted_score=risk_adjusted_score,
            dt=pred.dt,
        )
        signal_items.append(signal_item)
    
    # Sort by risk_adjusted_score descending
    signal_items.sort(key=lambda x: x.risk_adjusted_score, reverse=True)
    
    # Limit to top N
    signal_items = signal_items[:top]
    
    logger.info(f"Returning {len(signal_items)} signals")
    
    return SignalsResponse(signals=signal_items, count=len(signal_items), horizon=horizon)
