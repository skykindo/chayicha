#!/usr/bin/env python3
"""
读取鼠标屏幕坐标，用于校准 layout.json。

用法:
  npm run vision:calibrate              # 实时刷新坐标
  npm run vision:calibrate -- --record    # 按 Enter 逐条记录（适合 pageClickSlots / points）

将鼠标移到目标位置，记下 [x, y]，写入 layout.json → profiles → 当前机位。
按 Ctrl+C 退出。
"""

from __future__ import annotations

import argparse
import sys
import time

import dpi_fix  # noqa: F401

import pyautogui

pyautogui.FAILSAFE = True

RECORD_LABELS = [
    "pageClickSlots[0] grid_01 左上",
    "pageClickSlots[1] grid_02 中上",
    "pageClickSlots[2] grid_03 右上",
    "pageClickSlots[3] grid_04 左下",
    "pageClickSlots[4] grid_05 中下",
    "pageClickSlots[5] grid_06 右下",
    "points.card_info 卡牌信息",
    "points.product_tab 商品",
    "points.tab_auction 竞价",
    "points.tab_recent_deals 最近成交",
    "points.back_button 返回",
    "productPage.auctionScrollCenter 竞价列表滚轮落点",
    "screenshotRegion 左上角 (仅记 x,y，宽高另测)",
]


def run_live() -> None:
    print("移动鼠标到目标位置，坐标会实时刷新。Ctrl+C 退出。\n")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\r当前坐标: [{x}, {y}]   ", end="", flush=True)
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n已退出。")


def run_record() -> None:
    print("=== 逐条记录模式（模拟器 3×2 + 导航按钮）===")
    print("对每一项：先将鼠标移到目标中心，再回来按 Enter 记录当前鼠标位置。\n")
    recorded: list[tuple[str, list[int]]] = []
    for label in RECORD_LABELS:
        try:
            input(f"{label}\n  移好鼠标后按 Enter 记录（Ctrl+C 退出）: ")
        except KeyboardInterrupt:
            print("\n已退出。")
            return
        x, y = pyautogui.position()
        print(f"  → [{x}, {y}]\n")
        recorded.append((label, [x, y]))

    print("\n=== 复制到 layout.json ===\n")
    slots = [p for lb, p in recorded if lb.startswith("pageClickSlots")]
    if slots:
        print('"pageClickSlots": [')
        for p in slots:
            print(f"  {p},")
        print("],\n")
    for label, p in recorded:
        if label.startswith("points."):
            key = label.split()[0].split(".", 1)[1]
            print(f'"{key}": {p},  # {label}')
    for label, p in recorded:
        if "auctionScrollCenter" in label:
            print(f'"auctionScrollCenter": {p},')
        if label.startswith("screenshotRegion"):
            print(f'"screenshotRegion": {{ "x": {p[0]}, "y": {p[1]}, "width": ???, "height": ??? }}')
            print("  (宽高：移到区域右下角再看坐标，width=右下x-左上x，height=右下y-左上y)")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="VISION 坐标校准")
    parser.add_argument(
        "--record",
        action="store_true",
        help="逐条记录模式（适合首次配置模拟器）",
    )
    args = parser.parse_args()

    print("=== VISION 坐标校准 ===")
    print("FAILSAFE: 鼠标快速移到屏幕左上角可紧急中止 PyAutoGUI。\n")
    print("前提：模拟器窗口已固定在屏幕左上角 (0,0)，与 vision.config.json windowPosition 一致。\n")

    if args.record:
        run_record()
    else:
        run_live()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
