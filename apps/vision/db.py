"""PostgreSQL：读取 VISION 渠道、upsert PriceStream。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

from config import VisionConfig

# Gemini priceKind → PriceStream.info（与策划案 6.4 一致）
PRICE_KIND_TO_INFO: dict[str, str] = {
    "最低价": "[VISION] 一口价-最低价",
    "集换价": "[VISION] 一口价-集换价",
    "当前竞价": "[VISION] 竞价-当前价",
    "成交价": "[VISION] 竞价-成交价",
}

EXPECTED_BY_KIND: dict[str, tuple[str, str]] = {
    "最低价": ("FLOOR", "RAW"),
    "集换价": ("FLOOR", "PSA10"),
    "当前竞价": ("AUCTION", "PSA10"),
    "成交价": ("AUCTION", "PSA10"),
}


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
    captured_at: datetime | None = None,
) -> None:
    captured_at = captured_at or datetime.now(timezone.utc)
    captured_date = to_captured_date(captured_at)

    sql = """
        INSERT INTO "PriceStream" (
            "assetKey", platform, "tradeType", "cardCondition",
            price, info, "capturedAt", "capturedDate"
        ) VALUES (
            %s, %s::"Platform", %s, %s,
            %s, %s, %s, %s
        )
        ON CONFLICT (
            "assetKey", platform, "tradeType", price,
            "capturedDate", "cardCondition", info
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
    written = 0
    for raw in items:
        normalized = normalize_item(raw)
        if not normalized:
            continue
        upsert_price_stream(
            cfg,
            asset_key=asset_key,
            platform=platform,
            trade_type=normalized["trade_type"],
            card_condition=normalized["card_condition"],
            price=normalized["price"],
            info=normalized["info"],
            captured_at=captured_at,
        )
        written += 1
    return written
