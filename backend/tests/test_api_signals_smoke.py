"""Smoke tests for signals API endpoint."""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.db.models import Feature, Pred

client = TestClient(app)


def test_signals_empty_db(db_session: Session):
    """Test signals endpoint with empty database."""
    response = client.get("/signals/daily?horizon=1d&top=10")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["signals"] == []
    assert data["horizon"] == "1d"


def test_signals_with_data(db_session: Session):
    """Test signals endpoint with seed data."""
    # Create test date
    test_date = date.today() - timedelta(days=1)
    
    # Insert test predictions and features
    tickers = ["AAPL", "MSFT", "GOOGL"]
    
    for ticker in tickers:
        # Create prediction
        pred = Pred(
            ticker=ticker,
            dt=test_date,
            horizon="1d",
            yhat=0.02 if ticker == "AAPL" else -0.01,
            yhat_std=0.01,
            prob_up=0.6 if ticker == "AAPL" else 0.4,
        )
        db_session.add(pred)
        
        # Create feature with scores
        feature = Feature(
            ticker=ticker,
            dt=test_date,
            features_json={
                "quality_score": 0.7,
                "valuation_score": 0.5,
                "momentum_score": 0.6,
                "sentiment_score": 0.4,
                "composite_score": 0.55,
                "rsi14": 55.0,
                "sma20": 150.0,
            },
            label_ret_1d=None,
        )
        db_session.add(feature)
    
    db_session.commit()
    
    # Test endpoint
    response = client.get("/signals/daily?horizon=1d&top=5")
    assert response.status_code == 200
    
    data = response.json()
    assert data["count"] == 3
    assert len(data["signals"]) == 3
    assert data["horizon"] == "1d"
    
    # Check first signal structure
    signal = data["signals"][0]
    assert "ticker" in signal
    assert "signal" in signal
    assert signal["signal"] in ["LONG", "SHORT", "NEUTRAL"]
    assert "exp_return" in signal
    assert "confidence" in signal
    assert "risk_adjusted_score" in signal
    assert "dt" in signal


def test_signals_respects_top_parameter(db_session: Session):
    """Test that top parameter limits results."""
    test_date = date.today() - timedelta(days=1)
    
    # Insert 10 test predictions
    for i in range(10):
        ticker = f"TICK{i}"
        pred = Pred(
            ticker=ticker,
            dt=test_date,
            horizon="1d",
            yhat=0.01 * i,
            yhat_std=0.01,
            prob_up=0.5,
        )
        db_session.add(pred)
        
        feature = Feature(
            ticker=ticker,
            dt=test_date,
            features_json={"composite_score": 0.5},
            label_ret_1d=None,
        )
        db_session.add(feature)
    
    db_session.commit()
    
    # Test with top=5
    response = client.get("/signals/daily?horizon=1d&top=5")
    assert response.status_code == 200
    
    data = response.json()
    assert data["count"] == 5
    assert len(data["signals"]) == 5
