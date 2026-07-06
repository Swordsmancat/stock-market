export type MarketColorScheme = "china" | "international";

type MarketColorClasses = {
  up: string;
  down: string;
  upBg: string;
  downBg: string;
  neutral: string;
  neutralBg: string;
};

export const MARKET_COLOR_CLASSES: Record<MarketColorScheme, MarketColorClasses> = {
  china: {
    up: "text-green-600 dark:text-green-400",
    down: "text-red-600 dark:text-red-400",
    upBg: "bg-green-50 dark:bg-green-950",
    downBg: "bg-red-50 dark:bg-red-950",
    neutral: "text-muted-foreground",
    neutralBg: "bg-muted/40",
  },
  international: {
    up: "text-red-600 dark:text-red-400",
    down: "text-green-600 dark:text-green-400",
    upBg: "bg-red-50 dark:bg-red-950",
    downBg: "bg-green-50 dark:bg-green-950",
    neutral: "text-muted-foreground",
    neutralBg: "bg-muted/40",
  },
};

export function getMarketMovementTextClass(
  colorScheme: MarketColorScheme,
  value: number,
): string {
  const colors = MARKET_COLOR_CLASSES[colorScheme] ?? MARKET_COLOR_CLASSES.china;
  if (value > 0) {
    return colors.up;
  }
  if (value < 0) {
    return colors.down;
  }
  return colors.neutral;
}

export function getMarketMovementBgClass(
  colorScheme: MarketColorScheme,
  value: number,
): string {
  const colors = MARKET_COLOR_CLASSES[colorScheme] ?? MARKET_COLOR_CLASSES.china;
  if (value > 0) {
    return colors.upBg;
  }
  if (value < 0) {
    return colors.downBg;
  }
  return colors.neutralBg;
}
