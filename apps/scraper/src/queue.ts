import type { BrowserContext } from "playwright";
import { TrackType, type StandardAsset, type AssetChannel } from "@everyasset/db";
import {
  loadCheckpoint,
  markAssetCompleted,
  markRunFinished,
  shouldProcessAsset,
  type ScraperCheckpoint,
} from "./checkpoint.js";
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
  const orderedKeys = assets.map((a) => a.assetKey);
  let checkpoint: ScraperCheckpoint = loadCheckpoint();

  const resumeFrom =
    checkpoint.startFromAssetKey ?? checkpoint.lastCompletedAssetKey;
  if (resumeFrom) {
    const mode = checkpoint.startFromAssetKey ? "startFrom" : "lastCompleted";
    console.log(
      `[checkpoint] 续跑模式 ${mode}=${resumeFrom}（跳过此前已完成的卡）`,
    );
  }

  const toRun = assets.filter((a) =>
    shouldProcessAsset(a.assetKey, orderedKeys, checkpoint),
  );

  const channelCount = toRun.reduce((n, a) => n + a.channels.length, 0);
  console.log(
    `[queue] 标准资产 ${assets.length} 个，本轮执行 ${toRun.length} 个，渠道 ${channelCount} 条`,
  );

  let skipped = assets.length - toRun.length;
  if (skipped > 0) {
    console.log(`[checkpoint] 已跳过 ${skipped} 张（断点之前）`);
  }

  for (const asset of assets) {
    if (!shouldProcessAsset(asset.assetKey, orderedKeys, checkpoint)) {
      continue;
    }

    if (asset.channels.length === 0) {
      console.warn(`[queue] ${asset.name} — 无 AssetChannel 配置，跳过`);
      checkpoint = markAssetCompleted(asset.assetKey, checkpoint);
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

    checkpoint = markAssetCompleted(asset.assetKey, checkpoint);
    console.log(`[checkpoint] 已完成 ${asset.assetKey}`);
  }

  const finalCheckpoint = loadCheckpoint();
  const anyLeft = assets.some((a) =>
    shouldProcessAsset(a.assetKey, orderedKeys, finalCheckpoint),
  );
  if (!anyLeft) {
    markRunFinished();
    console.log("[checkpoint] 全部监控资产已跑完，断点已清空");
  }
}
