"""Tests for Alembic migrations."""

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from src.core.config import settings


def test_migration_schema_consistency():
    """Test that migration schema matches model schema."""
    # Create alembic config
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    # Reset to clean state and upgrade to head
    try:
        command.downgrade(alembic_cfg, "base")
    except Exception:
        # If downgrade fails (tables already dropped), continue
        pass
    command.upgrade(alembic_cfg, "head")

    # Create engine and inspector
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)

    # Verify all expected tables exist
    tables = inspector.get_table_names()
    expected_tables = [
        "prices",
        "news",
        "fundamentals",
        "features",
        "preds",
        "backtests",
    ]
    for table in expected_tables:
        assert table in tables

    # Check prices table
    prices_columns = {col["name"]: col for col in inspector.get_columns("prices")}
    assert "ticker" in prices_columns
    assert "dt" in prices_columns
    assert "open" in prices_columns
    assert "high" in prices_columns
    assert "low" in prices_columns
    assert "close" in prices_columns
    assert "volume" in prices_columns
    assert "adj_close" in prices_columns

    # Verify indexes exist
    prices_indexes = inspector.get_indexes("prices")
    index_names = [idx["name"] for idx in prices_indexes]
    assert "ix_prices_ticker" in index_names
    assert "ix_prices_dt" in index_names

    # Check news table
    news_columns = {col["name"]: col for col in inspector.get_columns("news")}
    assert "id" in news_columns
    assert "dt" in news_columns
    assert "ticker" in news_columns
    assert "headline" in news_columns
    assert "sent_pos" in news_columns

    # Check fundamentals table
    fund_columns = {col["name"]: col for col in inspector.get_columns("fundamentals")}
    assert "ticker" in fund_columns
    assert "asof" in fund_columns
    assert "pe" in fund_columns
    assert "roe" in fund_columns

    # Check features table
    feat_columns = {col["name"]: col for col in inspector.get_columns("features")}
    assert "ticker" in feat_columns
    assert "dt" in feat_columns
    assert "features_json" in feat_columns
    assert "label_ret_1d" in feat_columns

    # Check preds table
    pred_columns = {col["name"]: col for col in inspector.get_columns("preds")}
    assert "ticker" in pred_columns
    assert "dt" in pred_columns
    assert "horizon" in pred_columns
    assert "yhat" in pred_columns
    assert "prob_up" in pred_columns

    # Check backtests table
    bt_columns = {col["name"]: col for col in inspector.get_columns("backtests")}
    assert "run_id" in bt_columns
    assert "started_at" in bt_columns
    assert "params" in bt_columns
    assert "metrics" in bt_columns


def test_database_migration_current():
    """Test that database is at the expected migration version."""
    # Create alembic config
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    # Ensure we're at head
    command.upgrade(alembic_cfg, "head")

    # Verify alembic version table exists and has a version
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        assert version is not None
        assert len(version) > 0
