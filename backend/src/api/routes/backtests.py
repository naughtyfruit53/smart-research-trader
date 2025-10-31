"""Backtests API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db.repo import BacktestRepository
from src.db.session import get_db

from ..schemas.backtests import BacktestMetrics, BacktestResponse, EquityPoint

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/latest", response_model=BacktestResponse)
def get_latest_backtest(
    db: Annotated[Session, Depends(get_db)],
) -> BacktestResponse:
    """Get the most recent completed backtest.

    Returns the backtest run with the latest finished_at timestamp,
    including performance metrics and equity curve series.

    Examples:
        GET /backtests/latest
    """
    logger.info("Getting latest backtest")

    backtest = BacktestRepository.get_latest_backtest(db)

    if not backtest:
        raise HTTPException(status_code=404, detail="No completed backtests found")

    # Extract metrics
    metrics_data = backtest.metrics or {}

    # Extract equity curve if stored in metrics
    equity_curve_data = metrics_data.pop("equity_curve", [])
    equity_curve = [EquityPoint(**point) for point in equity_curve_data]

    # Build metrics object
    metrics = BacktestMetrics(**metrics_data)

    return BacktestResponse(
        run_id=backtest.run_id,
        started_at=backtest.started_at,
        finished_at=backtest.finished_at,
        params=backtest.params,
        metrics=metrics,
        equity_curve=equity_curve,
    )
