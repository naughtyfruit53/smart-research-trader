"""Stocks API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from src.db.repo import PriceRepository, get_stock_snapshot
from src.db.session import get_db

from ..schemas.stocks import (
    FundamentalsSnapshot,
    PredictionSnapshot,
    PriceSeries,
    ScoresSnapshot,
    SentimentSnapshot,
    StockSnapshot,
    TechnicalsSnapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{ticker}", response_model=StockSnapshot)
def get_stock(
    ticker: Annotated[str, Path(description="Stock ticker symbol")],
    db: Annotated[Session, Depends(get_db)],
) -> StockSnapshot:
    """Get complete stock snapshot with all metrics.
    
    Returns:
        - Latest fundamentals snapshot
        - Recent technicals (RSI, SMAs, momentum, volatility)
        - Sentiment aggregates
        - Latest prediction and scores
        - Price series for chart (last 200 trading days)
    
    Examples:
        GET /stocks/AAPL
        GET /stocks/RELIANCE.NS
    """
    logger.info(f"Getting stock snapshot for {ticker}")
    
    # Get snapshot data
    snapshot_data = get_stock_snapshot(db, ticker)
    
    # Get price series for chart
    prices = PriceRepository.get_price_series(db, ticker, lookback_days=200)
    
    # Build price series (reverse to chronological order)
    price_dates = [p.dt.strftime("%Y-%m-%d") for p in reversed(prices)]
    price_closes = [float(p.close) for p in reversed(prices)]
    
    # Build response
    return StockSnapshot(
        ticker=ticker,
        fundamentals=FundamentalsSnapshot(**snapshot_data.get("fundamentals", {})),
        technicals=TechnicalsSnapshot(**snapshot_data.get("technicals", {})),
        sentiment=SentimentSnapshot(**snapshot_data.get("sentiment", {})),
        prediction=PredictionSnapshot(**snapshot_data.get("prediction", {})),
        scores=ScoresSnapshot(**snapshot_data.get("scores", {})),
        price_series=PriceSeries(dates=price_dates, closes=price_closes),
    )
