export type SentimentFields = {
  bidCount?: number | null;
  bidderCount?: number | null;
  watchCount?: number | null;
  isDelayed?: boolean;
};

function pickInt(text: string, patterns: RegExp[]): number | null {
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match?.[1]) {
      const n = parseInt(match[1], 10);
      if (!Number.isNaN(n)) return n;
    }
  }
  return null;
}

/** 从列表行/标题文本解析拍卖情绪指标 */
export function parseSentimentFromText(text: string): SentimentFields {
  const bidCount = pickInt(text, [
    /(?:出价|竞拍|竞价)\s*(\d+)\s*次/i,
    /(\d+)\s*次(?:出价|竞拍|竞价)/i,
    /出价次数\s*[：:]\s*(\d+)/i,
  ]);

  const bidderCount = pickInt(text, [
    /(\d+)\s*人(?:出价|参与|竞拍)/i,
    /(?:参与|出价)\s*(\d+)\s*人/i,
    /围猎\s*(\d+)\s*人/i,
  ]);

  const watchCount = pickInt(text, [
    /(\d+)\s*人(?:围观|收藏|关注)/i,
    /(?:围观|收藏|关注)\s*(\d+)/i,
    /(\d+)\s*(?:次浏览|浏览)/i,
  ]);

  const isDelayed =
    /延时|延迟截标|延时结束|进入延时/i.test(text) &&
    !/未延时|无延时/i.test(text);

  return { bidCount, bidderCount, watchCount, isDelayed };
}

/** 从文本片段解析成交日期，失败则返回 null */
export function parseCapturedDateFromText(text: string): Date | null {
  const iso = text.match(/(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})/);
  if (iso) {
    const d = new Date(
      Number(iso[1]),
      Number(iso[2]) - 1,
      Number(iso[3]),
      12,
      0,
      0,
    );
    if (!Number.isNaN(d.getTime())) return d;
  }

  const cn = text.match(/(\d{1,2})月(\d{1,2})日/);
  if (cn) {
    const year = new Date().getFullYear();
    const d = new Date(year, Number(cn[1]) - 1, Number(cn[2]), 12, 0, 0);
    if (!Number.isNaN(d.getTime())) return d;
  }

  return null;
}

export function toCapturedDateString(date: Date): string {
  return date.toISOString().slice(0, 10);
}
