"""Shared helpers for DataFrame normalization and data processing."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def normalize_dates(df: pd.DataFrame, date_column: str = "dt") -> pd.DataFrame:
    """Normalize date column to consistent format.

    Args:
        df: Input DataFrame
        date_column: Name of the date column

    Returns:
        DataFrame with normalized dates
    """
    if date_column not in df.columns:
        return df

    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column], errors="coerce")

    # Drop rows with invalid dates
    before_count = len(df)
    df = df.dropna(subset=[date_column])
    after_count = len(df)

    if before_count != after_count:
        logger.warning(f"Dropped {before_count - after_count} rows with invalid dates")

    return df


def normalize_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Normalize numeric columns, coercing errors to NaN.

    Args:
        df: Input DataFrame
        columns: List of column names to normalize

    Returns:
        DataFrame with normalized numeric columns
    """
    df = df.copy()

    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def batch_dataframe(df: pd.DataFrame, batch_size: int):
    """Yield batches of a DataFrame.

    Args:
        df: Input DataFrame
        batch_size: Number of rows per batch

    Yields:
        DataFrame batches
    """
    for i in range(0, len(df), batch_size):
        yield df.iloc[i : i + batch_size]


def deduplicate_by_key(
    df: pd.DataFrame, key_columns: list[str], keep: str = "last"
) -> pd.DataFrame:
    """Remove duplicate rows based on key columns.

    Args:
        df: Input DataFrame
        key_columns: List of columns that form the unique key
        keep: Which duplicate to keep ('first', 'last')

    Returns:
        DataFrame with duplicates removed
    """
    before_count = len(df)
    df = df.drop_duplicates(subset=key_columns, keep=keep)
    after_count = len(df)

    if before_count != after_count:
        logger.info(f"Removed {before_count - after_count} duplicate rows")

    return df


def validate_required_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    """Validate that DataFrame contains required columns.

    Args:
        df: Input DataFrame
        required_columns: List of required column names

    Raises:
        ValueError: If any required columns are missing
    """
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def fill_missing_values(df: pd.DataFrame, fill_values: dict[str, any]) -> pd.DataFrame:
    """Fill missing values with specified defaults.

    Args:
        df: Input DataFrame
        fill_values: Dictionary mapping column names to fill values

    Returns:
        DataFrame with filled values
    """
    df = df.copy()

    for col, value in fill_values.items():
        if col in df.columns:
            df[col] = df[col].fillna(value)

    return df
