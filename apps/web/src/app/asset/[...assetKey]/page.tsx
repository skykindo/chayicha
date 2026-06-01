import Link from "next/link";
import { notFound } from "next/navigation";
import { prisma, formatPlatformLabel, formatTrackTypeLabel } from "@/lib/db";
import { AssetCardThumb } from "@/components/asset-card-thumb";
import {
  ScatterMaChart,
  type ScatterPricePoint,
} from "@/components/charts/scatter-ma-chart";
import { formatAssetSpec } from "@/lib/asset-spec";
import { parseAssetKeyParam } from "@/lib/asset-key";
import {
  computeMarketSnapshot,
  formatMoney,
  formatPct,
  type PriceTick,
} from "@/lib/market-stats";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ assetKey: string[] }>;
};

function toScatterPoints(
  prices: Array<{
    id: string;
    capturedDate: string;
    price: number;
    platform: string;
    tradeType: string;
    cardCondition: string;
    info: string | null;
    bidCount: number | null;
    bidderCount: number | null;
    watchCount: number | null;
    isDelayed: boolean;
  }>,
): ScatterPricePoint[] {
  return prices.map((row) => ({
    id: row.id,
    date: row.capturedDate,
    price: row.price,
    platform: row.platform,
    tradeType: row.tradeType,
    cardCondition: row.cardCondition,
    info: row.info,
    bidCount: row.bidCount,
    bidderCount: row.bidderCount,
    watchCount: row.watchCount,
    isDelayed: row.isDelayed,
  }));
}

export default async function AssetDetailPage({ params }: PageProps) {
  const { assetKey: segments } = await params;
  const assetKey = parseAssetKeyParam(segments);

  let asset = null;
  let holding = null;
  let dbError: string | null = null;

  try {
    asset = await prisma.standardAsset.findUnique({
      where: { assetKey },
      include: {
        channels: true,
        prices: { orderBy: { capturedAt: "asc" } },
        holding: true,
      },
    });
    holding = asset?.holding ?? null;
  } catch (error) {
    dbError =
      error instanceof Error ? error.message : "数据库连接失败";
  }

  if (!asset && !dbError) {
    notFound();
  }

  const ticks: PriceTick[] =
    asset?.prices.map((p) => ({
      platform: p.platform,
      tradeType: p.tradeType,
      price: p.price,
      capturedDate: p.capturedDate,
    })) ?? [];

  const market = computeMarketSnapshot(ticks);
  const priceCount = asset?.prices.length ?? 0;

  return (
    <div className="min-h-full bg-zinc-950 text-zinc-50">
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="mx-auto max-w-6xl">
          <Link href="/" className="text-xs text-zinc-400 hover:text-zinc-200">
            ← 返回资产列表
          </Link>
          {asset && (
            <div className="mt-3 flex flex-col gap-6 sm:flex-row sm:items-start">
              <AssetCardThumb
                imageUrl={asset.imageUrl}
                name={asset.name}
                variant="detail"
                className="mx-auto sm:mx-0"
              />
              <div className="min-w-0 flex-1 space-y-3">
              <div>
                <p className="text-xs uppercase tracking-wider text-emerald-400">
                  {asset.category}
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-3">
                  <h1 className="text-xl font-semibold">{asset.name}</h1>
                  {holding && (
                    <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs text-emerald-400 ring-1 ring-emerald-500/30">
                      已持仓 ×{holding.quantity}
                    </span>
                  )}
                </div>
                {formatAssetSpec(asset) && (
                  <p className="mt-1 text-xs text-zinc-400">
                    {formatAssetSpec(asset)}
                  </p>
                )}
                <p className="mt-1 font-mono text-[10px] text-zinc-600">
                  {asset.assetKey}
                </p>
              </div>

              <div className="flex flex-wrap gap-4 text-sm">
                <span className="text-zinc-400">
                  最新全网价{" "}
                  <strong className="text-zinc-100">
                    {market.latestAvg != null
                      ? formatMoney(market.latestAvg)
                      : "暂无"}
                  </strong>
                </span>
                <span className="text-zinc-400">
                  日涨跌{" "}
                  <strong
                    className={
                      (market.dayChangePct ?? 0) >= 0
                        ? "text-red-400"
                        : "text-emerald-400"
                    }
                  >
                    {formatPct(market.dayChangePct)}
                  </strong>
                </span>
                <span className="text-zinc-400">
                  成交样本{" "}
                  <strong className="text-zinc-100">{priceCount} 笔</strong>
                </span>
                {holding && (
                  <span className="text-zinc-400">
                    成本 {formatMoney(holding.avgCost)} · 浮盈{" "}
                    <strong
                      className={
                        market.latestAvg != null &&
                        market.latestAvg * holding.quantity >=
                          holding.avgCost * holding.quantity
                          ? "text-red-400"
                          : "text-emerald-400"
                      }
                    >
                      {market.latestAvg != null
                        ? formatMoney(
                            market.latestAvg * holding.quantity -
                              holding.avgCost * holding.quantity,
                          )
                        : "—"}
                    </strong>
                  </span>
                )}
              </div>

              {market.hasArbitrage && (
                <span className="inline-flex animate-pulse items-center gap-1 rounded-md bg-red-500/15 px-2.5 py-1 text-xs font-medium text-red-400 ring-1 ring-red-500/40">
                  ⚠️ 今日触发套利信号：卡淘拍卖显著低于集换社一口价
                </span>
              )}

              <div className="flex flex-wrap gap-2">
                {asset.channels.map((ch) => (
                  <span
                    key={ch.id}
                    className="rounded bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-300"
                  >
                    {formatPlatformLabel(ch.platform)} ·{" "}
                    {formatTrackTypeLabel(ch.trackType)}
                    {ch.sourceUrl
                      ? " · 列表页"
                      : ch.searchKeyword
                        ? ` · ${ch.searchKeyword}`
                        : ""}
                  </span>
                ))}
              </div>
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {dbError && (
          <div className="mb-6 rounded-lg border border-amber-700/50 bg-amber-950/40 px-4 py-3 text-sm text-amber-200">
            {dbError}
          </div>
        )}

        {asset && (
          <ScatterMaChart
            points={toScatterPoints(asset.prices)}
            title="多源标的全量散点 · 情绪均线组合图"
          />
        )}
      </main>
    </div>
  );
}
