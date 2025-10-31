"""Schemas for backtests API endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EquityPoint(BaseModel):
    """Single point in equity curve."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    equity: float = Field(..., description="Portfolio equity value")


class BacktestMetrics(BaseModel):
    """Backtest performance metrics."""

    ann_return: float | None = None
    ann_vol: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    max_dd: float | None = None
    turnover: float | None = None
    hit_rate: float | None = None
    avg_long_exposure: float | None = None
    avg_short_exposure: float | None = None
    avg_gross_exposure: float | None = None


class BacktestResponse(BaseModel):
    """Response for backtest endpoint."""

    run_id: UUID = Field(..., description="Unique backtest run identifier")
    started_at: datetime = Field(..., description="Backtest start timestamp")
    finished_at: datetime | None = Field(None, description="Backtest completion timestamp")
    params: dict[str, Any] = Field(..., description="Backtest parameters")
    metrics: BacktestMetrics | None = Field(None, description="Performance metrics")
    equity_curve: list[EquityPoint] = Field(default_factory=list, description="Equity curve series")
