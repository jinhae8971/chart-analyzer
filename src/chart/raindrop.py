"""Raindrop-like Volume Profile chart — TrendSpider Raindrop Chart alternative.

Strategy:
    TrendSpider's Raindrop Chart shows volume-at-price distribution within
    each bar's time period. We approximate this with:
        1. For each daily bar, compute a volume-weighted kernel density
           estimate of prices traded that day (using high, low, OHLC
           as anchor points).
        2. Render the KDE as a horizontal "raindrop" shape aligned with
           the bar's time slot.
        3. Wider horizontal = more volume at that price.

This gives essentially the same visual — "institutional accumulation zones"
become visible as thick horizontal bulges on the chart.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection


def _estimate_bar_volume_distribution(
    bar: pd.Series,
    n_points: int = 30,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate price-vs-volume distribution within a single bar.

    Real tick data isn't available, so we approximate:
        - OHLC prices are 'anchor' points with higher weight at close
        - Kernel-smoothed between low and high
        - Typical price (H+L+C)/3 gets extra weight

    Returns:
        (prices, volume_density) arrays of length n_points.
    """
    low, high = float(bar["low"]), float(bar["high"])
    if high == low:
        return np.array([low]), np.array([float(bar["volume"])])

    open_, close = float(bar["open"]), float(bar["close"])
    typical = (high + low + close) / 3.0

    # Evaluate KDE-like distribution
    prices = np.linspace(low, high, n_points)
    bandwidth = (high - low) / 6.0

    # Anchor weights: close (2x), typical (1.5x), open (1x), high/low (0.5x each)
    anchors = [
        (close, 2.0),
        (typical, 1.5),
        (open_, 1.0),
        (high, 0.5),
        (low, 0.5),
    ]

    density = np.zeros_like(prices)
    for anchor_price, weight in anchors:
        # Gaussian kernel around each anchor
        kernel = np.exp(-0.5 * ((prices - anchor_price) / bandwidth) ** 2)
        density += weight * kernel

    # Normalize and scale by actual bar volume
    if density.sum() > 0:
        density = density / density.sum() * float(bar["volume"])

    return prices, density


def render_raindrop_chart(
    df: pd.DataFrame,
    ticker: str,
    *,
    lookback_days: int = 60,
    output_path: str | Path = None,
    figsize: tuple[int, int] = (14, 8),
    dpi: int = 120,
    title_suffix: str = "",
) -> Path:
    """Render a Raindrop-like chart showing volume distribution per bar.

    Wider horizontal bulges = higher volume at that price level within the bar.
    This visualizes institutional accumulation/distribution zones that a
    standard candlestick chart cannot show.
    """
    if output_path is None:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"output/{ticker}_raindrop_{ts}.png")
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = df.tail(lookback_days).copy()

    # Normalize columns
    df.columns = [c.lower() if isinstance(c, str) else c for c in df.columns]
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1, figsize=figsize, dpi=dpi,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.1},
        sharex=True,
    )

    # Compute max raindrop width based on bar spacing
    bar_spacing = 1.0  # bar index units
    max_width = bar_spacing * 0.4  # raindrops occupy ~40% of bar slot

    # Precompute max density across all bars for normalization
    all_densities = []
    distributions = []
    for _, row in df.iterrows():
        prices, density = _estimate_bar_volume_distribution(row)
        distributions.append((prices, density))
        if density.size > 0:
            all_densities.append(density.max())
    max_density = max(all_densities) if all_densities else 1.0

    # Build raindrop patches
    patches_up, patches_down = [], []
    for i, ((prices, density), (idx, row)) in enumerate(zip(distributions, df.iterrows())):
        if density.max() == 0:
            continue
        # Normalize width
        width_arr = (density / max_density) * max_width
        # Build polygon: left side = x - width, right side = x + width
        x_left = i - width_arr
        x_right = i + width_arr
        # Polygon points: go up on right, down on left
        poly_points = np.column_stack([
            np.concatenate([x_right, x_left[::-1]]),
            np.concatenate([prices, prices[::-1]]),
        ])
        patch = Polygon(poly_points, closed=True)
        if row["close"] >= row["open"]:
            patches_up.append(patch)
        else:
            patches_down.append(patch)

    # Up bars = green, down bars = red
    up_coll = PatchCollection(patches_up, facecolor="#26a69a", alpha=0.7, edgecolor="#004d40", linewidth=0.3)
    down_coll = PatchCollection(patches_down, facecolor="#ef5350", alpha=0.7, edgecolor="#b71c1c", linewidth=0.3)
    ax_price.add_collection(up_coll)
    ax_price.add_collection(down_coll)

    # Overlay close price line for reference
    ax_price.plot(range(len(df)), df["close"].values, color="black", linewidth=0.8, alpha=0.6, label="Close")
    # MA20 if enough data
    if len(df) > 20:
        ma20 = df["close"].rolling(20).mean()
        ax_price.plot(range(len(df)), ma20.values, color="blue", linewidth=0.8, alpha=0.7, label="MA20")

    ax_price.set_title(f"{ticker} Raindrop-like Volume Profile{(' ' + title_suffix) if title_suffix else ''}",
                       fontsize=13)
    ax_price.set_ylabel("Price")
    ax_price.grid(alpha=0.2)
    ax_price.legend(loc="upper left", fontsize=9)

    # Set y-axis range with padding
    y_min, y_max = df["low"].min(), df["high"].max()
    y_pad = (y_max - y_min) * 0.05
    ax_price.set_ylim(y_min - y_pad, y_max + y_pad)
    ax_price.set_xlim(-1, len(df))

    # Volume subplot
    volume_colors = ["#26a69a" if c >= o else "#ef5350"
                     for c, o in zip(df["close"], df["open"])]
    ax_vol.bar(range(len(df)), df["volume"].values, color=volume_colors, alpha=0.7, width=0.7)
    ax_vol.set_ylabel("Volume")
    ax_vol.grid(alpha=0.2)

    # X-axis: date labels
    date_strs = [d.strftime("%m-%d") if hasattr(d, "strftime") else str(d) for d in df.index]
    n_ticks = min(10, len(df))
    tick_indices = np.linspace(0, len(df) - 1, n_ticks, dtype=int)
    ax_vol.set_xticks(tick_indices)
    ax_vol.set_xticklabels([date_strs[i] for i in tick_indices], rotation=0, fontsize=8)

    fig.savefig(str(output_path), dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return output_path
