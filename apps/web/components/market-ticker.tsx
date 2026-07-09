"use client";

import { memo, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { useMarketColorsContext } from "@/context/market-colors-context";
import { createDataTrustSignal, getDataTrustTitle } from "@/lib/data-trust";

type TickerItem = {
  code: string;
  name: string;
  close: number | null;
  change: number | null;
  changePercent: number | null;
  sparkline?: number[];
  region?: string;
  status?: string | null;
  freshness?: string | null;
  source?: string | null;
  provider?: string | null;
  requested_provider?: string | null;
  effective_provider?: string | null;
  generated_at?: string | null;
  no_data_reason?: string | null;
};

interface MarketTickerProps {
  items: TickerItem[];
  labels?: {
    allMarkets: string;
    cnMarket: string;
    hkMarket: string;
    usMarket: string;
  };
  className?: string;
}

function formatNumber(value: number | null, locale: string, fallback: string): string {
  if (value === null) return fallback;
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatChange(value: number | null, locale: string, fallback: string): string {
  if (value === null) return fallback;
  const formatted = formatNumber(Math.abs(value), locale, fallback);
  if (value > 0) return `+${formatted}`;
  if (value < 0) return `-${formatted}`;
  return formatted;
}

function formatPercent(value: number | null, locale: string, fallback: string): string {
  if (value === null) return fallback;
  const formatted = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
    style: "percent",
  }).format(Math.abs(value));
  if (value > 0) return `+${formatted}`;
  if (value < 0) return `-${formatted}`;
  return formatted;
}

function getTickerMovementColor(value: number, getMovementColor: (value: number) => string): string {
  if (value === 0) {
    return "text-muted-foreground";
  }
  return getMovementColor(value);
}

function buildSparklinePath(values: number[], width: number, height: number): string | null {
  const points = values.filter((value) => Number.isFinite(value));
  if (points.length < 2) {
    return null;
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  return points
    .map((value, index) => {
      const x = (index / (points.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function Sparkline({
  values,
  movement,
}: {
  values: number[] | undefined;
  movement: number;
}) {
  const width = 124;
  const height = 34;
  const path = buildSparklinePath(values ?? [], width, height);
  const movementClassName = movement < 0 ? "stroke-negative" : movement > 0 ? "stroke-positive" : "stroke-muted-foreground";

  return (
    <svg
      className="mt-2 h-9 w-full overflow-visible"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-hidden="true"
      focusable="false"
    >
      <path d={`M0,${height - 3} L${width},${height - 3}`} className="stroke-border" strokeWidth="1" strokeDasharray="2 5" />
      {path ? (
        <path
          d={path}
          className={movementClassName}
          fill="none"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : null}
    </svg>
  );
}

function MarketTickerComponent({ items, labels, className }: MarketTickerProps) {
  const locale = "zh-CN";
  const [selectedMarket, setSelectedMarket] = useState<string>("all");
  const { getMovementColor } = useMarketColorsContext();
  const resolvedLabels = labels ?? {
    allMarkets: "All",
    cnMarket: "CN",
    hkMarket: "HK",
    usMarket: "US",
  };

  const marketOptions = useMemo(
    () => [
      { value: "all", label: resolvedLabels.allMarkets },
      { value: "CN", label: resolvedLabels.cnMarket },
      { value: "HK", label: resolvedLabels.hkMarket },
      { value: "US", label: resolvedLabels.usMarket },
    ],
    [
      resolvedLabels.allMarkets,
      resolvedLabels.cnMarket,
      resolvedLabels.hkMarket,
      resolvedLabels.usMarket,
    ],
  );

  const filteredItems = useMemo(
    () => selectedMarket === "all"
      ? items
      : items.filter((item) => item.region === selectedMarket),
    [items, selectedMarket],
  );

  return (
    <div
      className={cn(
        "rounded-md border bg-card/95 text-foreground shadow-[0_0_0_1px_hsl(var(--primary)/0.05)]",
        className
      )}
    >
      <div className="flex flex-col gap-2 overflow-hidden p-2 lg:flex-row lg:items-stretch">
        <div className="flex shrink-0 items-center gap-1 rounded-sm border bg-background/70 p-0.5 lg:self-start">
          {marketOptions.map((option) => {
            const isSelected = selectedMarket === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={isSelected}
                className={cn(
                  "h-8 rounded-sm px-2 text-xs font-medium transition-colors hover:bg-accent",
                  isSelected ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground",
                )}
                onClick={() => setSelectedMarket(option.value)}
              >
                {option.label}
              </button>
            );
          })}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 max-w-full gap-2 overflow-x-auto whitespace-nowrap scrollbar-thin [contain:layout_paint]">
            {filteredItems.map((item) => {
              const changeValue = item.change ?? 0;
              const changeColor = getTickerMovementColor(changeValue, getMovementColor);
              const trustSignal = createDataTrustSignal({
                status: item.status,
                freshness: item.freshness,
                source: item.source,
                provider: item.provider,
                requested_provider: item.requested_provider,
                effective_provider: item.effective_provider,
                generated_at: item.generated_at,
                no_data_reason: item.no_data_reason,
              });
              const trustTitle = getDataTrustTitle(trustSignal);

              return (
                <div
                  key={item.code}
                  className="inline-flex min-h-[7.25rem] w-[13.5rem] shrink-0 flex-col rounded-sm border bg-background/60 px-2.5 py-2 font-mono text-sm transition-colors hover:border-primary/30 hover:bg-accent/50"
                  title={trustTitle}
                  aria-label={`${item.name} ${trustTitle}`}
                >
                  <span className="min-w-0 truncate font-sans text-xs font-medium text-muted-foreground">{item.name}</span>
                  <span className="mt-1 shrink-0 text-xl font-semibold tabular-nums">
                    {formatNumber(item.close, locale, "--")}
                  </span>
                  <span className={cn("mt-0.5 shrink-0 text-xs tabular-nums", changeColor)}>
                    {formatChange(item.change, locale, "--")} ({formatPercent(item.changePercent, locale, "--")})
                  </span>
                  <Sparkline values={item.sparkline} movement={changeValue} />
                  <span className="sr-only">{trustTitle}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export const MarketTicker = memo(MarketTickerComponent);
MarketTicker.displayName = "MarketTicker";
