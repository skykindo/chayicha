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
  ReferenceLine,
} from "recharts";

export type KLinePoint = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

type KLineChartProps = {
  data: KLinePoint[];
  targetPrice?: number | null;
  title?: string;
};

export function KLineChart({ data, targetPrice, title }: KLineChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-zinc-600 bg-zinc-900/50 text-sm text-zinc-400">
        暂无 K 线数据，等待爬虫写入 PriceHistory
      </div>
    );
  }

  const latest = data[data.length - 1];

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-900/80 p-4">
      {title && (
        <h3 className="mb-2 text-sm font-medium text-zinc-400">{title}</h3>
      )}
      <p className="mb-3 text-sm text-zinc-300">
        最新收盘价{" "}
        <span className="text-lg font-semibold text-emerald-400">
          ¥{latest.close.toLocaleString("zh-CN")}
        </span>
        <span className="ml-2 text-xs text-zinc-500">{latest.date}</span>
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
          <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#a1a1aa" }} />
          <YAxis
            tick={{ fontSize: 12, fill: "#a1a1aa" }}
            domain={["auto", "auto"]}
            tickFormatter={(v) => `¥${Number(v).toLocaleString("zh-CN")}`}
          />
          <Tooltip
            contentStyle={{
              background: "#18181b",
              border: "1px solid #3f3f46",
              borderRadius: "8px",
            }}
            formatter={(value) => [
              `¥${Number(value).toLocaleString("zh-CN")}`,
              "价格",
            ]}
            labelFormatter={(label) => `日期: ${label}`}
          />
          <Bar dataKey="close" fill="#22c55e" opacity={0.85} barSize={24} />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#4ade80"
            dot={{ fill: "#4ade80", r: 4 }}
            strokeWidth={2}
          />
          {targetPrice != null && (
            <ReferenceLine
              y={targetPrice}
              stroke="#ef4444"
              strokeDasharray="4 4"
              label={{ value: "抄底价", fill: "#ef4444", fontSize: 12 }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
