"""Fundamentals CSV importer compatible with Screener-like formats."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Expected column mappings from Screener CSV format to our schema
COLUMN_MAPPINGS = {
    "Ticker": "ticker",
    "Name": "name",
    "As Of": "asof",
    "P/E": "pe",
    "P/B": "pb",
    "EV/EBITDA": "ev_ebitda",
    "ROE": "roe",
    "ROCE": "roce",
    "D/E": "de_ratio",
    "EPS Growth 3Y": "eps_g3y",
    "Revenue Growth 3Y": "rev_g3y",
    "Profit Growth 3Y": "profit_g3y",
    "OPM": "opm",
    "NPM": "npm",
    "Dividend Yield": "div_yield",
    "Promoter Holding": "promoter_hold",
    "Pledged %": "pledged_pct",
}


class FundamentalScreenerAdapter:
    """CSV importer for fundamental data in Screener-like format."""

    def parse_csv(self, csv_path: str | Path) -> pd.DataFrame:
        """Parse fundamentals CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            DataFrame with normalized fundamental data
        """
        logger.info(f"Parsing fundamentals CSV: {csv_path}")

        try:
            df = pd.read_csv(csv_path)

            # Check for required columns
            if "Ticker" not in df.columns and "ticker" not in df.columns:
                raise ValueError("CSV must contain 'Ticker' or 'ticker' column")

            # Rename columns to match schema
            df = df.rename(columns=COLUMN_MAPPINGS)

            # Ensure ticker column exists
            if "ticker" not in df.columns:
                raise ValueError("Unable to identify ticker column")

            # Set default asof date if not provided
            if "asof" not in df.columns:
                df["asof"] = pd.Timestamp.now().date()
            else:
                df["asof"] = pd.to_datetime(df["asof"]).dt.date

            # Select only schema columns (ticker + asof + metrics)
            schema_cols = [
                "ticker",
                "asof",
                "pe",
                "pb",
                "ev_ebitda",
                "roe",
                "roce",
                "de_ratio",
                "eps_g3y",
                "rev_g3y",
                "profit_g3y",
                "opm",
                "npm",
                "div_yield",
                "promoter_hold",
                "pledged_pct",
            ]

            # Keep only columns that exist
            available_cols = [col for col in schema_cols if col in df.columns]
            df = df[available_cols]

            # Convert percentage strings to floats if needed
            for col in df.columns:
                if col not in ["ticker", "asof"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            logger.info(f"Parsed {len(df)} fundamental records")
            return df

        except Exception as e:
            logger.error(f"Error parsing CSV {csv_path}: {e}")
            raise
