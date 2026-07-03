"use client";

import { Line, LineChart, ResponsiveContainer } from "recharts";

type BarItem = {
  timestamp: string;
  close: number;
};

type MiniPriceChartProps = {
  items?: BarItem[];
  className?: string;
};

export function MiniPriceChart({ items = [], className }: MiniPriceChartProps) {
  if (!items || items.length === 0) {
    return null;
  }

  const data = items.map((item) => ({
    close: Number(item.close),
  }));

  const first = data[0]?.close ?? 0;
  const last = data[data.length - 1]?.close ?? 0;
  const stroke = last >= first ? "#16a34a" : "#dc2626";

  return (
    <div className={className ?? "h-16 w-full"}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Line type="monotone" dataKey="close" stroke={stroke} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
