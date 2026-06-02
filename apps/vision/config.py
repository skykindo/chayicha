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
    window_position: tuple[int, int]
    gemini_model: str
    gemini_min_interval_sec: float
    layout_path: Path
    checkpoint_path: Path
    screenshots_dir: Path
    direct_url: str
    gemini_api_key: str
    mock_rpa: bool
    mock_gemini: bool


def _load_json_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(
            f"缺少配置文件 {CONFIG_PATH}，请从 vision.config.json 复制或创建。"
        )
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


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
        page_load_wait_sec=float(raw.get("pageLoadWaitSec", 2.5)),
        window_position=tuple(raw.get("windowPosition", [0, 0])),  # type: ignore[arg-type]
        gemini_model=str(raw.get("geminiModel", "gemini-2.5-flash")),
        gemini_min_interval_sec=float(raw.get("geminiMinIntervalSec", 13)),
        layout_path=VISION_DIR / str(paths.get("layout", "layout.json")),
        checkpoint_path=VISION_DIR / str(paths.get("checkpoint", "checkpoint.json")),
        screenshots_dir=VISION_DIR / str(paths.get("screenshotsDir", "screenshots")),
        direct_url=os.getenv("DIRECT_URL", "").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        mock_rpa=os.getenv("VISION_MOCK", "").lower() in ("1", "true", "yes"),
        mock_gemini=os.getenv("VISION_MOCK_GEMINI", "").lower() in ("1", "true", "yes"),
    )
