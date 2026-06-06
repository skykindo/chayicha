#!/usr/bin/env python3
"""
实时显示鼠标屏幕坐标，用于校准 layout.json。

用法:
  python apps/vision/calibrate_layout.py
  npm run vision:calibrate

将鼠标移到目标位置，记下输出的 [x, y]，写入 layout.json 对应 profile。
按 Ctrl+C 退出。
"""

from __future__ import annotations

import sys
import time

import pyautogui

pyautogui.FAILSAFE = True


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== VISION 坐标校准 ===")
    print("移动鼠标到目标位置，下方会实时刷新坐标。")
    print("FAILSAFE: 鼠标移到屏幕左上角可紧急中止。")
    print("按 Ctrl+C 退出。\n")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\r当前坐标: [{x}, {y}]   ", end="", flush=True)
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n已退出。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
