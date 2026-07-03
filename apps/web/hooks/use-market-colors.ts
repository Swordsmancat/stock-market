"use client";

import { useEffect, useState } from "react";

export type ColorScheme = "china" | "international";

interface MarketColors {
  up: string;
  down: string;
  upBg: string;
  downBg: string;
}

const MARKET_COLORS: Record<ColorScheme, MarketColors> = {
  china: {
    up: "text-green-600 dark:text-green-400",
    down: "text-red-600 dark:text-red-400",
    upBg: "bg-green-50 dark:bg-green-950",
    downBg: "bg-red-50 dark:bg-red-950",
  },
  international: {
    up: "text-red-600 dark:text-red-400",
    down: "text-green-600 dark:text-green-400",
    upBg: "bg-red-50 dark:bg-red-950",
    downBg: "bg-green-50 dark:bg-green-950",
  },
};

export interface UseMarketColorsReturn {
  colorScheme: ColorScheme;
  setColorScheme: (scheme: ColorScheme) => void;
  getMovementColor: (value: number) => string;
  getMovementBg: (value: number) => string;
  colors: MarketColors;
}

export function useMarketColors(): UseMarketColorsReturn {
  const [colorScheme, setColorScheme] = useState<ColorScheme>("china");

  useEffect(() => {
    async function loadColorScheme() {
      try {
        const response = await fetch("/api/platform-settings");
        if (response.ok) {
          const settings = await response.json();
          const scheme = settings.color_scheme || "china";
          setColorScheme(scheme);
        }
      } catch (error) {
        console.warn("Failed to load color scheme, using default:", error);
      }
    }
    loadColorScheme();
  }, []);

  const colors = MARKET_COLORS[colorScheme];

  const getMovementColor = (value: number): string => {
    return value >= 0 ? colors.up : colors.down;
  };

  const getMovementBg = (value: number): string => {
    return value >= 0 ? colors.upBg : colors.downBg;
  };

  return {
    colorScheme,
    setColorScheme,
    getMovementColor,
    getMovementBg,
    colors,
  };
}
