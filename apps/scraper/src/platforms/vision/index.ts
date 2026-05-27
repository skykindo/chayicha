import type { AssetChannel, StandardAsset } from "@everyasset/db";

/**
 * 轨道 B：集换社 / 闲鱼 AI 视觉外挂
 * Phase 2 — 由 apps/vision/main.py + PyAutoGUI + Gemini 接管
 */
export async function runVisionChannel(
  channel: AssetChannel,
  asset: StandardAsset,
): Promise<number> {
  console.log(
    `[VISION] ${asset.name} / ${channel.platform} — 接下来由本地 AI 视觉模块接管`,
  );
  console.log(
    `[VISION] 搜索词: ${channel.searchKeyword ?? "(未配置)"} | trackType=${channel.trackType}`,
  );
  void channel;
  return 0;
}
