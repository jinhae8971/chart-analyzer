"""CLI entry point for chart-analyzer.

Usage:
    # Basic: render + analyze with Claude Vision
    python -m src.analyze --ticker NVDA --type elliott

    # With Telegram notification
    python -m src.analyze --ticker NVDA --type elliott --telegram

    # Raindrop chart
    python -m src.analyze --ticker NVDA --chart raindrop

    # Multi-timeframe confluence view
    python -m src.analyze --ticker NVDA --chart multitf --type trend

    # Custom question
    python -m src.analyze --ticker SPY --type custom \\
        --question "현재 RSI 과매수 상태로 보이는가? 약세 다이버전스 있는가?"

    # Just render chart (no AI analysis)
    python -m src.analyze --ticker NVDA --chart raindrop --no-ai
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render chart → analyze with Claude Vision → send to Telegram",
    )
    parser.add_argument("--ticker", required=True, help="e.g., NVDA, SPY, BTC-USD, 005930.KS")
    parser.add_argument("--timeframe", default="daily",
                        choices=["15m", "1h", "4h", "daily", "weekly"])
    parser.add_argument("--days", type=int, default=180, help="Lookback days")
    parser.add_argument("--chart", default="standard",
                        choices=["standard", "raindrop", "multitf"])
    parser.add_argument("--type", default="elliott", dest="analysis_type",
                        choices=["elliott", "trend", "support_resistance", "custom"])
    parser.add_argument("--question", default=None, help="Custom question (works with any --type)")
    parser.add_argument("--custom-prompt", default=None,
                        help="Full system prompt override (only for --type custom)")
    parser.add_argument("--model", default="claude-opus-4-5",
                        help="Claude model ID (tries opus-4-7 first then falls back)")
    parser.add_argument("--telegram", action="store_true", help="Send result via Telegram")
    parser.add_argument("--no-ai", action="store_true",
                        help="Skip AI analysis, just render chart")
    parser.add_argument("--output-json", default=None,
                        help="Save full result as JSON (default: output/{ticker}_{type}.json)")
    args = parser.parse_args()

    # Lazy imports to avoid forcing all deps
    from .chart.data_loader import load_ohlcv
    from .chart.standard import render_standard_chart
    from .chart.raindrop import render_raindrop_chart
    from .chart.multitf import render_multi_timeframe

    print(f"📊 Rendering {args.chart} chart for {args.ticker}...")

    try:
        if args.chart == "multitf":
            chart_path = render_multi_timeframe(args.ticker)
        else:
            df = load_ohlcv(args.ticker, timeframe=args.timeframe)
            df = df.tail(args.days)
            if args.chart == "raindrop":
                chart_path = render_raindrop_chart(
                    df, args.ticker, lookback_days=args.days,
                    title_suffix=f"({args.timeframe}, {args.days}d)",
                )
            else:
                chart_path = render_standard_chart(
                    df, args.ticker,
                    title_suffix=f"({args.timeframe}, {args.days}d)",
                )
        print(f"  → saved: {chart_path}")
    except Exception as e:
        print(f"❌ Chart rendering failed: {e}")
        return 1

    if args.no_ai:
        print("✅ Chart rendered. AI analysis skipped (--no-ai).")
        return 0

    # AI analysis
    from .analyzer.vision import analyze_chart_image
    print(f"🤖 Analyzing with Claude ({args.model}, type={args.analysis_type})...")
    try:
        result = analyze_chart_image(
            chart_path,
            analysis_type=args.analysis_type,
            custom_question=args.question,
            custom_prompt=args.custom_prompt,
            model=args.model,
        )
        result["ticker"] = args.ticker
        result["timeframe"] = args.timeframe
        result["chart_path"] = str(chart_path)
    except Exception as e:
        print(f"❌ AI analysis failed: {e}")
        return 2

    # Print summary to stdout
    print("\n📋 Analysis Result:")
    print("─" * 60)
    for k, v in result.items():
        if k in ("raw_response", "_usage"):
            continue
        if isinstance(v, str) and len(v) > 100:
            print(f"  {k}: {v[:100]}...")
        else:
            print(f"  {k}: {v}")
    usage = result.get("_usage", {})
    if usage:
        print(f"\n  (tokens: in={usage.get('input_tokens')} out={usage.get('output_tokens')})")
    print("─" * 60)

    # Save JSON
    json_path = args.output_json or f"output/{args.ticker}_{args.analysis_type}.json"
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 JSON saved: {json_path}")

    # Telegram
    if args.telegram:
        try:
            from .notifier.telegram import send_chart_analysis
            print("\n📱 Sending to Telegram...")
            resp = send_chart_analysis(chart_path, result)
            if resp.get("ok"):
                print("  ✅ Sent")
            else:
                print(f"  ⚠️ Response: {resp}")
        except Exception as e:
            print(f"  ❌ Telegram failed: {e}")
            return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
