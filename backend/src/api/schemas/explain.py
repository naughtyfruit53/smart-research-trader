"""Schemas for explainability API endpoints."""

from datetime import date

from pydantic import BaseModel, Field


class FeatureContribution(BaseModel):
    """Individual feature contribution to prediction."""

    feature_name: str = Field(..., description="Feature name")
    shap_value: float = Field(..., description="SHAP contribution value")
    feature_value: float = Field(..., description="Actual feature value")


class ExplainResponse(BaseModel):
    """Response for explain endpoint."""

    ticker: str = Field(..., description="Stock ticker symbol")
    dt: date = Field(..., description="Prediction date")
    yhat: float = Field(..., description="Model prediction")
    contributions: list[FeatureContribution] = Field(
        ..., description="Top-K feature contributions ranked by absolute SHAP value"
    )
    base_value: float = Field(..., description="Expected value (baseline prediction)")
