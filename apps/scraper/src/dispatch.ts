import type { BrowserContext } from "playwright";
import { Platform, TrackType, type AssetChannel, type StandardAsset } from "@everyasset/db";
import { scrapeKataoList } from "./platforms/katao/list-scraper.js";
import { scrapePokecolorList } from "./platforms/pokecolor/list-scraper.js";
import { runVisionChannel } from "./platforms/vision/index.js";
import { upsertPriceStream } from "./upsert.js";

export async function dispatchChannel(
  context: BrowserContext | null,
  asset: StandardAsset,
  channel: AssetChannel,
): Promise<number> {
  if (channel.trackType === TrackType.VISION_AI) {
    return runVisionChannel(channel, asset);
  }

  if (channel.trackType !== TrackType.WEB) {
    console.warn(`[dispatch] 未知 trackType: ${channel.trackType}`);
    return 0;
  }

  if (!context) {
    throw new Error("WEB 轨道需要 Playwright 浏览器上下文");
  }

  if (!channel.sourceUrl && !channel.sourceUrlAuction) {
    console.warn(
      `[dispatch] ${asset.name} / ${channel.platform} — WEB 渠道缺少 sourceUrl / sourceUrlAuction`,
    );
    return 0;
  }

  const page = await context.newPage();
  let written = 0;

  try {
    const items = await scrapeListByPlatform(page, channel, asset);

    if (items.length === 0) {
      console.warn(
        `[dispatch] ${asset.name} / ${channel.platform} — 列表页未匹配到成交/挂牌`,
      );
      return 0;
    }

    for (const item of items) {
      await upsertPriceStream({
        assetId: asset.id,
        platform: channel.platform,
        tradeType: item.tradeType,
        gradeLabel: item.gradeLabel ?? null,
        price: item.price,
        info: item.info ?? item.title.slice(0, 120),
      });
      written += 1;
      console.log(
        `[dispatch] ✓ ${asset.name} / ${channel.platform} / ${item.tradeType}${item.gradeLabel ? ` / ${item.gradeLabel}` : ""} — ¥${item.price} ← ${item.title.slice(0, 40)}…`,
      );
    }
  } finally {
    await page.close();
  }

  return written;
}

async function scrapeListByPlatform(
  page: import("playwright").Page,
  channel: AssetChannel,
  asset: StandardAsset,
) {
  switch (channel.platform) {
    case Platform.KATAO:
      return scrapeKataoList(page, channel, asset);
    case Platform.POKECOLOR:
      return scrapePokecolorList(page, channel, asset);
    case Platform.JIHUANSHE:
      console.log(
        `[dispatch] ${channel.platform} WEB 列表解析待实现，请使用 trackType=VISION_AI`,
      );
      return [];
    default: {
      const _exhaustive: never = channel.platform;
      console.warn(`[dispatch] 未支持的平台: ${_exhaustive}`);
      return [];
    }
  }
}
