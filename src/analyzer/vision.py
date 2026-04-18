"""Claude Vision-powered chart analysis.

Sends chart PNG images to Claude and parses structured JSON responses.
Replaces TrendSpider's Sidekick AI with the same underlying model (Claude).
"""
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Literal

AnalysisType = Literal["elliott", "trend", "support_resistance", "custom"]

DEFAULT_MODEL = "claude-opus-4-5"  # fallback — will try claude-opus-4-7 first
PROMPT_DIR = Path(__file__).parent / "prompts"


def _load_prompt(analysis_type: AnalysisType, custom_prompt: str | None = None) -> str:
    """Load system prompt for the requested analysis type."""
    if analysis_type == "custom" and custom_prompt:
        return custom_prompt
    prompt_path = PROMPT_DIR / f"{analysis_type}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"No prompt found for type '{analysis_type}' at {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def _encode_image(image_path: str | Path) -> tuple[str, str]:
    """Encode image to base64 and detect media type."""
    image_path = Path(image_path)
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    ext = image_path.suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")
    return data, media_type


def _extract_json(text: str) -> dict:
    """Tolerantly extract first JSON object from model response."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()
    # Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    # Find first { and try from there
    start = text.find("{")
    if start < 0:
        raise ValueError(f"No JSON object in response: {text[:200]!r}")
    for end in range(len(text), start, -1):
        if text[end - 1] != "}":
            continue
        try:
            result = json.loads(text[start:end])
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No valid JSON object in response: {text[:200]!r}")


def analyze_chart_image(
    image_path: str | Path,
    *,
    analysis_type: AnalysisType = "elliott",
    custom_question: str | None = None,
    custom_prompt: str | None = None,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    max_tokens: int = 2048,
) -> dict:
    """Analyze a chart image using Claude Vision.

    Args:
        image_path: Path to chart PNG/JPG
        analysis_type: 'elliott' | 'trend' | 'support_resistance' | 'custom'
        custom_question: Override default question (works with any type)
        custom_prompt: Full system prompt override (only for analysis_type='custom')
        model: Claude model ID
        api_key: ANTHROPIC_API_KEY (falls back to env var)
        max_tokens: Response token limit

    Returns:
        Parsed JSON dict from Claude's response. Always includes:
            - raw_response: full text response
            - any fields specified in the prompt's JSON schema

    Raises:
        RuntimeError: If anthropic SDK not installed or API key missing
        ValueError: If response cannot be parsed as JSON
    """
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic SDK not installed. Run: pip install anthropic"
        ) from e

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set (env var or explicit arg)")

    system = _load_prompt(analysis_type, custom_prompt)
    image_data, media_type = _encode_image(image_path)

    user_content = []
    user_content.append({
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": image_data,
        },
    })
    if custom_question:
        user_content.append({"type": "text", "text": custom_question})
    else:
        user_content.append({
            "type": "text",
            "text": "위 차트를 분석하여 지정된 JSON 스키마로 응답해주세요.",
        })

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )

    raw_text = "".join(
        block.text for block in response.content
        if getattr(block, "type", None) == "text"
    )

    try:
        parsed = _extract_json(raw_text)
    except ValueError:
        # Return raw text wrapped if JSON parse fails
        return {
            "raw_response": raw_text,
            "parse_error": "Could not extract JSON",
            "analysis_type": analysis_type,
        }

    parsed["raw_response"] = raw_text
    parsed["analysis_type"] = analysis_type
    parsed["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return parsed


def analyze_chart(
    ticker: str,
    *,
    timeframe: str = "daily",
    analysis_type: AnalysisType = "elliott",
    custom_question: str | None = None,
    lookback_days: int = 180,
    chart_type: str = "standard",  # 'standard' | 'raindrop' | 'multitf'
    model: str = DEFAULT_MODEL,
    keep_chart: bool = True,
) -> dict:
    """End-to-end: fetch data → render chart → analyze with Claude.

    Convenience wrapper around chart rendering + analyze_chart_image.
    """
    from ..chart.data_loader import load_ohlcv
    from ..chart.standard import render_standard_chart
    from ..chart.raindrop import render_raindrop_chart
    from ..chart.multitf import render_multi_timeframe

    if chart_type == "multitf":
        # Multi-timeframe renderer loads its own data
        chart_path = render_multi_timeframe(ticker)
    else:
        df = load_ohlcv(ticker, timeframe=timeframe)
        df = df.tail(lookback_days)
        if chart_type == "raindrop":
            chart_path = render_raindrop_chart(df, ticker, lookback_days=lookback_days)
        else:
            chart_path = render_standard_chart(
                df, ticker,
                title_suffix=f"({timeframe}, {lookback_days}d)",
            )

    result = analyze_chart_image(
        chart_path,
        analysis_type=analysis_type,
        custom_question=custom_question,
        model=model,
    )
    result["ticker"] = ticker
    result["timeframe"] = timeframe
    result["chart_path"] = str(chart_path)

    if not keep_chart:
        try:
            Path(chart_path).unlink()
        except OSError:
            pass

    return result
