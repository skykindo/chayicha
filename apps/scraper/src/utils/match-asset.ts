import type { CardLanguage } from "@everyasset/db";
import {
  formatAssetGradeLabel,
  parseGradeLabelFromTitle,
  matchesGradeSpec,
} from "@everyasset/db";

export type AssetMatchFields = Pick<
  import("@everyasset/db").StandardAsset,
  | "name"
  | "language"
  | "series"
  | "cardNumber"
  | "rarity"
  | "gradingCompany"
  | "gradeScore"
>;

const LANGUAGE_ALIASES: Record<CardLanguage, string[]> = {
  JA: ["日版", "日文", "日语", "ja", "japanese", "jp"],
  ZH: ["简中", "简体中文", "中文", "国行", "cn", "chs"],
  EN: ["美版", "英文", "英语", "en", "english"],
};

export { formatAssetGradeLabel, parseGradeLabelFromTitle, matchesGradeSpec };

/** 看板展示用标准规格标签 */
export function formatAssetSpec(asset: AssetMatchFields): string {
  const parts: string[] = [];
  if (asset.language) {
    parts.push(
      asset.language === "JA"
        ? "日版"
        : asset.language === "ZH"
          ? "简中"
          : "英文",
    );
  }
  if (asset.series) parts.push(asset.series);
  if (asset.cardNumber) parts.push(`#${asset.cardNumber}`);
  if (asset.rarity) parts.push(asset.rarity);
  if (asset.gradingCompany !== "RAW" || asset.gradeScore) {
    parts.push(formatAssetGradeLabel(asset));
  }
  return parts.join(" · ");
}

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

  if (asset.gradingCompany !== "RAW") {
    tokens.add(asset.gradingCompany);
    if (asset.gradeScore) {
      tokens.add(`${asset.gradingCompany}${asset.gradeScore}`);
      tokens.add(asset.gradeScore);
    }
  }

  return Array.from(tokens);
}

/**
 * 标题是否匹配标准资产（卡牌身份 + 评级规格）。
 */
export function matchesAsset(
  title: string,
  asset: AssetMatchFields,
  searchKeyword?: string | null,
): boolean {
  const haystack = title.toLowerCase().replace(/\s+/g, " ");
  const tokens = buildMatchTokens(asset, searchKeyword);

  if (tokens.length === 0) {
    if (!haystack.includes(asset.name.toLowerCase())) return false;
  } else {
    const hits = tokens.filter((token) =>
      haystack.includes(token.toLowerCase()),
    );

    const hasStrictField = Boolean(
      asset.cardNumber ||
        asset.rarity ||
        asset.series ||
        asset.gradingCompany !== "RAW",
    );
    const required = hasStrictField
      ? Math.min(3, tokens.length)
      : Math.min(2, tokens.length);

    if (hits.length < required) return false;
  }

  const gradeLabel = parseGradeLabelFromTitle(title) ?? "裸卡";
  return matchesGradeSpec(asset, gradeLabel);
}
