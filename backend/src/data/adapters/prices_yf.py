"""Yahoo Finance price adapter with retry logic."""

import logging
from datetime import datetime, timedelta

import pandas as pd
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger(__name__)


class YFinancePriceAdapter:
    """Yahoo Finance adapter for fetching historical OHLCV data."""

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def fetch_prices(
        self, ticker: str, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> pd.DataFrame:
        """Fetch historical prices for a ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'RELIANCE.NS')
            start_date: Start date for data fetch (default: 10 years ago)
            end_date: End date for data fetch (default: today)

        Returns:
            DataFrame with columns: [ticker, dt, open, high, low, close, volume, adj_close]
        """
        if yf is None:
            raise ImportError("yfinance package not installed. Install with: pip install yfinance")

        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 10)
        if end_date is None:
            end_date = datetime.now()

        logger.info(f"Fetching prices for {ticker} from {start_date} to {end_date}")

        try:
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date, auto_adjust=False)

            if df.empty:
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            # Normalize columns to match schema
            df = df.reset_index()
            df = df.rename(
                columns={
                    "Date": "dt",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                    "Adj Close": "adj_close",
                }
            )

            # Add ticker column
            df["ticker"] = ticker

            # Select only required columns in correct order
            df = df[["ticker", "dt", "open", "high", "low", "close", "volume", "adj_close"]]

            # Convert dt to date (remove time component)
            df["dt"] = pd.to_datetime(df["dt"]).dt.date

            # Ensure volume is integer
            df["volume"] = df["volume"].astype(int)

            logger.info(f"Fetched {len(df)} rows for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching prices for {ticker}: {e}")
            raise
