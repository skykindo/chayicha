"""PostgreSQL：读取 VISION 渠道、upsert PriceStream。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

from config import VisionConfig

# Gemini priceKind → PriceStream.info
# 一口价 = 商家挂牌价；集换价 = 平台按近10单算的平均价（仅 RAW 详情页）
PRICE_KIND_TO_INFO: dict[str, str] = {
    "最低价": "[VISION] 一口价-最低价",
    "集换价": "[VISION] 集换价-RAW",
    "PSA一口价": "[VISION] 一口价-PSA10",
    "CCIC一口价": "[VISION] 一口价-CCIC金10",
    "PSA集换价": "[VISION] 集换价-PSA10",
    "CCIC集换价": "[VISION] 集换价-CCIC金10",
    "当前竞价": "[VISION] 竞价-当前价",
}

# 竞价成交价按评级分 info（priceKind 仍为「成交价」，靠 cardCondition 区分）
AUCTION_DEAL_INFO: dict[str, str] = {
    "PSA10": "[VISION] 竞价-成交价-PSA10",
    "CCIC10": "[VISION] 竞价-成交价-CCIC金10",
    "RAW": "[VISION] 竞价-成交价-裸卡",
}

VISION_INFO_LABELS: tuple[str, ...] = tuple(PRICE_KIND_TO_INFO.values()) + tuple(
    AUCTION_DEAL_INFO.values()
)

# 历史误写 info → 标准 info（仅文档/迁移参考；重采前建议 delete-all）
LEGACY_VISION_INFO: dict[str, str] = {
    "[VISION] 一口价-拍卖价": "[VISION] 集换价-RAW",
    "[VISION] 一口价-集换价": "[VISION] 集换价-RAW",
    "[VISION] 一口价-PSA集换价": "[VISION] 集换价-PSA10",
    "[VISION] 一口价-CCIC集换价": "[VISION] 集换价-CCIC金10",
    "[VISION] 竞价-成交价": "[VISION] 竞价-成交价-PSA10",
}

EXPECTED_BY_KIND: dict[str, tuple[str, str]] = {
    "最低价": ("FLOOR", "RAW"),
    "集换价": ("FLOOR", "RAW"),
    "PSA一口价": ("FLOOR", "PSA10"),
    "CCIC一口价": ("FLOOR", "CCIC10"),
    "PSA集换价": ("FLOOR", "PSA10"),
    "CCIC集换价": ("FLOOR", "CCIC10"),
    "当前竞价": ("AUCTION", "PSA10"),
}

GRADED_LISTING_KINDS = ("PSA一口价", "CCIC一口价")
GRADED_JIHUAN_KINDS = ("PSA集换价", "CCIC集换价")


GRADING_MARKERS: tuple[str, ...] = (
    "PSA",
    "CCIC",
    "BGS",
    "CGC",
    "ARS",
    "SGC",
    "HGA",
    "GMA",
    "PCG",
    "GBTC",
    "TAG",
    "金10",
    "银10",
    "金标",
    "银标",
)

OTHER_GRADERS: tuple[str, ...] = (
    "BGS",
    "CGC",
    "ARS",
    "SGC",
    "HGA",
    "GMA",
    "PCG",
    "GBTC",
    "TAG",
)


def _badge_text(item: dict) -> str:
    parts = [
        str(item.get("gradeBadge") or "").strip(),
        str(item.get("cardCondition") or "").strip(),
    ]
    return " ".join(p for p in parts if p)


def has_grading_marker(text: str | None) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    upper = raw.upper().replace(" ", "")
    return any(marker in upper or marker in raw for marker in GRADING_MARKERS)


def has_other_grader(text: str | None) -> bool:
    upper = str(text or "").upper().replace(" ", "")
    return any(grader in upper for grader in OTHER_GRADERS)


def is_ccic_silver(raw: str | None) -> bool:
    text = str(raw or "").strip()
    if not text:
        return False
    upper = text.upper().replace(" ", "")
    return (
        "银10" in text
        or "银标" in text
        or "银级" in text
        or "CCIC银" in upper
        or "CCIC-SILVER" in upper
        or "SILVER" in upper
        or ("银" in text and "CCIC" in upper)
        or ("银" in text and "金" not in text and "10" in text)
    )


def is_psa_badge(text: str | None) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    upper = raw.upper().replace(" ", "")
    if "CCIC" in upper or is_ccic_silver(raw) or has_other_grader(raw):
        return False
    if "裸" in raw or upper in ("RAW", "NONE", "UNGRADED"):
        return False
    return "PSA" in upper


def is_ccic_gold_badge(text: str | None) -> bool:
    raw = str(text or "").strip()
    if not raw or is_ccic_silver(raw) or has_other_grader(raw):
        return False
    upper = raw.upper().replace(" ", "")
    if "金10" in raw or "金标" in raw or "CCIC金" in upper:
        return True
    if "CCIC" in upper and "银" not in raw:
        return "10" in raw or upper.endswith("CCIC10") or "CCIC10" in upper
    return False


def is_raw_deal_badge(text: str | None) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return True
    if has_grading_marker(raw):
        return False
    upper = raw.upper().replace(" ", "")
    return upper in ("RAW", "NONE", "UNGRADED") or "裸" in raw


def resolve_auction_deal_condition(item: dict) -> str | None:
    """最近成交：以 gradeBadge 为准严格分桶，防止裸卡/他社/CCIC银10 混入。"""
    badge = str(item.get("gradeBadge") or "").strip()
    raw_cond = str(item.get("cardCondition") or "").strip()

    if is_ccic_silver(badge) or is_ccic_silver(raw_cond):
        return None
    if has_other_grader(badge) or has_other_grader(raw_cond):
        return None

    if badge:
        if is_ccic_gold_badge(badge):
            return "CCIC10"
        if is_psa_badge(badge):
            return "PSA10"
        if is_raw_deal_badge(badge):
            return "RAW"
        return None

    if is_ccic_gold_badge(raw_cond):
        return "CCIC10"
    if is_psa_badge(raw_cond):
        return "PSA10"
    if raw_cond.upper() in ("RAW", "NONE", "UNGRADED") or "裸" in raw_cond:
        return "RAW"
    return None


def normalize_card_condition(raw: str | None) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if is_ccic_silver(text):
        return None
    upper = text.upper().replace(" ", "")
    if "CCIC" in upper or "金10" in text or "金标" in text or "CCIC金" in upper:
        return "CCIC10"
    if upper in ("RAW", "NONE", "UNGRADED") or "裸" in text:
        return "RAW"
    if "PSA" in upper:
        return "PSA10"
    if upper in ("PSA10", "CCIC10", "RAW"):
        return upper
    return None


def _resolve_graded_kind(
    item: dict,
    *,
    allowed_kinds: tuple[str, ...],
    ccic_kind: str,
    psa_kind: str,
) -> tuple[str, str] | None:
    """竞价页评级区：按角标纠正 PSA/CCIC，银10 丢弃。"""
    price_kind = str(item.get("priceKind", "")).strip()
    if price_kind not in allowed_kinds:
        return None

    badge = _badge_text(item)
    if is_ccic_silver(badge):
        return None

    resolved = normalize_card_condition(badge)
    if resolved == "CCIC10":
        price_kind = ccic_kind
    elif resolved == "PSA10":
        price_kind = psa_kind
    elif price_kind == psa_kind and "CCIC" in badge.upper():
        price_kind = ccic_kind
        resolved = "CCIC10"
    elif price_kind == ccic_kind and "PSA" in badge.upper():
        price_kind = psa_kind
        resolved = "PSA10"
    elif resolved is None:
        _, expected_condition = EXPECTED_BY_KIND[price_kind]
        return price_kind, expected_condition
    elif resolved not in ("PSA10", "CCIC10"):
        return None

    _, expected_condition = EXPECTED_BY_KIND[price_kind]
    if resolved != expected_condition:
        price_kind = ccic_kind if resolved == "CCIC10" else psa_kind
    return price_kind, EXPECTED_BY_KIND[price_kind][1]


def is_valid_auction_deal(item: dict, card_condition: str) -> bool:
    badge = str(item.get("gradeBadge") or "").strip()
    raw_cond = str(item.get("cardCondition") or "").strip()

    if card_condition == "PSA10":
        if not badge:
            return False
        return is_psa_badge(badge) and not is_ccic_gold_badge(badge)

    if card_condition == "CCIC10":
        if not badge:
            return False
        return is_ccic_gold_badge(badge) and not is_psa_badge(badge)

    if card_condition == "RAW":
        if badge and not is_raw_deal_badge(badge):
            return False
        if has_grading_marker(raw_cond) and "裸" not in raw_cond:
            return False
        return True

    return False


@dataclass(frozen=True)
class VisionChannel:
    asset_key: str
    platform: str
    series: str
    card_number: str
    name: str
    search_keyword: str | None


def _connect(cfg: VisionConfig):
    if not cfg.direct_url:
        raise RuntimeError("缺少 DIRECT_URL，请在 monorepo 根目录 .env 中配置。")
    return psycopg2.connect(cfg.direct_url)


def fetch_vision_channels(cfg: VisionConfig) -> list[VisionChannel]:
    sql = """
        SELECT
            ac."assetKey" AS asset_key,
            ac.platform::text AS platform,
            sa.series,
            sa."cardNumber" AS card_number,
            sa.name,
            ac."searchKeyword" AS search_keyword
        FROM "AssetChannel" ac
        JOIN "StandardAsset" sa ON sa."assetKey" = ac."assetKey"
        WHERE ac."trackType" = %s
          AND ac.platform::text = %s
          AND sa."isMonitoring" = true
        ORDER BY ac."createdAt" ASC
        LIMIT %s
    """
    with _connect(cfg) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (cfg.track_type, cfg.platform, cfg.max_limit))
            rows = cur.fetchall()

    channels: list[VisionChannel] = []
    for row in rows:
        channels.append(
            VisionChannel(
                asset_key=row["asset_key"],
                platform=row["platform"],
                series=(row["series"] or "").strip(),
                card_number=(row["card_number"] or "").strip(),
                name=(row["name"] or "").strip(),
                search_keyword=(row["search_keyword"] or "").strip() or None,
            )
        )
    return channels


def to_captured_date(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def normalize_item(item: dict) -> dict | None:
    price = item.get("price")
    if price is None:
        return None
    try:
        price_f = float(price)
    except (TypeError, ValueError):
        return None
    if price_f <= 0:
        return None

    price_kind = str(item.get("priceKind", "")).strip()

    if price_kind == "成交价":
        card_condition = resolve_auction_deal_condition(item)
        if not card_condition or card_condition not in AUCTION_DEAL_INFO:
            return None
        if not is_valid_auction_deal(item, card_condition):
            return None
        return {
            "price": price_f,
            "trade_type": "AUCTION",
            "card_condition": card_condition,
            "info": AUCTION_DEAL_INFO[card_condition],
        }

    if price_kind in GRADED_LISTING_KINDS:
        graded = _resolve_graded_kind(
            item,
            allowed_kinds=GRADED_LISTING_KINDS,
            ccic_kind="CCIC一口价",
            psa_kind="PSA一口价",
        )
        if not graded:
            return None
        floor_kind, card_condition = graded
        return {
            "price": price_f,
            "trade_type": "FLOOR",
            "card_condition": card_condition,
            "info": PRICE_KIND_TO_INFO[floor_kind],
        }

    if price_kind in GRADED_JIHUAN_KINDS:
        graded = _resolve_graded_kind(
            item,
            allowed_kinds=GRADED_JIHUAN_KINDS,
            ccic_kind="CCIC集换价",
            psa_kind="PSA集换价",
        )
        if not graded:
            return None
        jihuan_kind, card_condition = graded
        return {
            "price": price_f,
            "trade_type": "FLOOR",
            "card_condition": card_condition,
            "info": PRICE_KIND_TO_INFO[jihuan_kind],
        }

    info = PRICE_KIND_TO_INFO.get(price_kind)
    if not info:
        return None

    expected_trade, expected_condition = EXPECTED_BY_KIND[price_kind]
    trade_type = str(item.get("tradeType", expected_trade)).upper()
    card_condition = str(item.get("cardCondition", expected_condition)).upper()

    if trade_type != expected_trade or card_condition != expected_condition:
        trade_type = expected_trade
        card_condition = expected_condition

    return {
        "price": price_f,
        "trade_type": trade_type,
        "card_condition": card_condition,
        "info": info,
    }


def upsert_price_stream(
    cfg: VisionConfig,
    *,
    asset_key: str,
    platform: str,
    trade_type: str,
    card_condition: str,
    price: float,
    info: str,
    deal_seq: int = 0,
    captured_at: datetime | None = None,
) -> None:
    captured_at = captured_at or datetime.now(timezone.utc)
    captured_date = to_captured_date(captured_at)

    sql = """
        INSERT INTO "PriceStream" (
            "assetKey", platform, "tradeType", "cardCondition",
            price, info, "dealSeq", "capturedAt", "capturedDate"
        ) VALUES (
            %s, %s::"Platform", %s, %s,
            %s, %s, %s, %s, %s
        )
        ON CONFLICT (
            "assetKey", platform, "tradeType", price,
            "capturedDate", "cardCondition", info, "dealSeq"
        )
        DO UPDATE SET
            "capturedAt" = EXCLUDED."capturedAt"
    """
    with _connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    asset_key,
                    platform,
                    trade_type,
                    card_condition,
                    price,
                    info,
                    deal_seq,
                    captured_at,
                    captured_date,
                ),
            )
        conn.commit()


def upsert_items_from_gemini(
    cfg: VisionConfig,
    *,
    asset_key: str,
    platform: str,
    items: list[dict],
    captured_at: datetime | None = None,
) -> int:
    auction_infos = set(AUCTION_DEAL_INFO.values())
    deal_counters: dict[tuple[str, str, float], int] = defaultdict(int)
    written = 0
    for raw in items:
        normalized = normalize_item(raw)
        if not normalized:
            continue
        deal_seq = 0
        if normalized["info"] in auction_infos:
            deal_key = (
                normalized["info"],
                normalized["card_condition"],
                normalized["price"],
            )
            deal_seq = deal_counters[deal_key]
            deal_counters[deal_key] += 1
        upsert_price_stream(
            cfg,
            asset_key=asset_key,
            platform=platform,
            trade_type=normalized["trade_type"],
            card_condition=normalized["card_condition"],
            price=normalized["price"],
            info=normalized["info"],
            deal_seq=deal_seq,
            captured_at=captured_at,
        )
        written += 1
    return written
