import type { BrowserContext } from "playwright";
import {
  Platform,
  TrackType,
  parseCardCondition,
  type AssetChannel,
  type StandardAsset,
} from "@everyasset/db";
import { scrapeKataoList } from "./platforms/katao/list-scraper.js";
import { scrapePokecolorList } from "./platforms/pokecolor/list-scraper.js";
import { runVisionChannel } from "./platforms/vision/index.js";
import { upsertPriceStream } from "./upsert.js";

export async function dispatchChannel(
  context: BrowserContext | null,
  asset: StandardAsset,
  channel: AssetChannel,
): Promise<number> {
  if (channel.trackType === TrackType.VISION) {
    return runVisionChannel(channel, asset);
  }

  if (channel.trackType !== TrackType.WEB) {
    console.warn(`[dispatch] 未知 trackType: ${channel.trackType}`);
    return 0;
  }

  if (!context) {
    throw new Error("WEB 轨道需要 Playwright 浏览器上下文");
  }

  if (
    channel.platform !== Platform.KATAO &&
    channel.platform !== Platform.POKECOLOR &&
    !channel.sourceUrl &&
    !channel.sourceUrlAuction
  ) {
    console.warn(
      `[dispatch] ${asset.name} / ${channel.platform} — WEB 渠道缺少 sourceUrl`,
    );
    return 0;
  }

  if (
    (channel.platform === Platform.KATAO ||
      channel.platform === Platform.POKECOLOR) &&
    !channel.sourceUrl &&
    !channel.sourceUrlAuction
  ) {
    console.warn(
      `[dispatch] ${asset.name} / ${channel.platform} — 缺少历史成交列表页 URL`,
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
      const cardCondition =
        item.cardCondition ??
        parseCardCondition(item.title, item.gradeLabel ?? null);

      await upsertPriceStream({
        assetKey: asset.assetKey,
        platform: channel.platform,
        tradeType: item.tradeType,
        cardCondition,
        price: item.price,
        info: item.info ?? item.title.slice(0, 120),
        bidCount: item.bidCount,
        bidderCount: item.bidderCount,
        watchCount: item.watchCount,
        isDelayed: item.isDelayed,
        capturedAt: item.capturedAt,
      });
      written += 1;
      const sentiment =
        item.bidCount != null
          ? ` | 出价${item.bidCount}次/${item.bidderCount ?? "?"}人`
          : "";
      console.log(
        `[dispatch] ✓ ${asset.name} / ${channel.platform} / ${item.tradeType} / ${cardCondition} — ¥${item.price}${sentiment} ← ${item.title.slice(0, 40)}…`,
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
        `[dispatch] ${channel.platform} WEB 列表解析待实现，请使用 trackType=VISION`,
      );
      return [];
    case Platform.IDLEFISH:
      console.log(
        `[dispatch] ${channel.platform} — 请配置 trackType=VISION 走 AI 视觉轨`,
      );
      return [];
    default: {
      const _exhaustive: never = channel.platform;
      console.warn(`[dispatch] 未支持的平台: ${_exhaustive}`);
      return [];
    }
  }
}
