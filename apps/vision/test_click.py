#!/usr/bin/env python3
"""
测试 layout 坐标是否点对：点击 → 等待 → 截心愿单区域对比。

用法:
  python apps/vision/test_click.py --slot 0
  python apps/vision/test_click.py --point 85 230
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import dpi_fix  # noqa: F401

import pyautogui

from config import load_config
from layout_loader import load_layout_file
from layout_regions import click_point_for_cell
from rpa import Layout, focus_window, screenshot_region


def main() -> int:
    parser = argparse.ArgumentParser(description="测试单点点击是否生效")
    parser.add_argument("--slot", type=int, help="pageClickSlots 索引")
    parser.add_argument("--point", nargs=2, type=int, metavar=("X", "Y"), help="直接测屏幕坐标")
    parser.add_argument("--wait", type=float, default=3.0, help="点击后等待秒数")
    parser.add_argument("--double", action="store_true", help="双击")
    parser.add_argument(
        "--move-only",
        action="store_true",
        help="只移动鼠标到目标点，不点击（检查坐标是否对准卡牌中心）",
    )
    args = parser.parse_args()

    cfg = load_config()
    data = load_layout_file(cfg.layout_path, cfg.layout_profile)
    layout = Layout(data)

    if args.point:
        x, y = args.point
        label = f"手动点 ({x},{y})"
    elif args.slot is not None:
        col = args.slot % int(data["wishlistPageScan"]["cols"])
        row = args.slot // int(data["wishlistPageScan"]["cols"])
        x, y = click_point_for_cell(data, col, row)
        label = f"slot[{args.slot}] row={row} col={col} → ({x},{y})"
    else:
        parser.error("请指定 --slot N 或 --point X Y")

    try:
        import pygetwindow as gw

        wins = [w for w in gw.getAllWindows() if layout.window_title_keyword in (w.title or "")]
        if wins:
            w = wins[0]
            print(
                f"窗口「{w.title}」位置: left={w.left} top={w.top} "
                f"size={w.width}×{w.height}"
            )
            print(f"点击相对窗口约: ({x - w.left}, {y - w.top})")
    except Exception:
        pass

    print("\n3 秒内请把集换社窗口置于最前…")
    time.sleep(3)
    focus_window(cfg, layout)
    region = layout.region
    print(
        f"截图区域 screen=({region[0]},{region[1]}) "
        f"点击在截图内偏移≈({x - region[0]}, {y - region[1]})"
    )

    if args.move_only:
        before = pyautogui.position()
        print(f"移动前光标: ({before.x}, {before.y})")
        print(f"移动鼠标到 {label}（不点击）")
        pyautogui.moveTo(x, y, duration=0.4)
        after = pyautogui.position()
        print(f"移动后光标: ({after.x}, {after.y})  目标: ({x}, {y})")
        print("请看光标是否落在卡牌正中心")
        return 0

    print(f"点击 {label}" + ("（双击）" if args.double else ""))
    if args.double:
        pyautogui.doubleClick(x, y)
    else:
        pyautogui.click(x, y)
    time.sleep(args.wait)

    ts = datetime.now().strftime("%H%M%S")
    dest = cfg.screenshots_dir / f"test_click_{ts}.png"
    screenshot_region(layout, dest)
    print("\n若截图仍是心愿单列表 → 坐标偏了")
    print("若已是详情页 → 坐标正确")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
