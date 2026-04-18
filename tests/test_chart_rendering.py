"""Tests for chart rendering (no external API required)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _make_ohlcv(n: int = 60, seed: int = 42) -> pd.DataFrame:
    """Generate deterministic OHLCV data for rendering tests."""
    np.random.seed(seed)
    base = 100 + np.cumsum(np.random.randn(n) * 0.8)
    noise = np.random.randn(n) * 0.5
    df = pd.DataFrame({
        "open": base + noise,
        "high": base + np.abs(noise) + 0.3,
        "low": base - np.abs(noise) - 0.3,
        "close": base,
        "volume": np.random.randint(1000000, 5000000, n),
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))
    # Ensure high >= max(open, close) and low <= min(open, close)
    df["high"] = df[["open", "high", "close"]].max(axis=1) + 0.1
    df["low"] = df[["open", "low", "close"]].min(axis=1) - 0.1
    return df


class TestStandardChart:
    def test_renders_to_png(self, tmp_path):
        from src.chart.standard import render_standard_chart
        df = _make_ohlcv(60)
        out = tmp_path / "test.png"
        result = render_standard_chart(df, "TEST", output_path=out)
        assert result.exists()
        assert result.stat().st_size > 5000  # non-trivial PNG

    def test_handles_short_data(self, tmp_path):
        from src.chart.standard import render_standard_chart
        df = _make_ohlcv(30)
        out = tmp_path / "short.png"
        # MA120 should be auto-filtered since n < 120
        result = render_standard_chart(df, "SHORT", output_path=out, ma_periods=(5, 20, 60, 120))
        assert result.exists()

    def test_with_overlays(self, tmp_path):
        from src.chart.standard import render_with_overlays
        df = _make_ohlcv(60)
        out = tmp_path / "overlay.png"
        support = [{"slope": 0.1, "intercept": 98, "start_index": 0, "end_index": 59}]
        resistance = [{"slope": 0.05, "intercept": 105, "start_index": 0, "end_index": 59}]
        swings = [
            {"index": 10, "price": 99.0, "type": "low"},
            {"index": 30, "price": 105.0, "type": "high"},
        ]
        result = render_with_overlays(
            df, "TEST", output_path=out,
            support_lines=support, resistance_lines=resistance,
            swing_points=swings,
        )
        assert result.exists()


class TestRaindropChart:
    def test_renders_raindrop(self, tmp_path):
        from src.chart.raindrop import render_raindrop_chart
        df = _make_ohlcv(60)
        out = tmp_path / "raindrop.png"
        result = render_raindrop_chart(df, "TEST", output_path=out, lookback_days=60)
        assert result.exists()
        assert result.stat().st_size > 10000  # raindrop PNGs are larger

    def test_raindrop_requires_volume(self, tmp_path):
        from src.chart.raindrop import render_raindrop_chart
        df = _make_ohlcv(60).drop(columns=["volume"])
        out = tmp_path / "norainfail.png"
        with pytest.raises(ValueError, match="Missing required columns"):
            render_raindrop_chart(df, "TEST", output_path=out)


class TestDataLoader:
    def test_timeframe_map_has_all_intervals(self):
        from src.chart.data_loader import _YF_INTERVAL_MAP, _YF_PERIOD_MAP
        for tf in ["15m", "1h", "4h", "daily", "weekly"]:
            assert tf in _YF_INTERVAL_MAP
            assert tf in _YF_PERIOD_MAP

    def test_normalize_columns_lowercases(self):
        from src.chart.data_loader import _normalize_columns
        df = pd.DataFrame({
            "Open": [1, 2],
            "High": [2, 3],
            "Low": [0.5, 1],
            "Close": [1.5, 2.5],
        })
        out = _normalize_columns(df)
        assert list(out.columns) == ["open", "high", "low", "close"]

    def test_normalize_flattens_multiindex(self):
        from src.chart.data_loader import _normalize_columns
        cols = pd.MultiIndex.from_tuples([("Open", "AAPL"), ("Close", "AAPL")])
        df = pd.DataFrame([[1, 2], [3, 4]], columns=cols)
        out = _normalize_columns(df)
        assert "open" in out.columns
        assert "close" in out.columns


class TestAnalyzerUtils:
    def test_extract_json_clean(self):
        from src.analyzer.vision import _extract_json
        text = '{"key": "value", "num": 42}'
        result = _extract_json(text)
        assert result == {"key": "value", "num": 42}

    def test_extract_json_with_fences(self):
        from src.analyzer.vision import _extract_json
        text = '```json\n{"a": 1}\n```'
        result = _extract_json(text)
        assert result == {"a": 1}

    def test_extract_json_with_preamble(self):
        from src.analyzer.vision import _extract_json
        text = 'Here is my analysis:\n\n{"wave": "3", "confidence": 0.8}\n\nEnd.'
        result = _extract_json(text)
        assert result == {"wave": "3", "confidence": 0.8}

    def test_extract_json_raises_on_garbage(self):
        from src.analyzer.vision import _extract_json
        with pytest.raises(ValueError):
            _extract_json("no json here at all")

    def test_load_prompt_elliott(self):
        from src.analyzer.vision import _load_prompt
        text = _load_prompt("elliott")
        assert "엘리엇 파동" in text
        assert "JSON" in text
