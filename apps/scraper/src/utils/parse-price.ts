/** 从页面文本中提取人民币/美元价格（支持千分位逗号） */
export function extractFirstPrice(text: string, label: string): number | null {
  const pattern = new RegExp(
    `${label}[\\s\\S]{0,60}?([\\d,]+(?:\\.\\d+)?)`,
    "i",
  );
  const match = text.match(pattern);
  if (!match) return null;
  return parseMoney(match[1]);
}

export function parseMoney(raw: string): number | null {
  if (!raw) return null;
  const match = raw.match(/[\$¥￥]?\s*([\d,]+(?:\.\d+)?)/);
  if (!match) return null;
  const value = parseFloat(match[1].replace(/,/g, ""));
  return Number.isFinite(value) ? value : null;
}

export function pickLowest(...values: Array<number | null | undefined>): number | null {
  const valid = values.filter(
    (v): v is number => v != null && Number.isFinite(v),
  );
  return valid.length > 0 ? Math.min(...valid) : null;
}
