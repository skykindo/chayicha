"""Gemini：截图 → 结构化价格 JSON。"""

from __future__ import annotations

import re
import time
from pathlib import Path

import google.generativeai as genai
from PIL import Image

from config import VisionConfig
from vision_prompts import (
    AUCTION_PROMPT,
    AUCTION_SCROLL_PROMPT,
    CARD_LABEL_PROMPT,
    DETAIL_ENTRY_PROMPT,
    FLOOR_PROMPT,
    PRODUCT_PROMPT,
    WISHLIST_SCAN_PROMPT,
    coerce_item_dicts,
    extract_json,
    parse_items_response,
)

_last_gemini_call_at: float = 0.0


def _configure(cfg: VisionConfig) -> None:
    if not cfg.gemini_api_key:
        raise RuntimeError("缺少 GEMINI_API_KEY，请在 .env 中配置。")
    genai.configure(api_key=cfg.gemini_api_key)


def _is_rate_limited(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "resourceexhausted" in type(exc).__name__.lower() or "quota" in msg


def _is_daily_quota_exhausted(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "free_tier" in msg or "free tier" in msg


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
    wait = cfg.vision_min_interval_sec - elapsed
    if wait > 0:
        print(f"[gemini] 请求间隔，等待 {wait:.0f}s …", flush=True)
        time.sleep(wait)


def _generate_with_retry(model: genai.GenerativeModel, content: list, cfg: VisionConfig):
    global _last_gemini_call_at
    last_exc: Exception | None = None
    max_retries = max(1, cfg.vision_max_retries)
    for attempt in range(max_retries):
        _wait_interval(cfg)
        try:
            response = model.generate_content(content, request_options={"timeout": 120})
            _last_gemini_call_at = time.time()
            return response
        except Exception as exc:
            if not _is_rate_limited(exc):
                raise
            last_exc = exc
            if _is_daily_quota_exhausted(exc):
                raise RuntimeError(
                    "Gemini 免费档今日请求次数已用尽（约 20 次/天）。"
                    "请明天再跑 npm run vision，或开通 Gemini 付费 API。"
                    f"原始错误: {exc}"
                ) from exc
            delay = _retry_delay_sec(exc, attempt)
            print(
                f"[gemini] 429 配额/频率超限，{delay:.0f}s 后重试 ({attempt + 1}/{max_retries}) …",
                flush=True,
            )
            time.sleep(delay)
    raise RuntimeError(f"Gemini 429 重试次数已用尽: {last_exc}") from last_exc


def parse_screenshot(cfg: VisionConfig, image_path: Path, *, tab: str) -> list[dict]:
    _configure(cfg)
    model = genai.GenerativeModel(cfg.gemini_model)
    if tab == "floor":
        prompt = FLOOR_PROMPT
        tab_label = "一口价"
    elif tab == "auction":
        prompt = AUCTION_PROMPT
        tab_label = "竞价"
    else:
        prompt = PRODUCT_PROMPT
        tab_label = "商品"
    image = Image.open(image_path)
    print(f"[gemini] 请求中 ({tab_label}, {cfg.gemini_model}) …", flush=True)

    response = _generate_with_retry(model, [prompt, image], cfg)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"Gemini 返回空内容: {image_path}")

    data = extract_json(text)
    items = coerce_item_dicts(data.get("items"))
    if not items:
        raise RuntimeError(f"Gemini JSON 缺少 items 数组: {text[:200]}")
    if tab == "product":
        card_name = data.get("cardName")
        if card_name is not None:
            card_name = str(card_name).strip() or None
        return items, card_name
    return items


def parse_detail_entry(
    cfg: VisionConfig, image_path: Path
) -> tuple[str | None, str | None, str | None, list[dict]]:
    _configure(cfg)
    model = genai.GenerativeModel(cfg.gemini_model)
    image = Image.open(image_path)
    print("[gemini] 请求中 (详情首屏 set/编号+一口价) …", flush=True)
    response = _generate_with_retry(model, [DETAIL_ENTRY_PROMPT, image], cfg)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"Gemini 返回空内容: {image_path}")

    data = extract_json(text)
    card_name = data.get("cardName")
    series = data.get("series")
    card_number = data.get("cardNumber")
    if card_name is not None:
        card_name = str(card_name).strip() or None
    if series is not None:
        series = str(series).strip() or None
    if card_number is not None:
        card_number = str(card_number).strip() or None
    items = coerce_item_dicts(data.get("items"))
    if not items:
        raise RuntimeError(f"Gemini JSON 缺少 items 数组: {text[:200]}")
    return series, card_number, card_name, items


def parse_auction_scroll(cfg: VisionConfig, image_path: Path) -> list[dict]:
    _configure(cfg)
    model = genai.GenerativeModel(cfg.gemini_model)
    image = Image.open(image_path)
    print("[gemini] 请求中 (竞价最近成交下滚) …", flush=True)
    response = _generate_with_retry(model, [AUCTION_SCROLL_PROMPT, image], cfg)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"Gemini 返回空内容: {image_path}")
    return parse_items_response(text)


def parse_card_label(cfg: VisionConfig, image_path: Path) -> tuple[str | None, str | None]:
    _configure(cfg)
    model = genai.GenerativeModel(cfg.gemini_model)
    image = Image.open(image_path)
    print("[gemini] 请求中 (商品页编号区) …", flush=True)
    response = _generate_with_retry(model, [CARD_LABEL_PROMPT, image], cfg)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"Gemini 返回空内容: {image_path}")

    data = extract_json(text)
    series = data.get("series")
    card_number = data.get("cardNumber")
    if series is not None:
        series = str(series).strip() or None
    if card_number is not None:
        card_number = str(card_number).strip() or None
    return series, card_number


def parse_wishlist_list(cfg: VisionConfig, image_path: Path) -> list[dict]:
    _configure(cfg)
    model = genai.GenerativeModel(cfg.gemini_model)
    image = Image.open(image_path)
    print("[gemini] 请求中 (心愿单列表扫描) …", flush=True)
    response = _generate_with_retry(model, [WISHLIST_SCAN_PROMPT, image], cfg)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"Gemini 返回空内容: {image_path}")

    data = extract_json(text)
    cards = data.get("cards")
    if not isinstance(cards, list):
        raise RuntimeError(f"Gemini JSON 缺少 cards 数组: {text[:200]}")
    return cards
