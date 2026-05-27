import Link from "next/link";
import {
  prisma,
  formatPlatformLabel,
  formatTrackTypeLabel,
  type StandardAsset,
  type PriceStream,
  type AssetChannel,
} from "@/lib/db";
import { MultiSeriesKLineChart, type KLinePoint } from "@/components/charts/multi-series-chart";
import { formatDate } from "@/lib/utils";
import { formatAssetSpec } from "@/lib/asset-spec";

export const dynamic = "force-dynamic";

type AssetBundle = StandardAsset & {
  channels: AssetChannel[];
  prices: PriceStream[];
};

function buildSeriesKeys(prices: PriceStream[]) {
  const keys = new Set<string>();
  for (const p of prices) {
    keys.add(`${p.platform}_${p.tradeType}`);
  }
  if (keys.size > 1) keys.add("avg");
  return Array.from(keys).sort();
}

function buildChartData(prices: PriceStream[]): {
  data: KLinePoint[];
  seriesKeys: string[];
} {
  const seriesKeys = buildSeriesKeys(prices);
  const byDate = new Map<string, KLinePoint>();

  for (const row of prices) {
    const date = formatDate(row.capturedAt);
    const key = `${row.platform}_${row.tradeType}`;
    const point = byDate.get(date) ?? { date };
    point[key] = row.price;
    byDate.set(date, point);
  }

  const data = Array.from(byDate.values())
    .sort((a, b) => String(a.date).localeCompare(String(b.date)))
    .map((point) => {
      const nums = seriesKeys
        .filter((k) => k !== "avg")
        .map((k) => point[k])
        .filter((v): v is number => typeof v === "number");
      if (nums.length > 0) {
        point.avg = Math.round(nums.reduce((a, b) => a + b, 0) / nums.length);
      }
      return point;
    });

  return { data, seriesKeys };
}

export default async function DashboardPage() {
  let assets: AssetBundle[] = [];
  let dbError: string | null = null;

  try {
    assets = await prisma.standardAsset.findMany({
      where: { isMonitoring: true },
      include: {
        channels: true,
        prices: { orderBy: { capturedAt: "asc" }, take: 180 },
      },
      orderBy: { createdAt: "desc" },
    });
  } catch (error) {
    dbError =
      error instanceof Error
        ? error.message
        : "数据库连接失败，请检查 .env 中的 DATABASE_URL";
  }

  return (
    <div className="min-h-full bg-zinc-950 text-zinc-50">
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div>
            <Link href="/" className="text-xs text-zinc-400 hover:text-zinc-200">
              ← 返回首页
            </Link>
            <h1 className="mt-1 text-xl font-semibold">标准资产池看板</h1>
          </div>
          <span className="rounded-full bg-zinc-800 px-3 py-1 text-xs text-zinc-300">
            {assets.length} 个标准资产
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {dbError && (
          <div className="mb-6 rounded-lg border border-amber-700/50 bg-amber-950/40 px-4 py-3 text-sm text-amber-200">
            {dbError}
          </div>
        )}

        {assets.length === 0 && !dbError && (
          <div className="rounded-xl border border-dashed border-zinc-700 px-6 py-12 text-center text-zinc-400">
            暂无 StandardAsset。请在 Supabase 配置标准资产 + AssetChannel，然后运行 npm run scraper
          </div>
        )}

        <div className="grid gap-10">
          {assets.map((asset) => {
            const { data, seriesKeys } = buildChartData(asset.prices);
            return (
              <section key={asset.id} className="space-y-3">
                <div>
                  <p className="text-xs uppercase tracking-wider text-emerald-400">
                    {asset.category}
                  </p>
                  <h2 className="text-lg font-semibold">{asset.name}</h2>
                  {formatAssetSpec(asset) && (
                    <p className="mt-1 text-xs text-zinc-400">
                      {formatAssetSpec(asset)}
                    </p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-2">
                    {asset.channels.map((ch) => (
                      <span
                        key={ch.id}
                        className="rounded bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-300"
                      >
                        {formatPlatformLabel(ch.platform)} · {formatTrackTypeLabel(ch.trackType)}
                        {ch.sourceUrl
                          ? " · 列表页"
                          : ch.searchKeyword
                            ? ` · ${ch.searchKeyword}`
                            : ""}
                      </span>
                    ))}
                  </div>
                </div>
                <MultiSeriesKLineChart
                  data={data}
                  seriesKeys={seriesKeys}
                  title="多平台价格流水（含均值线 avg）"
                />
              </section>
            );
          })}
        </div>
      </main>
    </div>
  );
}
