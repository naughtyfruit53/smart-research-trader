"""Tests for ML labeling module."""

from datetime import date

import pandas as pd
import pytest

from src.db.models import Feature, Price
from src.ml.labeling import (
    compute_and_upsert_labels,
    compute_forward_returns,
    upsert_labels_to_features,
)


def test_compute_forward_returns_basic():
    """Test basic forward return computation."""
    prices = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "dt": [date(2024, 1, i) for i in range(1, 6)],
            "close": [100.0, 102.0, 101.0, 103.0, 102.5],
        }
    )

    labels = compute_forward_returns(prices, horizon_days=1)

    # Check shape (last row dropped due to no forward data)
    assert len(labels) == 4
    assert "label_ret_1d" in labels.columns

    # Check first value: (102.0 / 100.0) - 1 = 0.02
    assert abs(labels.iloc[0]["label_ret_1d"] - 0.02) < 1e-6

    # Check second value: (101.0 / 102.0) - 1 ≈ -0.0098
    assert abs(labels.iloc[1]["label_ret_1d"] - (-0.0098039)) < 1e-5


def test_compute_forward_returns_multiple_tickers():
    """Test forward returns with multiple tickers."""
    prices = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 3 + ["MSFT"] * 3,
            "dt": [date(2024, 1, i) for i in range(1, 4)] * 2,
            "close": [100.0, 105.0, 103.0, 200.0, 210.0, 205.0],
        }
    )

    labels = compute_forward_returns(prices, horizon_days=1)

    # Each ticker should have 2 labels (last row dropped per ticker)
    assert len(labels) == 4

    # Check AAPL first return: 105/100 - 1 = 0.05
    aapl_labels = labels[labels["ticker"] == "AAPL"]
    assert abs(aapl_labels.iloc[0]["label_ret_1d"] - 0.05) < 1e-6

    # Check MSFT first return: 210/200 - 1 = 0.05
    msft_labels = labels[labels["ticker"] == "MSFT"]
    assert abs(msft_labels.iloc[0]["label_ret_1d"] - 0.05) < 1e-6


def test_compute_forward_returns_multi_day_horizon():
    """Test forward returns with 2-day horizon."""
    prices = pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "dt": [date(2024, 1, i) for i in range(1, 6)],
            "close": [100.0, 102.0, 101.0, 103.0, 102.5],
        }
    )

    labels = compute_forward_returns(prices, horizon_days=2)

    # 5 prices - 2 horizon = 3 labels
    assert len(labels) == 3
    assert "label_ret_2d" in labels.columns

    # First label: (101.0 / 100.0) - 1 = 0.01
    assert abs(labels.iloc[0]["label_ret_2d"] - 0.01) < 1e-6


def test_compute_forward_returns_empty_dataframe():
    """Test handling of empty DataFrame."""
    prices = pd.DataFrame()
    labels = compute_forward_returns(prices)

    assert labels.empty


def test_compute_forward_returns_missing_columns():
    """Test error on missing required columns."""
    prices = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "dt": [date(2024, 1, 1)],
            # Missing 'close' column
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        compute_forward_returns(prices)


def test_upsert_labels_to_features(db_session):
    """Test upserting labels to existing features."""
    # Create prices
    prices = [
        Price(
            ticker="AAPL",
            dt=date(2024, 1, i),
            open=100,
            high=105,
            low=95,
            close=100 + i,
            volume=1000,
            adj_close=100 + i,
        )
        for i in range(1, 4)
    ]
    db_session.add_all(prices)

    # Create features (without labels)
    features = [
        Feature(ticker="AAPL", dt=date(2024, 1, i), features_json={"sma_20": 100.0})
        for i in range(1, 3)
    ]
    db_session.add_all(features)
    db_session.commit()

    # Create labels DataFrame
    labels = pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "dt": [date(2024, 1, 1), date(2024, 1, 2)],
            "label_ret_1d": [0.01, 0.02],
        }
    )

    # Upsert labels
    num_updated = upsert_labels_to_features(db_session, labels, "label_ret_1d")

    assert num_updated == 2

    # Verify labels were updated
    feat1 = db_session.query(Feature).filter_by(ticker="AAPL", dt=date(2024, 1, 1)).first()
    assert feat1.label_ret_1d == 0.01

    feat2 = db_session.query(Feature).filter_by(ticker="AAPL", dt=date(2024, 1, 2)).first()
    assert feat2.label_ret_1d == 0.02


def test_upsert_labels_no_matching_features(db_session):
    """Test upserting labels when no matching features exist."""
    labels = pd.DataFrame({"ticker": ["AAPL"], "dt": [date(2024, 1, 1)], "label_ret_1d": [0.01]})

    num_updated = upsert_labels_to_features(db_session, labels, "label_ret_1d")

    assert num_updated == 0


def test_compute_and_upsert_labels_integration(db_session):
    """Test end-to-end label computation and upsertion."""
    # Create prices
    prices = [
        Price(
            ticker="AAPL",
            dt=date(2024, 1, i),
            open=100,
            high=105,
            low=95,
            close=100 + i,
            volume=1000,
            adj_close=100 + i,
        )
        for i in range(1, 5)
    ]
    db_session.add_all(prices)

    # Create features
    features = [
        Feature(ticker="AAPL", dt=date(2024, 1, i), features_json={"sma_20": 100.0})
        for i in range(1, 4)
    ]
    db_session.add_all(features)
    db_session.commit()

    # Compute and upsert labels
    num_updated = compute_and_upsert_labels(db_session, tickers=["AAPL"], horizon_days=1)

    # Should update 3 features (last price has no forward data)
    assert num_updated == 3

    # Verify first label
    feat = db_session.query(Feature).filter_by(ticker="AAPL", dt=date(2024, 1, 1)).first()
    # (102 / 101) - 1 ≈ 0.0099
    assert feat.label_ret_1d is not None
    assert abs(feat.label_ret_1d - 0.0099009) < 1e-5
