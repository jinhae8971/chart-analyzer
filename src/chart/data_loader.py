"""OHLCV data loader — yfinance primary, stale-resistant."""
from __future__ import annotations

from typing import Literal

import pandas as pd

Timeframe = Literal["15m", "1h", "4h", "daily", "weekly"]

_YF_INTERVAL_MAP = {
    "15m": "15m",
    "1h": "60m",
    "4h": "60m",    # yfinance has no 4h; resample from 1h
    "daily": "1d",
    "weekly": "1wk",
}

_YF_PERIOD_MAP = {
    "15m": "60d",     # yfinance 15m max = 60 days
    "1h": "730d",     # yfinance 1h max = 730 days
    "4h": "730d",
    "daily": "2y",
    "weekly": "10y",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten multi-level columns and lowercase."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df.rename(columns={c: c.lower() for c in df.columns})


def load_ohlcv(
    ticker: str,
    timeframe: Timeframe = "daily",
    *,
    period: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Load OHLCV data from yfinance.

    Args:
        ticker: e.g., 'NVDA', 'SPY', 'BTC-USD', '005930.KS' (Korean stocks)
        timeframe: '15m', '1h', '4h', 'daily', 'weekly'
        period: Override default period (e.g., '6mo', '1y', '5y')
        start, end: Alternative to period; explicit date range (YYYY-MM-DD)

    Returns:
        DataFrame with columns: open, high, low, close, volume
        Index: DatetimeIndex
    """
    import yfinance as yf

    interval = _YF_INTERVAL_MAP[timeframe]
    default_period = _YF_PERIOD_MAP[timeframe]

    kwargs = {"interval": interval, "progress": False, "auto_adjust": False}
    if start or end:
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end
    else:
        kwargs["period"] = period or default_period

    df = yf.download(ticker, **kwargs)
    if df is None or len(df) == 0:
        raise ValueError(f"No data for {ticker} @ {timeframe}")

    df = _normalize_columns(df)

    # Synthesize 4h by resampling 1h
    if timeframe == "4h":
        df = df.resample("4h").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()

    return df
