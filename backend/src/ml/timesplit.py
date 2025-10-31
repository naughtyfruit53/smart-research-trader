"""Time-series cross-validation with expanding window and embargo."""

import logging
from datetime import date

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def expanding_window_split(
    dates: pd.Series | list[date] | np.ndarray,
    n_splits: int = 5,
    embargo_days: int = 0,
    test_size: float = 0.2,
    seed: int = 42,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Generate expanding window time-series cross-validation splits with embargo.

    Each split uses an expanding training window and a fixed-size test window.
    An embargo period can be added between train and test to prevent leakage.

    Args:
        dates: Series or array of dates (will be sorted)
        n_splits: Number of folds/splits
        embargo_days: Days to embargo between train and test (default 0)
        test_size: Fraction of data for test set in each split (default 0.2)
        seed: Random seed for deterministic splits (default 42)

    Returns:
        List of (train_indices, test_indices) tuples

    Example:
        >>> dates = pd.date_range('2024-01-01', periods=100, freq='D')
        >>> splits = expanding_window_split(dates, n_splits=3, embargo_days=5)
        >>> for i, (train_idx, test_idx) in enumerate(splits):
        ...     print(f"Fold {i}: train={len(train_idx)}, test={len(test_idx)}")
    """
    # Convert to numpy array of dates
    if isinstance(dates, pd.Series):
        dates_arr = dates.values
    elif isinstance(dates, list):
        dates_arr = np.array(dates)
    else:
        dates_arr = dates

    # Sort dates
    dates_sorted = np.sort(dates_arr)
    n_samples = len(dates_sorted)

    if n_samples < n_splits + 1:
        raise ValueError(
            f"Not enough samples ({n_samples}) for {n_splits} splits. "
            f"Need at least {n_splits + 1} samples."
        )

    # Set random seed for deterministic splits
    np.random.seed(seed)

    # Calculate test window size
    test_window_size = int(n_samples * test_size)
    if test_window_size < 1:
        test_window_size = 1

    # Generate splits
    splits = []

    # Calculate step size for test windows
    available_for_test = n_samples - test_window_size
    step = max(1, available_for_test // n_splits)

    for i in range(n_splits):
        # Test window: move forward for each split
        test_end_idx = min(n_samples, test_window_size + (i + 1) * step)
        test_start_idx = max(0, test_end_idx - test_window_size)

        # Skip if test window would extend beyond data
        if test_end_idx > n_samples:
            continue

        # Get test dates
        test_start_date = dates_sorted[test_start_idx]
        test_end_date = dates_sorted[test_end_idx - 1]

        # Apply embargo: train ends embargo_days before test start
        if embargo_days > 0:
            train_end_date = test_start_date - pd.Timedelta(days=embargo_days)
        else:
            train_end_date = test_start_date - pd.Timedelta(days=1)

        # Train indices: all data up to train_end_date
        train_mask = dates_sorted <= train_end_date
        train_indices = np.where(train_mask)[0]

        # Test indices: test window
        test_mask = (dates_sorted >= test_start_date) & (dates_sorted <= test_end_date)
        test_indices = np.where(test_mask)[0]

        # Skip if train or test is empty
        if len(train_indices) == 0 or len(test_indices) == 0:
            logger.warning(
                f"Skipping split {i}: train={len(train_indices)}, test={len(test_indices)}"
            )
            continue

        splits.append((train_indices, test_indices))

        logger.debug(
            f"Split {i}: train_end={train_end_date}, test_start={test_start_date}, "
            f"test_end={test_end_date}, train_size={len(train_indices)}, "
            f"test_size={len(test_indices)}"
        )

    if not splits:
        raise ValueError("No valid splits generated. Try reducing n_splits or embargo_days.")

    logger.info(f"Generated {len(splits)} time-series splits with {embargo_days}d embargo")

    return splits


def get_cv_dates(
    df: pd.DataFrame,
    date_col: str = "dt",
    n_splits: int = 5,
    embargo_days: int = 0,
    test_size: float = 0.2,
    seed: int = 42,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Generate CV splits from a DataFrame with dates.

    Convenience wrapper around expanding_window_split for DataFrames.

    Args:
        df: DataFrame with date column
        date_col: Name of date column (default 'dt')
        n_splits: Number of folds
        embargo_days: Days to embargo between train and test
        test_size: Fraction for test set
        seed: Random seed for deterministic splits

    Returns:
        List of (train_indices, test_indices) tuples

    Example:
        >>> df = pd.DataFrame({'dt': pd.date_range('2024-01-01', periods=100)})
        >>> splits = get_cv_dates(df, n_splits=3, embargo_days=5)
    """
    if date_col not in df.columns:
        raise ValueError(f"Date column '{date_col}' not found in DataFrame")

    dates = df[date_col]
    return expanding_window_split(
        dates=dates, n_splits=n_splits, embargo_days=embargo_days, test_size=test_size, seed=seed
    )


def get_train_test_dates(
    train_indices: np.ndarray, test_indices: np.ndarray, dates: pd.Series | list[date] | np.ndarray
) -> tuple[date, date, date, date]:
    """Get train and test date ranges from indices.

    Args:
        train_indices: Training indices
        test_indices: Test indices
        dates: Array of dates

    Returns:
        (train_start, train_end, test_start, test_end) dates
    """
    if isinstance(dates, pd.Series):
        dates_arr = dates.values
    elif isinstance(dates, list):
        dates_arr = np.array(dates)
    else:
        dates_arr = dates

    train_start = dates_arr[train_indices[0]]
    train_end = dates_arr[train_indices[-1]]
    test_start = dates_arr[test_indices[0]]
    test_end = dates_arr[test_indices[-1]]

    return train_start, train_end, test_start, test_end
