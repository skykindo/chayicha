import { readFileSync, writeFileSync, existsSync, unlinkSync } from "fs";
import { scraperConfig } from "./config.js";

export type ScraperCheckpoint = {
  /** 下轮从该 assetKey 开始（含本卡），首次生效后转为 lastCompletedAssetKey 链式续跑 */
  startFromAssetKey?: string;
  /** 上一张已全部渠道处理完成的 assetKey */
  lastCompletedAssetKey?: string;
};

export function loadCheckpoint(): ScraperCheckpoint {
  const path = scraperConfig.checkpointPath;
  if (!existsSync(path)) {
    const fromEnv = scraperConfig.startFromAssetKey;
    return fromEnv ? { startFromAssetKey: fromEnv } : {};
  }
  try {
    const data = JSON.parse(readFileSync(path, "utf8")) as ScraperCheckpoint;
    if (scraperConfig.startFromAssetKey) {
      return { ...data, startFromAssetKey: scraperConfig.startFromAssetKey };
    }
    return data;
  } catch {
    console.warn("[checkpoint] 无法解析 checkpoint.json，将从头开始");
    return {};
  }
}

export function saveCheckpoint(data: ScraperCheckpoint): void {
  writeFileSync(scraperConfig.checkpointPath, JSON.stringify(data, null, 2), "utf8");
}

export function resetCheckpoint(): void {
  if (existsSync(scraperConfig.checkpointPath)) {
    unlinkSync(scraperConfig.checkpointPath);
  }
}

/** 是否应处理该 assetKey（按 createdAt 顺序的 keys 列表） */
export function shouldProcessAsset(
  assetKey: string,
  orderedKeys: string[],
  checkpoint: ScraperCheckpoint,
): boolean {
  const idx = orderedKeys.indexOf(assetKey);
  if (idx < 0) return true;

  if (checkpoint.startFromAssetKey) {
    const startIdx = orderedKeys.indexOf(checkpoint.startFromAssetKey);
    if (startIdx < 0) {
      console.warn(
        `[checkpoint] 未找到 startFromAssetKey=${checkpoint.startFromAssetKey}，将处理全部`,
      );
      return true;
    }
    return idx >= startIdx;
  }

  if (checkpoint.lastCompletedAssetKey) {
    const lastIdx = orderedKeys.indexOf(checkpoint.lastCompletedAssetKey);
    if (lastIdx < 0) return true;
    return idx > lastIdx;
  }

  return true;
}

export function markAssetCompleted(
  assetKey: string,
  checkpoint: ScraperCheckpoint,
): ScraperCheckpoint {
  const next: ScraperCheckpoint = {
    lastCompletedAssetKey: assetKey,
  };
  if (checkpoint.startFromAssetKey) {
    // 已开始续跑，不再需要 startFrom
  }
  saveCheckpoint(next);
  return next;
}

export function markRunFinished(): void {
  resetCheckpoint();
}
