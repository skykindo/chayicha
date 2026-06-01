import { Platform } from "@prisma/client";

/** Supabase / 看板展示用中文名 */
export const PLATFORM_LABELS: Record<Platform, string> = {
  JIHUANSHE: "集换社",
  POKECOLOR: "卡乐",
  KATAO: "卡淘",
  IDLEFISH: "闲鱼",
};

export function formatPlatformLabel(platform: Platform): string {
  return PLATFORM_LABELS[platform];
}

/** 将 KATAO_AUCTION 转为「卡淘·拍卖」 */
export function formatPlatformSeriesKey(key: string): string {
  if (key === "avg") return "均值";

  const sep = key.indexOf("_");
  if (sep === -1) return key;

  const platform = key.slice(0, sep) as Platform;
  const tradeType = key.slice(sep + 1);
  const platformLabel = PLATFORM_LABELS[platform] ?? platform;
  const tradeLabel =
    tradeType === "AUCTION"
      ? "拍卖"
      : tradeType === "FLOOR"
        ? "挂牌"
        : tradeType;

  return `${platformLabel}·${tradeLabel}`;
}
