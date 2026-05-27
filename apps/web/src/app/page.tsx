import Link from "next/link";
import { KLineChart } from "@/components/charts/kline-chart";

const demoData = [
  { date: "05-01", open: 1200, high: 1250, low: 1180, close: 1220 },
  { date: "05-02", open: 1220, high: 1230, low: 1150, close: 1160 },
  { date: "05-03", open: 1160, high: 1180, low: 1100, close: 1110 },
  { date: "05-04", open: 1110, high: 1120, low: 1050, close: 1060 },
  { date: "05-05", open: 1060, high: 1080, low: 1020, close: 1040 },
];

export default function HomePage() {
  return (
    <div className="min-h-full bg-zinc-950 text-zinc-50">
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-emerald-400">
              EveryAsset-KLine
            </p>
            <h1 className="text-xl font-semibold">万物皆可K线</h1>
          </div>
          <Link
            href="/dashboard"
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500"
          >
            进入看板
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <section className="mb-10 grid gap-6 md:grid-cols-3">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
            <p className="text-sm text-emerald-400">StandardAsset</p>
            <p className="mt-2 font-medium">标准资产池 — 跨平台同款卡牌聚合</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
            <p className="text-sm text-sky-400">AssetChannel · WEB</p>
            <p className="mt-2 font-medium">卡淘/卡乐列表页扫描，自动匹配结标与地板价</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
            <p className="text-sm text-violet-400">AssetChannel · VISION_AI</p>
            <p className="mt-2 font-medium">集换社/闲鱼 — AI 视觉外挂预留</p>
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-lg font-medium">K 线预览（Demo 数据）</h2>
          <KLineChart data={demoData} targetPrice={1100} title="示例：日版奇树 SAR" />
        </section>
      </main>
    </div>
  );
}
