"""Repository helpers for common database operations."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .models import Backtest, Feature, Fundamental, News, Pred, Price


class PriceRepository:
    """Repository for Price operations."""

    @staticmethod
    def get_by_ticker_date(db: Session, ticker: str, dt: date) -> Price | None:
        """Get price by ticker and date."""
        return db.execute(
            select(Price).where(Price.ticker == ticker, Price.dt == dt)
        ).scalar_one_or_none()

    @staticmethod
    def get_latest_by_ticker(db: Session, ticker: str, limit: int = 100) -> list[Price]:
        """Get latest prices for a ticker."""
        return list(
            db.execute(
                select(Price).where(Price.ticker == ticker).order_by(desc(Price.dt)).limit(limit)
            ).scalars()
        )


class NewsRepository:
    """Repository for News operations."""

    @staticmethod
    def get_by_ticker(db: Session, ticker: str, limit: int = 100, offset: int = 0) -> list[News]:
        """Get news articles for a ticker."""
        return list(
            db.execute(
                select(News)
                .where(News.ticker == ticker)
                .order_by(desc(News.dt))
                .limit(limit)
                .offset(offset)
            ).scalars()
        )

    @staticmethod
    def get_latest(db: Session, limit: int = 100) -> list[News]:
        """Get latest news articles."""
        return list(db.execute(select(News).order_by(desc(News.dt)).limit(limit)).scalars())


class FundamentalRepository:
    """Repository for Fundamental operations."""

    @staticmethod
    def get_latest_by_ticker(db: Session, ticker: str) -> Fundamental | None:
        """Get latest fundamental data for a ticker."""
        return db.execute(
            select(Fundamental)
            .where(Fundamental.ticker == ticker)
            .order_by(desc(Fundamental.asof))
            .limit(1)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_ticker_date(db: Session, ticker: str, asof: date) -> Fundamental | None:
        """Get fundamental data by ticker and date."""
        return db.execute(
            select(Fundamental).where(Fundamental.ticker == ticker, Fundamental.asof == asof)
        ).scalar_one_or_none()


class FeatureRepository:
    """Repository for Feature operations."""

    @staticmethod
    def get_by_ticker_date(db: Session, ticker: str, dt: date) -> Feature | None:
        """Get features by ticker and date."""
        return db.execute(
            select(Feature).where(Feature.ticker == ticker, Feature.dt == dt)
        ).scalar_one_or_none()

    @staticmethod
    def get_latest_by_ticker(db: Session, ticker: str, limit: int = 100) -> list[Feature]:
        """Get latest features for a ticker."""
        return list(
            db.execute(
                select(Feature)
                .where(Feature.ticker == ticker)
                .order_by(desc(Feature.dt))
                .limit(limit)
            ).scalars()
        )


class PredRepository:
    """Repository for Pred operations."""

    @staticmethod
    def get_latest_by_date(db: Session, dt: date, limit: int = 100) -> list[Pred]:
        """Get latest predictions by date."""
        return list(db.execute(select(Pred).where(Pred.dt == dt).limit(limit)).scalars())

    @staticmethod
    def get_by_ticker(db: Session, ticker: str, limit: int = 100, offset: int = 0) -> list[Pred]:
        """Get predictions for a ticker."""
        return list(
            db.execute(
                select(Pred)
                .where(Pred.ticker == ticker)
                .order_by(desc(Pred.dt))
                .limit(limit)
                .offset(offset)
            ).scalars()
        )

    @staticmethod
    def get_by_ticker_date_horizon(db: Session, ticker: str, dt: date, horizon: str) -> Pred | None:
        """Get prediction by ticker, date, and horizon."""
        return db.execute(
            select(Pred).where(Pred.ticker == ticker, Pred.dt == dt, Pred.horizon == horizon)
        ).scalar_one_or_none()


class BacktestRepository:
    """Repository for Backtest operations."""

    @staticmethod
    def get_by_run_id(db: Session, run_id: UUID) -> Backtest | None:
        """Get backtest by run_id."""
        return db.execute(select(Backtest).where(Backtest.run_id == run_id)).scalar_one_or_none()

    @staticmethod
    def get_latest(db: Session, limit: int = 10) -> list[Backtest]:
        """Get latest backtests."""
        return list(
            db.execute(select(Backtest).order_by(desc(Backtest.started_at)).limit(limit)).scalars()
        )

    @staticmethod
    def create(
        db: Session,
        run_id: UUID,
        started_at: Any,
        params: dict[str, Any],
        finished_at: Any = None,
        metrics: dict[str, Any] | None = None,
    ) -> Backtest:
        """Create a new backtest."""
        backtest = Backtest(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            params=params,
            metrics=metrics,
        )
        db.add(backtest)
        db.commit()
        db.refresh(backtest)
        return backtest
