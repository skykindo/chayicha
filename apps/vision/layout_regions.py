"""layout.json 区域计算（心愿单整页 4×3 扫描，供后续 RPA 使用）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    """屏幕像素矩形：左上 (x1,y1)、右下 (x2,y2)。"""

    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def as_pyautogui_region(self) -> tuple[int, int, int, int]:
        return self.x1, self.y1, self.width, self.height

    def shift(self, dx: int, dy: int) -> Rect:
        return Rect(self.x1 + dx, self.y1 + dy, self.x2 + dx, self.y2 + dy)


def _page_scan(page: dict) -> dict:
    """兼容 wishlistPageScan / 旧 wishlistRowScan。"""
    return page.get("wishlistPageScan") or page.get("wishlistRowScan") or page


def col_row_strides(page_scan: dict) -> tuple[int, int]:
    """列距、行距（像素）。优先 pageClickSlots 前 5 点推算。"""
    slots = page_scan.get("pageClickSlots") or page_scan.get("rowClickSlots") or []
    if len(slots) >= 2:
        col_stride = int(slots[1][0]) - int(slots[0][0])
    else:
        col_stride = int(page_scan.get("colStride", 80))
    if len(slots) >= 5:
        row_stride = int(slots[4][1]) - int(slots[0][1])
    else:
        row_stride = int(page_scan.get("rowStride", 300))
    return col_stride, row_stride


def scroll_probe_rect(page: dict) -> Rect:
    """心愿单下翻前后对比用的小区域（以首格点击坐标为中心）。"""
    scan = _page_scan(page)
    slots = scan.get("pageClickSlots") or scan.get("rowClickSlots") or []
    if not slots:
        raise KeyError("需要 pageClickSlots 至少 1 个点作滚动探测")
    cx, cy = int(slots[0][0]), int(slots[0][1])
    return Rect(cx - 50, cy - 50, cx + 50, cy + 50)


def click_point_for_cell(page: dict, col: int, row: int) -> tuple[int, int]:
    """第 col、row 格的点进坐标。"""
    scan = _page_scan(page)
    cols = int(scan.get("cols", 4))
    slots = scan.get("pageClickSlots") or scan.get("rowClickSlots") or []
    idx = row * cols + col
    if idx < len(slots):
        return int(slots[idx][0]), int(slots[idx][1])
    col_stride, row_stride = col_row_strides(scan)
    if not slots:
        raise KeyError("需要 pageClickSlots 至少 1 个点作锚点")
    ax, ay = int(slots[0][0]), int(slots[0][1])
    return ax + col * col_stride, ay + row * row_stride


def auction_scroll_settings(
    data: dict, *, cfg_steps: int, cfg_per_step: int
) -> tuple[tuple[int, int], int, int]:
    """
    竞价/最近成交页 (scroll_center, 滚动次数, 每次滚轮格数)。
    auctionScrollClicks=-2 表示下滚 2 次；每次幅度用 auctionScrollClicksPerStep（默认与心愿单下翻一致）。
    """
    product = data.get("productPage") or {}
    scan = _page_scan(data)
    center = (
        product.get("auctionScrollCenter")
        or product.get("scrollCenter")
        or scan.get("scrollCenter")
        or [200, 500]
    )
    raw_steps = int(product.get("auctionScrollClicks") or cfg_steps)
    steps = max(1, abs(raw_steps))
    per_step = int(
        product.get("auctionScrollClicksPerStep")
        or product.get("scrollOnePageClicks")
        or cfg_per_step
    )
    if raw_steps < 0 and per_step > 0:
        per_step = -per_step
    elif raw_steps > 0 and per_step < 0:
        per_step = abs(per_step)
    return (int(center[0]), int(center[1])), steps, per_step


def product_scroll_settings(data: dict, *, cfg_pages: int, cfg_clicks: int) -> tuple[tuple[int, int], int, int]:
    """(scroll_center, scroll_pages, scroll_clicks_per_page)。"""
    product = data.get("productPage") or {}
    scan = _page_scan(data)
    center = product.get("scrollCenter") or scan.get("scrollCenter") or [200, 500]
    pages = int(product.get("scrollPages", cfg_pages))
    clicks = int(
        product.get("scrollClicksPerPage")
        or product.get("scrollOnePageClicks")
        or cfg_clicks
    )
    return (int(center[0]), int(center[1])), max(1, pages), clicks


def page_scroll_settings(
    data: dict,
    *,
    cfg_scroll_down: int,
    cfg_scroll_up: int,
    cfg_reset_clicks: int,
    cfg_scroll_down_steps: float = 1.0,
) -> tuple[tuple[int, int], float, int, int, int]:
    """
    心愿单 (scroll_center, 下翻次数, 每次滚轮幅度, 上滚格数, 滚顶次数)。
    scrollOnePageSteps=8.5 表示滚轮滚 8.5 次（可含半次）；每次幅度 scrollOnePageClicksPerStep，默认 -1。
    """
    scan = _page_scan(data)
    center = scan.get("scrollCenter") or [200, 500]
    per_step = int(
        scan.get("scrollOnePageClicksPerStep")
        or scan.get("scrollOnePageClicks")
        or cfg_scroll_down
    )
    raw_steps = scan.get("scrollOnePageSteps", cfg_scroll_down_steps)
    steps = max(0.5, float(raw_steps))
    up = int(scan.get("scrollClicksUp", cfg_scroll_up))
    reset = int(scan.get("scrollResetClicks", cfg_reset_clicks))
    return (int(center[0]), int(center[1])), steps, per_step, up, max(1, reset)


def occupied_slots_for_page(page: dict, page_no: int, channel_count: int) -> int | None:
    """
    第一屏实际有卡的格数。6 张卡占 2 行时只需扫 6 格，勿点第 7～12 空格子。
    优先 wishlistPageScan.occupiedSlots；否则第一页用 channel_count。
    """
    scan = _page_scan(page)
    fixed = scan.get("occupiedSlots")
    if fixed is not None:
        return int(fixed)
    if page_no == 1 and channel_count > 0:
        cols = int(scan.get("cols", 4))
        rows = int(scan.get("rows", 3))
        return min(channel_count, cols * rows)
    return None


def iter_page_cells(page: dict) -> list[tuple[int, int, int]]:
    """本页所有格 (row, col, index)，行列数由 layout wishlistPageScan.cols/rows 决定。"""
    scan = _page_scan(page)
    cols = int(scan.get("cols", 4))
    rows = int(scan.get("rows", 3))
    out: list[tuple[int, int, int]] = []
    for row in range(rows):
        for col in range(cols):
            out.append((row, col, row * cols + col))
    return out


def cells_for_scan_page(
    page: dict, *, page_no: int, channel_count: int
) -> list[tuple[int, int, int]]:
    cells = iter_page_cells(page)
    limit = occupied_slots_for_page(page, page_no, channel_count)
    if limit is not None and limit < len(cells):
        return cells[:limit]
    return cells
