#!/usr/bin/env python3
"""
轨道 B：AI 视觉外挂流（集换社 / 闲鱼小程序）

流程（Phase 1 占位）：
  1. PyAutoGUI 打开微信 PC 端 → 进入小程序
  2. 输入 searchKeyword 搜索
  3. 截图 → Gemini 1.5 Flash 提取 minFloorPrice / lastSoldPrice
  4. stdout 输出 JSON 供 Node 调度器读取

用法：
  python main.py --target-id <uuid> --keyword "日版奇树 SAR" --name "奇树SAR"
"""

from __future__ import annotations

import argparse
import json
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EveryAsset VISION track")
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(
        f"[vision] 占位模式 — {args.name} / 搜索词: {args.keyword}",
        file=sys.stderr,
    )
    print(
        "[vision] 待实现: PyAutoGUI 打开集换社小程序 → 截图 → Gemini 读价",
        file=sys.stderr,
    )
    # Node 调度器读取 stdout 最后一行 JSON；null 表示本轮无数据
    print("null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
