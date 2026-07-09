"use client";

import * as React from "react";
import {
  Bar,
  Cell,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  buildChartPoints,
  deriveOhlcBar,
  type ChartPoint,
  type OhlcBar,
} from "@/lib/chart-indicators";

type CompactCandlestickChartProps = {
  data: Array<Partial<OhlcBar> & { timestamp: string; close: number }>;
  emptyMessage: string;
  className?: string;
  candleBarSize?: number;
  plotHeight?: number;
  showGrid?: boolean;
};

type CompactCandleShapeProps = {
  x?: number;
  width?: number;
  payload?: ChartPoint;
  domainMin: number;
  domainMax: number;
  plotHeight: number;
};

function CompactCandleShape({
  x = 0,
  width = 0,
  payload,
  domainMin,
  domainMax,
  plotHeight,
}: CompactCandleShapeProps) {
  if (!payload) {
    return null;
  }

  const priceRange = Math.max(domainMax - domainMin, 1);
  const scalePriceToY = (value: number) =>
    plotHeight - ((value - domainMin) / priceRange) * plotHeight + 4;

  const isUp = payload.close >= payload.open;
  const color = isUp ? "hsl(142 71% 45%)" : "hsl(0 84% 60%)";
  const centerX = x + width / 2;
  const bodyTop = scalePriceToY(Math.max(payload.open, payload.close));
  const bodyBottom = scalePriceToY(Math.min(payload.open, payload.close));
  const bodyHeight = Math.max(bodyBottom - bodyTop, 1);
  const bodyWidth = Math.max(width * 0.58, 2.5);

  return (
    <g>
      <line
        x1={centerX}
        x2={centerX}
        y1={scalePriceToY(payload.high)}
        y2={scalePriceToY(payload.low)}
        stroke={color}
        strokeWidth={1.2}
      />
      <rect
        x={centerX - bodyWidth / 2}
        y={bodyTop}
        width={bodyWidth}
        height={bodyHeight}
        fill={color}
        stroke={color}
      />
    </g>
  );
}

export function CompactCandlestickChart({
  data,
  emptyMessage,
  className,
  candleBarSize = 8,
  plotHeight = 142,
  showGrid = false,
}: CompactCandlestickChartProps) {
  const normalizedBars = React.useMemo(
    () => data.map((bar) => deriveOhlcBar(bar)),
    [data],
  );
  const chartData = React.useMemo(() => buildChartPoints(normalizedBars), [normalizedBars]);

  if (!chartData.length) {
    return (
      <div className={className ?? "h-40 w-full"}>
        <div className="flex h-full items-center justify-center rounded-md border text-sm text-muted-foreground">
          {emptyMessage}
        </div>
      </div>
    );
  }

  const minPrice = Math.min(...normalizedBars.map((bar) => bar.low));
  const maxPrice = Math.max(...normalizedBars.map((bar) => bar.high));
  const padding = Math.max((maxPrice - minPrice) * 0.08, 1);
  const domainMin = minPrice - padding;
  const domainMax = maxPrice + padding;
  const hasVolume = normalizedBars.some((bar) => bar.volume !== undefined);

  return (
    <div className={className ?? "h-40 w-full"}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
          {showGrid ? (
            <CartesianGrid
              stroke="hsl(var(--border))"
              strokeDasharray="3 6"
              vertical={false}
              opacity={0.45}
            />
          ) : null}
          <XAxis dataKey="date" hide />
          <YAxis yAxisId="price" domain={[domainMin, domainMax]} hide />
          {hasVolume ? <YAxis yAxisId="volume" orientation="right" hide /> : null}
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) {
                return null;
              }
              const point = payload[0]?.payload as ChartPoint | undefined;
              if (!point) {
                return null;
              }
              return (
                <div className="rounded-lg border bg-background p-2 text-xs shadow-sm">
                  <div className="font-medium">{label}</div>
                  <div>O: {point.open.toFixed(2)}</div>
                  <div>H: {point.high.toFixed(2)}</div>
                  <div>L: {point.low.toFixed(2)}</div>
                  <div>C: {point.close.toFixed(2)}</div>
                  {point.ma20 ? <div>MA20: {point.ma20.toFixed(2)}</div> : null}
                  {point.volume ? <div>Vol: {point.volume.toLocaleString()}</div> : null}
                </div>
              );
            }}
          />
          <Bar
            yAxisId="price"
            dataKey="close"
            barSize={candleBarSize}
            shape={(props) => (
              <CompactCandleShape
                {...props}
                payload={props.payload as ChartPoint}
                domainMin={domainMin}
                domainMax={domainMax}
                plotHeight={plotHeight}
              />
            )}
          >
            {chartData.map((entry) => (
              <Cell key={entry.timestamp} fill="transparent" />
            ))}
          </Bar>
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="ma20"
            stroke="hsl(var(--muted-foreground))"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 4"
            connectNulls
          />
          {hasVolume ? (
            <Bar
              yAxisId="volume"
              dataKey="volume"
              fill="hsl(var(--primary))"
              opacity={0.14}
              radius={[2, 2, 0, 0]}
            />
          ) : null}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
