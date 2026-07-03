import { cn } from "@/lib/utils";

export type ChangeLevel = "strong-up" | "up" | "slight-up" | "flat" | "slight-down" | "down" | "strong-down" | "limit-up" | "limit-down";

interface MarketColorScheme {
  upStrong: string;
  up: string;
  upLight: string;
  downLight: string;
  down: string;
  downStrong: string;
  limitUp: string;
  limitDown: string;
}

export const MARKET_COLORS: MarketColorScheme = {
  upStrong: "text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-950",
  up: "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/50",
  upLight: "text-green-600 dark:text-green-400",
  downLight: "text-red-600 dark:text-red-400",
  down: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/50",
  downStrong: "text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-950",
  limitUp: "text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-950 border-2 border-red-500",
  limitDown: "text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-950 border-2 border-green-500",
};

export function getChangeLevel(percentChange: number | null, isLimitUp = false, isLimitDown = false): ChangeLevel {
  if (isLimitUp) return "limit-up";
  if (isLimitDown) return "limit-down";
  if (percentChange === null || percentChange === 0) return "flat";
  
  const absChange = Math.abs(percentChange);
  
  if (percentChange > 0) {
    if (absChange >= 0.05) return "strong-up";
    if (absChange >= 0.02) return "up";
    return "slight-up";
  } else {
    if (absChange >= 0.05) return "strong-down";
    if (absChange >= 0.02) return "down";
    return "slight-down";
  }
}

export function getChangeLevelColor(level: ChangeLevel): string {
  switch (level) {
    case "strong-up":
    case "limit-up":
      return MARKET_COLORS.upStrong;
    case "up":
      return MARKET_COLORS.up;
    case "slight-up":
      return MARKET_COLORS.upLight;
    case "flat":
      return "text-muted-foreground";
    case "slight-down":
      return MARKET_COLORS.downLight;
    case "down":
      return MARKET_COLORS.down;
    case "strong-down":
    case "limit-down":
      return MARKET_COLORS.downStrong;
  }
}

export function getChangeArrow(percentChange: number | null): string {
  if (percentChange === null || percentChange === 0) return "";
  
  const absChange = Math.abs(percentChange);
  
  if (percentChange > 0) {
    return absChange >= 0.05 ? "↑↑" : "↑";
  } else {
    return absChange >= 0.05 ? "↓↓" : "↓";
  }
}

export function isLimitUp(percentChange: number | null, marketType: "CN" | "HK" | "US" = "CN"): boolean {
  if (percentChange === null) return false;
  
  const limits = {
    CN: 0.10, // 10%
    HK: 0.20, // 20% (一般没有涨跌停)
    US: 0.20, // 20% (一般没有涨跌停)
  };
  
  return marketType === "CN" && Math.abs(percentChange - limits[marketType]) < 0.001;
}

export function isLimitDown(percentChange: number | null, marketType: "CN" | "HK" | "US" = "CN"): boolean {
  if (percentChange === null) return false;
  
  const limits = {
    CN: -0.10, // -10%
    HK: -0.20,
    US: -0.20,
  };
  
  return marketType === "CN" && Math.abs(percentChange - limits[marketType]) < 0.001;
}
