"""PyAutoGUI RPA：窗口归位、中文搜索、Tab 切换、区域截图。"""

from __future__ import annotations

import json
import time
from pathlib import Path

import dpi_fix  # noqa: F401 — Windows 高 DPI 坐标修正（须在 pyautogui 前）

import pyautogui
import pyperclip

from config import VisionConfig
from layout_loader import load_layout_file

pyautogui.FAILSAFE = True


class Layout:
    def __init__(self, data: dict) -> None:
        self.window_title_keyword = str(data.get("windowTitleKeyword", "微信"))
        self.points: dict[str, list[int]] = dict(data.get("points", {}))
        region = data.get("screenshotRegion") or data.get("screenshot_region") or {}
        self.region = (
            int(region.get("x", 0)),
            int(region.get("y", 0)),
            int(region.get("width", 400)),
            int(region.get("height", 600)),
        )

    def point(self, name: str) -> tuple[int, int]:
        if name not in self.points:
            raise KeyError(f"layout.json 缺少坐标 points.{name}")
        x, y = self.points[name]
        return int(x), int(y)

    def grid_slot_key(self, index: int) -> str:
        """index 0-based，对应 grid_01 …（行列数见 layout wishlistPageScan）。"""
        if index < 0:
            raise ValueError(f"grid 槽位 index 无效: {index}")
        return f"grid_{index + 1:02d}"


def load_layout(path: Path, profile: str | None = None) -> Layout:
    return Layout(load_layout_file(path, profile))


def load_layout_data(path: Path, profile: str | None = None) -> dict:
    return load_layout_file(path, profile)


def _try_activate_window(win) -> None:
    try:
        if win.isMinimized:
            win.restore()
    except Exception as exc:
        print(f"[rpa] 警告: 无法还原窗口: {exc}", flush=True)
    try:
        win.activate()
    except Exception as exc:
        print(
            f"[rpa] 警告: 无法自动激活窗口 ({exc})，尝试点击窗口中心…",
            flush=True,
        )
        try:
            cx = int(win.left) + int(win.width) // 2
            cy = int(win.top) + int(win.height) // 2
            pyautogui.click(cx, cy)
        except Exception as click_exc:
            print(
                f"[rpa] 警告: 点击窗口失败 ({click_exc})，请手动点一下集换社窗口",
                flush=True,
            )


def focus_window(cfg: VisionConfig, layout: Layout) -> None:
    try:
        import pygetwindow as gw
    except ImportError as exc:
        raise RuntimeError("请安装 pygetwindow: pip install pygetwindow") from exc

    keyword = layout.window_title_keyword
    matches = [w for w in gw.getAllWindows() if keyword in (w.title or "")]
    if not matches:
        raise RuntimeError(
            f"未找到标题含「{keyword}」的窗口。"
            f"请打开集换社（小程序/模拟器），页面停在心愿单，并检查 layout.json 的 windowTitleKeyword。"
        )

    win = matches[0]
    _try_activate_window(win)
    time.sleep(0.3)
    if not cfg.window_move_enabled:
        print(
            "[rpa] windowMoveEnabled=false，跳过自动移位（请保持窗口在校准时位置）",
            flush=True,
        )
        return
    x, y = cfg.window_position
    try:
        win.moveTo(x, y)
    except Exception as exc:
        print(
            f"[rpa] 警告: 无法移动窗口到 ({x},{y}) ({exc})。"
            "模拟器常拒绝程序移位，请手动将窗口放到校准时位置。",
            flush=True,
        )


def paste_and_submit(text: str) -> None:
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)
    pyautogui.press("enter")


def click_named(layout: Layout, name: str, *, pause_sec: float) -> None:
    x, y = layout.point(name)
    pyautogui.click(x, y)
    time.sleep(pause_sec)


def wait_seconds(cfg: VisionConfig, seconds: float, *, label: str) -> None:
    if label:
        print(f"[rpa] 等待 {seconds:g}s（{label}）…", flush=True)
    time.sleep(seconds)


def scroll_wheel_times(*, per_step: int, times: float, label: str) -> None:
    """按次数滚轮：times=8.5 表示 8 次整 + 0.5 次（半格）。"""
    full = int(times)
    fraction = round(times - full, 2)
    total_label = f"{times} 次" if fraction else f"{full} 次"
    for i in range(full):
        pyautogui.scroll(per_step)
        time.sleep(0.25)
        print(f"[rpa] {label} {i + 1}/{total_label}（{per_step} 格）", flush=True)
    if fraction > 0:
        half_step = per_step * fraction
        pyautogui.scroll(half_step)
        time.sleep(0.25)
        print(f"[rpa] {label} +{fraction} 次（{half_step} 格）", flush=True)


def screenshot_region(layout: Layout, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = pyautogui.screenshot(region=layout.region)
    img.save(dest)
    print(f"[rpa] 截图已保存 → {dest.resolve()}", flush=True)
    return dest


class VisionRpa:
    def __init__(self, cfg: VisionConfig, layout: Layout, layout_data: dict | None = None) -> None:
        self.cfg = cfg
        self.layout = layout
        self.layout_data = layout_data or {}
        pyautogui.PAUSE = cfg.click_pause_sec

    def ensure_focus(self) -> None:
        if self.cfg.mock_rpa:
            return
        focus_window(self.cfg, self.layout)

    def _click_point(self, x: int, y: int, *, label: str) -> None:
        if self.cfg.mock_rpa:
            print(f"[rpa] mock 点击 {label} → ({x},{y})", flush=True)
            return
        self.ensure_focus()
        print(f"[rpa] 点击 {label} → ({x},{y})", flush=True)
        pyautogui.click(x, y)
        time.sleep(self.cfg.click_pause_sec)

    def _click(self, name: str) -> None:
        x, y = self.layout.point(name)
        self._click_point(x, y, label=name)

    def _wait_nav(self, label: str) -> None:
        if self.cfg.navigation_mode in (
            "wishlist",
            "wishlist_scroll",
            "wishlist_page_scan",
        ):
            wait_seconds(self.cfg, self.cfg.wishlist_page_wait_sec, label=label)
        else:
            wait_seconds(self.cfg, self.cfg.page_load_wait_sec, label=label)

    def prepare_window(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] VISION_MOCK=1，跳过窗口定位")
            return
        focus_window(self.cfg, self.layout)

    def search_box(self, series: str) -> None:
        if self.cfg.mock_rpa:
            print(f"[rpa] mock 搜卡盒: {series}")
            return
        self._click("global_search")
        paste_and_submit(series)
        self._wait_nav("搜索卡盒")

    def pick_series(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 点系列按钮")
            return
        self._click("series_button")
        self._wait_nav("系列筛选")

    def enter_box(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 点第一条卡盒结果")
            return
        self._click("box_result_first")
        self._wait_nav("进入卡盒")

    def search_number(self, card_number: str) -> None:
        if self.cfg.mock_rpa:
            print(f"[rpa] mock 搜编号: {card_number}")
            return
        self._click("inner_search")
        paste_and_submit(card_number)
        self._wait_nav("搜索编号")

    def enter_card(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 进入卡牌")
            return
        self._click("card_result_first")
        self._wait_nav("进入卡牌")

    def shot_floor_tab(self, dest: Path) -> Path:
        if self.cfg.mock_rpa:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file():
                from PIL import Image

                Image.new("RGB", (400, 600), color=(240, 240, 240)).save(dest)
            print(f"[rpa] mock 一口价截图 → {dest}")
            return dest
        self._click("tab_floor")
        wait_seconds(self.cfg, self.cfg.screenshot_wait_sec, label="一口价页渲染")
        return screenshot_region(self.layout, dest)

    def shot_auction_tab(self, dest: Path) -> Path:
        if self.cfg.mock_rpa:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file():
                from PIL import Image

                Image.new("RGB", (400, 600), color=(230, 230, 230)).save(dest)
            print(f"[rpa] mock 竞价截图 → {dest}")
            return dest
        self._click("tab_auction")
        wait_seconds(self.cfg, self.cfg.screenshot_wait_sec, label="竞价页渲染")
        return screenshot_region(self.layout, dest)

    def open_grid_card(self, slot_index: int) -> None:
        scan = self.layout_data.get("wishlistPageScan") or {}
        cols = int(scan.get("cols", 4))
        row = slot_index // cols
        col = slot_index % cols
        key = self.layout.grid_slot_key(slot_index)
        if self.cfg.mock_rpa:
            print(f"[rpa] mock 点心愿单格位 {key} (index={slot_index})")
            return
        if key in self.layout.points:
            self._click(key)
        else:
            self.click_page_cell(col, row)
        self._wait_nav(f"打开格位 {key}")

    def click_page_cell(self, col: int, row: int) -> None:
        from layout_regions import click_point_for_cell

        x, y = click_point_for_cell(self.layout_data, col, row)
        if self.cfg.mock_rpa:
            print(f"[rpa] mock 点格 (row={row}, col={col}) → ({x},{y})")
            return
        self._click_point(x, y, label=f"心愿单格 row={row} col={col}")
        self._wait_nav(f"卡牌详情页 row={row} col={col}")

    def shot_detail_entry(self, dest: Path) -> Path:
        """点进卡牌后的详情首屏：截价格区，识 set/编号与一口价。"""
        if self.cfg.mock_rpa:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file():
                from PIL import Image

                Image.new("RGB", (400, 600), color=(242, 242, 242)).save(dest)
            print(f"[rpa] mock 详情首屏截图 → {dest}")
            return dest
        wait_seconds(self.cfg, self.cfg.screenshot_wait_sec, label="详情首屏渲染")
        return screenshot_region(self.layout, dest)

    def tap_card_info(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 点卡牌信息")
            return
        self.ensure_focus()
        self._click("card_info")
        self._wait_nav("卡牌信息页")

    def tap_product(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 点商品")
            return
        self.ensure_focus()
        self._click("product_tab")
        self._wait_nav("商品页")

    def tap_auction(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 点竞价")
            return
        self.ensure_focus()
        self._click("tab_auction")
        self._wait_nav("竞价页")

    def tap_recent_deals(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 点最近成交")
            return
        self.ensure_focus()
        self._click("tab_recent_deals")
        self._wait_nav("最近成交")

    def scroll_auction_list(self) -> None:
        from layout_regions import auction_scroll_settings

        center, steps, per_step = auction_scroll_settings(
            self.layout_data,
            cfg_steps=self.cfg.auction_scroll_clicks,
            cfg_per_step=self.cfg.auction_scroll_clicks_per_step,
        )
        if self.cfg.mock_rpa:
            print(
                f"[rpa] mock 竞价/最近成交下滚 {steps} 次（每次 {per_step} 格）",
                flush=True,
            )
            return
        self.ensure_focus()
        sx, sy = center
        pyautogui.moveTo(sx, sy)
        time.sleep(0.15)
        scroll_wheel_times(per_step=per_step, times=float(steps), label="竞价列表下滚")
        self._wait_nav(f"竞价列表下滚 {steps} 次")
        print(
            f"[rpa] 竞价/最近成交已下滚 {steps} 次（每次 {per_step} 格）",
            flush=True,
        )

    def shot_auction_price(self, dest: Path) -> Path:
        if self.cfg.mock_rpa:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file():
                from PIL import Image

                Image.new("RGB", (400, 600), color=(235, 235, 235)).save(dest)
            print(f"[rpa] mock 竞价下滚后截图 → {dest}")
            return dest
        wait_seconds(self.cfg, self.cfg.screenshot_wait_sec, label="竞价列表渲染")
        return screenshot_region(self.layout, dest)

    def back_to_wishlist_grid(self) -> None:
        n = max(1, self.cfg.wishlist_back_clicks)
        if self.cfg.mock_rpa:
            print(f"[rpa] mock 返回心愿单（{n} 次）")
            return
        for i in range(n):
            self.ensure_focus()
            self._click("back_button")
            self._wait_nav(f"返回 {i + 1}/{n}")
        print(f"[rpa] 已点返回 {n} 次（wishlistBackClicks={n}）", flush=True)

    def scroll_wishlist_page_to_top(self) -> None:
        from layout_regions import page_scroll_settings

        center, _, _, up, reset = page_scroll_settings(
            self.layout_data,
            cfg_scroll_down=self.cfg.wishlist_scroll_clicks_down,
            cfg_scroll_up=self.cfg.wishlist_scroll_clicks_up,
            cfg_reset_clicks=self.cfg.wishlist_scroll_reset_clicks,
            cfg_scroll_down_steps=self.cfg.wishlist_scroll_page_steps,
        )
        if self.cfg.mock_rpa:
            print(f"[rpa] mock 心愿单滚到顶部（{reset} 次 × {up} 格）")
            return
        sx, sy = center
        pyautogui.moveTo(sx, sy)
        for _ in range(reset):
            pyautogui.scroll(up)
            time.sleep(0.15)
        self._wait_nav("滚到列表顶部")

    def scroll_wishlist_page_down(self) -> bool:
        """下翻一整页（3 行）。返回 False 表示疑似已到列表底部。"""
        from layout_regions import page_scroll_settings, scroll_probe_rect

        center, steps, per_step, _, _ = page_scroll_settings(
            self.layout_data,
            cfg_scroll_down=self.cfg.wishlist_scroll_clicks_down,
            cfg_scroll_up=self.cfg.wishlist_scroll_clicks_up,
            cfg_reset_clicks=self.cfg.wishlist_scroll_reset_clicks,
            cfg_scroll_down_steps=self.cfg.wishlist_scroll_page_steps,
        )
        if self.cfg.mock_rpa:
            print(
                f"[rpa] mock 心愿单下翻一页（{steps} 次，每次 {per_step} 格）",
                flush=True,
            )
            return True

        before = scroll_probe_rect(self.layout_data)
        img_before = pyautogui.screenshot(region=before.as_pyautogui_region())

        self.ensure_focus()
        sx, sy = center
        pyautogui.moveTo(sx, sy)
        time.sleep(0.15)
        scroll_wheel_times(per_step=per_step, times=float(steps), label="心愿单下翻")
        self._wait_nav("心愿单下翻一页")

        img_after = pyautogui.screenshot(region=before.as_pyautogui_region())
        if list(img_before.getdata()) == list(img_after.getdata()):
            print("[rpa] 心愿单疑似已到底（首格探测区截图无变化）", flush=True)
            return False
        return True

    def scroll_wishlist_to_top(self) -> None:
        """wishlist_scroll 模式兼容入口。"""
        self.scroll_wishlist_page_to_top()

    def scroll_wishlist_down(self) -> None:
        """wishlist_scroll 模式兼容入口。"""
        self.scroll_wishlist_page_down()

    def screenshot_list_region(self, dest: Path) -> Path:
        from wishlist_nav import load_wishlist_list_layout

        ll = load_wishlist_list_layout(self.layout_data)
        dest.parent.mkdir(parents=True, exist_ok=True)
        img = pyautogui.screenshot(region=ll.list_region)
        img.save(dest)
        return dest

    def open_card_on_wishlist(self, card_name: str, scan_path: Path) -> None:
        from wishlist_nav import load_wishlist_list_layout, pick_visible_card
        from vision_client import parse_wishlist_list

        if self.cfg.mock_rpa:
            print(f"[rpa] mock 滑动找卡: {card_name}")
            return

        ll = load_wishlist_list_layout(self.layout_data)
        self.scroll_wishlist_to_top()

        for page in range(1, self.cfg.wishlist_max_scroll_pages + 1):
            self.screenshot_list_region(scan_path)
            print(f"[rpa] 扫描心愿单第 {page} 屏 → {scan_path.name}", flush=True)
            visible = parse_wishlist_list(self.cfg, scan_path)
            hit = pick_visible_card(card_name, visible)
            if hit:
                row = int(hit.get("row", 0))
                col = int(hit.get("col", 0))
                x, y = ll.grid.cell_center(row, col)
                print(
                    f"[rpa] 找到「{hit.get('name')}」@ row={row} col={col} → 点击 ({x},{y})",
                    flush=True,
                )
                pyautogui.click(x, y)
                time.sleep(self.cfg.click_pause_sec)
                self._wait_nav("打开卡牌")
                return

            if page < self.cfg.wishlist_max_scroll_pages:
                self.scroll_wishlist_down()

        raise RuntimeError(
            f"心愿单中未找到「{card_name}」（已滑动 {self.cfg.wishlist_max_scroll_pages} 屏）。"
            f"请确认 CSV 渠道在 App 心愿单里，或增大 wishlistMaxScrollPages。"
        )
