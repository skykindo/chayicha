"""VISION 识图统一入口：按 visionProvider 路由 Gemini / 豆包 / DeepSeek。"""

from __future__ import annotations

from pathlib import Path

from config import VisionConfig
from vision_prompts import verify_card_name

__all__ = [
    "parse_auction_scroll",
    "parse_card_label",
    "parse_detail_entry",
    "parse_screenshot",
    "parse_wishlist_list",
    "verify_card_name",
]


def _provider(cfg: VisionConfig) -> str:
    return (cfg.vision_provider or "gemini").strip().lower()


def _vision_client(cfg: VisionConfig):
    provider = _provider(cfg)
    if provider == "deepseek":
        import deepseek_client

        return deepseek_client
    if provider == "doubao":
        import doubao_client

        return doubao_client
    import gemini_client

    return gemini_client


def _mock_detail_entry() -> tuple[str | None, str | None, str | None, list[dict]]:
    return "M2a", "234/193", "皮卡丘ex", [
        {"price": 520.0, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "最低价"},
        {"price": 680.0, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "集换价"},
    ]


def _mock_auction_scroll() -> list[dict]:
    return [
        {"price": 1918.6, "tradeType": "FLOOR", "cardCondition": "PSA10", "priceKind": "PSA一口价"},
        {"price": 3999.0, "tradeType": "FLOOR", "cardCondition": "CCIC10", "priceKind": "CCIC一口价"},
        {"price": None, "tradeType": "FLOOR", "cardCondition": "PSA10", "priceKind": "PSA集换价"},
        {"price": 4200.0, "tradeType": "FLOOR", "cardCondition": "CCIC10", "priceKind": "CCIC集换价"},
        {"price": 4000.0, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "成交价"},
        {"price": 3500.0, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "成交价"},
        {"price": 2800.0, "tradeType": "AUCTION", "cardCondition": "CCIC10", "priceKind": "成交价"},
    ]


def parse_screenshot(cfg: VisionConfig, image_path: Path, *, tab: str) -> list[dict]:
    if cfg.mock_vision:
        if tab == "floor":
            return [
                {"price": 520.0, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "最低价"},
                {"price": None, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "集换价"},
            ]
        if tab == "auction":
            return [
                {"price": 750.0, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "当前竞价"},
                {"price": None, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "成交价"},
            ]
        return [
            {"price": 520.0, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "最低价"},
            {"price": 680.0, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "集换价"},
            {"price": 750.0, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "当前竞价"},
            {"price": None, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "成交价"},
        ]

    return _vision_client(cfg).parse_screenshot(cfg, image_path, tab=tab)


def parse_detail_entry(
    cfg: VisionConfig, image_path: Path
) -> tuple[str | None, str | None, list[dict]]:
    if cfg.mock_vision:
        return _mock_detail_entry()

    return _vision_client(cfg).parse_detail_entry(cfg, image_path)


def parse_auction_scroll(cfg: VisionConfig, image_path: Path) -> list[dict]:
    if cfg.mock_vision:
        return _mock_auction_scroll()

    return _vision_client(cfg).parse_auction_scroll(cfg, image_path)


def parse_card_label(cfg: VisionConfig, image_path: Path) -> tuple[str | None, str | None]:
    if cfg.mock_vision:
        return "M2a", "234"

    return _vision_client(cfg).parse_card_label(cfg, image_path)


def parse_wishlist_list(cfg: VisionConfig, image_path: Path) -> list[dict]:
    if cfg.mock_vision:
        return [
            {"name": "闪耀鲤鱼王", "row": 0, "col": 0},
            {"name": "皮卡丘ex", "row": 1, "col": 1},
        ]

    return _vision_client(cfg).parse_wishlist_list(cfg, image_path)
