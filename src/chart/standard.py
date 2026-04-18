"""Standard OHLCV candlestick chart with MAs and volume."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt


def render_standard_chart(
    df: pd.DataFrame,
    ticker: str,
    *,
    ma_periods: tuple[int, ...] = (5, 20, 60, 120),
    title_suffix: str = "",
    output_path: str | Path = None,
    show_volume: bool = True,
    style: str = "yahoo",
    figsize: tuple[int, int] = (14, 9),
    dpi: int = 120,
) -> Path:
    """Render a standard candlestick chart with MAs and volume.

    Args:
        df: OHLCV DataFrame (open, high, low, close, volume)
        ticker: e.g., 'NVDA'
        ma_periods: Moving averages to overlay. Default (5, 20, 60, 120).
        title_suffix: Extra text after ticker (e.g., '(daily, 6mo)')
        output_path: Save path. If None, auto-generate in 'output/{ticker}_{timestamp}.png'
        show_volume: Whether to include volume subplot
        style: mplfinance style name
        figsize: (width, height) in inches
        dpi: Output DPI

    Returns:
        Path to saved PNG
    """
    if output_path is None:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"output/{ticker}_{ts}.png")
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    title = f"{ticker}"
    if title_suffix:
        title += f" {title_suffix}"

    # Filter MAs to only those that fit within data range
    valid_mas = tuple(p for p in ma_periods if p < len(df))

    kwargs = {
        "type": "candle",
        "style": style,
        "title": title,
        "volume": show_volume and "volume" in df.columns,
        "mav": valid_mas if valid_mas else None,
        "figsize": figsize,
        "savefig": dict(fname=str(output_path), dpi=dpi, bbox_inches="tight"),
        "tight_layout": True,
        "datetime_format": "%Y-%m-%d",
        "xrotation": 0,
    }

    # Strip kwargs that are None (mplfinance is picky)
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    mpf.plot(df, **kwargs)
    plt.close("all")

    return output_path


def render_with_overlays(
    df: pd.DataFrame,
    ticker: str,
    *,
    support_lines: list[dict] | None = None,  # [{slope, intercept, start_idx, end_idx}]
    resistance_lines: list[dict] | None = None,
    swing_points: list[dict] | None = None,   # [{index, price, type}]
    output_path: str | Path = None,
    title_suffix: str = "",
    figsize: tuple[int, int] = (14, 9),
    dpi: int = 120,
) -> Path:
    """Render chart with trendline-detector output overlays.

    This consumes the JSON schema from the 'trendline-detector' repo.
    """
    if output_path is None:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"output/{ticker}_overlay_{ts}.png")
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # mplfinance 'alines' expects list of line segments in (date, price) pairs
    alines_data = []
    colors = []

    if support_lines:
        for line in support_lines:
            s_idx = line.get("start_index", 0)
            e_idx = min(line.get("end_index", len(df) - 1), len(df) - 1)
            # Extend line to end of data for visibility
            e_idx = len(df) - 1
            s_price = line["slope"] * s_idx + line["intercept"]
            e_price = line["slope"] * e_idx + line["intercept"]
            alines_data.append([(df.index[s_idx], s_price), (df.index[e_idx], e_price)])
            colors.append("g")

    if resistance_lines:
        for line in resistance_lines:
            s_idx = line.get("start_index", 0)
            e_idx = min(line.get("end_index", len(df) - 1), len(df) - 1)
            e_idx = len(df) - 1
            s_price = line["slope"] * s_idx + line["intercept"]
            e_price = line["slope"] * e_idx + line["intercept"]
            alines_data.append([(df.index[s_idx], s_price), (df.index[e_idx], e_price)])
            colors.append("r")

    # Swing points as markers
    add_plots = []
    if swing_points:
        import numpy as np
        swing_series = pd.Series([float("nan")] * len(df), index=df.index)
        for sp in swing_points:
            idx = sp["index"]
            if 0 <= idx < len(df):
                swing_series.iloc[idx] = sp["price"]
        # Only add if at least one marker present
        if swing_series.notna().any():
            add_plots.append(
                mpf.make_addplot(
                    swing_series,
                    type="scatter",
                    marker="o",
                    markersize=50,
                    color="orange",
                )
            )

    title = f"{ticker}"
    if title_suffix:
        title += f" {title_suffix}"

    kwargs = dict(
        type="candle",
        style="yahoo",
        title=title,
        volume="volume" in df.columns,
        figsize=figsize,
        savefig=dict(fname=str(output_path), dpi=dpi, bbox_inches="tight"),
        tight_layout=True,
    )
    if alines_data:
        kwargs["alines"] = dict(alines=alines_data, colors=colors, linewidths=1, alpha=0.7)
    if add_plots:
        kwargs["addplot"] = add_plots

    mpf.plot(df, **kwargs)
    plt.close("all")

    return output_path
