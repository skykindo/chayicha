"""心愿单滑动模式：识图找卡名 → 点击，不依赖固定 gridSlot。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from vision_client import parse_wishlist_list
from vision_prompts import _normalize_card_label


@dataclass(frozen=True)
class GridGeometry:
    origin_x: int
    origin_y: int
    cols: int
    cell_width: int
    cell_height: int

    def cell_center(self, row: int, col: int) -> tuple[int, int]:
        x = self.origin_x + col * self.cell_width + self.cell_width // 2
        y = self.origin_y + row * self.cell_height + self.cell_height // 2
        return x, y


@dataclass(frozen=True)
class WishlistListLayout:
    list_region: tuple[int, int, int, int]
    scroll_center: tuple[int, int]
    grid: GridGeometry


def load_wishlist_list_layout(data: dict) -> WishlistListLayout:
    region = data.get("wishlistListRegion") or {}
    scroll = data.get("scrollCenter") or data.get("points", {}).get("scroll_center")
    geom = data.get("gridGeometry") or {}

    if isinstance(scroll, list) and len(scroll) >= 2:
        scroll_center = (int(scroll[0]), int(scroll[1]))
    elif "scroll_center" in data.get("points", {}):
        p = data["points"]["scroll_center"]
        scroll_center = (int(p[0]), int(p[1]))
    else:
        raise KeyError("layout.json 缺少 scrollCenter 或 points.scroll_center")

    points = data.get("points", {})
    origin = geom.get("origin")
    if not origin and "grid_01" in points:
        g1 = points["grid_01"]
        g2 = points.get("grid_02")
        g5 = points.get("grid_05")
        origin = g1
        cell_width = int(g2[0]) - int(g1[0]) if g2 else int(geom.get("cellWidth", 80))
        cell_height = int(g5[1]) - int(g1[1]) if g5 else int(geom.get("cellHeight", 300))
    else:
        origin = origin or [60, 230]
        cell_width = int(geom.get("cellWidth", 80))
        cell_height = int(geom.get("cellHeight", 300))

    grid = GridGeometry(
        origin_x=int(origin[0]),
        origin_y=int(origin[1]),
        cols=int(geom.get("cols", 4)),
        cell_width=cell_width,
        cell_height=cell_height,
    )

    return WishlistListLayout(
        list_region=(
            int(region.get("x", 0)),
            int(region.get("y", 140)),
            int(region.get("width", 420)),
            int(region.get("height", 700)),
        ),
        scroll_center=scroll_center,
        grid=grid,
    )


def names_match(expected: str, detected: str) -> bool:
    exp = _normalize_card_label(expected)
    det = _normalize_card_label(detected)
    if not exp or not det:
        return False
    if exp in det or det in exp:
        return True
    for i in range(len(exp) - 1):
        if exp[i : i + 2] in det:
            return True
    return False


def pick_visible_card(expected_name: str, cards: list[dict]) -> dict | None:
    for card in cards:
        name = str(card.get("name") or "").strip()
        if name and names_match(expected_name, name):
            return card
    return None
