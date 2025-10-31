"""Schemas for stocks API endpoints."""

from datetime import date

from pydantic import BaseModel, Field


class FundamentalsSnapshot(BaseModel):
    """Fundamental metrics snapshot."""

    pe: float | None = None
    pb: float | None = None
    ev_ebitda: float | None = None
    roe: float | None = None
    roce: float | None = None
    de_ratio: float | None = None
    eps_g3y: float | None = None
    rev_g3y: float | None = None
    profit_g3y: float | None = None
    opm: float | None = None
    npm: float | None = None
    div_yield: float | None = None
    asof: date | None = None


class TechnicalsSnapshot(BaseModel):
    """Technical indicators snapshot."""

    rsi14: float | None = None
    sma20: float | None = None
    sma50: float | None = None
    sma200: float | None = None
    momentum20: float | None = None
    momentum60: float | None = None
    rv20: float | None = None


class SentimentSnapshot(BaseModel):
    """Sentiment metrics snapshot."""

    sent_mean_comp: float | None = None
    burst_3d: float | None = None
    burst_7d: float | None = None


class PredictionSnapshot(BaseModel):
    """Latest prediction snapshot."""

    yhat: float | None = None
    yhat_std: float | None = None
    prob_up: float | None = None
    dt: date | None = None
    horizon: str | None = None


class ScoresSnapshot(BaseModel):
    """Feature scores snapshot."""

    quality_score: float | None = None
    valuation_score: float | None = None
    momentum_score: float | None = None
    sentiment_score: float | None = None
    composite_score: float | None = None
    risk_adjusted_score: float | None = None


class PriceSeries(BaseModel):
    """Price chart data."""

    dates: list[str] = Field(default_factory=list, description="Trading dates")
    closes: list[float] = Field(default_factory=list, description="Close prices")


class StockSnapshot(BaseModel):
    """Complete stock snapshot with all metrics."""

    ticker: str = Field(..., description="Stock ticker symbol")
    fundamentals: FundamentalsSnapshot = Field(default_factory=FundamentalsSnapshot)
    technicals: TechnicalsSnapshot = Field(default_factory=TechnicalsSnapshot)
    sentiment: SentimentSnapshot = Field(default_factory=SentimentSnapshot)
    prediction: PredictionSnapshot = Field(default_factory=PredictionSnapshot)
    scores: ScoresSnapshot = Field(default_factory=ScoresSnapshot)
    price_series: PriceSeries = Field(default_factory=PriceSeries)
