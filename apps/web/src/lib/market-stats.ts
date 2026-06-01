export type PriceTick = {
  platform: string;
  tradeType: string;
  price: number;
  capturedDate: string;
};

export type MarketSnapshot = {
  latestAvg: number | null;
  latestDate: string | null;
  dayChangePct: number | null;
  hasArbitrage: boolean;
};

/** 按日聚合全网成交均价 */
export function getDailyAverages(prices: PriceTick[]): Map<string, number> {
  const byDate = new Map<string, number[]>();
  for (const p of prices) {
    const bucket = byDate.get(p.capturedDate) ?? [];
    bucket.push(p.price);
    byDate.set(p.capturedDate, bucket);
  }
  const result = new Map<string, number>();
  for (const [date, arr] of byDate) {
    result.set(date, arr.reduce((a, b) => a + b, 0) / arr.length);
  }
  return result;
}

/** 最新公允均价 + 日涨跌幅 */
export function computeMarketSnapshot(prices: PriceTick[]): MarketSnapshot {
  const daily = getDailyAverages(prices);
  const dates = Array.from(daily.keys()).sort();

  if (dates.length === 0) {
    return {
      latestAvg: null,
      latestDate: null,
      dayChangePct: null,
      hasArbitrage: false,
    };
  }

  const latestDate = dates[dates.length - 1]!;
  const latestAvg = daily.get(latestDate)!;
  const prevDate = dates.length >= 2 ? dates[dates.length - 2]! : null;
  const prevAvg = prevDate ? daily.get(prevDate)! : null;

  const dayChangePct =
    prevAvg != null && prevAvg > 0
      ? ((latestAvg - prevAvg) / prevAvg) * 100
      : null;

  return {
    latestAvg: Math.round(latestAvg),
    latestDate,
    dayChangePct:
      dayChangePct != null ? Math.round(dayChangePct * 100) / 100 : null,
    hasArbitrage: detectArbitrageOpportunity(prices, latestDate),
  };
}

/**
 * 卡淘拍卖价低于集换社一口价 20% 以上 → 套利机会
 */
export function detectArbitrageOpportunity(
  prices: PriceTick[],
  date?: string | null,
): boolean {
  const targetDate =
    date ??
    [...new Set(prices.map((p) => p.capturedDate))].sort().pop() ??
    null;
  if (!targetDate) return false;

  const today = prices.filter((p) => p.capturedDate === targetDate);
  const kataoAuction = today.filter(
    (p) => p.platform === "KATAO" && p.tradeType === "AUCTION",
  );
  const jihuansheFloor = today.filter(
    (p) => p.platform === "JIHUANSHE" && p.tradeType === "FLOOR",
  );

  if (kataoAuction.length === 0 || jihuansheFloor.length === 0) {
    return false;
  }

  const kataoAvg =
    kataoAuction.reduce((s, p) => s + p.price, 0) / kataoAuction.length;
  const jhsAvg =
    jihuansheFloor.reduce((s, p) => s + p.price, 0) / jihuansheFloor.length;

  return kataoAvg < jhsAvg * 0.8;
}

export type PortfolioMetrics = {
  totalMarketValue: number;
  totalCost: number;
  pnl: number;
  roiPct: number | null;
};

export function computePortfolioMetrics(
  holdings: Array<{
    quantity: number;
    avgCost: number;
    latestAvg: number | null;
  }>,
): PortfolioMetrics {
  let totalMarketValue = 0;
  let totalCost = 0;

  for (const h of holdings) {
    totalCost += h.avgCost * h.quantity;
    if (h.latestAvg != null) {
      totalMarketValue += h.latestAvg * h.quantity;
    }
  }

  const pnl = totalMarketValue - totalCost;
  const roiPct =
    totalCost > 0 ? Math.round((pnl / totalCost) * 10000) / 100 : null;

  return {
    totalMarketValue: Math.round(totalMarketValue),
    totalCost: Math.round(totalCost),
    pnl: Math.round(pnl),
    roiPct,
  };
}

export function formatPct(value: number | null): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatMoney(value: number): string {
  return `¥${value.toLocaleString("zh-CN")}`;
}
