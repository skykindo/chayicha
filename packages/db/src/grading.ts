import type { GradingCompany } from "@prisma/client";

export type GradeSpecFields = {
  gradingCompany: GradingCompany;
  gradeScore: string | null;
};

/** 标准资产配置的评级标签，如 PSA10 / CGC黑金10 / 裸卡 */
export function formatAssetGradeLabel(asset: GradeSpecFields): string {
  if (asset.gradingCompany === "RAW") return "裸卡";
  const score = asset.gradeScore?.trim();
  if (!score) return asset.gradingCompany;
  return `${asset.gradingCompany}${score}`;
}

/** 从卡乐 API 或标题解析评级标签 */
export function buildGradeLabel(
  rateType: string | null | undefined,
  rateScoreDisplay: string | null | undefined,
  rateScore?: string | null,
): string {
  const type = rateType?.trim().toUpperCase();
  if (!type || type === "RAW" || type === "NONE") return "裸卡";

  const display = (rateScoreDisplay ?? "")
    .trim()
    .replace(/分$/u, "")
    .replace(/\s+/g, "");

  if (display) return `${type}${display}`;

  if (rateScore) {
    const n = parseFloat(rateScore);
    if (!Number.isNaN(n) && Number.isInteger(n)) {
      return `${type}${n}`;
    }
    return `${type}${rateScore}`;
  }

  return type;
}

/** 从商品标题兜底解析评级 */
export function parseGradeLabelFromTitle(title: string): string | null {
  const t = title.replace(/\s+/g, " ");

  if (/裸卡|无评级|未评级|raw\b/i.test(t)) return "裸卡";

  const cgcGold = t.match(/\bCGC\s*(黑金10|金10|10\s*PRISTINE|PRISTINE)/i);
  if (cgcGold) return `CGC${cgcGold[1].replace(/\s+/g, "")}`;

  const graded = t.match(/\b(PSA|CGC|BGS|SGC|GCG|ARS)\s*([^\s]{1,8})/i);
  if (graded) {
    const company = graded[1].toUpperCase();
    let score = graded[2].replace(/分$/u, "");
    if (/^10$/i.test(score)) score = "10";
    return `${company}${score}`;
  }

  return null;
}

function normalizeGrade(label: string): string {
  return label
    .toUpperCase()
    .replace(/\s+/g, "")
    .replace(/分$/u, "")
    .replace(/^RAW$/i, "裸卡");
}

/** 列表项评级是否匹配标准资产配置的评级 */
export function matchesGradeSpec(
  asset: GradeSpecFields,
  listingGradeLabel: string,
): boolean {
  const expected = normalizeGrade(formatAssetGradeLabel(asset));
  const actual = normalizeGrade(listingGradeLabel);

  if (asset.gradingCompany === "RAW") {
    return actual === "裸卡" || actual === "RAW";
  }

  return actual === expected || actual.includes(expected) || expected.includes(actual);
}

export const GRADING_COMPANY_LABELS: Record<GradingCompany, string> = {
  RAW: "裸卡",
  PSA: "PSA",
  CGC: "CGC",
  BGS: "BGS",
  OTHER: "其他",
};
