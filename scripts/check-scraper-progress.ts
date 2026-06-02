/**
 * 查看卡乐 WEB 爬虫进度
 *
 * 注意：PriceStream.capturedAt 存的是「成交日期」，不是抓取时间，
 *       因此不能用「近 N 小时写入」判断本轮进度。
 *
 * 用法:
 *   npx tsx scripts/check-scraper-progress.ts
 *   npm run scraper:progress
 */
import { config } from "dotenv";
import { resolve } from "path";
import { prisma } from "@everyasset/db";

config({ path: resolve(".env") });

async function main() {
  const pokeChannels = await prisma.assetChannel.findMany({
    where: { platform: "POKECOLOR", trackType: "WEB" },
    select: { assetKey: true, asset: { select: { name: true } } },
    orderBy: { createdAt: "asc" },
  });
  const channelKeys = pokeChannels.map((c) => c.assetKey);

  const withAnyPoke = await prisma.priceStream.groupBy({
    by: ["assetKey"],
    where: { platform: "POKECOLOR", assetKey: { in: channelKeys } },
  });
  const withApiPoke = await prisma.priceStream.groupBy({
    by: ["assetKey"],
    where: {
      platform: "POKECOLOR",
      assetKey: { in: channelKeys },
      info: { contains: "[POKECOLOR/API]" },
    },
  });

  const totalRows = await prisma.priceStream.count({
    where: { platform: "POKECOLOR", assetKey: { in: channelKeys } },
  });

  const doneSet = new Set(withAnyPoke.map((r) => r.assetKey));
  const notDone = pokeChannels.filter((c) => !doneSet.has(c.assetKey));

  console.log("=== 卡乐 WEB 爬虫进度（数据库推断）===");
  console.log(`卡乐 WEB 渠道总数: ${channelKeys.length}`);
  console.log(
    `至少写过 1 条卡乐流水的卡: ${withAnyPoke.length} / ${channelKeys.length}`,
  );
  console.log(
    `其中走 turnover API 全量入库的卡: ${withApiPoke.length}`,
  );
  console.log(`卡乐 PriceStream 总条数: ${totalRows}`);
  console.log(
    `从未写过流水的卡(可能未跑到/或匹配不到): ${notDone.length}`,
  );

  if (notDone.length > 0) {
    console.log("\n尚未有流水的卡(前 15 张，按渠道 createdAt 顺序):");
    for (const ch of notDone.slice(0, 15)) {
      console.log(`  ${ch.assetKey}  (${ch.asset.name})`);
    }
    if (notDone.length > 15) {
      console.log(`  … 另有 ${notDone.length - 15} 张`);
    }
  }

  console.log("\n--- 如何看「本轮」跑到第几张 ---");
  console.log("1. 终端往上翻，数 [queue] 卡名 → POKECOLOR (WEB) 行数");
  console.log("2. 或看最后一条 [queue] / [dispatch] 前的卡名");
  console.log(
    "3. 数据库无法按抓取时间精确统计（capturedAt=成交日，非抓取时刻）",
  );

  await prisma.$disconnect();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
