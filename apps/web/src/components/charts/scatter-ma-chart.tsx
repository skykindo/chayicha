"use client";

import { useMemo, useState } from "react";
import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
} from "recharts";
import {
  formatPlatformLabel,
  formatCardConditionLabel,
  type Platform,
} from "@/lib/db";

export type ScatterPricePoint = {
  id: string;
  date: string;
  xIndex?: number;
  price: number;
  platform: string;
  tradeType: string;
  cardCondition: string;
  info: string | null;
  bidCount: number | null;
  bidderCount: number | null;
  watchCount: number | null;
  isDelayed: boolean;
};

type MaRow = {
  date: string;
  xIndex: number;
  ma5: number | null;
  ma20: number | null;
};

const CONDITION_OPTIONS = [
  { value: "ALL", label: "全选" },
  { value: "PSA10", label: "PSA 10" },
  { value: "PSA9", label: "PSA 9" },
  { value: "CGC10", label: "CGC 10" },
  { value: "RAW", label: "裸卡(RAW)" },
] as const;

const PLATFORM_OPTIONS = [
  { value: "KATAO", label: "卡淘(KATAO)" },
  { value: "POKECOLOR", label: "卡乐(POKECOLOR)" },
  { value: "JIHUANSHE", label: "集换社(JIHUANSHE)" },
] as const;

const TRADE_OPTIONS = [
  { value: "AUCTION", label: "纯拍卖(AUCTION)" },
  { value: "FLOOR", label: "一口价(FLOOR)" },
] as const;

export type TimeRange = "1M" | "3M" | "6M" | "1Y" | "ALL";

const TIME_RANGE_OPTIONS: ReadonlyArray<{ value: TimeRange; label: string }> = [
  { value: "1M", label: "1 个月" },
  { value: "3M", label: "3 个月" },
  { value: "6M", label: "半年" },
  { value: "1Y", label: "1 年" },
  { value: "ALL", label: "全部" },
];

function getCutoffDateString(range: TimeRange): string | null {
  if (range === "ALL") return null;
  const cutoff = new Date();
  switch (range) {
    case "1M":
      cutoff.setMonth(cutoff.getMonth() - 1);
      break;
    case "3M":
      cutoff.setMonth(cutoff.getMonth() - 3);
      break;
    case "6M":
      cutoff.setMonth(cutoff.getMonth() - 6);
      break;
    case "1Y":
      cutoff.setFullYear(cutoff.getFullYear() - 1);
      break;
  }
  return cutoff.toISOString().slice(0, 10);
}

function filterByTimeRange(
  points: ScatterPricePoint[],
  range: TimeRange,
): ScatterPricePoint[] {
  const cutoff = getCutoffDateString(range);
  if (!cutoff) return points;
  return points.filter((p) => p.date >= cutoff);
}

function getPointColor(point: ScatterPricePoint): string {
  const graded =
    point.cardCondition === "PSA10" ||
    point.cardCondition === "PSA9" ||
    point.cardCondition === "CGC10";

  if (point.platform === "KATAO") {
    return point.tradeType === "AUCTION"
      ? graded
        ? "#fbbf24"
        : "#38bdf8"
      : graded
        ? "#fcd34d"
        : "#0ea5e9";
  }
  if (point.platform === "POKECOLOR") {
    return point.tradeType === "AUCTION"
      ? graded
        ? "#e879f9"
        : "#a78bfa"
      : graded
        ? "#f0abfc"
        : "#c084fc";
  }
  if (point.platform === "JIHUANSHE") {
    return graded ? "#86efac" : "#22c55e";
  }
  return graded ? "#fbbf24" : "#94a3b8";
}

function computeMaSeries(
  points: ScatterPricePoint[],
  xDates: string[],
): MaRow[] {
  const dateToIndex = new Map(xDates.map((d, i) => [d, i]));
  const byDate = new Map<string, number[]>();
  for (const p of points) {
    const bucket = byDate.get(p.date) ?? [];
    bucket.push(p.price);
    byDate.set(p.date, bucket);
  }

  const dailyAvg = xDates.map((date) => {
    const prices = byDate.get(date) ?? [];
    return {
      date,
      xIndex: dateToIndex.get(date) ?? 0,
      avg:
        prices.length > 0
          ? prices.reduce((a, b) => a + b, 0) / prices.length
          : null,
    };
  });

  return dailyAvg.map((row, index) => {
    const withAvg = dailyAvg.filter((d) => d.avg != null);
    const avgIndex = withAvg.findIndex((d) => d.date === row.date);
    const ma5Slice =
      avgIndex >= 0
        ? withAvg.slice(Math.max(0, avgIndex - 4), avgIndex + 1)
        : [];
    const ma20Slice =
      avgIndex >= 0
        ? withAvg.slice(Math.max(0, avgIndex - 19), avgIndex + 1)
        : [];

    return {
      date: row.date,
      xIndex: row.xIndex,
      ma5:
        ma5Slice.length > 0
          ? Math.round(
              ma5Slice.reduce((a, b) => a + (b.avg ?? 0), 0) / ma5Slice.length,
            )
          : null,
      ma20:
        ma20Slice.length > 0
          ? Math.round(
              ma20Slice.reduce((a, b) => a + (b.avg ?? 0), 0) /
                ma20Slice.length,
            )
          : null,
    };
  });
}

function attachXIndex(
  points: ScatterPricePoint[],
  xDates: string[],
): ScatterPricePoint[] {
  const dateToIndex = new Map(xDates.map((d, i) => [d, i]));
  return points.map((p) => ({
    ...p,
    xIndex: dateToIndex.get(p.date) ?? 0,
  }));
}

function ScatterDot(props: {
  cx?: number;
  cy?: number;
  payload?: ScatterPricePoint;
}) {
  const { cx = 0, cy = 0, payload } = props;
  if (!payload) return null;

  const color = getPointColor(payload);
  const isGraded = payload.cardCondition !== "RAW";
  const r = isGraded ? 5.5 : 4;

  return (
    <g>
      {isGraded && (
        <circle
          cx={cx}
          cy={cy}
          r={r + 3}
          fill="none"
          stroke="#fbbf24"
          strokeWidth={1.5}
          opacity={0.85}
        />
      )}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill={color}
        stroke="#18181b"
        strokeWidth={1}
        opacity={0.92}
      />
    </g>
  );
}

function TradeTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ScatterPricePoint }>;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const tradeLabel = p.tradeType === "AUCTION" ? "拍卖结标" : "一口价直售";

  return (
    <div className="max-w-xs rounded-lg border border-zinc-600 bg-zinc-950/95 px-4 py-3 text-xs shadow-2xl">
      <p className="font-medium text-sky-400">
        [{formatPlatformLabel(p.platform as Platform)}] {p.info ?? "—"}
      </p>
      <p className="mt-2 text-sm text-zinc-100">
        <span className="text-emerald-400">¥{p.price.toLocaleString("zh-CN")}</span>
        {" | "}
        <span>{formatCardConditionLabel(p.cardCondition)}</span>
        {" | "}
        <span>{tradeLabel}</span>
      </p>
      <p className="mt-2 leading-relaxed text-amber-300/90">
        [情绪热度] 本场共激战 {p.bidCount ?? "—"} 次，由{" "}
        {p.bidderCount ?? "—"} 人参与围猎！
        (触发延时: {p.isDelayed ? "是" : "否"})
      </p>
      {p.watchCount != null && (
        <p className="mt-1 text-zinc-400">围观/收藏: {p.watchCount} 人</p>
      )}
    </div>
  );
}

type TimeRangeBarProps = {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
};

function TimeRangeBar({ value, onChange }: TimeRangeBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-[11px] uppercase tracking-wider text-zinc-500">
        时间
      </span>
      {TIME_RANGE_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`rounded-md border px-2.5 py-1 text-xs transition ${
            value === opt.value
              ? "border-emerald-500 bg-emerald-600/20 text-emerald-300"
              : "border-zinc-700 bg-zinc-800/60 text-zinc-300 hover:border-zinc-500"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

type FilterBarProps = {
  label: string;
  options: ReadonlyArray<{ value: string; label: string }>;
  selected: Set<string>;
  onToggle: (value: string) => void;
  allowAll?: boolean;
};

function FilterBar({
  label,
  options,
  selected,
  onToggle,
  allowAll,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-[11px] uppercase tracking-wider text-zinc-500">
        {label}
      </span>
      {allowAll && (
        <label className="flex cursor-pointer items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-800/60 px-2 py-1 text-xs text-zinc-200">
          <input
            type="checkbox"
            checked={selected.size === options.filter((o) => o.value !== "ALL").length}
            onChange={() => {
              const values = options.filter((o) => o.value !== "ALL").map((o) => o.value);
              if (selected.size === values.length) {
                values.forEach((v) => onToggle(v));
              } else {
                values.forEach((v) => {
                  if (!selected.has(v)) onToggle(v);
                });
              }
            }}
            className="accent-emerald-500"
          />
          全选
        </label>
      )}
      {options
        .filter((o) => o.value !== "ALL")
        .map((opt) => (
          <label
            key={opt.value}
            className="flex cursor-pointer items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-800/60 px-2 py-1 text-xs text-zinc-200 transition hover:border-zinc-500"
          >
            <input
              type="checkbox"
              checked={selected.has(opt.value)}
              onChange={() => onToggle(opt.value)}
              className="accent-emerald-500"
            />
            {opt.label}
          </label>
        ))}
    </div>
  );
}

type ScatterMaChartProps = {
  points: ScatterPricePoint[];
  title?: string;
};

export function ScatterMaChart({ points, title }: ScatterMaChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>("3M");
  const [conditions, setConditions] = useState(
    () => new Set(["PSA10", "PSA9", "RAW", "CGC10"]),
  );
  const [platforms, setPlatforms] = useState(
    () => new Set(["KATAO", "POKECOLOR", "JIHUANSHE"]),
  );
  const [tradeTypes, setTradeTypes] = useState(
    () => new Set(["AUCTION", "FLOOR"]),
  );

  const toggle = (
    set: React.Dispatch<React.SetStateAction<Set<string>>>,
    value: string,
  ) => {
    set((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  const timeFiltered = useMemo(
    () => filterByTimeRange(points, timeRange),
    [points, timeRange],
  );

  const filtered = useMemo(
    () =>
      timeFiltered.filter(
        (p) =>
          conditions.has(p.cardCondition) &&
          platforms.has(p.platform) &&
          tradeTypes.has(p.tradeType) &&
          !p.info?.includes("集换价"),
      ),
    [timeFiltered, conditions, platforms, tradeTypes],
  );

  /** 唯一日期轴 — 同一天多笔成交共用同一 X 坐标，Y 轴按价格垂直排列 */
  const xDates = useMemo(
    () => Array.from(new Set(filtered.map((p) => p.date))).sort(),
    [filtered],
  );

  const scatterData = useMemo(
    () => attachXIndex(filtered, xDates),
    [filtered, xDates],
  );

  const maSeries = useMemo(
    () => computeMaSeries(scatterData, xDates),
    [scatterData, xDates],
  );

  if (points.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center rounded-xl border border-dashed border-zinc-600 bg-zinc-900/50 text-sm text-zinc-400">
        暂无价格流水，请配置 AssetChannel 并运行 npm run scraper
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-900/80 p-4">
      {title && (
        <h3 className="mb-3 text-sm font-medium text-zinc-400">{title}</h3>
      )}

      <div className="mb-4 space-y-2 rounded-lg border border-zinc-800 bg-zinc-950/50 p-3">
        <TimeRangeBar value={timeRange} onChange={setTimeRange} />
        <FilterBar
          label="品相"
          options={CONDITION_OPTIONS}
          selected={conditions}
          onToggle={(v) => toggle(setConditions, v)}
          allowAll
        />
        <FilterBar
          label="平台"
          options={PLATFORM_OPTIONS}
          selected={platforms}
          onToggle={(v) => toggle(setPlatforms, v)}
        />
        <FilterBar
          label="交易模式"
          options={TRADE_OPTIONS}
          selected={tradeTypes}
          onToggle={(v) => toggle(setTradeTypes, v)}
        />
        <p className="text-[10px] text-zinc-500">
          时间范围内 {timeFiltered.length} 笔 · 筛选后 {filtered.length} 笔 · 共{" "}
          {points.length} 笔 · MA5(红) 短期情绪 · MA20(蓝) 长期公允
        </p>
      </div>

      {filtered.length === 0 ? (
        <div className="flex h-72 items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-950/30 text-sm text-zinc-400">
          当前时间范围与筛选条件下无成交数据，请调整时间或 Tag 筛选
        </div>
      ) : (
      <ResponsiveContainer width="100%" height={380}>
        <ComposedChart
          data={maSeries}
          margin={{ top: 12, right: 16, left: 8, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
          <XAxis
            dataKey="xIndex"
            type="number"
            domain={[0, Math.max(0, xDates.length - 1)]}
            ticks={xDates.map((_, i) => i)}
            tick={{ fontSize: 10, fill: "#a1a1aa" }}
            tickFormatter={(i) => xDates[Number(i)]?.slice(5) ?? ""}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#a1a1aa" }}
            tickFormatter={(v) => `¥${Number(v).toLocaleString("zh-CN")}`}
            domain={["auto", "auto"]}
          />
          <ZAxis range={[40, 40]} />
          <Tooltip content={<TradeTooltip />} />
          <Scatter
            name="成交散点"
            data={scatterData}
            dataKey="price"
            fill="#8884d8"
            shape={<ScatterDot />}
          />
          <Line
            type="monotone"
            dataKey="ma5"
            name="MA5"
            stroke="#ef4444"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="ma20"
            name="MA20"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
      )}

      <div className="mt-2 flex flex-wrap gap-4 text-[10px] text-zinc-500">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-sky-400" />
          卡淘拍卖
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-violet-400" />
          卡乐
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
          集换社
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded-full border border-amber-400" />
          评级卡金色光环
        </span>
      </div>
    </div>
  );
}
