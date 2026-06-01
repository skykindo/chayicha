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

export type CardCondition = "RAW" | "PSA10" | "PSA9" | "CGC10";

export const CARD_CONDITION_LABELS: Record<CardCondition, string> = {
  RAW: "裸卡",
  PSA10: "PSA 10",
  PSA9: "PSA 9",
  CGC10: "CGC 10",
};

/** 将标题/评级标签归一化为标准 cardCondition 枚举 */
export function parseCardCondition(
  title: string,
  gradeLabel?: string | null,
): CardCondition {
  const label = (gradeLabel ?? parseGradeLabelFromTitle(title) ?? "裸卡")
    .toUpperCase()
    .replace(/\s+/g, "");

  if (label === "裸卡" || label === "RAW") return "RAW";
  if (/PSA10|^PSA\s*10$/.test(label)) return "PSA10";
  if (/PSA9|^PSA\s*9$/.test(label)) return "PSA9";
  if (/CGC10|CGC黑金10|CGC金10/.test(label)) return "CGC10";

  if (/PSA/.test(label) && /10/.test(label)) return "PSA10";
  if (/PSA/.test(label) && /9/.test(label)) return "PSA9";
  if (/CGC/.test(label) && /10/.test(label)) return "CGC10";

  return "RAW";
}

export function formatCardConditionLabel(condition: string): string {
  return (
    CARD_CONDITION_LABELS[condition as CardCondition] ??
    condition
  );
}
