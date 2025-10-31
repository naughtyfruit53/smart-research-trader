"""SQLAlchemy 2.0 database models."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Date,
    Float,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Price(Base):
    """Price table for historical OHLCV data."""

    __tablename__ = "prices"

    ticker: Mapped[str] = mapped_column(Text, primary_key=True)
    dt: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Numeric)
    high: Mapped[float] = mapped_column(Numeric)
    low: Mapped[float] = mapped_column(Numeric)
    close: Mapped[float] = mapped_column(Numeric)
    volume: Mapped[int] = mapped_column(BigInteger)
    adj_close: Mapped[float] = mapped_column(Numeric)

    __table_args__ = (Index("ix_prices_ticker", "ticker"), Index("ix_prices_dt", "dt"))


class News(Base):
    """News table for news articles and sentiment analysis."""

    __tablename__ = "news"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dt: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    ticker: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    headline: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    sent_pos: Mapped[float] = mapped_column(Float)
    sent_neg: Mapped[float] = mapped_column(Float)
    sent_comp: Mapped[float] = mapped_column(Float)

    __table_args__ = (
        Index("ix_news_ticker", "ticker"),
        Index("ix_news_dt", "dt"),
        Index("ix_news_ticker_dt", "ticker", "dt"),
    )


class Fundamental(Base):
    """Fundamental table for fundamental analysis metrics."""

    __tablename__ = "fundamentals"

    ticker: Mapped[str] = mapped_column(Text, primary_key=True)
    asof: Mapped[date] = mapped_column(Date, primary_key=True)
    pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    pb: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    roce: Mapped[float | None] = mapped_column(Float, nullable=True)
    de_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps_g3y: Mapped[float | None] = mapped_column(Float, nullable=True)
    rev_g3y: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_g3y: Mapped[float | None] = mapped_column(Float, nullable=True)
    opm: Mapped[float | None] = mapped_column(Float, nullable=True)
    npm: Mapped[float | None] = mapped_column(Float, nullable=True)
    div_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    promoter_hold: Mapped[float | None] = mapped_column(Float, nullable=True)
    pledged_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_fundamentals_ticker", "ticker"),
        Index("ix_fundamentals_asof", "asof"),
    )


class Feature(Base):
    """Feature table for engineered features."""

    __tablename__ = "features"

    ticker: Mapped[str] = mapped_column(Text, primary_key=True)
    dt: Mapped[date] = mapped_column(Date, primary_key=True)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    label_ret_1d: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (Index("ix_features_ticker", "ticker"), Index("ix_features_dt", "dt"))


class Pred(Base):
    """Pred table for model predictions."""

    __tablename__ = "preds"

    ticker: Mapped[str] = mapped_column(Text, primary_key=True)
    dt: Mapped[date] = mapped_column(Date, primary_key=True)
    horizon: Mapped[str] = mapped_column(String(50), primary_key=True)
    yhat: Mapped[float] = mapped_column(Float)
    yhat_std: Mapped[float] = mapped_column(Float)
    prob_up: Mapped[float] = mapped_column(Float)

    __table_args__ = (
        Index("ix_preds_ticker", "ticker"),
        Index("ix_preds_dt", "dt"),
        Index("ix_preds_ticker_dt", "ticker", "dt"),
    )


class Backtest(Base):
    """Backtest table for backtest results."""

    __tablename__ = "backtests"

    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (Index("ix_backtests_started_at", "started_at"),)
