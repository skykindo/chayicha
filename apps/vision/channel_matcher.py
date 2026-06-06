"""渠道 series / cardNumber 与 Gemini 识别结果比对。"""

from __future__ import annotations

import re

from db import VisionChannel


def _norm_token(value: str) -> str:
    s = re.sub(r"\s+", "", (value or "").strip()).upper()
    s = s.replace("／", "/").replace("－", "-").replace("—", "-")
    return s


def _norm_card_number(value: str) -> str:
    s = _norm_token(value)
    s = re.sub(r"[^A-Z0-9/\-]", "", s)
    return s


def _number_parts(value: str) -> tuple[str, str | None]:
    """
    拆分卡牌编号。如 007/025、240/193-SAR → 主编号 + 集内总数。
    只取数字段，忽略 SAR 等稀有度后缀（避免 240/193-SAR 误当成 240/SAR）。
    """
    s = _norm_card_number(value)
    if not s:
        return "", None
    numeric = [p for p in re.split(r"[/\-]", s) if p.isdigit()]
    if not numeric:
        return "", None
    if len(numeric) == 1:
        return numeric[0], None
    return numeric[0], numeric[1]


def _cmp_part(a: str, b: str) -> bool:
    if a == b:
        return True
    if a.isdigit() and b.isdigit():
        return int(a) == int(b)
    return False


def _numbers_match(expected: str, detected: str) -> bool:
    exp = _norm_card_number(expected)
    det = _norm_card_number(detected)
    if not exp or not det:
        return False
    if exp == det:
        return True

    exp_pri, exp_sec = _number_parts(expected)
    det_pri, det_sec = _number_parts(detected)
    if not exp_pri or not det_pri:
        return False

    if not _cmp_part(exp_pri, det_pri):
        return False

    if exp_sec and det_sec and not _cmp_part(exp_sec, det_sec):
        return False

    # 同系列多卡（如 M2a 234/240/246）时，识别结果必须含完整分数，避免只读到 "240" 就匹配
    if exp_sec and not det_sec:
        return False

    return True


def _series_match(expected: str, detected: str) -> bool:
    exp = _norm_token(expected)
    det = _norm_token(detected)
    if not exp or not det:
        return False
    if exp == det:
        return True
    return exp in det or det in exp


def label_matches_channel(
    channel: VisionChannel,
    *,
    series: str | None,
    card_number: str | None,
) -> bool:
    if not series or not card_number:
        return False
    return _series_match(channel.series, str(series)) and _numbers_match(
        channel.card_number, str(card_number)
    )


def find_channel_by_label(
    channels: list[VisionChannel],
    *,
    series: str | None,
    card_number: str | None,
) -> VisionChannel | None:
    if not series or not card_number:
        return None
    hits = [
        ch
        for ch in channels
        if label_matches_channel(ch, series=series, card_number=card_number)
    ]
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]

    det_full = _norm_card_number(str(card_number))
    exact = [ch for ch in hits if _norm_card_number(ch.card_number) == det_full]
    if len(exact) == 1:
        return exact[0]

    keys = ", ".join(h.asset_key for h in hits)
    raise RuntimeError(
        f"编号 {series}/{card_number} 匹配到多条渠道: {keys}，请检查 DB 配置。"
    )


def verify_channel_label(
    channel: VisionChannel,
    *,
    series: str | None,
    card_number: str | None,
) -> None:
    """商品页编号区识别结果须与 CSV 渠道一致，防止点错卡。"""
    if not series or not str(series).strip():
        raise RuntimeError(
            f"商品页未识别到 series，无法确认是否为「{channel.name}」。"
            f"请检查详情首屏 screenshotRegion 是否包含 set/编号。"
        )
    if not card_number or not str(card_number).strip():
        raise RuntimeError(
            f"商品页未识别到 cardNumber，无法确认是否为「{channel.name}」。"
        )
    if not _series_match(channel.series, str(series)):
        raise RuntimeError(
            f"series 与渠道不一致：CSV={channel.series!r}，截图识别={series!r}。"
            f"可能点错格位，请核对心愿单坐标。"
        )
    if not _numbers_match(channel.card_number, str(card_number)):
        raise RuntimeError(
            f"cardNumber 与渠道不一致：CSV={channel.card_number!r}，"
            f"截图识别={card_number!r}。可能点错格位。"
        )
    print(
        f"[vision] 编号校验通过: {series} / {card_number} ↔ {channel.series} / {channel.card_number}",
        flush=True,
    )
