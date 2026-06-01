import Link from "next/link";
import { AssetCardThumb } from "@/components/asset-card-thumb";
import {
  formatMoney,
  formatPct,
  type MarketSnapshot,
} from "@/lib/market-stats";
import { assetDetailHref } from "@/lib/asset-key";

export type AssetListRow = {
  assetKey: string;
  name: string;
  imageUrl: string | null;
  category: string;
  spec: string;
  isHeld: boolean;
  priceCount: number;
  market: MarketSnapshot;
};

type AssetListProps = {
  rows: AssetListRow[];
};

/** 表格基准字号 14px，整体 +15% */
const CELL = "px-4 py-3.5 text-[16px]";
const HEAD = "px-4 py-3.5 text-[13px] uppercase tracking-wider text-zinc-500";

function ChangeCell({ pct }: { pct: number | null }) {
  if (pct == null) {
    return <span className="text-zinc-500">—</span>;
  }
  const up = pct >= 0;
  return (
    <span className={up ? "text-red-400" : "text-emerald-400"}>
      {formatPct(pct)}
    </span>
  );
}

export function AssetList({ rows }: AssetListProps) {
  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-700 px-6 py-12 text-center text-[16px] text-zinc-400">
        暂无监控资产，请在 Supabase 配置 StandardAsset 并运行 npm run scraper
      </div>
    );
  }

  return (
    <div className="overflow-visible rounded-xl border border-zinc-800">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[874px] text-left">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/80">
              <th className={`${HEAD} font-medium`}>状态</th>
              <th className={`${HEAD} font-medium`}>资产</th>
              <th className={`${HEAD} text-right font-medium`}>最新全网价</th>
              <th className={`${HEAD} text-right font-medium`}>日涨跌幅</th>
              <th className={`${HEAD} text-right font-medium`}>样本</th>
              <th className={`${HEAD} font-medium`}>异动</th>
              <th className={`${HEAD} font-medium`} />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.assetKey}
                className="group overflow-visible border-b border-zinc-800/80 transition hover:bg-zinc-900/60"
              >
                <td className={CELL}>
                  {row.isHeld ? (
                    <span className="inline-flex rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[12px] font-medium text-emerald-400 ring-1 ring-emerald-500/30">
                      已持仓
                    </span>
                  ) : (
                    <span className="text-zinc-700">—</span>
                  )}
                </td>
                <td className={`relative overflow-visible ${CELL}`}>
                  <div className="flex items-start gap-3.5">
                    <AssetCardThumb
                      imageUrl={row.imageUrl}
                      name={row.name}
                      variant="list"
                    />
                    <Link href={assetDetailHref(row.assetKey)} className="min-w-0 flex-1">
                      <p className="text-[17px] font-medium text-zinc-100 group-hover:text-emerald-300">
                        {row.name}
                      </p>
                      <div className="mt-1.5 flex flex-wrap gap-2">
                        <span className="rounded bg-zinc-800 px-2 py-0.5 text-[12px] text-zinc-400">
                          {row.category}
                        </span>
                        {row.spec && (
                          <span className="text-[12px] text-zinc-500">
                            {row.spec}
                          </span>
                        )}
                      </div>
                    </Link>
                  </div>
                </td>
                <td className={`${CELL} text-right tabular-nums`}>
                  <Link href={assetDetailHref(row.assetKey)} className="block">
                    {row.market.latestAvg != null ? (
                      formatMoney(row.market.latestAvg)
                    ) : (
                      <span className="text-zinc-500">暂无</span>
                    )}
                  </Link>
                </td>
                <td className={`${CELL} text-right tabular-nums`}>
                  <Link href={assetDetailHref(row.assetKey)} className="block">
                    <ChangeCell pct={row.market.dayChangePct} />
                  </Link>
                </td>
                <td className={`${CELL} text-right tabular-nums text-zinc-400`}>
                  <Link href={assetDetailHref(row.assetKey)} className="block">
                    {row.priceCount} 笔
                  </Link>
                </td>
                <td className={CELL}>
                  <Link href={assetDetailHref(row.assetKey)} className="block">
                    {row.market.hasArbitrage ? (
                      <span className="inline-flex animate-pulse items-center gap-1 rounded-md bg-red-500/15 px-2.5 py-1 text-[12px] font-medium text-red-400 ring-1 ring-red-500/40">
                        ⚠️ 套利
                      </span>
                    ) : (
                      <span className="text-[12px] text-zinc-600">—</span>
                    )}
                  </Link>
                </td>
                <td className={`${CELL} text-right`}>
                  <Link
                    href={assetDetailHref(row.assetKey)}
                    className="text-[14px] text-zinc-500 transition group-hover:text-emerald-400"
                  >
                    散点图 →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
