"use client";

import { memo, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
    return "text-gray-300";
  }
  return getMovementColor(value);
}

function MarketTickerComponent({ items, className }: MarketTickerProps) {
  const locale = "zh-CN";
  const [selectedMarket, setSelectedMarket] = useState<string>("all");
  const { getMovementColor } = useMarketColorsContext();

  const marketOptions = useMemo(
    () => [
      { value: "all", label: "全部市场" },
      { value: "CN", label: "中国A股" },
      { value: "HK", label: "香港" },
      { value: "US", label: "美股" },
    ],
    [],
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
        "bg-black text-white border-b border-gray-800",
        className
      )}
    >
      <div className="flex items-center gap-4 overflow-hidden px-4 py-2">
        <Select value={selectedMarket} onValueChange={setSelectedMarket}>
          <SelectTrigger className="h-7 w-32 shrink-0 bg-gray-900 border-gray-700 text-white text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-gray-900 border-gray-700">
            {marketOptions.map(option => (
              <SelectItem 
                key={option.value} 
                value={option.value}
                className="text-white hover:bg-gray-800 focus:bg-gray-800"
              >
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="min-w-0 flex-1">
          <div className="grid min-w-0 grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
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
                  className="inline-flex min-w-0 items-center gap-2 font-mono text-sm whitespace-nowrap"
                  title={trustTitle}
                  aria-label={`${item.name} ${trustTitle}`}
                >
                  <span className="truncate text-gray-400 font-sans">{item.name}</span>
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
