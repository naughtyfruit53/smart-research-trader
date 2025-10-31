"""Smoke tests for backtests API endpoint."""

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.db.models import Backtest

client = TestClient(app)


def test_backtests_empty_db(db_session: Session):
    """Test backtests endpoint with no completed backtests."""
    response = client.get("/backtests/latest")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_backtests_with_dummy_data(db_session: Session):
    """Test backtests endpoint with a dummy backtest record."""
    # Create dummy backtest
    run_id = uuid4()
    started_at = datetime(2024, 1, 1, 10, 0, 0)
    finished_at = datetime(2024, 1, 1, 11, 0, 0)
    
    params = {
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "long_threshold": 0.5,
        "short_threshold": -0.5,
        "transaction_cost_bps": 10.0,
        "max_long": 20,
        "max_short": 10,
        "max_gross": 30,
        "rebalance_daily": True,
    }
    
    metrics = {
        "ann_return": 0.15,
        "ann_vol": 0.12,
        "sharpe": 1.25,
        "sortino": 1.8,
        "max_dd": -0.08,
        "turnover": 0.5,
        "hit_rate": 0.55,
        "avg_long_exposure": 0.6,
        "avg_short_exposure": 0.3,
        "avg_gross_exposure": 0.9,
        "equity_curve": [
            {"date": "2024-01-01", "equity": 100000.0},
            {"date": "2024-06-01", "equity": 105000.0},
            {"date": "2024-12-31", "equity": 115000.0},
        ],
    }
    
    backtest = Backtest(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        params=params,
        metrics=metrics,
    )
    db_session.add(backtest)
    db_session.commit()
    
    # Test endpoint
    response = client.get("/backtests/latest")
    assert response.status_code == 200
    
    data = response.json()
    assert data["run_id"] == str(run_id)
    assert data["params"]["long_threshold"] == 0.5
    assert data["params"]["max_long"] == 20
    
    # Check metrics
    assert data["metrics"]["ann_return"] == 0.15
    assert data["metrics"]["sharpe"] == 1.25
    assert data["metrics"]["max_dd"] == -0.08
    
    # Check equity curve
    assert len(data["equity_curve"]) == 3
    assert data["equity_curve"][0]["date"] == "2024-01-01"
    assert data["equity_curve"][0]["equity"] == 100000.0
    assert data["equity_curve"][-1]["equity"] == 115000.0


def test_backtests_returns_latest(db_session: Session):
    """Test that endpoint returns the most recent backtest."""
    # Create multiple backtests
    for i in range(3):
        run_id = uuid4()
        started_at = datetime(2024, 1, i + 1, 10, 0, 0)
        finished_at = datetime(2024, 1, i + 1, 11, 0, 0)
        
        backtest = Backtest(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            params={"index": i},
            metrics={"sharpe": float(i), "equity_curve": []},
        )
        db_session.add(backtest)
    
    db_session.commit()
    
    # Test endpoint
    response = client.get("/backtests/latest")
    assert response.status_code == 200
    
    data = response.json()
    # Should return the one with index=2 (latest finished_at)
    assert data["params"]["index"] == 2
    assert data["metrics"]["sharpe"] == 2.0
