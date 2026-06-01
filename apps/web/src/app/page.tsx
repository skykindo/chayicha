import { prisma } from "@/lib/db";
import { PortfolioSummary } from "@/components/portfolio-summary";
import { AssetList, type AssetListRow } from "@/components/asset-list";
import { SectionHeader } from "@/components/section-header";
import { formatAssetSpec } from "@/lib/asset-spec";
import {
  computeMarketSnapshot,
  computePortfolioMetrics,
  type PriceTick,
} from "@/lib/market-stats";

export const dynamic = "force-dynamic";

function toPriceTicks(
  prices: Array<{
    platform: string;
    tradeType: string;
    price: number;
    capturedDate: string;
  }>,
): PriceTick[] {
  return prices.map((p) => ({
    platform: p.platform,
    tradeType: p.tradeType,
    price: p.price,
    capturedDate: p.capturedDate,
  }));
}

export default async function HomePage() {
  let dbError: string | null = null;
  let assetRows: AssetListRow[] = [];
  let portfolioMetrics = null;
  let holdingCount = 0;

  try {
    let heldAssetKeys = new Set<string>();

    try {
      heldAssetKeys = new Set(
        (await prisma.holding.findMany({ select: { assetKey: true } })).map(
          (h) => h.assetKey,
        ),
      );
      holdingCount = heldAssetKeys.size;
    } catch (holdingError) {
      console.warn("[home] Holding 表不可用，跳过持仓摘要:", holdingError);
    }

    const assets = await prisma.standardAsset.findMany({
      where: { isMonitoring: true },
      include: {
        prices: {
          orderBy: { capturedAt: "desc" },
          select: {
            platform: true,
            tradeType: true,
            price: true,
            capturedDate: true,
          },
        },
      },
      orderBy: { name: "asc" },
    });

    assetRows = assets.map((asset) => {
      const ticks = toPriceTicks(asset.prices);
      return {
        assetKey: asset.assetKey,
        name: asset.name,
        imageUrl: asset.imageUrl,
        category: asset.category,
        spec: formatAssetSpec(asset),
        isHeld: heldAssetKeys.has(asset.assetKey),
        priceCount: asset.prices.length,
        market: computeMarketSnapshot(ticks),
      };
    });

    if (holdingCount > 0) {
      try {
        const holdings = await prisma.holding.findMany({
          include: {
            asset: {
              include: {
                prices: {
                  orderBy: { capturedAt: "desc" },
                  select: {
                    platform: true,
                    tradeType: true,
                    price: true,
                    capturedDate: true,
                  },
                },
              },
            },
          },
        });

        portfolioMetrics = computePortfolioMetrics(
          holdings.map((h) => ({
            quantity: h.quantity,
            avgCost: h.avgCost,
            latestAvg: computeMarketSnapshot(toPriceTicks(h.asset.prices))
              .latestAvg,
          })),
        );
      } catch (holdingError) {
        console.warn("[home] 持仓聚合失败:", holdingError);
      }
    }
  } catch (error) {
    dbError =
      error instanceof Error
        ? error.message
        : "数据库连接失败，请检查 .env 中的 DATABASE_URL";
  }

  return (
    <div className="min-h-full bg-zinc-950 text-zinc-50">
      <header className="border-b border-zinc-800 px-6 py-5">
        <div className="mx-auto max-w-6xl">
          <p className="text-[14px] uppercase tracking-widest text-emerald-400">
            EveryAsset-KLine
          </p>
          <h1 className="mt-1.5 text-[23px] font-semibold">万物皆可K线</h1>
          <p className="mt-1 text-[14px] text-zinc-500">
            点击资产行进入独立散点趋势页
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-10 px-6 py-8">
        {dbError && (
          <div className="rounded-lg border border-amber-700/50 bg-amber-950/40 px-4 py-3.5 text-[16px] text-amber-200">
            {dbError}
          </div>
        )}

        <PortfolioSummary
          metrics={portfolioMetrics}
          holdingCount={holdingCount}
        />

        <section className="space-y-4">
          <SectionHeader
            label="Assets"
            title="监控资产列表"
            description="每张卡对应独立散点图 · 大盘行情与个人持仓分离"
            labelTone="sky"
            trailing={
              <span className="rounded-full bg-zinc-800 px-3.5 py-1.5 text-[14px] text-zinc-400">
                {assetRows.length} 张
              </span>
            }
          />

          <AssetList rows={assetRows} />
        </section>
      </main>
    </div>
  );
}
