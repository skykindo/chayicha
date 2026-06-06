"""VISION 识图 Prompt 与 JSON 解析（Gemini / DeepSeek 共用）。"""

from __future__ import annotations

import json
import re

FLOOR_PROMPT = """你是集换社小程序「一口价」页签的价格识别助手。
请从截图中提取可见价格，只输出 JSON，不要 Markdown 代码块，不要解释。

输出格式：
{"items": [
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "最低价"},
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "集换价"}
]}

规则：
- **最低价** = 某位商家上架的一口价（RAW 裸卡挂牌价）
- **集换价** = 集换社平台标价，根据近10单成交均价算出，不是商家一口价；cardCondition 固定 RAW
- 找不到对应价格时 price 为 null
- 不要猜测；看不清就 null
- priceKind 只能是「最低价」或「集换价」
"""

PRODUCT_PROMPT = """你是集换社「商品」页的价格识别助手（可能同时含一口价与竞价信息）。
请从截图中提取卡牌名称与可见价格，只输出 JSON，不要 Markdown 代码块，不要解释。

输出格式：
{"cardName": "截图中卡牌中文名或null",
 "items": [
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "最低价"},
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "集换价"},
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "当前竞价"},
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "成交价"}
]}

规则：
- cardName 为页面上卡牌主标题，看不清填 null
- 找不到对应价格时 price 为 null
- 不要猜测；看不清就 null
- priceKind 只能是「最低价」「集换价」「当前竞价」「成交价」之一
"""

CARD_LABEL_PROMPT = """你是集换社「商品」页卡牌编号识别助手。
请只识别截图中的系列代号（set/series）与卡牌编号（card number），输出 JSON，不要 Markdown，不要解释。

输出格式：
{"series": "系列代号或null", "cardNumber": "卡牌编号或null"}

规则：
- series 如 M2a、s8a-p、PTCG-JA-M4 等，看不清填 null
- cardNumber 如 234、007、114/083 等，看不清填 null
- 不要猜测；看不清就 null
"""

DETAIL_ENTRY_PROMPT = """你是集换社「点进卡牌后的商品详情首屏」识图助手。
请识别卡牌中文名、系列代号、卡牌编号，以及详情首屏 RAW 裸卡区的最低价与集换价，只输出 JSON，不要 Markdown，不要解释。

输出格式：
{"cardName": "卡牌中文主标题或null",
 "series": "系列代号或null", "cardNumber": "卡牌编号或null",
 "items": [
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "最低价"},
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "RAW", "priceKind": "集换价"}
]}

规则：
- cardName 为页面主标题（如 闪耀鲤鱼王、超级耿鬼ex），看不清填 null
- series 如 M2a、s8a-p 等；cardNumber 须含分数如 234/193、010/025，仅单个数字时也要尽量读全
- M2a 系列多张卡编号接近（234/240/246），务必逐位核对编号，勿混淆
- **最低价**：某位商家上架的 RAW 裸卡一口价（挂牌价）
- **集换价**：平台「集换价」标价，根据近10单成交均价计算，不是商家一口价；cardCondition=RAW
- 本页只采 RAW 裸卡的最低价与集换价，不要输出 PSA/CCIC 评级价
- priceKind 只能是「最低价」或「集换价」
- 不要猜测；看不清就 null
"""

AUCTION_SCROLL_PROMPT = """你是集换社「竞价 → 最近成交」页的价格识别助手。
请识别 PSA10/CCIC金10 评级区的商家一口价与平台集换价，以及「最近成交」列表的全部成交价，只输出 JSON，不要 Markdown，不要解释。

输出格式：
{"items": [
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "PSA10", "priceKind": "PSA一口价", "gradeBadge": "PSA10"},
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "CCIC10", "priceKind": "CCIC一口价", "gradeBadge": "CCIC金10"},
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "PSA10", "priceKind": "PSA集换价", "gradeBadge": "PSA10"},
  {"price": 数字或null, "tradeType": "FLOOR", "cardCondition": "CCIC10", "priceKind": "CCIC集换价", "gradeBadge": "CCIC金10"},
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "成交价", "gradeBadge": "PSA10"},
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "CCIC10", "priceKind": "成交价", "gradeBadge": "CCIC金10"},
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "RAW", "priceKind": "成交价", "gradeBadge": null}
]}

规则：
- **一口价** = 某位商家上架的挂牌价；**集换价** = 平台按近10单成交均价算出的参考价。二者不同，须分别识别
- gradeBadge 为该行/该区可见的评级角标；**必须看清角标再填 priceKind**
- **PSA一口价** / **CCIC一口价**：评级区商家挂牌价；无则 price=null
- **PSA集换价** / **CCIC集换价**：评级区平台「集换价」标价（近10单均价）；页面上没有则 price=null，不要猜
- CCIC 只采金10，忽略 CCIC银10/银标
- **成交价**（与上面一口价/集换价无关）来自「最近成交」列表：每一条可见成交单独输出一个 item（允许多条同评级、同价格也要重复输出）
  - **PSA10 成交**：左侧角标必须清晰可见「PSA」字样 → cardCondition=PSA10, gradeBadge 必填 PSA 相关文字（如 PSA10）；无 PSA 角标不要标 PSA10
  - **CCIC金10 成交**：角标必须含「CCIC金10」或「CCIC金」→ cardCondition=CCIC10, gradeBadge 必填；**CCIC银10/银标整条跳过，不要输出，也不要填入 CCIC10**
  - **裸卡**：左侧无任何 PSA/CCIC/BGS/CGC 等评级角标，仅数字 → cardCondition=RAW, gradeBadge=null
  - BGS/CGC/ARS 等其他评级公司成交：**整条跳过，不要输出**
  - 严禁把裸卡或其他评级成交误标为 PSA10 或 CCIC10
- 每条右侧红色「最高 ¥xxxx」即该条成交价；同评级同价格出现多次就输出多个 item
- priceKind 只能是「PSA一口价」「CCIC一口价」「PSA集换价」「CCIC集换价」「成交价」
- 不要猜测；看不清或页面上没有就 null
"""

WISHLIST_SCAN_PROMPT = """你是集换社「心愿单」卡牌网格列表识图助手。
请识别当前截图中可见的每一张卡牌名称及其网格位置，只输出 JSON。

输出格式：
{"cards": [
  {"name": "卡牌中文名", "row": 0, "col": 0},
  {"name": "另一张卡", "row": 0, "col": 1}
]}

规则：
- 只列看得清名称的卡牌；row/col 从 0 开始，左上为 (0,0)，同一行 col 从左到右递增
- 每行通常 4 列（col 0~3）；换行则 row+1
- 看不清的跳过，不要猜测
"""

AUCTION_PROMPT = """你是集换社小程序「竞价」页签的价格识别助手。
请从截图中提取可见价格，只输出 JSON，不要 Markdown 代码块，不要解释。

输出格式：
{"items": [
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "当前竞价", "gradeBadge": "PSA10"},
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "PSA10", "priceKind": "成交价", "gradeBadge": "PSA10"},
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "CCIC10", "priceKind": "成交价", "gradeBadge": "CCIC金10"},
  {"price": 数字或null, "tradeType": "AUCTION", "cardCondition": "RAW", "priceKind": "成交价", "gradeBadge": null}
]}

规则：
- gradeBadge 为可见评级角标；裸卡无任何角标时 gradeBadge=null
- PSA10 成交 gradeBadge 必填且含 PSA；CCIC金10 成交 gradeBadge 必填且含金10，CCIC银10 跳过；裸卡 gradeBadge=null
- BGS/CGC 等其他评级整条跳过；严禁误标 PSA10/CCIC10
- 同价格多条成交须重复输出多个 item
- 找不到对应价格时 price 为 null
- 不要猜测；看不清就 null
- priceKind 只能是「当前竞价」或「成交价」
"""


def _normalize_card_label(name: str) -> str:
    s = re.sub(r"\s+", "", name.strip())
    for token in ("EX", "ex", "VMAX", "Vmax", "VSTAR", "V"):
        s = s.replace(token, "")
    return s


def verify_card_name(expected_name: str, detected: str | None) -> None:
    """防止点错格位：识别名与渠道名明显不一致则拒绝入库。"""
    if not detected or not str(detected).strip():
        print("[vision] 未识别到 cardName，跳过名称校验", flush=True)
        return
    exp = _normalize_card_label(expected_name)
    det = _normalize_card_label(str(detected))
    if not exp or not det:
        return
    if exp in det or det in exp:
        print(f"[vision] 卡牌名校验通过: {detected}", flush=True)
        return
    for i in range(len(exp) - 1):
        if exp[i : i + 2] in det:
            print(f"[vision] 卡牌名校验通过(部分匹配): {detected}", flush=True)
            return
    raise RuntimeError(
        f"卡牌名与 CSV 不一致，可能点错格位：期望「{expected_name}」，截图识别「{detected}」。"
        f"请核对 vision-channels.csv 的 gridSlot 与 layout.json 坐标。"
    )


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def parse_items_response(text: str) -> list[dict]:
    data = extract_json(text)
    items = data.get("items")
    if not isinstance(items, list):
        raise RuntimeError(f"识图 JSON 缺少 items 数组: {text[:200]}")
    return items
