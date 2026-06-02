"""Gemini：截图 → 结构化价格 JSON。"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import google.generativeai as genai
from PIL import Image

from config import VisionConfig

FLOOR_PROMPT = """你是集换社小程序「一口价」页签的价格识别助手。
请从截图中提取可见价格，只输出 JSON，不要 Markdown 代码块，不要解释。

输出格式：
{"items": [
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "最低价"},
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "PSA10", "priceKind": "集换价"}
]}

规则：
- 找不到对应价格时 price 为 null
- 不要猜测；看不清就 null
- priceKind 只能是「最低价」或「集换价」
"""

AUCTION_PROMPT = """你是集换社小程序「竞价」页签的价格识别助手。
请从截图中提取可见价格，只输出 JSON，不要 Markdown 代码块，不要解释。

输出格式：
{"items": [
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "当前竞价"},
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "成交价"}
]}

规则：
- 找不到对应价格时 price 为 null
- 不要猜测；看不清就 null
- priceKind 只能是「当前竞价」或「成交价」
"""

_last_gemini_call_at: float = 0.0


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _configure(cfg: VisionConfig) -> None:
    if not cfg.gemini_api_key:
        raise RuntimeError("缺少 GEMINI_API_KEY，请在 .env 中配置。")
    genai.configure(api_key=cfg.gemini_api_key)


def _is_rate_limited(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "resourceexhausted" in type(exc).__name__.lower() or "quota" in msg


def _retry_delay_sec(exc: Exception, attempt: int) -> float:
    match = re.search(r"retry in ([0-9.]+)s", str(exc), re.I)
    if match:
        return float(match.group(1)) + 1.0
    return max(15.0, 13.0 * (attempt + 1))


def _wait_interval(cfg: VisionConfig) -> None:
    global _last_gemini_call_at
    if _last_gemini_call_at <= 0:
        return
    elapsed = time.time() - _last_gemini_call_at
    wait = cfg.gemini_min_interval_sec - elapsed
    if wait > 0:
        print(f"[gemini] 免费档限流间隔，等待 {wait:.0f}s …", flush=True)
        time.sleep(wait)


def _generate_with_retry(model: genai.GenerativeModel, content: list, cfg: VisionConfig):
    global _last_gemini_call_at
    last_exc: Exception | None = None
    for attempt in range(5):
        _wait_interval(cfg)
        try:
            response = model.generate_content(content, request_options={"timeout": 120})
            _last_gemini_call_at = time.time()
            return response
        except Exception as exc:
            if not _is_rate_limited(exc):
                raise
            last_exc = exc
            delay = _retry_delay_sec(exc, attempt)
            print(
                f"[gemini] 429 配额/频率超限，{delay:.0f}s 后重试 ({attempt + 1}/5) …",
                flush=True,
            )
            time.sleep(delay)
    raise RuntimeError(f"Gemini 429 重试次数已用尽: {last_exc}") from last_exc


def parse_screenshot(cfg: VisionConfig, image_path: Path, *, tab: str) -> list[dict]:
    if cfg.mock_gemini:
        if tab == "floor":
            return [
                {"price": 520.0, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "最低价"},
                {"price": None, "tradeType": "FLOOR", "cardCondition": "PSA10", "priceKind": "集换价"},
            ]
        return [
            {"price": 750.0, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "当前竞价"},
            {"price": None, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "成交价"},
        ]

    _configure(cfg)
    model = genai.GenerativeModel(cfg.gemini_model)
    prompt = FLOOR_PROMPT if tab == "floor" else AUCTION_PROMPT
    image = Image.open(image_path)

    tab_label = "一口价" if tab == "floor" else "竞价"
    print(
        f"[gemini] 请求中 ({tab_label}, {cfg.gemini_model}) … "
        f"免费档约 5 次/分钟，请耐心等待",
        flush=True,
    )

    response = _generate_with_retry(model, [prompt, image], cfg)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"Gemini 返回空内容: {image_path}")

    data = _extract_json(text)
    items = data.get("items")
    if not isinstance(items, list):
        raise RuntimeError(f"Gemini JSON 缺少 items 数组: {text[:200]}")
    return items
