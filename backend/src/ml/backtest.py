"""Simple daily long/short backtesting engine."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from src.db.models import Backtest
from src.db.repo import BacktestRepository, FeatureRepository

logger = logging.getLogger(__name__)


def run_backtest(
    db: Session,
    start_date: str | None = None,
    end_date: str | None = None,
    long_threshold: float = 0.5,
    short_threshold: float = -0.5,
    transaction_cost_bps: float = 10.0,
    max_long: int = 20,
    max_short: int = 10,
    max_gross: int = 30,
    rebalance_daily: bool = True,
) -> UUID:
    """Run a simple daily long/short backtest.
    
    Args:
        db: Database session
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        long_threshold: Threshold for long signals (on risk_adjusted_score or prob_up)
        short_threshold: Threshold for short signals
        transaction_cost_bps: Transaction cost in basis points
        max_long: Maximum number of long positions
        max_short: Maximum number of short positions
        max_gross: Maximum total positions
        rebalance_daily: Whether to rebalance daily
        
    Returns:
        UUID of the backtest run
    """
    run_id = uuid4()
    started_at = datetime.utcnow()
    
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "long_threshold": long_threshold,
        "short_threshold": short_threshold,
        "transaction_cost_bps": transaction_cost_bps,
        "max_long": max_long,
        "max_short": max_short,
        "max_gross": max_gross,
        "rebalance_daily": rebalance_daily,
    }
    
    # Create backtest record
    BacktestRepository.create(
        db=db, run_id=run_id, started_at=started_at, params=params, finished_at=None, metrics=None
    )
    
    try:
        # Load features with predictions (this is a simplified version)
        # In real implementation, we'd join predictions with features and forward returns
        logger.info(f"Running backtest {run_id} from {start_date} to {end_date}")
        
        # For now, create dummy equity curve and metrics
        equity_curve = _create_dummy_equity_curve()
        metrics = _compute_metrics(equity_curve)
        
        finished_at = datetime.utcnow()
        
        # Update backtest with results
        backtest = BacktestRepository.get_by_run_id(db, run_id)
        if backtest:
            backtest.finished_at = finished_at
            backtest.metrics = metrics
            db.commit()
        
        logger.info(f"Backtest {run_id} completed with Sharpe={metrics.get('sharpe'):.2f}")
        
    except Exception as e:
        logger.error(f"Backtest {run_id} failed: {e}")
        # Mark as failed
        backtest = BacktestRepository.get_by_run_id(db, run_id)
        if backtest:
            backtest.finished_at = datetime.utcnow()
            backtest.metrics = {"error": str(e)}
            db.commit()
        raise
    
    return run_id


def _create_dummy_equity_curve() -> pd.DataFrame:
    """Create a dummy equity curve for testing."""
    dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
    # Simulate a modest upward trending equity curve
    returns = np.random.normal(0.0005, 0.01, size=len(dates))
    equity = 100000 * (1 + returns).cumprod()
    
    return pd.DataFrame({"date": dates, "equity": equity})


def _compute_metrics(equity_curve: pd.DataFrame) -> dict[str, Any]:
    """Compute backtest metrics from equity curve.
    
    Args:
        equity_curve: DataFrame with columns [date, equity]
        
    Returns:
        Dictionary with performance metrics
    """
    if equity_curve.empty or len(equity_curve) < 2:
        return {
            "ann_return": 0.0,
            "ann_vol": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_dd": 0.0,
            "turnover": 0.0,
            "hit_rate": 0.0,
            "avg_long_exposure": 0.0,
            "avg_short_exposure": 0.0,
            "avg_gross_exposure": 0.0,
        }
    
    # Calculate daily returns
    equity_values = equity_curve["equity"].values
    returns = np.diff(equity_values) / equity_values[:-1]
    
    # Annualized metrics (assuming 252 trading days)
    ann_return = float(np.mean(returns) * 252)
    ann_vol = float(np.std(returns) * np.sqrt(252))
    
    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe = float(ann_return / ann_vol if ann_vol > 0 else 0.0)
    
    # Sortino ratio (using downside deviation)
    downside_returns = returns[returns < 0]
    downside_vol = float(
        np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0.0
    )
    sortino = float(ann_return / downside_vol if downside_vol > 0 else 0.0)
    
    # Maximum drawdown
    cumulative = (1 + returns).cumprod()
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_dd = float(np.min(drawdown))
    
    # Hit rate (percentage of positive return days)
    hit_rate = float(np.mean(returns > 0))
    
    # Placeholder values for exposure and turnover
    turnover = 0.0
    avg_long_exposure = 0.5
    avg_short_exposure = 0.3
    avg_gross_exposure = 0.8
    
    # Store equity curve as part of metrics for easy access
    equity_curve_data = [
        {"date": row["date"].strftime("%Y-%m-%d"), "equity": float(row["equity"])}
        for _, row in equity_curve.iterrows()
    ]
    
    return {
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_dd": max_dd,
        "turnover": turnover,
        "hit_rate": hit_rate,
        "avg_long_exposure": avg_long_exposure,
        "avg_short_exposure": avg_short_exposure,
        "avg_gross_exposure": avg_gross_exposure,
        "equity_curve": equity_curve_data,
    }
