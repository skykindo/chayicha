import type { CardLanguage } from "@everyasset/db";
import { parseGradeLabelFromTitle } from "@everyasset/db";

const LANGUAGE_ALIASES: Record<CardLanguage, string[]> = {
  JA: ["日版", "日文", "日语", "ja", "japanese", "jp"],
  ZH: ["简中", "简体中文", "中文", "国行", "cn", "chs"],
  EN: ["美版", "英文", "英语", "en", "english"],
};

export type AssetMatchFields = Pick<
  import("@everyasset/db").StandardAsset,
  "name" | "language" | "year" | "series" | "cardNumber" | "rarity"
>;

export { parseGradeLabelFromTitle };

/** 从标准资产字段生成列表标题匹配词 */
export function buildMatchTokens(
  asset: AssetMatchFields,
  searchKeyword?: string | null,
): string[] {
  if (searchKeyword?.trim()) {
    return searchKeyword
      .split(/[\s/\-_,，、|+]+/)
      .map((t) => t.trim())
      .filter(Boolean);
  }

  const tokens = new Set<string>();

  for (const part of asset.name.split(/[\s/\-_,，、|+]+/)) {
    if (part.length >= 2) tokens.add(part);
  }

  if (asset.series) tokens.add(asset.series);
  if (asset.rarity) tokens.add(asset.rarity);

  if (asset.year) {
    tokens.add(String(asset.year));
  }

  if (asset.cardNumber) {
    tokens.add(asset.cardNumber);
    const [num, total] = asset.cardNumber.split("/");
    if (num) tokens.add(num);
    if (total) tokens.add(total);
  }

  if (asset.language) {
    for (const alias of LANGUAGE_ALIASES[asset.language]) {
      tokens.add(alias);
    }
  }

  return Array.from(tokens);
}

/**
 * 标题是否匹配标准资产（卡牌身份，不含评级）。
 * 评级由 PriceStream.cardCondition 记录，散点图内筛选。
 */
export function matchesAsset(
  title: string,
  asset: AssetMatchFields,
  searchKeyword?: string | null,
): boolean {
  const haystack = title.toLowerCase().replace(/\s+/g, " ");
  const tokens = buildMatchTokens(asset, searchKeyword);

  if (tokens.length === 0) {
    return haystack.includes(asset.name.toLowerCase());
  }

  const hits = tokens.filter((token) =>
    haystack.includes(token.toLowerCase()),
  );

  const hasStrictField = Boolean(
    asset.cardNumber || asset.rarity || asset.series || asset.year,
  );
  const required = hasStrictField
    ? Math.min(3, tokens.length)
    : Math.min(2, tokens.length);

  return hits.length >= required;
}
