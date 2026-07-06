"use client";

import { cn } from "@/lib/utils";
import { useMarketColorsContext } from "@/context/market-colors-context";
import { getChangeLevel, getChangeArrow, isLimitUp, isLimitDown, type ChangeLevel } from "@/lib/market-colors";

interface PriceChangeBadgeProps {
  percentChange: number | null;
  absoluteChange?: number | null;
  marketType?: "CN" | "HK" | "US";
  showArrow?: boolean;
  showAbsolute?: boolean;
  className?: string;
  animate?: boolean;
}

function getContextAwareChangeClass(
  level: ChangeLevel,
  percentChange: number | null,
  getMovementColor: (value: number) => string,
  getMovementBg: (value: number) => string,
): string {
  if (level === "flat" || percentChange === null) {
    return "text-muted-foreground";
  }

  const baseValue = percentChange > 0 ? 1 : -1;
  return cn(
    getMovementColor(baseValue),
    getMovementBg(baseValue),
    (level === "limit-up" || level === "limit-down") && "border-2 border-current",
  );
}

export function PriceChangeBadge({
  percentChange,
  absoluteChange,
  marketType = "CN",
  showArrow = true,
  showAbsolute = false,
  className,
  animate = false,
}: PriceChangeBadgeProps) {
  const { getMovementColor, getMovementBg } = useMarketColorsContext();
  const isUp = isLimitUp(percentChange, marketType);
  const isDown = isLimitDown(percentChange, marketType);
  const level = getChangeLevel(percentChange, isUp, isDown);
  const colorClass = getContextAwareChangeClass(level, percentChange, getMovementColor, getMovementBg);
  const arrow = showArrow ? getChangeArrow(percentChange) : "";
  
  const formatPercent = (value: number | null): string => {
    if (value === null) return "--";
    const formatted = (Math.abs(value) * 100).toFixed(2);
    if (value > 0) return `+${formatted}%`;
    if (value < 0) return `-${formatted}%`;
    return `${formatted}%`;
  };
  
  const formatAbsolute = (value: number | null): string => {
    if (value === null) return "";
    const formatted = Math.abs(value).toFixed(2);
    if (value > 0) return `+${formatted}`;
    if (value < 0) return `-${formatted}`;
    return formatted;
  };
  
  const limitLabel = isUp ? "涨停" : isDown ? "跌停" : "";
  
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition-all",
        colorClass,
        animate && "animate-pulse",
        className
      )}
    >
      {arrow && <span className="font-bold">{arrow}</span>}
      {showAbsolute && absoluteChange !== null && (
        <span>{formatAbsolute(absoluteChange)}</span>
      )}
      <span>{formatPercent(percentChange)}</span>
      {limitLabel && (
        <span className="ml-1 px-1 py-0.5 rounded border font-bold text-[10px]">
          {limitLabel}
        </span>
      )}
    </span>
  );
}
