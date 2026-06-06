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

from checkpoint import Checkpoint
from config import load_config, validate_vision_backend
from db import fetch_vision_channels, upsert_items_from_gemini
from vision_client import parse_screenshot
from rpa import VisionRpa, load_layout, load_layout_data
from wishlist_page_scan import process_wishlist_detail, run_wishlist_page_scan
from wishlist_slots import load_grid_slot_map


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


def process_channel_search(
    *,
    rpa: VisionRpa,
    cfg,
    channel,
    checkpoint: Checkpoint,
    screenshots_dir: Path,
) -> bool:
    ck_path = cfg.checkpoint_path
    asset_key = channel.asset_key
    checkpoint.start_card(asset_key, ck_path, navigation_mode=cfg.navigation_mode)

    slug = _safe_slug(asset_key)
    floor_path = screenshots_dir / f"{slug}_floor.png"
    auction_path = screenshots_dir / f"{slug}_auction.png"

    if not channel.series or not channel.card_number:
        print(f"[vision] 跳过 {asset_key}：缺少 series 或 cardNumber", file=sys.stderr)
        checkpoint.finish_card(asset_key, ck_path, success=False)
        return False

    try:
        rpa.prepare_window()

        if checkpoint.should_run_step("box_search", cfg.navigation_mode):
            print(f"[vision] {channel.name} — 搜卡盒 {channel.series}")
            rpa.search_box(channel.series)
            checkpoint.advance("pick_series", ck_path)

        if checkpoint.should_run_step("pick_series", cfg.navigation_mode):
            print(f"[vision] {channel.name} — 点系列筛选")
            rpa.pick_series()
            checkpoint.advance("enter_box", ck_path)

        if checkpoint.should_run_step("enter_box", cfg.navigation_mode):
            rpa.enter_box()
            checkpoint.advance("number_search", ck_path)

        if checkpoint.should_run_step("number_search", cfg.navigation_mode):
            print(f"[vision] {channel.name} — 搜编号 {channel.card_number}")
            rpa.search_number(channel.card_number)
            checkpoint.advance("enter_card", ck_path)

        if checkpoint.should_run_step("enter_card", cfg.navigation_mode):
            rpa.enter_card()
            checkpoint.advance("shot_floor", ck_path)

        if checkpoint.should_run_step("shot_floor", cfg.navigation_mode):
            rpa.shot_floor_tab(floor_path)
            checkpoint.floor_screenshot = str(floor_path)
            checkpoint.advance("shot_auction", ck_path)

        if checkpoint.should_run_step("shot_auction", cfg.navigation_mode):
            rpa.shot_auction_tab(auction_path)
            checkpoint.auction_screenshot = str(auction_path)
            checkpoint.advance("db_write", ck_path)

        if checkpoint.should_run_step("db_write", cfg.navigation_mode):
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


def process_channel_wishlist(
    *,
    rpa: VisionRpa,
    cfg,
    channel,
    checkpoint: Checkpoint,
    screenshots_dir: Path,
    grid_slot_index: int,
) -> bool:
    ck_path = cfg.checkpoint_path
    asset_key = channel.asset_key
    slot_key = f"grid_{grid_slot_index + 1:02d}"
    checkpoint.start_card(asset_key, ck_path, navigation_mode=cfg.navigation_mode)

    slug = _safe_slug(asset_key)

    try:
        rpa.prepare_window()

        if checkpoint.should_run_step("open_grid_card", cfg.navigation_mode):
            if cfg.navigation_mode == "wishlist_scroll":
                scan_path = screenshots_dir / f"{slug}_wishlist_scan.png"
                print(f"[vision] {channel.name} — 滑动心愿单识图找卡")
                rpa.open_card_on_wishlist(channel.name, scan_path)
            else:
                print(f"[vision] {channel.name} — 点格位 {slot_key}")
                rpa.open_grid_card(grid_slot_index)
            checkpoint.advance("shot_detail_entry", ck_path)

        process_wishlist_detail(
            rpa=rpa,
            cfg=cfg,
            channel=channel,
            checkpoint=checkpoint,
            screenshots_dir=screenshots_dir,
            slug=slug,
        )
        return True

    except Exception as exc:
        print(f"[vision] {channel.name} 失败 @ {checkpoint.current_step}: {exc}", file=sys.stderr)
        checkpoint.fail_count += 1
        checkpoint.save(ck_path)
        return False


def process_channel(
    *,
    rpa: VisionRpa,
    cfg,
    channel,
    checkpoint: Checkpoint,
    screenshots_dir: Path,
    grid_slot_index: int,
) -> bool:
    if cfg.navigation_mode in ("wishlist", "wishlist_scroll"):
        return process_channel_wishlist(
            rpa=rpa,
            cfg=cfg,
            channel=channel,
            checkpoint=checkpoint,
            screenshots_dir=screenshots_dir,
            grid_slot_index=grid_slot_index,
        )
    return process_channel_search(
        rpa=rpa,
        cfg=cfg,
        channel=channel,
        checkpoint=checkpoint,
        screenshots_dir=screenshots_dir,
    )


def main() -> int:
    args = parse_args()
    cfg = load_config()
    try:
        validate_vision_backend(cfg)
    except RuntimeError as exc:
        print(f"[vision] {exc}", file=sys.stderr)
        return 1

    if args.reset_checkpoint and cfg.checkpoint_path.is_file():
        cfg.checkpoint_path.unlink()
        print("[vision] 已清空 checkpoint")

    channels = fetch_vision_channels(cfg)
    total_in_db = len(channels)

    if cfg.vision_provider == "deepseek":
        model_label = f"{cfg.vision_provider}/{cfg.deepseek_model}"
    elif cfg.vision_provider == "doubao":
        model_label = f"{cfg.vision_provider}/{cfg.doubao_model}"
    else:
        model_label = f"{cfg.vision_provider}/{cfg.gemini_model}"
    print(
        f"[vision] 配置 maxLimit={cfg.max_limit}，"
        f"platform={cfg.platform}，trackType={cfg.track_type}，"
        f"navigationMode={cfg.navigation_mode}，识图={model_label}"
    )
    if cfg.navigation_mode in ("wishlist", "wishlist_scroll", "wishlist_page_scan"):
        print(
            f"[vision] 等待：心愿单每步 {cfg.wishlist_page_wait_sec}s，"
            f"截图前 {cfg.screenshot_wait_sec}s，点击间隔 {cfg.click_pause_sec}s"
        )
    print(f"[vision] 待处理渠道 {total_in_db} 条（已按 createdAt ASC 截断）")

    grid_slot_map: dict[str, int] = {}
    if cfg.navigation_mode == "wishlist":
        try:
            grid_slot_map = load_grid_slot_map()
        except (FileNotFoundError, ValueError) as exc:
            print(f"[vision] {exc}", file=sys.stderr)
            return 1
        print(
            f"[vision] 心愿单·固定格位：gridSlot 1～12 对应 layout grid_01～12（不滑动）"
        )
        if total_in_db > cfg.wishlist_grid_slots:
            print(
                f"[vision] 警告：渠道 {total_in_db} 条超过格位 {cfg.wishlist_grid_slots}",
                file=sys.stderr,
            )
    elif cfg.navigation_mode == "wishlist_scroll":
        print(
            f"[vision] 心愿单·滑动识名：按渠道 name 在列表中查找，"
            f"最多滑 {cfg.wishlist_max_scroll_pages} 屏；无需 gridSlot"
        )
    elif cfg.navigation_mode == "wishlist_page_scan":
        print(
            f"[vision] 心愿单·编号匹配扫描：逐格进商品读 set/编号，不依赖 gridSlot 顺序"
        )

    if args.list:
        for i, ch in enumerate(channels, 1):
            if cfg.navigation_mode == "wishlist":
                idx = grid_slot_map.get(ch.asset_key)
                slot = f"grid_{idx + 1:02d}" if idx is not None else "?"
            elif cfg.navigation_mode == "wishlist_scroll":
                slot = "scroll"
            elif cfg.navigation_mode == "wishlist_page_scan":
                slot = "scan"
            else:
                slot = "-"
            extra = ""
            if cfg.navigation_mode in ("search", "wishlist_page_scan"):
                extra = f"{ch.series} / {ch.card_number} | "
            print(f"  {i:2}. {slot} | {ch.asset_key} | {extra}{ch.name}")
        return 0

    if not channels:
        print("[vision] 无 VISION 渠道，请在 AssetChannel 中配置后重试。", file=sys.stderr)
        return 1

    profile = cfg.layout_profile
    layout = load_layout(cfg.layout_path, profile)
    layout_data = load_layout_data(cfg.layout_path, profile)
    print(f"[vision] 坐标配置 profile={profile}", flush=True)
    rpa = VisionRpa(cfg, layout, layout_data)
    checkpoint = Checkpoint.load(cfg.checkpoint_path)
    cfg.screenshots_dir.mkdir(parents=True, exist_ok=True)

    pending = [ch for ch in channels if not checkpoint.should_skip(ch.asset_key)]
    print(f"[vision] 本轮执行 {len(pending)} 张（已完成 {len(checkpoint.completed_asset_keys)} 张）")

    if cfg.navigation_mode == "wishlist_page_scan":
        ok = run_wishlist_page_scan(
            rpa=rpa,
            cfg=cfg,
            channels=channels,
            checkpoint=checkpoint,
            screenshots_dir=cfg.screenshots_dir,
        )
        print(
            f"[vision] 完成 — 成功 {checkpoint.success_count}，"
            f"失败 {checkpoint.fail_count}，"
            f"累计完成 {len(checkpoint.completed_asset_keys)} 张"
        )
        return 0 if ok and checkpoint.fail_count == 0 else 2

    for ch in pending:
        if cfg.navigation_mode == "wishlist":
            if ch.asset_key not in grid_slot_map:
                print(
                    f"[vision] 跳过 {ch.asset_key}：CSV 中无 gridSlot",
                    file=sys.stderr,
                )
                continue
            grid_index = grid_slot_map[ch.asset_key]
        else:
            grid_index = 0

        if cfg.navigation_mode == "wishlist" and grid_index >= cfg.wishlist_grid_slots:
            print(
                f"[vision] 跳过 {ch.asset_key}：超出心愿单格位上限",
                file=sys.stderr,
            )
            continue

        ok = process_channel(
            rpa=rpa,
            cfg=cfg,
            channel=ch,
            checkpoint=checkpoint,
            screenshots_dir=cfg.screenshots_dir,
            grid_slot_index=grid_index,
        )
        if not ok:
            if cfg.navigation_mode in (
                "wishlist",
                "wishlist_scroll",
                "wishlist_page_scan",
            ) and not cfg.mock_rpa:
                print(
                    "[vision] 心愿单模式：本张失败后停止，请手动回到心愿单再重跑 npm run vision",
                    file=sys.stderr,
                )
            break
        if not cfg.mock_rpa:
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
