"""Schemas for signals API endpoints."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class SignalItem(BaseModel):
    """Individual signal item."""

    ticker: str = Field(..., description="Stock ticker symbol")
    signal: Literal["LONG", "SHORT", "NEUTRAL"] = Field(..., description="Trading signal")
    exp_return: float = Field(..., description="Expected return (yhat)")
    confidence: float = Field(..., description="Confidence score (1/(yhat_std+eps) or prob_up)")
    quality_score: float | None = Field(None, description="Quality score from fundamentals")
    valuation_score: float | None = Field(None, description="Valuation score")
    momentum_score: float | None = Field(None, description="Momentum score from technicals")
    sentiment_score: float | None = Field(None, description="Sentiment score from news")
    composite_score: float | None = Field(None, description="Composite score")
    risk_adjusted_score: float = Field(..., description="Final risk-adjusted score for ranking")
    dt: date = Field(..., description="Prediction date")


class SignalsResponse(BaseModel):
    """Response for signals endpoint."""

    signals: list[SignalItem] = Field(..., description="List of ranked signals")
    count: int = Field(..., description="Number of signals returned")
    horizon: str = Field(..., description="Prediction horizon")
