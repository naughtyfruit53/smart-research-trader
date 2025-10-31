"""NSE price adapter stub for future implementation."""

from datetime import datetime

import pandas as pd


class NSEPriceAdapter:
    """NSE adapter stub - demonstrates pluggability."""

    def fetch_prices(
        self, ticker: str, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> pd.DataFrame:
        """Fetch historical prices from NSE.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date for data fetch
            end_date: End date for data fetch

        Returns:
            DataFrame with columns: [ticker, dt, open, high, low, close, volume, adj_close]

        Raises:
            NotImplementedError: This is a placeholder adapter
        """
        raise NotImplementedError("NSE adapter not yet implemented. Use 'yf' provider.")
