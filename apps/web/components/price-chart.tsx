"use client";

import * as React from "react";
import {
  Bar,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { Button } from "@/components/ui/button";
import {
  buildChartPoints,
  deriveOhlcBar,
  type ChartPoint,
  type OhlcBar,
} from "@/lib/chart-indicators";

type PriceChartProps = {
  data: Array<Partial<OhlcBar> & { timestamp: string; close: number }>;
  labels?: Partial<PriceChartLabels>;
};

export type PriceChartLabels = {
  candles: string;
  movingAverage: string;
  bollingerBands: string;
  rsi: string;
  volume: string;
  empty: string;
  open: string;
  high: string;
  low: string;
  close: string;
  movingAverageShort: string;
  volumeShort: string;
};

const DEFAULT_PRICE_CHART_LABELS: PriceChartLabels = {
  candles: "Candles",
  movingAverage: "MA(20)",
  bollingerBands: "BOLL",
  rsi: "RSI",
  volume: "Volume",
  empty: "No price data available for chart.",
  open: "O",
  high: "H",
  low: "L",
  close: "C",
  movingAverageShort: "MA20",
  volumeShort: "Vol",
};

type CandleShapeProps = {
  x?: number;
  width?: number;
  payload?: ChartPoint;
  domainMin: number;
  domainMax: number;
  plotHeight: number;
};

function CandlestickShape(props: CandleShapeProps) {
  const { x = 0, width = 0, payload, domainMin, domainMax, plotHeight } = props;
  if (!payload) {
    return null;
  }

  const scale = (value: number) =>
    plotHeight - ((value - domainMin) / (domainMax - domainMin)) * plotHeight + 5;

  const { open, close, high, low } = payload;
  const isUp = close >= open;
  const color = isUp ? "hsl(142 71% 45%)" : "hsl(0 84% 60%)";
  const centerX = x + width / 2;
  const bodyTop = scale(Math.max(open, close));
  const bodyBottom = scale(Math.min(open, close));
  const bodyHeight = Math.max(bodyBottom - bodyTop, 1);
  const bodyWidth = Math.max(width * 0.6, 3);

  return (
    <g>
      <line
        x1={centerX}
        x2={centerX}
        y1={scale(high)}
        y2={scale(low)}
        stroke={color}
        strokeWidth={1.5}
      />
      <rect
        x={centerX - bodyWidth / 2}
        y={bodyTop}
        width={bodyWidth}
        height={bodyHeight}
        fill={color}
        stroke={color}
        strokeWidth={1}
      />
    </g>
  );
}

export function PriceChart({ data, labels }: PriceChartProps) {
  const [showCandles, setShowCandles] = React.useState(true);
  const [showMa, setShowMa] = React.useState(true);
  const [showBoll, setShowBoll] = React.useState(false);
  const [showRsi, setShowRsi] = React.useState(false);
  const [showVolume, setShowVolume] = React.useState(true);
  const chartLabels: PriceChartLabels = { ...DEFAULT_PRICE_CHART_LABELS, ...labels };

  const normalized = React.useMemo(
    () => data.map((bar) => deriveOhlcBar(bar)),
    [data],
  );
  const chartData = React.useMemo(() => buildChartPoints(normalized), [normalized]);

  if (!chartData.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-md border text-sm text-muted-foreground">
        {chartLabels.empty}
      </div>
    );
  }

  const minPrice = Math.min(...normalized.map((bar) => bar.low));
  const maxPrice = Math.max(...normalized.map((bar) => bar.high));
  const padding = Math.max((maxPrice - minPrice) * 0.08, 1);
  const domainMin = minPrice - padding;
  const domainMax = maxPrice + padding;
  const plotHeight = showRsi ? 230 : 310;
  const hasVolume = normalized.some((item) => item.volume !== undefined);

  return (
    <div className="mt-4 w-full space-y-3">
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant={showCandles ? "default" : "outline"}
          onClick={() => setShowCandles((value) => !value)}
        >
          {chartLabels.candles}
        </Button>
        <Button
          type="button"
          size="sm"
          variant={showMa ? "default" : "outline"}
          onClick={() => setShowMa((value) => !value)}
        >
          {chartLabels.movingAverage}
        </Button>
        <Button
          type="button"
          size="sm"
          variant={showBoll ? "default" : "outline"}
          onClick={() => setShowBoll((value) => !value)}
        >
          {chartLabels.bollingerBands}
        </Button>
        <Button
          type="button"
          size="sm"
          variant={showRsi ? "default" : "outline"}
          onClick={() => setShowRsi((value) => !value)}
        >
          {chartLabels.rsi}
        </Button>
        <Button
          type="button"
          size="sm"
          variant={showVolume ? "default" : "outline"}
          onClick={() => setShowVolume((value) => !value)}
          disabled={!hasVolume}
        >
          {chartLabels.volume}
        </Button>
      </div>

      <div className="w-full" style={{ height: showRsi ? 260 : 340 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground))" opacity={0.2} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              minTickGap={30}
            />
            <YAxis
              yAxisId="price"
              domain={[domainMin, domainMax]}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              tickFormatter={(value) => `$${Number(value).toFixed(0)}`}
              width={60}
            />
            {showVolume && hasVolume ? (
              <YAxis
                yAxisId="volume"
                orientation="right"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                tickFormatter={(value) => `${Number(value / 1000).toFixed(0)}k`}
                width={60}
              />
            ) : null}
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
                  <div className="rounded-lg border bg-background p-2 shadow-sm">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="col-span-2 font-medium">{label}</div>
                      <div>{chartLabels.open}: ${point.open.toFixed(2)}</div>
                      <div>{chartLabels.high}: ${point.high.toFixed(2)}</div>
                      <div>{chartLabels.low}: ${point.low.toFixed(2)}</div>
                      <div>{chartLabels.close}: ${point.close.toFixed(2)}</div>
                      {point.ma20 ? <div>{chartLabels.movingAverageShort}: ${point.ma20.toFixed(2)}</div> : null}
                      {point.rsi ? <div>{chartLabels.rsi}: {point.rsi.toFixed(1)}</div> : null}
                      {point.volume ? <div>{chartLabels.volumeShort}: {point.volume.toLocaleString()}</div> : null}
                    </div>
                  </div>
                );
              }}
            />
            {showCandles ? (
              <Bar
                yAxisId="price"
                dataKey="close"
                barSize={12}
                shape={(props) => (
                  <CandlestickShape
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
            ) : (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="close"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
              />
            )}
            {showMa ? (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="ma20"
                stroke="hsl(var(--muted-foreground))"
                strokeWidth={2}
                dot={false}
                strokeDasharray="4 4"
                connectNulls
              />
            ) : null}
            {showBoll ? (
              <>
                <Line yAxisId="price" type="monotone" dataKey="bollUpper" stroke="#f59e0b" dot={false} strokeWidth={1.5} connectNulls />
                <Line yAxisId="price" type="monotone" dataKey="bollMiddle" stroke="#94a3b8" dot={false} strokeWidth={1.5} connectNulls />
                <Line yAxisId="price" type="monotone" dataKey="bollLower" stroke="#f59e0b" dot={false} strokeWidth={1.5} connectNulls />
              </>
            ) : null}
            {showVolume && hasVolume ? (
              <Bar yAxisId="volume" dataKey="volume" fill="hsl(var(--primary))" opacity={0.18} radius={[3, 3, 0, 0]} />
            ) : null}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {showRsi ? (
        <div className="h-[120px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 0, right: 5, left: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground))" opacity={0.2} />
              <XAxis dataKey="date" hide />
              <YAxis
                domain={[0, 100]}
                tickLine={false}
                axisLine={false}
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                width={40}
              />
              <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
              <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="rsi" stroke="#8b5cf6" strokeWidth={2} dot={false} connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </div>
  );
}
