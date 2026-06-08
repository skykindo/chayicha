"""DeepSeek 识图：截图 → 结构化 JSON（OpenAI 兼容 API）。"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

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

_last_call_at: float = 0.0


def _mime_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".webp":
        return "image/webp"
    return "image/png"


def _image_data_url(path: Path) -> str:
    mime = _mime_type(path)
    raw = path.read_bytes()
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _is_rate_limited(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg


def _retry_delay_sec(attempt: int) -> float:
    return max(5.0, 8.0 * (attempt + 1))


def _wait_interval(cfg: VisionConfig) -> None:
    global _last_call_at
    if _last_call_at <= 0:
        return
    elapsed = time.time() - _last_call_at
    wait = cfg.vision_min_interval_sec - elapsed
    if wait > 0:
        print(f"[deepseek] 请求间隔，等待 {wait:.0f}s …", flush=True)
        time.sleep(wait)


def _chat_with_image(
    cfg: VisionConfig,
    *,
    prompt: str,
    image_path: Path,
    label: str,
) -> str:
    if not cfg.deepseek_api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，请在 .env 中配置。")

    url = f"{cfg.deepseek_base_url.rstrip('/')}/chat/completions"
    raise RuntimeError(
        "DeepSeek 官方 API (api.deepseek.com) 不支持识图（image_url），"
        "包括 deepseek-v4-pro。请设置 VISION_PROVIDER=gemini。"
    )

    payload = {
        "model": cfg.deepseek_model,
        "thinking": {"type": "disabled"},
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": _image_data_url(image_path)},
                    },
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg.deepseek_api_key}",
    }

    last_exc: Exception | None = None
    max_retries = max(1, cfg.vision_max_retries)
    for attempt in range(max_retries):
        _wait_interval(cfg)
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            print(
                f"[deepseek] 请求中 ({label}, {cfg.deepseek_model}) …",
                flush=True,
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            global _last_call_at
            _last_call_at = time.time()
            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError(f"DeepSeek 返回无 choices: {data}")
            message = choices[0].get("message") or {}
            text = (message.get("content") or "").strip()
            if not text:
                raise RuntimeError(f"DeepSeek 返回空内容: {image_path}")
            return text
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            wrapped = RuntimeError(f"DeepSeek HTTP {exc.code}: {err_body[:400]}")
            if exc.code == 400 and "image_url" in err_body:
                raise RuntimeError(
                    "DeepSeek 官方 API 不支持识图（image_url）。"
                    "请设置 VISION_PROVIDER=gemini。"
                    f"原始: {err_body[:300]}"
                ) from exc
            if exc.code == 429:
                last_exc = wrapped
                delay = _retry_delay_sec(attempt)
                print(
                    f"[deepseek] 429 限流，{delay:.0f}s 后重试 "
                    f"({attempt + 1}/{max_retries}) …",
                    flush=True,
                )
                time.sleep(delay)
                continue
            raise wrapped from exc
        except Exception as exc:
            if _is_rate_limited(exc):
                last_exc = exc
                delay = _retry_delay_sec(attempt)
                print(
                    f"[deepseek] 限流，{delay:.0f}s 后重试 "
                    f"({attempt + 1}/{max_retries}) …",
                    flush=True,
                )
                time.sleep(delay)
                continue
            raise

    raise RuntimeError(f"DeepSeek 重试次数已用尽: {last_exc}") from last_exc


def parse_screenshot(cfg: VisionConfig, image_path: Path, *, tab: str) -> list[dict]:
    if tab == "floor":
        prompt, tab_label = FLOOR_PROMPT, "一口价"
    elif tab == "auction":
        prompt, tab_label = AUCTION_PROMPT, "竞价"
    else:
        prompt, tab_label = PRODUCT_PROMPT, "商品"

    text = _chat_with_image(cfg, prompt=prompt, image_path=image_path, label=tab_label)
    data = extract_json(text)
    items = coerce_item_dicts(data.get("items"))
    if not items:
        raise RuntimeError(f"DeepSeek JSON 缺少 items 数组: {text[:200]}")
    if tab == "product":
        card_name = data.get("cardName")
        if card_name is not None:
            card_name = str(card_name).strip() or None
        return items, card_name
    return items


def parse_detail_entry(
    cfg: VisionConfig, image_path: Path
) -> tuple[str | None, str | None, str | None, list[dict]]:
    text = _chat_with_image(
        cfg,
        prompt=DETAIL_ENTRY_PROMPT,
        image_path=image_path,
        label="详情首屏 set/编号+一口价",
    )
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
        raise RuntimeError(f"DeepSeek JSON 缺少 items 数组: {text[:200]}")
    return series, card_number, card_name, items


def parse_auction_scroll(cfg: VisionConfig, image_path: Path) -> list[dict]:
    text = _chat_with_image(
        cfg,
        prompt=AUCTION_SCROLL_PROMPT,
        image_path=image_path,
        label="竞价最近成交下滚",
    )
    return parse_items_response(text)


def parse_card_label(cfg: VisionConfig, image_path: Path) -> tuple[str | None, str | None]:
    text = _chat_with_image(
        cfg,
        prompt=CARD_LABEL_PROMPT,
        image_path=image_path,
        label="商品页编号区",
    )
    data = extract_json(text)
    series = data.get("series")
    card_number = data.get("cardNumber")
    if series is not None:
        series = str(series).strip() or None
    if card_number is not None:
        card_number = str(card_number).strip() or None
    return series, card_number


def parse_wishlist_list(cfg: VisionConfig, image_path: Path) -> list[dict]:
    text = _chat_with_image(
        cfg,
        prompt=WISHLIST_SCAN_PROMPT,
        image_path=image_path,
        label="心愿单列表扫描",
    )
    data = extract_json(text)
    cards = data.get("cards")
    if not isinstance(cards, list):
        raise RuntimeError(f"DeepSeek JSON 缺少 cards 数组: {text[:200]}")
    return cards
