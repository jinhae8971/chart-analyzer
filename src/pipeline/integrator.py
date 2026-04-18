"""Integration layer for trendline-detector + backtest-lab.

Discovery strategy:
    1. Look in sibling directories (same parent as chart-analyzer)
    2. Look in user-specified paths (env var CHART_ANALYZER_SIBLING_PATH)
    3. Fall back to git clone into local cache (~/.cache/chart-analyzer/siblings)

Once found, sibling repos are added to sys.path and imported dynamically.
This keeps each repo independently deployable while allowing integration.
"""
from __future__ import annotations

import os
import subprocess
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any


# Sibling repo configuration
SIBLING_REPOS = {
    "trendline-detector": {
        "github": "https://github.com/jinhae8971/trendline-detector.git",
        "src_subdir": "",  # root contains src/
    },
    "backtest-lab": {
        "github": "https://github.com/jinhae8971/backtest-lab.git",
        "src_subdir": "",
    },
}

# Cache dir for auto-cloned repos
_CACHE_DIR = Path.home() / ".cache" / "chart-analyzer" / "siblings"


def find_sibling_repo(repo_name: str, auto_clone: bool = True) -> Path:
    """Find a sibling repo directory. Try multiple strategies.

    Search order:
        1. Environment variable CHART_ANALYZER_SIBLING_PATH (colon-separated)
        2. Parent directory of chart-analyzer (sibling folders)
        3. Common user paths (~/github-projects, ~/Documents/GitHub, ~/projects)
        4. Auto-clone into ~/.cache/chart-analyzer/siblings/ (if auto_clone=True)

    Args:
        repo_name: e.g., 'trendline-detector'
        auto_clone: Whether to git-clone if not found locally

    Returns:
        Path to the repo's root directory.

    Raises:
        FileNotFoundError: If not found and auto_clone=False
    """
    if repo_name not in SIBLING_REPOS:
        raise ValueError(
            f"Unknown sibling '{repo_name}'. Available: {list(SIBLING_REPOS.keys())}"
        )

    def _is_valid_repo(path: Path) -> bool:
        """A valid sibling has src/__init__.py."""
        return (path / "src" / "__init__.py").exists()

    # Strategy 1: explicit env var (STRICT mode — if set, only look here)
    env_paths = os.environ.get("CHART_ANALYZER_SIBLING_PATH", "")
    if env_paths:
        for base in env_paths.split(":"):
            if not base:
                continue
            candidate = Path(base).expanduser() / repo_name
            if _is_valid_repo(candidate):
                return candidate.resolve()
        # Env var was set but repo not found — skip further fallbacks
        # (user explicitly told us where to look; don't surprise them)
        if not auto_clone:
            raise FileNotFoundError(
                f"Could not find '{repo_name}' under CHART_ANALYZER_SIBLING_PATH={env_paths}"
            )

    # Strategy 2: sibling of chart-analyzer (most common layout)
    this_file = Path(__file__).resolve()
    # .../chart-analyzer/src/pipeline/integrator.py → .../chart-analyzer
    chart_analyzer_root = this_file.parent.parent.parent
    candidate = chart_analyzer_root.parent / repo_name
    if _is_valid_repo(candidate):
        return candidate.resolve()

    # Strategy 3: common user paths
    common_roots = [
        Path.home() / "github-projects",
        Path.home() / "Documents" / "GitHub",
        Path.home() / "projects",
        Path.home() / "workspace",
        Path.home() / "repos",
        Path.home() / "src",
        Path("/workspace"),
    ]
    for root in common_roots:
        candidate = root / repo_name
        if _is_valid_repo(candidate):
            return candidate.resolve()

    # Strategy 4: auto-clone
    if auto_clone:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        target = _CACHE_DIR / repo_name
        if _is_valid_repo(target):
            return target.resolve()

        github_url = SIBLING_REPOS[repo_name]["github"]
        print(f"  ↓ Cloning {repo_name} into {target}...")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", github_url, str(target)],
                check=True,
                capture_output=True,
                text=True,
            )
            if _is_valid_repo(target):
                return target.resolve()
        except subprocess.CalledProcessError as e:
            raise FileNotFoundError(
                f"Failed to clone {repo_name}: {e.stderr}"
            )

    raise FileNotFoundError(
        f"Could not find '{repo_name}'. Tried:\n"
        f"  - Env var CHART_ANALYZER_SIBLING_PATH\n"
        f"  - Sibling of chart-analyzer\n"
        f"  - Common paths (~/github-projects, ~/projects, etc)\n"
        f"  - Auto-clone to {_CACHE_DIR}\n"
        f"Hint: Set CHART_ANALYZER_SIBLING_PATH=/path/to/parent-dir, or clone manually."
    )


def _import_from_sibling(repo_name: str, module_path: str) -> Any:
    """Dynamically import a module from a sibling repo.

    Uses a unique sys.modules namespace to avoid src/ collisions between repos.
    """
    repo_path = find_sibling_repo(repo_name)
    # Insert at front so our src doesn't shadow sibling's src
    repo_path_str = str(repo_path)
    if repo_path_str not in sys.path:
        sys.path.insert(0, repo_path_str)

    # We need to import sibling's 'src' under a unique alias to avoid
    # collision with chart-analyzer's own src module.
    alias = f"_sibling_{repo_name.replace('-', '_')}"

    if alias not in sys.modules:
        import importlib.util
        src_init = repo_path / "src" / "__init__.py"
        spec = importlib.util.spec_from_file_location(
            alias, src_init, submodule_search_locations=[str(repo_path / "src")],
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[alias] = mod
        spec.loader.exec_module(mod)

    # Now import the submodule: e.g., alias + '.swings.detector'
    full = alias + "." + module_path
    if full not in sys.modules:
        import importlib
        importlib.import_module(full)
    return sys.modules[full]


# ──────────────────────────────────────────────────────────────────────────
# High-level API
# ──────────────────────────────────────────────────────────────────────────

def run_detection(
    ticker: str,
    *,
    days: int = 180,
    atr_multiplier: float = 1.5,
    min_touches: int = 3,
) -> dict:
    """Run trendline-detector on a ticker. Returns detection JSON dict.

    This is a thin wrapper that dynamically imports trendline-detector.
    """
    # Import sibling modules
    swings_mod = _import_from_sibling("trendline-detector", "swings.detector")
    trendlines_mod = _import_from_sibling("trendline-detector", "trendlines.fitter")
    elliott_mod = _import_from_sibling("trendline-detector", "elliott.labeler")
    export_mod = _import_from_sibling("trendline-detector", "export.builder")

    # Fetch data using chart-analyzer's loader (we're the main program)
    from ..chart.data_loader import load_ohlcv
    df = load_ohlcv(ticker, timeframe="daily")
    df = df.tail(days)

    # Run detection
    swings = swings_mod.detect_swings_with_atr_filter(
        df, distance=5, atr_multiplier=atr_multiplier,
    )
    trendlines = trendlines_mod.fit_trendlines(
        df, swings, min_touches=min_touches, top_k=10,
    )
    elliott = elliott_mod.label_elliott_wave(swings)

    result = export_mod.build_detection_result(
        ticker=ticker,
        timeframe="daily",
        swings=swings,
        trendlines=trendlines,
        elliott=elliott,
        data_start_date=swings[0].date if swings else None,
        data_end_date=swings[-1].date if swings else None,
    )
    return result


def run_backtest(
    ticker: str,
    *,
    strategy: str = "elliott_w3",
    years: int = 5,
    initial_cash: float = 100_000,
    output_dir: str | Path = "output/backtest",
) -> dict:
    """Run a backtest-lab strategy on the ticker. Returns summary JSON dict."""
    run_mod = _import_from_sibling("backtest-lab", "run")

    # We replicate the core of run_single_backtest here with minimal wrapping
    # to avoid subprocess overhead.
    summary = run_mod.run_single_backtest(
        strategy_name=strategy,
        ticker=ticker,
        start=None,
        end=None,
        initial_cash=initial_cash,
        commission=0.001,
        log_trades=False,
    )

    # Also save HTML
    reports_mod = _import_from_sibling("backtest-lab", "reports.builder")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"{ticker}_{strategy}.html"
    reports_mod.build_html_report(summary, html_path)
    summary["_html_path"] = str(html_path)

    return summary


def run_full_pipeline(
    ticker: str,
    *,
    days: int = 180,
    backtest_strategy: str | None = "elliott_w3",
    backtest_years: int = 5,
    analysis_type: str = "elliott",
    chart_type: str = "standard",
    include_overlays: bool = True,
    send_telegram: bool = False,
    output_dir: str | Path = "output",
) -> dict:
    """End-to-end pipeline: detect → chart → analyze → backtest.

    Returns:
        Combined result dict with keys:
            - detection: trendline-detector JSON
            - chart_path: path to rendered chart PNG
            - analysis: Claude Vision result (if requested)
            - backtest: backtest-lab summary (if requested)
            - telegram_sent: bool
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    combined: dict = {
        "ticker": ticker,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "schema_version": "0.2.0-integrated",
    }

    # ─── 1. Detection ───────────────────────────────────────────
    print(f"🔍 Running trendline + Elliott detection on {ticker}...")
    try:
        detection = run_detection(ticker, days=days)
        combined["detection"] = detection
        # Save detection JSON
        det_path = output_dir / f"{ticker}_detection.json"
        with open(det_path, "w", encoding="utf-8") as f:
            json.dump(detection, f, ensure_ascii=False, indent=2, default=str)
        print(f"  → {len(detection.get('swings', []))} swings, "
              f"{len(detection.get('trendlines', []))} trendlines")
        if detection.get("elliott_wave", {}).get("pattern") != "none":
            ew = detection["elliott_wave"]
            print(f"  → Elliott: {ew['pattern']} ({ew['direction']}) "
                  f"wave={ew['current_wave']} conf={ew['confidence']}")
    except Exception as e:
        print(f"  ⚠️ Detection failed: {e}")
        combined["detection"] = None

    # ─── 2. Render chart with overlays ───────────────────────────
    print(f"📊 Rendering {chart_type} chart...")
    from ..chart.data_loader import load_ohlcv
    from ..chart.standard import render_standard_chart, render_with_overlays
    from ..chart.raindrop import render_raindrop_chart
    from ..chart.multitf import render_multi_timeframe

    try:
        if chart_type == "multitf":
            chart_path = render_multi_timeframe(
                ticker,
                output_path=output_dir / f"{ticker}_multitf.png",
            )
        else:
            df = load_ohlcv(ticker, timeframe="daily").tail(days)

            if chart_type == "raindrop":
                chart_path = render_raindrop_chart(
                    df, ticker,
                    lookback_days=days,
                    output_path=output_dir / f"{ticker}_raindrop.png",
                    title_suffix=f"(daily, {days}d)",
                )
            elif include_overlays and combined.get("detection"):
                # Use render_with_overlays using detection results
                det = combined["detection"]
                support_lines = [t for t in det.get("trendlines", []) if t["type"] == "support"][:5]
                resistance_lines = [t for t in det.get("trendlines", []) if t["type"] == "resistance"][:5]
                # Rebuild swing indices as relative to the tail(days) slice
                # The detection ran on the same tail(days) slice, so indices match.
                swings = det.get("swings", [])
                chart_path = render_with_overlays(
                    df, ticker,
                    support_lines=support_lines,
                    resistance_lines=resistance_lines,
                    swing_points=swings,
                    output_path=output_dir / f"{ticker}_overlay.png",
                    title_suffix=f"(daily, {days}d, {len(support_lines)+len(resistance_lines)} lines)",
                )
            else:
                chart_path = render_standard_chart(
                    df, ticker,
                    output_path=output_dir / f"{ticker}_standard.png",
                    title_suffix=f"(daily, {days}d)",
                )
        combined["chart_path"] = str(chart_path)
        print(f"  → {chart_path}")
    except Exception as e:
        print(f"  ⚠️ Chart rendering failed: {e}")
        combined["chart_path"] = None

    # ─── 3. Claude Vision analysis ────────────────────────────────
    if combined.get("chart_path") and analysis_type:
        print(f"🤖 Analyzing with Claude Vision ({analysis_type})...")
        try:
            from ..analyzer.vision import analyze_chart_image
            analysis = analyze_chart_image(
                combined["chart_path"],
                analysis_type=analysis_type,
            )
            combined["analysis"] = analysis
            wave = analysis.get("current_wave", "?")
            conf = analysis.get("confidence", 0)
            action = analysis.get("entry_decision") or analysis.get("action_recommendation", "?")
            print(f"  → wave={wave}, confidence={conf:.2f}, action={action}")
        except Exception as e:
            print(f"  ⚠️ Analysis failed: {e}")
            combined["analysis"] = {"error": str(e)}

    # ─── 4. Backtest ──────────────────────────────────────────────
    if backtest_strategy:
        print(f"🧪 Running backtest ({backtest_strategy}, {backtest_years}y)...")
        try:
            bt_result = run_backtest(
                ticker,
                strategy=backtest_strategy,
                years=backtest_years,
                output_dir=output_dir / "backtest",
            )
            combined["backtest"] = {
                "strategy": bt_result["strategy"],
                "period": bt_result["period"],
                "pnl_pct": bt_result["pnl_pct"],
                "final_value": bt_result["final_value"],
                "metrics": bt_result["metrics"],
                "html_path": bt_result.get("_html_path"),
                "trade_count": bt_result.get("trade_count", 0),
            }
            print(f"  → PnL: {bt_result['pnl_pct']:+.2f}%, "
                  f"Sharpe: {bt_result['metrics'].get('sharpe_ratio')}, "
                  f"Win rate: {bt_result['metrics'].get('win_rate_pct') or 0:.1f}%")
        except Exception as e:
            print(f"  ⚠️ Backtest failed: {e}")
            combined["backtest"] = {"error": str(e)}

    # ─── 5. Save combined result ─────────────────────────────────
    combined_path = output_dir / f"{ticker}_pipeline.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 Combined result: {combined_path}")

    # ─── 6. Telegram ─────────────────────────────────────────────
    combined["telegram_sent"] = False
    if send_telegram and combined.get("chart_path"):
        print("📱 Sending to Telegram...")
        try:
            from ..notifier.telegram import send_photo
            caption = _format_pipeline_caption(combined)
            send_photo(combined["chart_path"], caption=caption)
            combined["telegram_sent"] = True
            print("  ✅ Sent")
        except Exception as e:
            print(f"  ⚠️ Telegram failed: {e}")

    return combined


def _format_pipeline_caption(combined: dict) -> str:
    """Format a rich Telegram caption integrating all three results."""
    ticker = combined.get("ticker", "?")
    lines = [f"*{ticker}* — Full Pipeline Report", ""]

    # Detection summary
    det = combined.get("detection") or {}
    summary = det.get("summary", {})
    swings = summary.get("swing_count", 0)
    tls = summary.get("trendline_count", 0)
    if swings or tls:
        lines.append(f"🔍 *검출*: swings={swings}, trendlines={tls}")

    ew = det.get("elliott_wave") or {}
    if ew.get("pattern") and ew.get("pattern") != "none":
        lines.append(
            f"🌊 *Elliott*: {ew.get('pattern')} ({ew.get('direction')}) "
            f"wave={ew.get('current_wave')} conf={ew.get('confidence')}"
        )

    # Claude analysis
    an = combined.get("analysis") or {}
    if an and not an.get("error"):
        wave = an.get("current_wave")
        conf = an.get("confidence", 0)
        decision = an.get("entry_decision") or an.get("action_recommendation", "?")
        if wave or decision:
            lines.append(f"🤖 *AI 판단*: wave={wave}, conf={conf:.2f}, action=`{decision}`")
        reasoning = an.get("reasoning", "")
        if reasoning:
            lines.append(f"\n💡 _{reasoning[:300]}_")

    # Backtest
    bt = combined.get("backtest") or {}
    if bt and not bt.get("error"):
        period = bt.get("period", {})
        pnl = bt.get("pnl_pct", 0)
        m = bt.get("metrics", {})
        lines.append("")
        lines.append(
            f"🧪 *Backtest* ({bt.get('strategy')}, "
            f"{period.get('start', '?')[:10]}~{period.get('end', '?')[:10]})"
        )
        lines.append(f"   PnL: *{pnl:+.2f}%* | Sharpe: {m.get('sharpe_ratio')} | "
                     f"MDD: -{m.get('max_drawdown_pct') or 0:.1f}% | "
                     f"Win: {m.get('win_rate_pct') or 0:.0f}%")

    risk = an.get("risk_warning") if an else None
    if risk:
        lines.append(f"\n⚠️ {risk}")

    # Telegram caption limit: 1024 chars
    caption = "\n".join(lines)
    if len(caption) > 1000:
        caption = caption[:997] + "..."
    return caption
