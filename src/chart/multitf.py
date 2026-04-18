"""Multi-timeframe chart composition — 1D + 4H + 15m in one image."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from .data_loader import load_ohlcv, Timeframe


def render_multi_timeframe(
    ticker: str,
    *,
    timeframes: tuple[Timeframe, ...] = ("daily", "4h", "15m"),
    lookback_map: dict[Timeframe, int] | None = None,
    output_path: str | Path = None,
    figsize: tuple[int, int] = (14, 12),
    dpi: int = 120,
) -> Path:
    """Render 3 timeframes stacked vertically in one PNG.

    Args:
        ticker: e.g., 'NVDA'
        timeframes: Tuple of 3 timeframes, typically (daily, 4h, 15m)
                    for trend / swing / entry confluence analysis.
        lookback_map: Override number of bars per timeframe.
                      Default: {daily: 180, 4h: 120, 15m: 60}
        output_path: PNG output path
        figsize: (width, height)
        dpi: Output DPI

    Returns:
        Path to saved PNG.

    Use case:
        Detect when daily trend is up AND 4h swing is pullback AND 15m entry
        triggers (e.g., engulfing candle) — all 3 confluences visible at once.
    """
    if output_path is None:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"output/{ticker}_multitf_{ts}.png")
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if lookback_map is None:
        lookback_map = {"daily": 180, "4h": 120, "1h": 120, "15m": 60, "weekly": 104}

    # Load data for each timeframe
    data_frames = {}
    for tf in timeframes:
        df = load_ohlcv(ticker, timeframe=tf)
        lookback = lookback_map.get(tf, 100)
        df = df.tail(lookback)
        data_frames[tf] = df

    # Build composite figure
    n = len(timeframes)
    fig = plt.figure(figsize=figsize, dpi=dpi)
    gs = GridSpec(n, 1, hspace=0.4)

    for i, tf in enumerate(timeframes):
        df = data_frames[tf]
        ax = fig.add_subplot(gs[i, 0])

        # Use mplfinance with ax-like mode: directly plot OHLC with matplotlib
        # (mpf.plot's ax param support is limited, so we manual-plot here)
        from mplfinance.original_flavor import candlestick_ohlc
        import matplotlib.dates as mdates

        # Moving averages based on timeframe
        ma_list = {"weekly": [4, 13], "daily": [20, 60], "4h": [20, 50],
                   "1h": [20, 50], "15m": [20]}.get(tf, [20])
        for ma_p in ma_list:
            if len(df) > ma_p:
                ma_series = df["close"].rolling(ma_p).mean()
                ax.plot(df.index, ma_series, linewidth=0.8, label=f"MA{ma_p}")

        # Candlestick data: (date_num, open, high, low, close)
        ohlc_data = [
            (mdates.date2num(idx), row["open"], row["high"], row["low"], row["close"])
            for idx, row in df.iterrows()
        ]
        candlestick_ohlc(ax, ohlc_data, width=0.0005 if tf in ("15m", "1h")
                                        else 0.3 if tf == "daily"
                                        else 0.1,
                         colorup="g", colordown="r", alpha=0.8)

        ax.set_title(f"{ticker} — {tf.upper()}")
        ax.xaxis_date()
        ax.grid(alpha=0.2)
        ax.legend(loc="upper left", fontsize=7)
        if tf in ("15m", "1h"):
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

    fig.suptitle(f"{ticker} Multi-Timeframe Confluence View", fontsize=14, y=0.995)
    fig.savefig(str(output_path), dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return output_path
