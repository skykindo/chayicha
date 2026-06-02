import { config } from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

config({ path: resolve(dirname(fileURLToPath(import.meta.url)), "../../../.env") });

import { prisma, TrackType } from "@everyasset/db";
import { createBrowserContext } from "./browser.js";
import { resetCheckpoint } from "./checkpoint.js";
import { runScrapeQueue } from "./queue.js";

async function main() {
  if (process.argv.includes("--reset-checkpoint")) {
    resetCheckpoint();
    console.log("[scraper] 已清空 checkpoint.json，将从第 1 张开始");
  }

  console.log("[scraper] 万物皆可K线 — 标准资产池调度启动");

  const assets = await prisma.standardAsset.findMany({
    where: { isMonitoring: true },
    include: { channels: true },
    orderBy: { createdAt: "asc" },
  });

  if (assets.length === 0) {
    console.log(
      "[scraper] 暂无 StandardAsset，请在 Supabase 配置标准资产与 AssetChannel",
    );
    return;
  }

  const needsBrowser = assets.some((a) =>
    a.channels.some((c) => c.trackType === TrackType.WEB),
  );

  let context = null;
  if (needsBrowser) {
    context = await createBrowserContext();
  }

  try {
    await runScrapeQueue(context, assets);
  } finally {
    if (context) {
      await context.close();
    }
    await prisma.$disconnect();
  }

  console.log("[scraper] 本轮标准资产池抓取完成");
}

main().catch((error) => {
  console.error("[scraper] 致命错误:", error);
  process.exit(1);
});
