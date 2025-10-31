"""Tests for database models."""

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from src.db.models import Backtest, Feature, Fundamental, News, Pred, Price


def test_price_model(db_session: Session):
    """Test Price model CRUD operations."""
    price = Price(
        ticker="AAPL",
        dt=date(2024, 1, 1),
        open=150.0,
        high=155.0,
        low=149.0,
        close=154.0,
        volume=1000000,
        adj_close=154.0,
    )
    db_session.add(price)
    db_session.commit()

    # Retrieve and verify
    retrieved = (
        db_session.query(Price).filter(Price.ticker == "AAPL", Price.dt == date(2024, 1, 1)).first()
    )
    assert retrieved is not None
    assert retrieved.ticker == "AAPL"
    assert retrieved.close == 154.0
    assert retrieved.volume == 1000000


def test_news_model(db_session: Session):
    """Test News model CRUD operations."""
    news = News(
        dt=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        ticker="AAPL",
        source="Reuters",
        headline="Apple announces new product",
        summary="Apple has announced a new product line",
        url="https://example.com/news",
        sent_pos=0.8,
        sent_neg=0.1,
        sent_comp=0.7,
    )
    db_session.add(news)
    db_session.commit()

    # Retrieve and verify
    retrieved = db_session.query(News).filter(News.ticker == "AAPL").first()
    assert retrieved is not None
    assert retrieved.headline == "Apple announces new product"
    assert retrieved.sent_pos == 0.8


def test_fundamental_model(db_session: Session):
    """Test Fundamental model CRUD operations."""
    fundamental = Fundamental(
        ticker="AAPL",
        asof=date(2024, 1, 1),
        pe=25.5,
        pb=5.2,
        roe=0.35,
        roce=0.28,
        de_ratio=1.5,
    )
    db_session.add(fundamental)
    db_session.commit()

    # Retrieve and verify
    retrieved = (
        db_session.query(Fundamental)
        .filter(Fundamental.ticker == "AAPL", Fundamental.asof == date(2024, 1, 1))
        .first()
    )
    assert retrieved is not None
    assert retrieved.pe == 25.5
    assert retrieved.roe == 0.35


def test_feature_model(db_session: Session):
    """Test Feature model CRUD operations."""
    feature = Feature(
        ticker="AAPL",
        dt=date(2024, 1, 1),
        features_json={"rsi": 65.5, "macd": 1.2, "bb_width": 0.05},
        label_ret_1d=0.02,
    )
    db_session.add(feature)
    db_session.commit()

    # Retrieve and verify
    retrieved = (
        db_session.query(Feature)
        .filter(Feature.ticker == "AAPL", Feature.dt == date(2024, 1, 1))
        .first()
    )
    assert retrieved is not None
    assert retrieved.features_json["rsi"] == 65.5
    assert retrieved.label_ret_1d == 0.02


def test_pred_model(db_session: Session):
    """Test Pred model CRUD operations."""
    pred = Pred(
        ticker="AAPL",
        dt=date(2024, 1, 1),
        horizon="1d",
        yhat=0.015,
        yhat_std=0.005,
        prob_up=0.65,
    )
    db_session.add(pred)
    db_session.commit()

    # Retrieve and verify
    retrieved = (
        db_session.query(Pred)
        .filter(Pred.ticker == "AAPL", Pred.dt == date(2024, 1, 1), Pred.horizon == "1d")
        .first()
    )
    assert retrieved is not None
    assert retrieved.yhat == 0.015
    assert retrieved.prob_up == 0.65


def test_backtest_model(db_session: Session):
    """Test Backtest model CRUD operations."""
    run_id = uuid4()
    backtest = Backtest(
        run_id=run_id,
        started_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        finished_at=datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC),
        params={"strategy": "momentum", "lookback": 30},
        metrics={"sharpe": 1.5, "max_dd": -0.15, "returns": 0.25},
    )
    db_session.add(backtest)
    db_session.commit()

    # Retrieve and verify
    retrieved = db_session.query(Backtest).filter(Backtest.run_id == run_id).first()
    assert retrieved is not None
    assert retrieved.params["strategy"] == "momentum"
    assert retrieved.metrics["sharpe"] == 1.5


def test_composite_primary_keys(db_session: Session):
    """Test that composite primary keys work correctly."""
    # Add two prices for same ticker, different dates
    price1 = Price(
        ticker="AAPL",
        dt=date(2024, 1, 1),
        open=150.0,
        high=155.0,
        low=149.0,
        close=154.0,
        volume=1000000,
        adj_close=154.0,
    )
    price2 = Price(
        ticker="AAPL",
        dt=date(2024, 1, 2),
        open=154.0,
        high=158.0,
        low=153.0,
        close=157.0,
        volume=1200000,
        adj_close=157.0,
    )
    db_session.add(price1)
    db_session.add(price2)
    db_session.commit()

    # Verify both are stored
    count = db_session.query(Price).filter(Price.ticker == "AAPL").count()
    assert count == 2


def test_nullable_fields(db_session: Session):
    """Test that nullable fields work correctly."""
    # Create fundamental with only required fields
    fundamental = Fundamental(
        ticker="AAPL",
        asof=date(2024, 1, 1),
        pe=None,
        pb=None,
        roe=None,
    )
    db_session.add(fundamental)
    db_session.commit()

    # Retrieve and verify
    retrieved = (
        db_session.query(Fundamental)
        .filter(Fundamental.ticker == "AAPL", Fundamental.asof == date(2024, 1, 1))
        .first()
    )
    assert retrieved is not None
    assert retrieved.pe is None
    assert retrieved.roe is None
