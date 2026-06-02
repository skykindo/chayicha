"""断点续爬：记录当前卡与步骤，支持从中断处恢复。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

Step = Literal[
    "box_search",
    "pick_series",
    "enter_box",
    "number_search",
    "enter_card",
    "shot_floor",
    "shot_auction",
    "db_write",
    "done",
]

STEP_ORDER: list[Step] = [
    "box_search",
    "pick_series",
    "enter_box",
    "number_search",
    "enter_card",
    "shot_floor",
    "shot_auction",
    "db_write",
    "done",
]


@dataclass
class Checkpoint:
    run_started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_asset_keys: list[str] = field(default_factory=list)
    current_asset_key: str | None = None
    current_step: Step | None = None
    success_count: int = 0
    fail_count: int = 0
    floor_screenshot: str | None = None
    auction_screenshot: str | None = None

    @classmethod
    def load(cls, path: Path) -> Checkpoint:
        if not path.is_file():
            return cls()
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            run_started_at=data.get("runStartedAt", cls().run_started_at),
            completed_asset_keys=list(data.get("completedAssetKeys", [])),
            current_asset_key=data.get("currentAssetKey"),
            current_step=data.get("currentStep"),
            success_count=int(data.get("successCount", 0)),
            fail_count=int(data.get("failCount", 0)),
            floor_screenshot=data.get("floorScreenshot"),
            auction_screenshot=data.get("auctionScreenshot"),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "runStartedAt": self.run_started_at,
            "completedAssetKeys": self.completed_asset_keys,
            "currentAssetKey": self.current_asset_key,
            "currentStep": self.current_step,
            "successCount": self.success_count,
            "failCount": self.fail_count,
            "floorScreenshot": self.floor_screenshot,
            "auctionScreenshot": self.auction_screenshot,
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def should_skip(self, asset_key: str) -> bool:
        return asset_key in self.completed_asset_keys

    def start_card(self, asset_key: str, path: Path) -> Step:
        if self.current_asset_key != asset_key:
            self.current_asset_key = asset_key
            self.current_step = "box_search"
            self.floor_screenshot = None
            self.auction_screenshot = None
            self.save(path)
        return self.current_step or "box_search"

    def advance(self, step: Step, path: Path) -> None:
        self.current_step = step
        self.save(path)

    def finish_card(self, asset_key: str, path: Path, *, success: bool) -> None:
        if asset_key not in self.completed_asset_keys:
            self.completed_asset_keys.append(asset_key)
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        self.current_asset_key = None
        self.current_step = None
        self.floor_screenshot = None
        self.auction_screenshot = None
        self.save(path)

    def step_index(self, step: Step) -> int:
        return STEP_ORDER.index(step)

    def should_run_step(self, step: Step) -> bool:
        if not self.current_step:
            return True
        return self.step_index(step) >= self.step_index(self.current_step)
