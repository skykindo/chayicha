#!/usr/bin/env python3
"""清理 JIHUANSHE [VISION] 价格流水。

用法:
  python apps/vision/cleanup_vision_prices.py --list          # 查看现有记录
  python apps/vision/cleanup_vision_prices.py --dry-run     # 预览将删除的行
  python apps/vision/cleanup_vision_prices.py --delete-all  # 删除全部 VISION 价
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_config
from db import VISION_INFO_LABELS, _connect
from psycopg2.extras import RealDictCursor

LIST_SQL = """
SELECT ps."assetKey", sa.name, ps."tradeType", ps."cardCondition",
       ps.price, ps.info, ps."capturedAt"
FROM "PriceStream" ps
LEFT JOIN "StandardAsset" sa ON sa."assetKey" = ps."assetKey"
WHERE ps.platform = 'JIHUANSHE' AND ps.info LIKE '[VISION]%%'
ORDER BY ps."capturedAt" DESC, ps."assetKey", ps.info
"""

SUMMARY_SQL = """
SELECT ps.info, ps."tradeType", ps."cardCondition", COUNT(*) AS n
FROM "PriceStream" ps
WHERE ps.platform = 'JIHUANSHE' AND ps.info LIKE '[VISION]%%'
GROUP BY ps.info, ps."tradeType", ps."cardCondition"
ORDER BY ps.info
"""

DELETE_ALL_SQL = """
DELETE FROM "PriceStream"
WHERE platform = 'JIHUANSHE' AND info LIKE '[VISION]%%'
RETURNING "assetKey", price, info
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="清理 JIHUANSHE [VISION] 价格")
    parser.add_argument("--list", action="store_true", help="列出全部 VISION 记录")
    parser.add_argument("--dry-run", action="store_true", help="预览删除，不执行")
    parser.add_argument(
        "--delete-all",
        action="store_true",
        help="删除全部 JIHUANSHE [VISION] 价格",
    )
    args = parser.parse_args()
    if not (args.list or args.dry_run or args.delete_all):
        parser.print_help()
        return 1

    cfg = load_config()
    with _connect(cfg) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(SUMMARY_SQL)
            summary = cur.fetchall()

    print("[cleanup] 当前标准 info 命名（重跑后将写入）:")
    for label in VISION_INFO_LABELS:
        print(f"    {label}")
    print()

    if summary:
        print("[cleanup] 库内现有 VISION 记录分布:")
        for row in summary:
            print(
                f"    {row['info']} | {row['tradeType']}/{row['cardCondition']} "
                f"| {row['n']} 条"
            )
        print(f"[cleanup] 合计 {sum(r['n'] for r in summary)} 条\n")
    else:
        print("[cleanup] 库内无 JIHUANSHE [VISION] 记录\n")

    if args.list:
        with _connect(cfg) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(LIST_SQL)
                rows = cur.fetchall()
        for r in rows:
            print(
                f"  {r['assetKey']} | {r.get('name') or '-'} | "
                f"{r['info']} | {r['tradeType']}/{r['cardCondition']} | "
                f"¥{r['price']} | {r['capturedAt']}"
            )
        return 0

    if args.dry_run or args.delete_all:
        total = sum(r["n"] for r in summary) if summary else 0
        if total == 0:
            print("[cleanup] 无需删除")
            return 0
        if args.dry_run:
            print(f"[cleanup] dry-run：将删除 {total} 条（未执行）")
            return 0

        with _connect(cfg) as conn:
            with conn.cursor() as cur:
                cur.execute(DELETE_ALL_SQL)
                deleted = cur.fetchall()
            conn.commit()
        print(f"[cleanup] 已删除 {len(deleted)} 条 JIHUANSHE [VISION] 价格")
        for asset_key, price, info in deleted:
            print(f"    - {asset_key} | price={price} | {info}")
        print(
            "\n[cleanup] 下一步：npm run vision -- --reset-checkpoint && npm run vision"
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
