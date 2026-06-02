#!/usr/bin/env python3
"""
轨道 B：集换社 VISION 采集

独立运行：python apps/vision/main.py
配置上限：apps/vision/vision.config.json → maxLimit（默认 50）
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

from checkpoint import Checkpoint, Step
from config import load_config
from db import fetch_vision_channels, upsert_items_from_gemini
from gemini_client import parse_screenshot
from rpa import VisionRpa, load_layout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EveryAsset VISION track — 集换社")
    parser.add_argument(
        "--list",
        action="store_true",
        help="仅列出将处理的渠道（不执行 RPA）",
    )
    parser.add_argument(
        "--reset-checkpoint",
        action="store_true",
        help="清空 checkpoint.json 后从头开始",
    )
    return parser.parse_args()


def _safe_slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)[:80]


def process_channel(
    *,
    rpa: VisionRpa,
    cfg,
    channel,
    checkpoint: Checkpoint,
    screenshots_dir: Path,
) -> bool:
    ck_path = cfg.checkpoint_path
    asset_key = channel.asset_key
    step = checkpoint.start_card(asset_key, ck_path)

    slug = _safe_slug(asset_key)
    floor_path = screenshots_dir / f"{slug}_floor.png"
    auction_path = screenshots_dir / f"{slug}_auction.png"

    if not channel.series or not channel.card_number:
        print(f"[vision] 跳过 {asset_key}：缺少 series 或 cardNumber", file=sys.stderr)
        checkpoint.finish_card(asset_key, ck_path, success=False)
        return False

    try:
        rpa.prepare_window()

        if checkpoint.should_run_step("box_search"):
            print(f"[vision] {channel.name} — 搜卡盒 {channel.series}")
            rpa.search_box(channel.series)
            checkpoint.advance("pick_series", ck_path)

        if checkpoint.should_run_step("pick_series"):
            print(f"[vision] {channel.name} — 点系列筛选")
            rpa.pick_series()
            checkpoint.advance("enter_box", ck_path)

        if checkpoint.should_run_step("enter_box"):
            rpa.enter_box()
            checkpoint.advance("number_search", ck_path)

        if checkpoint.should_run_step("number_search"):
            print(f"[vision] {channel.name} — 搜编号 {channel.card_number}")
            rpa.search_number(channel.card_number)
            checkpoint.advance("enter_card", ck_path)

        if checkpoint.should_run_step("enter_card"):
            rpa.enter_card()
            checkpoint.advance("shot_floor", ck_path)

        if checkpoint.should_run_step("shot_floor"):
            rpa.shot_floor_tab(floor_path)
            checkpoint.floor_screenshot = str(floor_path)
            checkpoint.advance("shot_auction", ck_path)

        if checkpoint.should_run_step("shot_auction"):
            rpa.shot_auction_tab(auction_path)
            checkpoint.auction_screenshot = str(auction_path)
            checkpoint.advance("db_write", ck_path)

        if checkpoint.should_run_step("db_write"):
            print(f"[vision] {channel.name} — Gemini 解析截图 …")
            floor_items = parse_screenshot(cfg, floor_path, tab="floor")
            auction_items = parse_screenshot(cfg, auction_path, tab="auction")
            all_items = floor_items + auction_items
            written = upsert_items_from_gemini(
                cfg,
                asset_key=asset_key,
                platform=channel.platform,
                items=all_items,
            )
            print(f"[vision] {channel.name} — 入库 {written} 条")
            checkpoint.advance("done", ck_path)

        checkpoint.finish_card(asset_key, ck_path, success=True)
        return True

    except Exception as exc:
        print(f"[vision] {channel.name} 失败 @ {checkpoint.current_step}: {exc}", file=sys.stderr)
        checkpoint.fail_count += 1
        checkpoint.save(ck_path)
        return False


def main() -> int:
    args = parse_args()
    cfg = load_config()

    if args.reset_checkpoint and cfg.checkpoint_path.is_file():
        cfg.checkpoint_path.unlink()
        print("[vision] 已清空 checkpoint")

    channels = fetch_vision_channels(cfg)
    total_in_db = len(channels)

    print(
        f"[vision] 配置 maxLimit={cfg.max_limit}，"
        f"platform={cfg.platform}，trackType={cfg.track_type}"
    )
    print(f"[vision] 待处理渠道 {total_in_db} 条（已按 createdAt ASC 截断）")

    if args.list:
        for i, ch in enumerate(channels, 1):
            print(f"  {i:2}. {ch.asset_key} | {ch.series} / {ch.card_number} | {ch.name}")
        return 0

    if not channels:
        print("[vision] 无 VISION 渠道，请在 AssetChannel 中配置后重试。", file=sys.stderr)
        return 1

    layout = load_layout(cfg.layout_path)
    rpa = VisionRpa(cfg, layout)
    checkpoint = Checkpoint.load(cfg.checkpoint_path)
    cfg.screenshots_dir.mkdir(parents=True, exist_ok=True)

    pending = [ch for ch in channels if not checkpoint.should_skip(ch.asset_key)]
    print(f"[vision] 本轮执行 {len(pending)} 张（已完成 {len(checkpoint.completed_asset_keys)} 张）")

    for ch in pending:
        ok = process_channel(
            rpa=rpa,
            cfg=cfg,
            channel=ch,
            checkpoint=checkpoint,
            screenshots_dir=cfg.screenshots_dir,
        )
        if ok and not cfg.mock_rpa:
            delay = random.randint(
                cfg.sleep_after_card_min_sec,
                cfg.sleep_after_card_max_sec,
            )
            print(f"[vision] 休眠 {delay}s …")
            time.sleep(delay)

    print(
        f"[vision] 完成 — 成功 {checkpoint.success_count}，"
        f"失败 {checkpoint.fail_count}，"
        f"累计完成 {len(checkpoint.completed_asset_keys)} 张"
    )
    return 0 if checkpoint.fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
