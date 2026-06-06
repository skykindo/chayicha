"""心愿单整页扫描：逐格进详情读编号匹配渠道（不依赖 gridSlot 顺序）。"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

from channel_matcher import find_channel_by_label, verify_channel_label
from checkpoint import Checkpoint
from config import VisionConfig
from db import VisionChannel, upsert_items_from_gemini
from vision_client import parse_auction_scroll, parse_detail_entry, verify_card_name
from layout_regions import cells_for_scan_page
from rpa import VisionRpa

# 详情首屏识图结果缓存，避免 db_write 对同一张图重复请求 Gemini
_detail_items_cache: dict[str, list[dict]] = {}


def _cache_detail_items(path: Path, items: list[dict]) -> None:
    _detail_items_cache[str(path.resolve())] = items


def _pop_detail_items(path: Path) -> list[dict] | None:
    return _detail_items_cache.pop(str(path.resolve()), None)


def process_wishlist_collect(
    *,
    rpa: VisionRpa,
    cfg: VisionConfig,
    channel: VisionChannel,
    checkpoint: Checkpoint,
    screenshots_dir: Path,
    slug: str,
) -> None:
    ck_path = cfg.checkpoint_path
    asset_key = channel.asset_key
    auction_path = screenshots_dir / f"{slug}_auction_scroll.png"
    detail_path = (
        Path(checkpoint.product_label_screenshot)
        if checkpoint.product_label_screenshot
        else None
    )

    if checkpoint.should_run_step("tap_auction", cfg.navigation_mode):
        print(f"[vision] {channel.name} — 点竞价")
        rpa.tap_auction()
        checkpoint.advance("tap_recent_deals", ck_path)

    if checkpoint.should_run_step("tap_recent_deals", cfg.navigation_mode):
        print(f"[vision] {channel.name} — 点最近成交")
        rpa.tap_recent_deals()
        checkpoint.advance("scroll_auction_list", ck_path)

    if checkpoint.should_run_step("scroll_auction_list", cfg.navigation_mode):
        steps = abs(cfg.auction_scroll_clicks)
        per = abs(cfg.auction_scroll_clicks_per_step)
        print(
            f"[vision] {channel.name} — 竞价列表下滚 {steps} 次（每次 {per} 格）",
            flush=True,
        )
        rpa.scroll_auction_list()
        checkpoint.advance("shot_auction_price", ck_path)

    if checkpoint.should_run_step("shot_auction_price", cfg.navigation_mode):
        print(f"[vision] {channel.name} — 截竞价下滚后价格区")
        rpa.shot_auction_price(auction_path)
        checkpoint.product_screenshot = str(auction_path)
        checkpoint.advance("back_to_grid", ck_path)

    if checkpoint.should_run_step("back_to_grid", cfg.navigation_mode):
        print(f"[vision] {channel.name} — 返回心愿单（{cfg.wishlist_back_clicks} 次）")
        rpa.back_to_wishlist_grid()
        checkpoint.advance("db_write", ck_path)

    if checkpoint.should_run_step("db_write", cfg.navigation_mode):
        print(f"[vision] {channel.name} — Gemini 解析双截图 …")
        detail_items: list[dict] = []
        if detail_path and detail_path.is_file():
            cached = _pop_detail_items(detail_path)
            if cached is not None:
                detail_items = cached
            else:
                _, _, _, detail_items = parse_detail_entry(cfg, detail_path)
        auction_items = (
            parse_auction_scroll(cfg, auction_path)
            if auction_path.is_file()
            else []
        )
        all_items = detail_items + auction_items
        if cfg.navigation_mode != "wishlist_page_scan":
            parsed_name = None
            for item in detail_items:
                if item.get("cardName"):
                    parsed_name = str(item["cardName"])
                    break
            verify_card_name(channel.name, parsed_name)
        written = upsert_items_from_gemini(
            cfg,
            asset_key=asset_key,
            platform=channel.platform,
            items=all_items,
        )
        print(f"[vision] {channel.name} — 入库 {written} 条")
        checkpoint.advance("done", ck_path)

    checkpoint.finish_card(asset_key, ck_path, success=True)


def process_wishlist_detail(
    *,
    rpa: VisionRpa,
    cfg: VisionConfig,
    channel: VisionChannel,
    checkpoint: Checkpoint,
    screenshots_dir: Path,
    slug: str,
) -> bool:
    ck_path = cfg.checkpoint_path
    detail_path = screenshots_dir / f"{slug}_detail_entry.png"

    if checkpoint.should_run_step("shot_detail_entry", cfg.navigation_mode):
        print(f"[vision] {channel.name} — 截详情首屏（set/编号+一口价）")
        rpa.shot_detail_entry(detail_path)
        checkpoint.product_label_screenshot = str(detail_path)
        series, card_number, card_name, items = parse_detail_entry(cfg, detail_path)
        _cache_detail_items(detail_path, items)
        verify_channel_label(channel, series=series, card_number=card_number)
        verify_card_name(channel.name, card_name)
        checkpoint.advance("tap_card_info", ck_path)

    if checkpoint.should_run_step("tap_card_info", cfg.navigation_mode):
        print(f"[vision] {channel.name} — 点卡牌信息")
        rpa.tap_card_info()
        checkpoint.advance("tap_product", ck_path)

    if checkpoint.should_run_step("tap_product", cfg.navigation_mode):
        print(f"[vision] {channel.name} — 点商品")
        rpa.tap_product()
        checkpoint.advance("tap_auction", ck_path)

    process_wishlist_collect(
        rpa=rpa,
        cfg=cfg,
        channel=channel,
        checkpoint=checkpoint,
        screenshots_dir=screenshots_dir,
        slug=slug,
    )
    return True


def _scan_cell_detail(
    *,
    rpa: VisionRpa,
    cfg: VisionConfig,
    detail_path: Path,
) -> tuple[str | None, str | None, str | None]:
    rpa.shot_detail_entry(detail_path)
    series, card_number, card_name, items = parse_detail_entry(cfg, detail_path)
    _cache_detail_items(detail_path, items)
    return series, card_number, card_name


def _safe_slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)[:80]


def _sleep_between_cards(cfg: VisionConfig) -> None:
    if cfg.mock_rpa:
        return
    delay = random.randint(cfg.sleep_after_card_min_sec, cfg.sleep_after_card_max_sec)
    print(f"[vision] 休眠 {delay}s …")
    time.sleep(delay)


def _ensure_focus(rpa: VisionRpa) -> None:
    rpa.ensure_focus()


def _scroll_to_top_once(rpa: VisionRpa, checkpoint: Checkpoint, ck_path: Path) -> None:
    """仅本轮首次进入第 1 页时滚到顶部；翻页后不再回顶。"""
    if checkpoint.scan_page != 1 or checkpoint.scrolled_to_top:
        return
    print("[vision] 心愿单滚到顶部（仅一次）…", flush=True)
    rpa.scroll_wishlist_page_to_top()
    checkpoint.scrolled_to_top = True
    checkpoint.save(ck_path)


def _resume_incomplete_card(
    *,
    rpa: VisionRpa,
    cfg: VisionConfig,
    channel: VisionChannel,
    checkpoint: Checkpoint,
    screenshots_dir: Path,
    cell_no: int,
) -> None:
    slug = _safe_slug(channel.asset_key)
    print(
        f"[vision] 格{cell_no:02d} 续跑 {channel.name} @ {checkpoint.current_step}",
        flush=True,
    )
    if checkpoint.should_run_step(
        "shot_detail_entry", cfg.navigation_mode
    ) or checkpoint.should_run_step(
        "tap_card_info", cfg.navigation_mode
    ) or checkpoint.should_run_step("tap_product", cfg.navigation_mode):
        process_wishlist_detail(
            rpa=rpa,
            cfg=cfg,
            channel=channel,
            checkpoint=checkpoint,
            screenshots_dir=screenshots_dir,
            slug=slug,
        )
    else:
        process_wishlist_collect(
            rpa=rpa,
            cfg=cfg,
            channel=channel,
            checkpoint=checkpoint,
            screenshots_dir=screenshots_dir,
            slug=slug,
        )


def run_wishlist_page_scan(
    *,
    rpa: VisionRpa,
    cfg: VisionConfig,
    channels: list[VisionChannel],
    checkpoint: Checkpoint,
    screenshots_dir: Path,
) -> bool:
    ck_path = cfg.checkpoint_path
    channels_by_key = {ch.asset_key: ch for ch in channels}
    pending = [ch for ch in channels if not checkpoint.should_skip(ch.asset_key)]

    if not pending and not checkpoint.current_asset_key:
        print("[vision] 全部渠道已完成，无需扫描。")
        return True

    try:
        rpa.prepare_window()
        _scroll_to_top_once(rpa, checkpoint, ck_path)

        max_pages = max(1, cfg.wishlist_max_scroll_pages)
        total_channels = len(channels)

        print(
            f"[vision] 编号匹配扫描：点格进详情首屏识 set/编号，"
            f"不依赖 gridSlot；待处理 {len(pending)} 张",
            flush=True,
        )

        while pending and checkpoint.scan_page <= max_pages:
            cells = cells_for_scan_page(
                rpa.layout_data,
                page_no=checkpoint.scan_page,
                channel_count=total_channels,
            )
            start = min(checkpoint.scan_cell_index, len(cells))
            if start >= len(cells):
                start = 0

            print(
                f"[vision] 第 {checkpoint.scan_page} 页：扫 {len(cells)} 格，"
                f"从格 {start + 1} 开始",
                flush=True,
            )

            for cell_i in range(start, len(cells)):
                checkpoint.scan_cell_index = cell_i
                checkpoint.save(ck_path)

                row, col, _idx = cells[cell_i]
                cell_no = cell_i + 1

                if checkpoint.current_asset_key:
                    ch = channels_by_key.get(checkpoint.current_asset_key)
                    if not ch:
                        raise RuntimeError(
                            f"断点 currentAssetKey={checkpoint.current_asset_key} 无效"
                        )
                    _resume_incomplete_card(
                        rpa=rpa,
                        cfg=cfg,
                        channel=ch,
                        checkpoint=checkpoint,
                        screenshots_dir=screenshots_dir,
                        cell_no=cell_no,
                    )
                    pending = [c for c in pending if c.asset_key != ch.asset_key]
                    checkpoint.scan_cell_index = cell_i + 1
                    checkpoint.save(ck_path)
                    _sleep_between_cards(cfg)
                    if not pending:
                        break
                    continue

                _ensure_focus(rpa)

                print(
                    f"[vision] 格{cell_no:02d} (row={row}, col={col}) — 点进详情 …",
                    flush=True,
                )
                rpa.click_page_cell(col, row)
                detail_path = (
                    screenshots_dir
                    / f"scan_p{checkpoint.scan_page:02d}_c{cell_no:02d}_detail_entry.png"
                )
                series, card_number, card_name = _scan_cell_detail(
                    rpa=rpa, cfg=cfg, detail_path=detail_path
                )
                channel = find_channel_by_label(
                    pending, series=series, card_number=card_number
                )

                if channel is None:
                    if series or card_number:
                        print(
                            f"[vision]   格{cell_no:02d} 未匹配待采: {series}/{card_number}",
                            flush=True,
                        )
                    else:
                        print(
                            f"[vision]   格{cell_no:02d} 编号未识别，跳过",
                            flush=True,
                        )
                    rpa.back_to_wishlist_grid()
                    checkpoint.scan_cell_index = cell_i + 1
                    checkpoint.save(ck_path)
                    continue

                print(
                    f"[vision]   格{cell_no:02d} 命中 {channel.name} "
                    f"({channel.series}/{channel.card_number})",
                    flush=True,
                )
                verify_channel_label(
                    channel, series=series, card_number=card_number
                )
                verify_card_name(channel.name, card_name)
                slug = _safe_slug(channel.asset_key)
                checkpoint.start_card(
                    channel.asset_key, ck_path, navigation_mode=cfg.navigation_mode
                )
                checkpoint.product_label_screenshot = str(detail_path)
                checkpoint.advance("tap_card_info", ck_path)
                process_wishlist_detail(
                    rpa=rpa,
                    cfg=cfg,
                    channel=channel,
                    checkpoint=checkpoint,
                    screenshots_dir=screenshots_dir,
                    slug=slug,
                )
                pending = [c for c in pending if c.asset_key != channel.asset_key]
                checkpoint.scan_cell_index = cell_i + 1
                checkpoint.save(ck_path)
                _sleep_between_cards(cfg)
                if not pending:
                    break

            if not pending:
                break

            if checkpoint.scan_page >= max_pages:
                print(
                    f"[vision] 已达最大页数 {max_pages}，仍有 {len(pending)} 张未找到",
                    file=sys.stderr,
                )
                break

            print(f"[vision] 第 {checkpoint.scan_page} 页扫完，下翻一整页 …")
            if not rpa.scroll_wishlist_page_down():
                print(
                    f"[vision] 心愿单无法下翻，仍有 {len(pending)} 张未找到",
                    file=sys.stderr,
                )
                break
            checkpoint.scan_page += 1
            checkpoint.scan_cell_index = 0
            checkpoint.scrolled_to_top = False
            checkpoint.save(ck_path)
            _ensure_focus(rpa)

        if pending:
            names = "、".join(ch.name for ch in pending)
            print(f"[vision] 未扫描到的渠道: {names}", file=sys.stderr)
            return False

        return True

    except Exception as exc:
        step = checkpoint.current_step or "scan"
        name = checkpoint.current_asset_key or "?"
        print(f"[vision] 整页扫描失败 @ {name} / {step}: {exc}", file=sys.stderr)
        checkpoint.fail_count += 1
        checkpoint.save(ck_path)
        if not cfg.mock_rpa:
            print(
                "[vision] 请手动回到心愿单后重跑 npm run vision",
                file=sys.stderr,
            )
        return False
