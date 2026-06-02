#!/usr/bin/env python3
"""查询本次 VISION mock 写入的 PriceStream。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_config
from db import _connect
from psycopg2.extras import RealDictCursor

ASSET_KEYS = [
    "PTCG-JA-M4-114/083-SAR",
    "PTCG-JA-M2a-234/193-SAR",
    "PTCG-JA-M2a-240/193-SAR",
    "PTCG-JA-M2a-246/193-SAR",
    "PTCG-JA-s8a-p-007/025-Promo",
    "PTCG-JA-s8a-p-010/025-Promo",
]

SQL_VISION = """
SELECT ps."assetKey", sa.name, ps."tradeType", ps."cardCondition",
       ps.price, ps.info, ps."capturedAt"
FROM "PriceStream" ps
JOIN "StandardAsset" sa ON sa."assetKey" = ps."assetKey"
WHERE ps.platform = 'JIHUANSHE'
  AND ps.info LIKE '[VISION]%%'
  AND ps."assetKey" = ANY(%s)
ORDER BY ps."capturedAt" DESC, ps."assetKey", ps.info
"""

SQL_ALL_JHS = """
SELECT ps."assetKey", sa.name, ps.price, ps.info, ps."capturedAt"
FROM "PriceStream" ps
JOIN "StandardAsset" sa ON sa."assetKey" = ps."assetKey"
WHERE ps.platform = 'JIHUANSHE'
  AND ps."assetKey" = ANY(%s)
ORDER BY ps."capturedAt" DESC
LIMIT 50
"""

SQL_RECENT_VISION = """
SELECT COUNT(*) AS cnt
FROM "PriceStream"
WHERE platform = 'JIHUANSHE' AND info LIKE '[VISION]%%'
"""

SQL_RECENT_ANY = """
SELECT ps."assetKey", ps.price, ps.info, ps."capturedAt"
FROM "PriceStream" ps
WHERE ps.platform = 'JIHUANSHE' AND ps.info LIKE '[VISION]%%'
ORDER BY ps."capturedAt" DESC
LIMIT 20
"""


def main() -> int:
    cfg = load_config()
    with _connect(cfg) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(SQL_VISION, (ASSET_KEYS,))
            rows = cur.fetchall()
            cur.execute(SQL_ALL_JHS, (ASSET_KEYS,))
            all_jhs = cur.fetchall()
            cur.execute(SQL_RECENT_VISION)
            vision_total = cur.fetchone()["cnt"]
            cur.execute(SQL_RECENT_ANY)
            recent_vision = cur.fetchall()

    print(f"[check] 6 张卡 [VISION] 标记记录: {len(rows)} 条")
    print(f"[check] 全库 JIHUANSHE+[VISION] 记录: {vision_total} 条")
    print(f"[check] 6 张卡任意 JIHUANSHE 记录(最近50): {len(all_jhs)} 条\n")
    if recent_vision:
        print("[check] 最近写入的 [VISION] 记录(任意卡):")
        for r in recent_vision[:10]:
            print(f"    {r['assetKey']} | {r['info']} | {r['price']} | {r['capturedAt']}")
        print()
    by_key: dict[str, list] = {}
    for r in rows:
        by_key.setdefault(r["assetKey"], []).append(r)

    for key in ASSET_KEYS:
        items = by_key.get(key, [])
        name = items[0]["name"] if items else "(无记录)"
        print(f"--- {key}")
        print(f"    {name}")
        if not items:
            print("    (无 [VISION] 价格)")
            continue
        for r in items:
            print(
                f"    {r['info']} | {r['tradeType']}/{r['cardCondition']} "
                f"| price={r['price']} | {r['capturedAt']}"
            )
        print()

    missing = [k for k in ASSET_KEYS if k not in by_key]
    with _connect(cfg) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT COUNT(*) AS n FROM "PriceStream"')
            total = cur.fetchone()["n"]
            cur.execute(
                'SELECT platform::text AS p, COUNT(*) AS n FROM "PriceStream" '
                "GROUP BY platform ORDER BY n DESC"
            )
            by_plat = cur.fetchall()
            cur.execute(
                'SELECT COUNT(*) AS n FROM "PriceStream" '
                "WHERE \"capturedAt\" > NOW() - interval '24 hours'"
            )
            last24 = cur.fetchone()["n"]

    print("[check] --- 库内概况 ---")
    print(f"    PriceStream 总行数: {total}")
    print(f"    近 24 小时新增: {last24}")
    for r in by_plat:
        print(f"    platform={r['p']}: {r['n']}")

    if missing:
        print("\n[check] 结论: 流程跑完，但 6 张卡没有 JIHUANSHE+[VISION] 价格。")
        print("    常见原因: mock 灰图识图 price 全为 null → 入库 0 条仍算成功。")
        return 1
    print("[check] 6 张卡均有 [VISION] 记录")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
