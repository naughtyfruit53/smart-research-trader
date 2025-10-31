"""Smoke tests for stocks API endpoint."""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.db.models import Feature, Fundamental, Pred, Price

client = TestClient(app)


def test_stocks_not_found(db_session: Session):
    """Test stocks endpoint with non-existent ticker."""
    response = client.get("/stocks/NONEXISTENT")
    assert response.status_code == 200  # Still returns 200 with empty data
    data = response.json()
    assert data["ticker"] == "NONEXISTENT"


def test_stocks_with_minimal_data(db_session: Session):
    """Test stocks endpoint with minimal seed data."""
    ticker = "AAPL"
    test_date = date.today() - timedelta(days=1)
    
    # Insert fundamental
    fundamental = Fundamental(
        ticker=ticker,
        asof=test_date,
        pe=15.5,
        pb=3.2,
        roe=0.25,
        roce=0.22,
        de_ratio=1.5,
    )
    db_session.add(fundamental)
    
    # Insert price
    price = Price(
        ticker=ticker,
        dt=test_date,
        open=150.0,
        high=152.0,
        low=149.0,
        close=151.5,
        volume=1000000,
        adj_close=151.5,
    )
    db_session.add(price)
    
    # Insert feature
    feature = Feature(
        ticker=ticker,
        dt=test_date,
        features_json={
            "rsi14": 55.0,
            "sma20": 150.0,
            "sma50": 148.0,
            "sma200": 145.0,
            "momentum20": 0.02,
            "momentum60": 0.05,
            "rv20": 0.015,
            "sent_mean_comp": 0.3,
            "burst_3d": 0.1,
            "burst_7d": 0.2,
            "quality_score": 0.7,
            "valuation_score": 0.5,
            "momentum_score": 0.6,
            "sentiment_score": 0.4,
            "composite_score": 0.55,
            "risk_adjusted_score": 0.6,
        },
        label_ret_1d=None,
    )
    db_session.add(feature)
    
    # Insert prediction
    pred = Pred(
        ticker=ticker,
        dt=test_date,
        horizon="1d",
        yhat=0.02,
        yhat_std=0.01,
        prob_up=0.65,
    )
    db_session.add(pred)
    
    db_session.commit()
    
    # Test endpoint
    response = client.get(f"/stocks/{ticker}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ticker"] == ticker
    
    # Check fundamentals
    assert data["fundamentals"]["pe"] == 15.5
    assert data["fundamentals"]["pb"] == 3.2
    assert data["fundamentals"]["roe"] == 0.25
    
    # Check technicals
    assert data["technicals"]["rsi14"] == 55.0
    assert data["technicals"]["sma20"] == 150.0
    
    # Check sentiment
    assert data["sentiment"]["sent_mean_comp"] == 0.3
    assert data["sentiment"]["burst_3d"] == 0.1
    
    # Check prediction
    assert data["prediction"]["yhat"] == 0.02
    assert data["prediction"]["prob_up"] == 0.65
    
    # Check scores
    assert data["scores"]["quality_score"] == 0.7
    assert data["scores"]["composite_score"] == 0.55
    
    # Check price series
    assert len(data["price_series"]["dates"]) == 1
    assert len(data["price_series"]["closes"]) == 1


def test_stocks_with_price_series(db_session: Session):
    """Test stocks endpoint with multiple price points."""
    ticker = "MSFT"
    
    # Insert multiple prices
    for i in range(10):
        test_date = date.today() - timedelta(days=i)
        price = Price(
            ticker=ticker,
            dt=test_date,
            open=250.0 + i,
            high=252.0 + i,
            low=249.0 + i,
            close=251.0 + i,
            volume=1000000,
            adj_close=251.0 + i,
        )
        db_session.add(price)
    
    db_session.commit()
    
    # Test endpoint
    response = client.get(f"/stocks/{ticker}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ticker"] == ticker
    assert len(data["price_series"]["dates"]) == 10
    assert len(data["price_series"]["closes"]) == 10
