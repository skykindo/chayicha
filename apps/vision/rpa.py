"""PyAutoGUI RPA：窗口归位、中文搜索、Tab 切换、区域截图。"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pyautogui
import pyperclip

from config import VisionConfig

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15


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


def load_layout(path: Path) -> Layout:
    if not path.is_file():
        raise FileNotFoundError(
            f"缺少 {path}。请复制 layout.example.json 为 layout.json 并校准坐标。"
        )
    with path.open(encoding="utf-8") as f:
        return Layout(json.load(f))


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
            f"请打开安卓模拟器中的集换社 App，并检查 layout.json 的 windowTitleKeyword。"
        )

    win = matches[0]
    if win.isMinimized:
        win.restore()
    win.activate()
    time.sleep(0.3)
    x, y = cfg.window_position
    win.moveTo(x, y)


def paste_and_submit(text: str) -> None:
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)
    pyautogui.press("enter")


def click_named(layout: Layout, name: str) -> None:
    x, y = layout.point(name)
    pyautogui.click(x, y)


def wait_page(cfg: VisionConfig) -> None:
    time.sleep(cfg.page_load_wait_sec)


def screenshot_region(layout: Layout, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = pyautogui.screenshot(region=layout.region)
    img.save(dest)
    return dest


class VisionRpa:
    def __init__(self, cfg: VisionConfig, layout: Layout) -> None:
        self.cfg = cfg
        self.layout = layout

    def prepare_window(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] VISION_MOCK=1，跳过窗口定位")
            return
        focus_window(self.cfg, self.layout)

    def search_box(self, series: str) -> None:
        if self.cfg.mock_rpa:
            print(f"[rpa] mock 搜卡盒: {series}")
            return
        click_named(self.layout, "global_search")
        paste_and_submit(series)
        wait_page(self.cfg)

    def pick_series(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 点系列按钮")
            return
        click_named(self.layout, "series_button")
        wait_page(self.cfg)

    def enter_box(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 点第一条卡盒结果")
            return
        click_named(self.layout, "box_result_first")
        wait_page(self.cfg)

    def search_number(self, card_number: str) -> None:
        if self.cfg.mock_rpa:
            print(f"[rpa] mock 搜编号: {card_number}")
            return
        click_named(self.layout, "inner_search")
        paste_and_submit(card_number)
        wait_page(self.cfg)

    def enter_card(self) -> None:
        if self.cfg.mock_rpa:
            print("[rpa] mock 进入卡牌")
            return
        click_named(self.layout, "card_result_first")
        wait_page(self.cfg)

    def shot_floor_tab(self, dest: Path) -> Path:
        if self.cfg.mock_rpa:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file():
                from PIL import Image

                Image.new("RGB", (400, 600), color=(240, 240, 240)).save(dest)
            print(f"[rpa] mock 一口价截图 → {dest}")
            return dest
        click_named(self.layout, "tab_floor")
        wait_page(self.cfg)
        return screenshot_region(self.layout, dest)

    def shot_auction_tab(self, dest: Path) -> Path:
        if self.cfg.mock_rpa:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file():
                from PIL import Image

                Image.new("RGB", (400, 600), color=(230, 230, 230)).save(dest)
            print(f"[rpa] mock 竞价截图 → {dest}")
            return dest
        click_named(self.layout, "tab_auction")
        wait_page(self.cfg)
        return screenshot_region(self.layout, dest)
