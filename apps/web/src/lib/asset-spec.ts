import type { CardLanguage, GradingCompany } from "@everyasset/db";
import { formatAssetGradeLabel } from "@everyasset/db";

const LANGUAGE_ALIASES: Record<CardLanguage, string[]> = {
  JA: ["日版", "日文", "日语", "ja", "japanese", "jp"],
  ZH: ["简中", "简体中文", "中文", "国行", "cn", "chs"],
  EN: ["美版", "英文", "英语", "en", "english"],
};

export type AssetSpecFields = {
  name: string;
  language?: CardLanguage | null;
  series?: string | null;
  cardNumber?: string | null;
  rarity?: string | null;
  gradingCompany?: GradingCompany;
  gradeScore?: string | null;
};

export function formatAssetSpec(asset: AssetSpecFields): string {
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
  if (asset.gradingCompany && asset.gradingCompany !== "RAW") {
    parts.push(
      formatAssetGradeLabel({
        gradingCompany: asset.gradingCompany,
        gradeScore: asset.gradeScore ?? null,
      }),
    );
  } else if (asset.gradingCompany === "RAW") {
    parts.push("裸卡");
  }
  return parts.join(" · ");
}

export { LANGUAGE_ALIASES };
