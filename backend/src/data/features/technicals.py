"""Technical indicators computation using ta library."""

import logging

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, ADXIndicator, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands

logger = logging.getLogger(__name__)


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute technical indicators for price data.
    
    Input DataFrame should have columns: [ticker, dt, open, high, low, close, volume, adj_close]
    Output DataFrame will have additional columns for each indicator.
    
    Indicators computed:
    - SMA (20, 50, 200)
    - EMA (20, 50, 200)
    - RSI (14)
    - MACD (12, 26, 9)
    - ADX (14)
    - ATR (14)
    - Bollinger Band width (20, 2)
    - Momentum (20, 60)
    - Realized volatility (20-day rolling)
    
    Args:
        df: DataFrame with OHLCV data keyed by [ticker, dt]
        
    Returns:
        DataFrame with technical indicators added
    """
    if df.empty:
        return df
    
    # Ensure required columns exist
    required_cols = ["ticker", "dt", "open", "high", "low", "close", "volume", "adj_close"]
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Sort by ticker and date
    df = df.sort_values(["ticker", "dt"]).reset_index(drop=True)
    
    # Group by ticker and compute indicators
    result_dfs = []
    for ticker, group_df in df.groupby("ticker", sort=False):
        try:
            # Work on a copy
            ticker_df = group_df.copy()
            
            # Use adj_close for price-based indicators
            close_prices = ticker_df["adj_close"]
            high_prices = ticker_df["high"]
            low_prices = ticker_df["low"]
            
            # Skip if insufficient data (need at least 20 days for shortest indicator)
            # Note: Longer indicators (SMA_200) will have NaN for first 200 days
            if len(ticker_df) < 20:
                logger.debug(f"Skipping {ticker}: insufficient data ({len(ticker_df)} rows)")
                # Add NaN columns
                ticker_df = _add_nan_columns(ticker_df)
                result_dfs.append(ticker_df)
                continue
            
            # Simple Moving Averages
            ticker_df["sma_20"] = SMAIndicator(close=close_prices, window=20).sma_indicator()
            ticker_df["sma_50"] = SMAIndicator(close=close_prices, window=50).sma_indicator()
            ticker_df["sma_200"] = SMAIndicator(close=close_prices, window=200).sma_indicator()
            
            # Exponential Moving Averages
            ticker_df["ema_20"] = EMAIndicator(close=close_prices, window=20).ema_indicator()
            ticker_df["ema_50"] = EMAIndicator(close=close_prices, window=50).ema_indicator()
            ticker_df["ema_200"] = EMAIndicator(close=close_prices, window=200).ema_indicator()
            
            # RSI
            ticker_df["rsi_14"] = RSIIndicator(close=close_prices, window=14).rsi()
            
            # MACD
            macd_indicator = MACD(close=close_prices, window_slow=26, window_fast=12, window_sign=9)
            ticker_df["macd"] = macd_indicator.macd()
            ticker_df["macd_signal"] = macd_indicator.macd_signal()
            ticker_df["macd_diff"] = macd_indicator.macd_diff()
            
            # ADX
            ticker_df["adx_14"] = ADXIndicator(
                high=high_prices, low=low_prices, close=close_prices, window=14
            ).adx()
            
            # ATR
            ticker_df["atr_14"] = AverageTrueRange(
                high=high_prices, low=low_prices, close=close_prices, window=14
            ).average_true_range()
            
            # Bollinger Bands
            bb = BollingerBands(close=close_prices, window=20, window_dev=2)
            ticker_df["bb_high"] = bb.bollinger_hband()
            ticker_df["bb_low"] = bb.bollinger_lband()
            ticker_df["bb_mid"] = bb.bollinger_mavg()
            ticker_df["bb_width"] = (ticker_df["bb_high"] - ticker_df["bb_low"]) / ticker_df["bb_mid"]
            
            # Momentum (rate of change)
            ticker_df["momentum_20"] = close_prices.pct_change(periods=20)
            ticker_df["momentum_60"] = close_prices.pct_change(periods=60)
            
            # Realized Volatility (20-day rolling std of returns)
            returns = close_prices.pct_change()
            ticker_df["rv_20"] = returns.rolling(window=20).std()
            
            result_dfs.append(ticker_df)
            
        except Exception as e:
            logger.error(f"Error computing indicators for {ticker}: {e}")
            # Add NaN columns
            ticker_df = _add_nan_columns(group_df.copy())
            result_dfs.append(ticker_df)
    
    # Concatenate all results
    result = pd.concat(result_dfs, ignore_index=True)
    return result


def _add_nan_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add indicator columns filled with NaN."""
    columns = [
        "sma_20", "sma_50", "sma_200",
        "ema_20", "ema_50", "ema_200",
        "rsi_14",
        "macd", "macd_signal", "macd_diff",
        "adx_14", "atr_14",
        "bb_high", "bb_low", "bb_mid", "bb_width",
        "momentum_20", "momentum_60",
        "rv_20"
    ]
    for col in columns:
        df[col] = float("nan")
    return df
