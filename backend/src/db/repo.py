"""Repository helpers for common database operations."""

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
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

    @staticmethod
    def get_price_series(db: Session, ticker: str, lookback_days: int = 200) -> list[Price]:
        """Get price series for a ticker for the last N trading days.
        
        Args:
            db: Database session
            ticker: Stock ticker symbol
            lookback_days: Number of trading days to retrieve
            
        Returns:
            List of Price objects ordered by date descending
        """
        return list(
            db.execute(
                select(Price)
                .where(Price.ticker == ticker)
                .order_by(desc(Price.dt))
                .limit(lookback_days)
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

    @staticmethod
    def get_latest_features_for_preds(db: Session, horizon: str = "1d") -> list[tuple[Pred, Feature]]:
        """Get latest predictions with their corresponding features.
        
        Args:
            db: Database session
            horizon: Prediction horizon
            
        Returns:
            List of (Pred, Feature) tuples
        """
        # Get latest date per ticker for this horizon
        subquery = (
            select(Pred.ticker, func.max(Pred.dt).label("max_dt"))
            .where(Pred.horizon == horizon)
            .group_by(Pred.ticker)
            .subquery()
        )
        
        # Join preds with features
        stmt = (
            select(Pred, Feature)
            .join(subquery, (Pred.ticker == subquery.c.ticker) & (Pred.dt == subquery.c.max_dt))
            .join(Feature, (Pred.ticker == Feature.ticker) & (Pred.dt == Feature.dt))
            .where(Pred.horizon == horizon)
        )
        
        return list(db.execute(stmt).all())


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

    @staticmethod
    def get_latest_preds(
        db: Session, horizon: str = "1d", tickers: list[str] | None = None, limit: int | None = None
    ) -> list[Pred]:
        """Get latest predictions per ticker for a given horizon.
        
        Args:
            db: Database session
            horizon: Prediction horizon (default: "1d")
            tickers: Optional list of tickers to filter
            limit: Optional limit on number of results
            
        Returns:
            List of latest predictions
        """
        # Get latest date per ticker for this horizon
        from sqlalchemy import func
        
        subquery = (
            select(Pred.ticker, func.max(Pred.dt).label("max_dt"))
            .where(Pred.horizon == horizon)
        )
        
        if tickers:
            subquery = subquery.where(Pred.ticker.in_(tickers))
        
        subquery = subquery.group_by(Pred.ticker).subquery()
        
        # Join to get full prediction records
        stmt = (
            select(Pred)
            .join(subquery, (Pred.ticker == subquery.c.ticker) & (Pred.dt == subquery.c.max_dt))
            .where(Pred.horizon == horizon)
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        return list(db.execute(stmt).scalars())


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
    def get_latest_backtest(db: Session) -> Backtest | None:
        """Get the most recent completed backtest by finished_at.
        
        Returns:
            Most recent backtest or None if no completed backtests exist
        """
        return db.execute(
            select(Backtest)
            .where(Backtest.finished_at.isnot(None))
            .order_by(desc(Backtest.finished_at))
            .limit(1)
        ).scalar_one_or_none()

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


def get_stock_snapshot(db: Session, ticker: str) -> dict[str, Any]:
    """Get complete stock snapshot with all metrics.
    
    Args:
        db: Database session
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary with fundamentals, technicals, sentiment, prediction, scores
    """
    result: dict[str, Any] = {
        "ticker": ticker,
        "fundamentals": {},
        "technicals": {},
        "sentiment": {},
        "prediction": {},
        "scores": {},
    }
    
    # Get latest fundamentals
    fund = FundamentalRepository.get_latest_by_ticker(db, ticker)
    if fund:
        result["fundamentals"] = {
            "pe": fund.pe,
            "pb": fund.pb,
            "ev_ebitda": fund.ev_ebitda,
            "roe": fund.roe,
            "roce": fund.roce,
            "de_ratio": fund.de_ratio,
            "eps_g3y": fund.eps_g3y,
            "rev_g3y": fund.rev_g3y,
            "profit_g3y": fund.profit_g3y,
            "opm": fund.opm,
            "npm": fund.npm,
            "div_yield": fund.div_yield,
            "asof": fund.asof,
        }
    
    # Get latest features for technicals, sentiment, and scores
    features = FeatureRepository.get_latest_by_ticker(db, ticker, limit=1)
    if features:
        feat = features[0]
        fj = feat.features_json or {}
        
        result["technicals"] = {
            "rsi14": fj.get("rsi14"),
            "sma20": fj.get("sma20"),
            "sma50": fj.get("sma50"),
            "sma200": fj.get("sma200"),
            "momentum20": fj.get("momentum20"),
            "momentum60": fj.get("momentum60"),
            "rv20": fj.get("rv20"),
        }
        
        result["sentiment"] = {
            "sent_mean_comp": fj.get("sent_mean_comp"),
            "burst_3d": fj.get("burst_3d"),
            "burst_7d": fj.get("burst_7d"),
        }
        
        result["scores"] = {
            "quality_score": fj.get("quality_score"),
            "valuation_score": fj.get("valuation_score"),
            "momentum_score": fj.get("momentum_score"),
            "sentiment_score": fj.get("sentiment_score"),
            "composite_score": fj.get("composite_score"),
            "risk_adjusted_score": fj.get("risk_adjusted_score"),
        }
    
    # Get latest prediction
    preds = PredRepository.get_by_ticker(db, ticker, limit=1)
    if preds:
        pred = preds[0]
        result["prediction"] = {
            "yhat": pred.yhat,
            "yhat_std": pred.yhat_std,
            "prob_up": pred.prob_up,
            "dt": pred.dt,
            "horizon": pred.horizon,
        }
    
    return result
