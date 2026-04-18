"""Telegram bot integration — send chart images + analysis results."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _get_creds(
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> tuple[str, str]:
    """Resolve Telegram credentials from args or env vars."""
    bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set (env var or explicit arg)")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID not set (env var or explicit arg)")
    return bot_token, chat_id


def send_message(
    text: str,
    *,
    bot_token: str | None = None,
    chat_id: str | None = None,
    parse_mode: str = "Markdown",
    timeout: int = 15,
) -> dict:
    """Send a text message to Telegram."""
    bot_token, chat_id = _get_creds(bot_token, chat_id)
    url = TELEGRAM_API.format(token=bot_token, method="sendMessage")
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    r = requests.post(url, data=data, timeout=timeout)
    r.raise_for_status()
    return r.json()


def send_photo(
    image_path: str | Path,
    *,
    caption: str | None = None,
    bot_token: str | None = None,
    chat_id: str | None = None,
    parse_mode: str = "Markdown",
    timeout: int = 30,
) -> dict:
    """Send a photo with optional caption.

    Telegram caption limit: 1024 characters. Longer captions will be truncated.
    """
    bot_token, chat_id = _get_creds(bot_token, chat_id)
    url = TELEGRAM_API.format(token=bot_token, method="sendPhoto")

    if caption and len(caption) > 1024:
        caption = caption[:1020] + "..."

    with open(image_path, "rb") as f:
        files = {"photo": f}
        data: dict[str, Any] = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        r = requests.post(url, data=data, files=files, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _format_elliott_result(result: dict) -> str:
    """Format an Elliott-analysis result as a Telegram caption."""
    ticker = result.get("ticker", "?")
    wave = result.get("current_wave", "?")
    pattern = result.get("pattern_type", "?")
    conf = result.get("confidence", 0)
    entry = result.get("entry_decision", "?")
    reasoning = result.get("reasoning", "")
    risk = result.get("risk_warning", "")

    support = result.get("key_support")
    resistance = result.get("key_resistance")
    target = result.get("target_price")
    invalidation = result.get("invalidation_level")

    entry_emoji = {
        "enter_now": "🟢 지금 진입",
        "wait_for_pullback": "🟡 조정 대기",
        "wait_for_confirmation": "🟠 확인 대기",
        "no_entry": "🔴 진입 불가",
    }.get(entry, "❔")

    lines = [
        f"*{ticker}* — Elliott Wave Analysis",
        f"",
        f"🌊 *현재 파동*: {wave} ({pattern})",
        f"📊 *신뢰도*: {conf:.2f}",
        f"🎯 *진입 판단*: {entry_emoji}",
        f"",
    ]

    if support is not None:
        lines.append(f"🟢 Support: `{support}`")
    if resistance is not None:
        lines.append(f"🔴 Resistance: `{resistance}`")
    if target is not None:
        lines.append(f"🎯 Target: `{target}`")
    if invalidation is not None:
        lines.append(f"⚠️ Invalid below: `{invalidation}`")

    if reasoning:
        lines.append(f"\n💡 _{reasoning}_")
    if risk:
        lines.append(f"\n⚠️ {risk}")

    return "\n".join(lines)


def _format_trend_result(result: dict) -> str:
    ticker = result.get("ticker", "?")
    direction = result.get("trend_direction", "?")
    strength = result.get("trend_strength", "?")
    ma = result.get("ma_alignment", "?")
    vol = "✅" if result.get("volume_confirms") else "❌"
    action = result.get("action_recommendation", "?")

    dir_emoji = {"up": "📈", "down": "📉", "sideways": "➡️"}.get(direction, "❔")

    lines = [
        f"*{ticker}* — Trend Analysis",
        f"",
        f"{dir_emoji} *추세*: {direction} ({strength})",
        f"📏 *MA 정렬*: {ma}",
        f"📊 *거래량 확인*: {vol}",
        f"🎯 *액션*: `{action}`",
    ]

    sup = result.get("key_support")
    res = result.get("key_resistance")
    if sup is not None:
        lines.append(f"🟢 Support: `{sup}`")
    if res is not None:
        lines.append(f"🔴 Resistance: `{res}`")

    reasoning = result.get("reasoning", "")
    risk = result.get("risk_warning", "")
    if reasoning:
        lines.append(f"\n💡 _{reasoning}_")
    if risk:
        lines.append(f"\n⚠️ {risk}")

    return "\n".join(lines)


def send_chart_analysis(
    chart_path: str | Path,
    analysis_result: dict,
    *,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> dict:
    """Send chart image + formatted analysis to Telegram.

    Auto-detects analysis_type and formats the caption accordingly.
    """
    atype = analysis_result.get("analysis_type", "elliott")
    if atype == "elliott":
        caption = _format_elliott_result(analysis_result)
    elif atype == "trend":
        caption = _format_trend_result(analysis_result)
    else:
        # Generic fallback: just send raw reasoning
        ticker = analysis_result.get("ticker", "?")
        reasoning = analysis_result.get("reasoning", "") or \
                    analysis_result.get("raw_response", "")[:900]
        caption = f"*{ticker}* — {atype} analysis\n\n{reasoning}"

    return send_photo(
        chart_path,
        caption=caption,
        bot_token=bot_token,
        chat_id=chat_id,
    )
