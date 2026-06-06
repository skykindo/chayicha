"""断点续爬：记录当前卡与步骤，支持从中断处恢复。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

SearchStep = Literal[
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

WishlistStep = Literal[
    "open_grid_card",
    "shot_detail_entry",
    "tap_card_info",
    "tap_product",
    "tap_auction",
    "tap_recent_deals",
    "scroll_auction_list",
    "shot_auction_price",
    "back_to_grid",
    "db_write",
    "done",
]

Step = SearchStep | WishlistStep

SEARCH_STEP_ORDER: list[SearchStep] = [
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

WISHLIST_STEP_ORDER: list[WishlistStep] = [
    "open_grid_card",
    "shot_detail_entry",
    "tap_card_info",
    "tap_product",
    "tap_auction",
    "tap_recent_deals",
    "scroll_auction_list",
    "shot_auction_price",
    "back_to_grid",
    "db_write",
    "done",
]

WISHLIST_MODES = ("wishlist", "wishlist_scroll", "wishlist_page_scan")

_LEGACY_WISHLIST_STEP: dict[str, str] = {
    "shot_product": "shot_detail_entry",
    "shot_product_label": "shot_detail_entry",
    "scroll_product_pages": "scroll_auction_list",
    "shot_product_price": "shot_auction_price",
}


def normalize_step(step: str | None, navigation_mode: str) -> str | None:
    if not step:
        return step
    if navigation_mode in WISHLIST_MODES:
        return _LEGACY_WISHLIST_STEP.get(step, step)
    return step


def step_order(navigation_mode: str) -> list[str]:
    if navigation_mode in WISHLIST_MODES:
        return list(WISHLIST_STEP_ORDER)
    return list(SEARCH_STEP_ORDER)


def first_step(navigation_mode: str) -> Step:
    order = step_order(navigation_mode)
    return order[0]  # type: ignore[return-value]


@dataclass
class Checkpoint:
    run_started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_asset_keys: list[str] = field(default_factory=list)
    current_asset_key: str | None = None
    current_step: str | None = None
    success_count: int = 0
    fail_count: int = 0
    floor_screenshot: str | None = None
    auction_screenshot: str | None = None
    product_screenshot: str | None = None
    product_label_screenshot: str | None = None
    scan_page: int = 1
    scan_cell_index: int = 0
    scrolled_to_top: bool = False

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
            product_screenshot=data.get("productScreenshot"),
            product_label_screenshot=data.get("productLabelScreenshot"),
            scan_page=int(data.get("scanPage", 1)),
            scan_cell_index=int(data.get("scanCellIndex", 0)),
            scrolled_to_top=bool(data.get("scrolledToTop", False)),
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
            "productScreenshot": self.product_screenshot,
            "productLabelScreenshot": self.product_label_screenshot,
            "scanPage": self.scan_page,
            "scanCellIndex": self.scan_cell_index,
            "scrolledToTop": self.scrolled_to_top,
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def should_skip(self, asset_key: str) -> bool:
        return asset_key in self.completed_asset_keys

    def start_card(self, asset_key: str, path: Path, *, navigation_mode: str) -> str:
        if self.current_asset_key != asset_key:
            self.current_asset_key = asset_key
            self.current_step = first_step(navigation_mode)
            self.floor_screenshot = None
            self.auction_screenshot = None
            self.product_screenshot = None
            self.product_label_screenshot = None
            self.save(path)
        elif normalize_step(self.current_step, navigation_mode) not in step_order(
            navigation_mode
        ):
            self.current_step = first_step(navigation_mode)
            self.save(path)
        else:
            normalized = normalize_step(self.current_step, navigation_mode)
            if normalized != self.current_step:
                self.current_step = normalized
                self.save(path)
        return self.current_step or first_step(navigation_mode)

    def advance(self, step: str, path: Path) -> None:
        self.current_step = step
        self.save(path)

    def advance_scan_cell(self, path: Path) -> None:
        self.scan_cell_index += 1
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
        self.product_screenshot = None
        self.product_label_screenshot = None
        self.save(path)

    def step_index(self, step: str, navigation_mode: str) -> int:
        order = step_order(navigation_mode)
        step = normalize_step(step, navigation_mode) or step
        return order.index(step)  # type: ignore[arg-type]

    def should_run_step(self, step: str, navigation_mode: str) -> bool:
        if not self.current_step:
            return True
        current = normalize_step(self.current_step, navigation_mode)
        if current not in step_order(navigation_mode):
            return True
        step = normalize_step(step, navigation_mode) or step
        return self.step_index(step, navigation_mode) >= self.step_index(
            current, navigation_mode
        )
