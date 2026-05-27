import type { BrowserContext } from "playwright";
import { TrackType, type StandardAsset, type AssetChannel } from "@everyasset/db";
import { scraperConfig } from "./config.js";
import { dispatchChannel } from "./dispatch.js";

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

type AssetWithChannels = StandardAsset & { channels: AssetChannel[] };

export async function runScrapeQueue(
  context: BrowserContext | null,
  assets: AssetWithChannels[],
) {
  const channelCount = assets.reduce((n, a) => n + a.channels.length, 0);
  console.log(
    `[queue] 标准资产 ${assets.length} 个，渠道 ${channelCount} 条`,
  );

  for (const asset of assets) {
    if (asset.channels.length === 0) {
      console.warn(`[queue] ${asset.name} — 无 AssetChannel 配置，跳过`);
      continue;
    }

    for (const channel of asset.channels) {
      try {
        console.log(
          `[queue] ${asset.name} → ${channel.platform} (${channel.trackType})`,
        );
        const count = await dispatchChannel(context, asset, channel);
        if (count === 0 && channel.trackType === TrackType.WEB) {
          console.warn(`[queue] 本轮未写入 ${channel.platform} 流水`);
        }
      } catch (error) {
        console.error(
          `[queue] ✗ ${asset.name} / ${channel.platform}:`,
          error,
        );
      }

      await sleep(scraperConfig.requestDelayMs);
    }
  }
}
