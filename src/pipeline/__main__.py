"""CLI entry point for the integrated pipeline.

Usage:
    python -m src.pipeline --ticker NVDA --days 180
    python -m src.pipeline --ticker NVDA --days 180 --chart raindrop
    python -m src.pipeline --ticker NVDA --days 180 --backtest elliott_w3 --telegram
    python -m src.pipeline --ticker NVDA,AAPL,MSFT --days 180 --telegram

One-command end-to-end:
    1. trendline-detector → swings + trendlines + Elliott wave
    2. chart-analyzer → render chart with overlays
    3. Claude Vision → AI analysis
    4. backtest-lab → strategy backtest
    5. Telegram → deliver combined report
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .integrator import run_full_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="End-to-end pipeline: detect → chart → analyze → backtest",
    )
    parser.add_argument("--ticker", required=True,
                        help="Ticker(s). Comma-separated for multi: 'NVDA,AAPL,MSFT'")
    parser.add_argument("--days", type=int, default=180,
                        help="Lookback window for detection + chart (default 180)")
    parser.add_argument("--chart", default="standard",
                        choices=["standard", "raindrop", "multitf"],
                        help="Chart type (standard gets overlays; raindrop/multitf do not)")
    parser.add_argument("--no-overlays", action="store_true",
                        help="Disable trendline/swing overlays on standard chart")
    parser.add_argument("--analysis", default="elliott",
                        choices=["elliott", "trend", "support_resistance", "none"],
                        help="Claude Vision analysis type. 'none' to skip AI.")
    parser.add_argument("--backtest", default="elliott_w3",
                        choices=["ma_golden", "rsi_oversold", "elliott_w3",
                                 "bollinger_breakout", "macd_divergence", "none"],
                        help="Backtest strategy. 'none' to skip.")
    parser.add_argument("--backtest-years", type=int, default=5)
    parser.add_argument("--output-dir", default="output/pipeline",
                        help="Output directory")
    parser.add_argument("--telegram", action="store_true",
                        help="Send combined report via Telegram")
    args = parser.parse_args()

    tickers = [t.strip() for t in args.ticker.split(",") if t.strip()]
    output_dir = Path(args.output_dir)

    all_results = []
    for i, ticker in enumerate(tickers):
        print(f"\n{'='*70}")
        print(f"  [{i+1}/{len(tickers)}] {ticker}")
        print('='*70)

        try:
            result = run_full_pipeline(
                ticker,
                days=args.days,
                backtest_strategy=None if args.backtest == "none" else args.backtest,
                backtest_years=args.backtest_years,
                analysis_type=None if args.analysis == "none" else args.analysis,
                chart_type=args.chart,
                include_overlays=not args.no_overlays,
                send_telegram=args.telegram,
                output_dir=output_dir / ticker,
            )
            all_results.append(result)
        except Exception as e:
            print(f"\n❌ Pipeline failed for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            all_results.append({"ticker": ticker, "error": str(e)})

    # Final summary
    print(f"\n{'='*70}")
    print(f"  ✅ Pipeline complete: {len(all_results)} tickers processed")
    print('='*70)
    for r in all_results:
        if "error" in r:
            print(f"  ❌ {r['ticker']}: {r['error'][:80]}")
            continue
        bt = (r.get("backtest") or {}).get("pnl_pct")
        det = r.get("detection") or {}
        ew = (det.get("elliott_wave") or {})
        ew_str = f"{ew.get('pattern')}/{ew.get('current_wave')}" if ew.get('pattern') != "none" else "no pattern"
        bt_str = f"bt={bt:+.1f}%" if bt is not None else ""
        tg_str = "📱" if r.get("telegram_sent") else ""
        print(f"  ✅ {r['ticker']:8s} | {ew_str:20s} | {bt_str} {tg_str}")

    return 0 if all(("error" not in r) for r in all_results) else 1


if __name__ == "__main__":
    sys.exit(main())
