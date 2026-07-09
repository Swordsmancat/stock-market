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
        "border-b bg-background/95 text-foreground",
        className
      )}
    >
      <div className="flex items-center gap-3 overflow-hidden px-3 py-2 sm:px-4">
        <div className="flex shrink-0 items-center gap-1 rounded-sm border bg-card p-0.5">
          {marketOptions.map((option) => {
            const isSelected = selectedMarket === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={isSelected}
                className={cn(
                  "h-7 rounded-sm px-2 text-xs font-medium transition-colors hover:bg-muted",
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
          <div className="flex min-w-0 max-w-full gap-3 overflow-x-auto whitespace-nowrap scrollbar-thin [contain:layout_paint]">
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
                  className="inline-flex min-w-[15rem] items-center gap-2 rounded-sm border bg-card px-2 py-1 font-mono text-sm"
                  title={trustTitle}
                  aria-label={`${item.name} ${trustTitle}`}
                >
                  <span className="truncate font-sans text-muted-foreground">{item.name}</span>
                  <span className="shrink-0 font-bold">
                    {formatNumber(item.close, locale, "--")}
                  </span>
                  <span className={cn("shrink-0", changeColor)}>
                    {formatChange(item.change, locale, "--")}{" "}
                    ({formatPercent(item.changePercent, locale, "--")})
                  </span>
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
