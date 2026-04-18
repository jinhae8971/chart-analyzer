"""End-to-end pipeline integrating trendline-detector + chart-analyzer + backtest-lab.

Usage:
    python -m src.pipeline --ticker NVDA --days 180
    python -m src.pipeline --ticker NVDA --days 180 --backtest --telegram
"""
from .integrator import (
    SIBLING_REPOS,
    find_sibling_repo,
    run_detection,
    run_backtest,
    run_full_pipeline,
)

__all__ = [
    "SIBLING_REPOS",
    "find_sibling_repo",
    "run_detection",
    "run_backtest",
    "run_full_pipeline",
]
