"""Load VISION settings from vision.config.json + environment overrides."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

VISION_DIR = Path(__file__).resolve().parent
REPO_ROOT = VISION_DIR.parents[1]
CONFIG_PATH = VISION_DIR / "vision.config.json"

load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class VisionConfig:
    max_limit: int
    platform: str
    track_type: str
    sleep_after_card_min_sec: int
    sleep_after_card_max_sec: int
    page_load_wait_sec: float
    wishlist_page_wait_sec: float
    screenshot_wait_sec: float
    click_pause_sec: float
    window_position: tuple[int, int]
    vision_provider: str
    vision_min_interval_sec: float
    vision_max_retries: int
    deepseek_model: str
    deepseek_base_url: str
    doubao_model: str
    doubao_base_url: str
    gemini_model: str
    gemini_min_interval_sec: float
    gemini_max_retries: int
    layout_path: Path
    layout_profile: str
    checkpoint_path: Path
    screenshots_dir: Path
    direct_url: str
    gemini_api_key: str
    deepseek_api_key: str
    doubao_api_key: str
    mock_rpa: bool
    mock_vision: bool
    navigation_mode: str
    wishlist_grid_slots: int
    wishlist_back_clicks: int
    wishlist_max_scroll_pages: int
    wishlist_scroll_clicks_down: int
    wishlist_scroll_clicks_up: int
    wishlist_scroll_reset_clicks: int
    wishlist_scroll_page_steps: float
    product_scroll_pages: int
    product_scroll_clicks_per_page: int
    auction_scroll_clicks: int
    auction_scroll_clicks_per_step: int


def _load_json_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(
            f"缺少配置文件 {CONFIG_PATH}，请从 vision.config.json 复制或创建。"
        )
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _looks_like_wrong_doubao_key(key: str) -> str | None:
    k = key.strip()
    if not k:
        return "DOUBAO_API_KEY 为空"
    upper = k.upper()
    if upper.startswith(("AKLT", "AKTP", "AKIA")):
        return (
            "DOUBAO_API_KEY 填的是云账号 Access Key ID（以 AKLT 开头），不是方舟 API Key。"
            "请到 console.volcengine.com/ark → API Key 管理 创建并复制明文 Key。"
        )
    if k.endswith("=") or (len(k) % 4 == 0 and len(k) >= 40 and "+" not in k and "/" in k):
        return (
            "DOUBAO_API_KEY 疑似 Base64 编码，方舟要求粘贴控制台「API Key 管理」里的明文 Key"
            "（通常形如 xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）"
        )
    if len(k) < 20:
        return "DOUBAO_API_KEY 过短，请从火山方舟控制台重新复制完整 Key"
    return None


def _looks_like_wrong_doubao_model(model: str) -> str | None:
    m = model.strip()
    if not m:
        return "DOUBAO_MODEL 为空"
    if m.startswith("ep-"):
        return None
    if any(ch in m for ch in (" ", ".")) or (m and m[0].isupper()):
        return (
            f"DOUBAO_MODEL={m!r} 是控制台展示名，不是 API 模型 ID。"
            "请填推理接入点 ep-xxxx（创建接入点后复制）"
        )
    if m.startswith("doubao-"):
        return (
            f"DOUBAO_MODEL={m} 可能未开通或版本不存在。"
            "推荐在方舟创建视觉模型推理接入点，将 DOUBAO_MODEL 设为 ep-xxxx"
        )
    return None


def validate_vision_backend(cfg: VisionConfig) -> None:
    """启动前检查识图后端是否可用。"""
    if cfg.mock_vision:
        return
    provider = (cfg.vision_provider or "gemini").strip().lower()
    if provider == "deepseek":
        raise RuntimeError(
            "DeepSeek 官方 API (api.deepseek.com) 仅支持纯文本，不支持识图（image_url）。"
            "请改用 VISION_PROVIDER=doubao 或 gemini。"
        )
    if provider == "doubao":
        if not cfg.doubao_api_key:
            raise RuntimeError(
                "缺少 DOUBAO_API_KEY（或 ARK_API_KEY），请在 .env 中配置火山方舟 API Key。"
            )
        key_err = _looks_like_wrong_doubao_key(cfg.doubao_api_key)
        if key_err:
            raise RuntimeError(key_err)
        model_err = _looks_like_wrong_doubao_model(cfg.doubao_model)
        if model_err:
            raise RuntimeError(model_err)
    if provider == "gemini" and not cfg.gemini_api_key:
        raise RuntimeError("缺少 GEMINI_API_KEY，请在 .env 中配置。")
    if provider not in ("gemini", "doubao"):
        raise RuntimeError(f"未知识图后端: {provider}（支持 gemini | doubao）")


def load_config() -> VisionConfig:
    raw = _load_json_config()
    paths = raw.get("paths", {})

    max_limit = int(os.getenv("VISION_MAX_LIMIT", raw.get("maxLimit", 50)))

    return VisionConfig(
        max_limit=max_limit,
        platform=str(raw.get("platform", "JIHUANSHE")),
        track_type=str(raw.get("trackType", "VISION")),
        sleep_after_card_min_sec=int(raw.get("sleepAfterCardMinSec", 6)),
        sleep_after_card_max_sec=int(raw.get("sleepAfterCardMaxSec", 12)),
        page_load_wait_sec=float(raw.get("pageLoadWaitSec", 4)),
        wishlist_page_wait_sec=float(raw.get("wishlistPageWaitSec", 6)),
        screenshot_wait_sec=float(raw.get("screenshotWaitSec", 2)),
        click_pause_sec=float(raw.get("clickPauseSec", 0.35)),
        window_position=tuple(raw.get("windowPosition", [0, 0])),  # type: ignore[arg-type]
        vision_provider=str(
            os.getenv("VISION_PROVIDER", raw.get("visionProvider", "gemini"))
        ).strip().lower(),
        vision_min_interval_sec=float(
            raw.get(
                "visionMinIntervalSec",
                raw.get("geminiMinIntervalSec", 20),
            )
        ),
        vision_max_retries=int(
            raw.get("visionMaxRetries", raw.get("geminiMaxRetries", 8))
        ),
        deepseek_model=str(
            os.getenv("DEEPSEEK_MODEL", raw.get("deepseekModel", "deepseek-v4-pro"))
        ),
        deepseek_base_url=str(
            os.getenv("DEEPSEEK_BASE_URL", raw.get("deepseekBaseUrl", "https://api.deepseek.com"))
        ),
        doubao_model=str(
            os.getenv("DOUBAO_MODEL", raw.get("doubaoModel", "doubao-1-5-vision-pro-32k-250115"))
        ),
        doubao_base_url=str(
            os.getenv(
                "DOUBAO_BASE_URL",
                raw.get("doubaoBaseUrl", "https://ark.cn-beijing.volces.com/api/v3"),
            )
        ),
        gemini_model=str(raw.get("geminiModel", "gemini-2.5-flash")),
        gemini_min_interval_sec=float(raw.get("geminiMinIntervalSec", 20)),
        gemini_max_retries=int(raw.get("geminiMaxRetries", 8)),
        layout_path=VISION_DIR / str(paths.get("layout", "layout.json")),
        layout_profile=str(
            os.getenv("VISION_LAYOUT_PROFILE", raw.get("layoutProfile", "笔记本"))
        ).strip(),
        checkpoint_path=VISION_DIR / str(paths.get("checkpoint", "checkpoint.json")),
        screenshots_dir=VISION_DIR / str(paths.get("screenshotsDir", "screenshots")),
        direct_url=os.getenv("DIRECT_URL", "").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        doubao_api_key=os.getenv("DOUBAO_API_KEY", os.getenv("ARK_API_KEY", "")).strip(),
        mock_rpa=os.getenv("VISION_MOCK", "").lower() in ("1", "true", "yes"),
        mock_vision=os.getenv("VISION_MOCK_VISION", os.getenv("VISION_MOCK_GEMINI", "")).lower()
        in ("1", "true", "yes"),
        navigation_mode=str(raw.get("navigationMode", "search")).strip().lower(),
        wishlist_grid_slots=int(raw.get("wishlistGridSlots", 12)),
        wishlist_back_clicks=int(raw.get("wishlistBackClicks", 1)),
        wishlist_max_scroll_pages=int(raw.get("wishlistMaxScrollPages", 8)),
        wishlist_scroll_clicks_down=int(raw.get("wishlistScrollClicksDown", -4)),
        wishlist_scroll_clicks_up=int(raw.get("wishlistScrollClicksUp", 4)),
        wishlist_scroll_reset_clicks=int(raw.get("wishlistScrollResetClicks", 6)),
        wishlist_scroll_page_steps=float(raw.get("wishlistScrollPageSteps", 1)),
        product_scroll_pages=int(raw.get("productScrollPages", 2)),
        product_scroll_clicks_per_page=int(raw.get("productScrollClicksPerPage", -4)),
        auction_scroll_clicks=int(raw.get("auctionScrollClicks", -2)),
        auction_scroll_clicks_per_step=int(
            raw.get(
                "auctionScrollClicksPerStep",
                raw.get("wishlistScrollClicksDown", -4),
            )
        ),
    )
