"use client";

import { useEffect, useState } from "react";
import { useLocale } from "next-intl";
import {
  MARKET_COLOR_CLASSES,
  getMarketMovementBgClass,
  getMarketMovementTextClass,
  type MarketColorScheme,
} from "@/lib/market-color-classes";

export type ColorScheme = MarketColorScheme;

interface MarketColors {
  up: string;
  down: string;
  upBg: string;
  downBg: string;
}

export interface UseMarketColorsReturn {
  colorScheme: ColorScheme;
  setColorScheme: (scheme: ColorScheme) => void;
  getMovementColor: (value: number) => string;
  getMovementBg: (value: number) => string;
  colors: MarketColors;
}

function getDefaultColorSchemeFromLocale(locale: string): ColorScheme {
  // 中文用户默认使用中国习惯（绿涨红跌）
  if (locale === "zh" || locale.startsWith("zh-")) {
    return "china";
  }
  // 其他语言默认使用国际习惯（红涨绿跌）
  return "international";
}

export function useMarketColors(): UseMarketColorsReturn {
  const locale = useLocale();
  const defaultScheme = getDefaultColorSchemeFromLocale(locale);
  const [colorScheme, setColorScheme] = useState<ColorScheme>(defaultScheme);

  useEffect(() => {
    async function loadColorScheme() {
      try {
        const response = await fetch("/api/platform-settings");
        if (response.ok) {
          const settings = await response.json();
          const scheme = settings.color_scheme || defaultScheme;
          setColorScheme(scheme);
        } else {
          // API 不可用时使用默认值
          setColorScheme(defaultScheme);
        }
      } catch (error) {
        // 网络错误或其他问题,使用默认值
        setColorScheme(defaultScheme);
      }
    }
    loadColorScheme();
  }, [defaultScheme]);

  const colors = MARKET_COLOR_CLASSES[colorScheme];

  const getMovementColor = (value: number): string => {
    return getMarketMovementTextClass(colorScheme, value);
  };

  const getMovementBg = (value: number): string => {
    return getMarketMovementBgClass(colorScheme, value);
  };

  return {
    colorScheme,
    setColorScheme,
    getMovementColor,
    getMovementBg,
    colors,
  };
}
