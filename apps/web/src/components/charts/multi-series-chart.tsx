"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { formatPlatformSeriesKey } from "@/lib/db";

export type KLinePoint = {
  date: string;
  [series: string]: string | number;
};

const SERIES_COLORS: Record<string, string> = {
  KATAO_AUCTION: "#38bdf8",
  KATAO_FLOOR: "#0ea5e9",
  POKECOLOR_FLOOR: "#a78bfa",
  POKECOLOR_AUCTION: "#c084fc",
  JIHUANSHE_FLOOR: "#f472b6",
  avg: "#22c55e",
};

type MultiSeriesChartProps = {
  data: KLinePoint[];
  seriesKeys: string[];
  title?: string;
};

export function MultiSeriesKLineChart({
  data,
  seriesKeys,
  title,
}: MultiSeriesChartProps) {
  if (data.length === 0 || seriesKeys.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-zinc-600 bg-zinc-900/50 text-sm text-zinc-400">
        暂无价格流水，请配置 AssetChannel 并运行 npm run scraper
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-900/80 p-4">
      {title && (
        <h3 className="mb-2 text-sm font-medium text-zinc-400">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#a1a1aa" }} />
          <YAxis
            tick={{ fontSize: 11, fill: "#a1a1aa" }}
            tickFormatter={(v) => `¥${Number(v).toLocaleString("zh-CN")}`}
          />
          <Tooltip
            contentStyle={{
              background: "#18181b",
              border: "1px solid #3f3f46",
              borderRadius: "8px",
            }}
            formatter={(value, name) => [
              value != null ? `¥${Number(value).toLocaleString("zh-CN")}` : "—",
              formatPlatformSeriesKey(String(name)),
            ]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {seriesKeys.map((key) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={formatPlatformSeriesKey(key)}
              stroke={SERIES_COLORS[key] ?? "#94a3b8"}
              dot={{ r: 3 }}
              strokeWidth={2}
              connectNulls
            />
          ))}
          {seriesKeys.includes("avg") && (
            <Bar dataKey="avg" fill="#22c55e" opacity={0.25} barSize={8} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
