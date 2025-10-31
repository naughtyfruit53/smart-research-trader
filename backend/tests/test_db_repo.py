"""Tests for database repository helpers."""

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from src.db.models import Backtest, Feature, Fundamental, News, Pred, Price
from src.db.repo import (
    BacktestRepository,
    FeatureRepository,
    FundamentalRepository,
    NewsRepository,
    PredRepository,
    PriceRepository,
)


def test_price_repository_get_by_ticker_date(db_session: Session):
    """Test PriceRepository.get_by_ticker_date."""
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

    result = PriceRepository.get_by_ticker_date(db_session, "AAPL", date(2024, 1, 1))
    assert result is not None
    assert result.close == 154.0


def test_price_repository_get_latest_by_ticker(db_session: Session):
    """Test PriceRepository.get_latest_by_ticker."""
    # Add multiple prices
    for i in range(5):
        price = Price(
            ticker="AAPL",
            dt=date(2024, 1, i + 1),
            open=150.0 + i,
            high=155.0 + i,
            low=149.0 + i,
            close=154.0 + i,
            volume=1000000,
            adj_close=154.0 + i,
        )
        db_session.add(price)
    db_session.commit()

    results = PriceRepository.get_latest_by_ticker(db_session, "AAPL", limit=3)
    assert len(results) == 3
    # Results should be in descending order by date
    assert results[0].dt == date(2024, 1, 5)
    assert results[1].dt == date(2024, 1, 4)
    assert results[2].dt == date(2024, 1, 3)


def test_news_repository_get_by_ticker(db_session: Session):
    """Test NewsRepository.get_by_ticker."""
    for i in range(3):
        news = News(
            dt=datetime(2024, 1, i + 1, 12, 0, 0, tzinfo=UTC),
            ticker="AAPL",
            source="Reuters",
            headline=f"News {i}",
            summary=f"Summary {i}",
            url=f"https://example.com/news{i}",
            sent_pos=0.8,
            sent_neg=0.1,
            sent_comp=0.7,
        )
        db_session.add(news)
    db_session.commit()

    results = NewsRepository.get_by_ticker(db_session, "AAPL", limit=2)
    assert len(results) == 2
    # Results should be in descending order by date
    assert "News 2" in results[0].headline


def test_news_repository_get_latest(db_session: Session):
    """Test NewsRepository.get_latest."""
    for ticker in ["AAPL", "GOOGL"]:
        news = News(
            dt=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            ticker=ticker,
            source="Reuters",
            headline=f"{ticker} news",
            summary="Summary",
            url="https://example.com/news",
            sent_pos=0.8,
            sent_neg=0.1,
            sent_comp=0.7,
        )
        db_session.add(news)
    db_session.commit()

    results = NewsRepository.get_latest(db_session, limit=10)
    assert len(results) == 2


def test_fundamental_repository_get_latest_by_ticker(db_session: Session):
    """Test FundamentalRepository.get_latest_by_ticker."""
    for i in range(3):
        fundamental = Fundamental(
            ticker="AAPL",
            asof=date(2024, 1, i + 1),
            pe=25.5 + i,
            pb=5.2,
            roe=0.35,
        )
        db_session.add(fundamental)
    db_session.commit()

    result = FundamentalRepository.get_latest_by_ticker(db_session, "AAPL")
    assert result is not None
    assert result.asof == date(2024, 1, 3)
    assert result.pe == 27.5


def test_fundamental_repository_get_by_ticker_date(db_session: Session):
    """Test FundamentalRepository.get_by_ticker_date."""
    fundamental = Fundamental(
        ticker="AAPL",
        asof=date(2024, 1, 1),
        pe=25.5,
        pb=5.2,
        roe=0.35,
    )
    db_session.add(fundamental)
    db_session.commit()

    result = FundamentalRepository.get_by_ticker_date(db_session, "AAPL", date(2024, 1, 1))
    assert result is not None
    assert result.pe == 25.5


def test_feature_repository_get_by_ticker_date(db_session: Session):
    """Test FeatureRepository.get_by_ticker_date."""
    feature = Feature(
        ticker="AAPL",
        dt=date(2024, 1, 1),
        features_json={"rsi": 65.5},
        label_ret_1d=0.02,
    )
    db_session.add(feature)
    db_session.commit()

    result = FeatureRepository.get_by_ticker_date(db_session, "AAPL", date(2024, 1, 1))
    assert result is not None
    assert result.features_json["rsi"] == 65.5


def test_feature_repository_get_latest_by_ticker(db_session: Session):
    """Test FeatureRepository.get_latest_by_ticker."""
    for i in range(3):
        feature = Feature(
            ticker="AAPL",
            dt=date(2024, 1, i + 1),
            features_json={"rsi": 65.5 + i},
            label_ret_1d=0.02,
        )
        db_session.add(feature)
    db_session.commit()

    results = FeatureRepository.get_latest_by_ticker(db_session, "AAPL", limit=2)
    assert len(results) == 2
    assert results[0].dt == date(2024, 1, 3)


def test_pred_repository_get_latest_by_date(db_session: Session):
    """Test PredRepository.get_latest_by_date."""
    for ticker in ["AAPL", "GOOGL"]:
        pred = Pred(
            ticker=ticker,
            dt=date(2024, 1, 1),
            horizon="1d",
            yhat=0.015,
            yhat_std=0.005,
            prob_up=0.65,
        )
        db_session.add(pred)
    db_session.commit()

    results = PredRepository.get_latest_by_date(db_session, date(2024, 1, 1))
    assert len(results) == 2


def test_pred_repository_get_by_ticker(db_session: Session):
    """Test PredRepository.get_by_ticker."""
    for i in range(3):
        pred = Pred(
            ticker="AAPL",
            dt=date(2024, 1, i + 1),
            horizon="1d",
            yhat=0.015 + i * 0.001,
            yhat_std=0.005,
            prob_up=0.65,
        )
        db_session.add(pred)
    db_session.commit()

    results = PredRepository.get_by_ticker(db_session, "AAPL", limit=2)
    assert len(results) == 2
    assert results[0].dt == date(2024, 1, 3)


def test_pred_repository_get_by_ticker_date_horizon(db_session: Session):
    """Test PredRepository.get_by_ticker_date_horizon."""
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

    result = PredRepository.get_by_ticker_date_horizon(db_session, "AAPL", date(2024, 1, 1), "1d")
    assert result is not None
    assert result.yhat == 0.015


def test_backtest_repository_get_by_run_id(db_session: Session):
    """Test BacktestRepository.get_by_run_id."""
    run_id = uuid4()
    backtest = Backtest(
        run_id=run_id,
        started_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        params={"strategy": "momentum"},
    )
    db_session.add(backtest)
    db_session.commit()

    result = BacktestRepository.get_by_run_id(db_session, run_id)
    assert result is not None
    assert result.params["strategy"] == "momentum"


def test_backtest_repository_get_latest(db_session: Session):
    """Test BacktestRepository.get_latest."""
    for i in range(3):
        backtest = Backtest(
            run_id=uuid4(),
            started_at=datetime(2024, 1, i + 1, 0, 0, 0, tzinfo=UTC),
            params={"strategy": f"strategy_{i}"},
        )
        db_session.add(backtest)
    db_session.commit()

    results = BacktestRepository.get_latest(db_session, limit=2)
    assert len(results) == 2
    # Results should be in descending order by started_at
    assert results[0].started_at == datetime(2024, 1, 3, 0, 0, 0, tzinfo=UTC)


def test_backtest_repository_create(db_session: Session):
    """Test BacktestRepository.create."""
    run_id = uuid4()
    started_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    params = {"strategy": "momentum", "lookback": 30}
    metrics = {"sharpe": 1.5}

    backtest = BacktestRepository.create(db_session, run_id, started_at, params, metrics=metrics)

    assert backtest.run_id == run_id
    assert backtest.params["strategy"] == "momentum"
    assert backtest.metrics["sharpe"] == 1.5

    # Verify it was persisted
    retrieved = BacktestRepository.get_by_run_id(db_session, run_id)
    assert retrieved is not None
    assert retrieved.run_id == run_id
