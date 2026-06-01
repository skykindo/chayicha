import {
  formatMoney,
  formatPct,
  type PortfolioMetrics,
} from "@/lib/market-stats";
import { SectionHeader } from "@/components/section-header";

type PortfolioSummaryProps = {
  metrics: PortfolioMetrics | null;
  holdingCount: number;
};

export function PortfolioSummary({
  metrics,
  holdingCount,
}: PortfolioSummaryProps) {
  const isEmpty = holdingCount === 0 || !metrics;

  return (
    <section className="space-y-4">
      <SectionHeader
        label="My Portfolio"
        title="个人资产动态摘要"
        description={
          isEmpty
            ? undefined
            : `基于持仓成本 vs 最新全网公允均价 · ${holdingCount} 个标的`
        }
        labelTone="emerald"
      />

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-7">
        {isEmpty ? (
          <p className="text-[16px] text-zinc-400">
            当前无实际持仓，请通过大盘列表关注异动。
          </p>
        ) : (
          <div className="grid gap-5 sm:grid-cols-3">
            <MetricCard
              label="持仓总市值"
              value={formatMoney(metrics!.totalMarketValue)}
            />
            <MetricCard
              label="累计盈亏 (P&L)"
              value={`${metrics!.pnl >= 0 ? "+" : ""}${formatMoney(metrics!.pnl)}`}
              valueClass={
                metrics!.pnl >= 0 ? "text-red-400" : "text-emerald-400"
              }
              sub={`成本基准 ${formatMoney(metrics!.totalCost)}`}
            />
            <MetricCard
              label="账户总回报率 (ROI)"
              value={formatPct(metrics!.roiPct)}
              valueClass={
                (metrics!.roiPct ?? 0) >= 0 ? "text-red-400" : "text-emerald-400"
              }
            />
          </div>
        )}
      </div>
    </section>
  );
}

function MetricCard({
  label,
  value,
  valueClass = "text-zinc-50",
  sub,
}: {
  label: string;
  value: string;
  valueClass?: string;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-zinc-700/80 bg-zinc-950/50 px-5 py-4">
      <p className="text-[13px] uppercase tracking-wider text-zinc-500">
        {label}
      </p>
      <p
        className={`mt-2.5 text-[28px] font-semibold tabular-nums ${valueClass}`}
      >
        {value}
      </p>
      {sub && <p className="mt-1.5 text-[12px] text-zinc-500">{sub}</p>}
    </div>
  );
}
