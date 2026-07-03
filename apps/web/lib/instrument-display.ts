const MARKET_INDEX_DISPLAY_NAMES: Record<string, { en: string; zh: string }> = {
  cn_shanghai_composite: { en: "Shanghai Composite", zh: "上证指数" },
  cn_shenzhen_component: { en: "Shenzhen Component", zh: "深证成指" },
  cn_chinext: { en: "ChiNext", zh: "创业板指" },
  cn_csi_300: { en: "CSI 300", zh: "沪深300" },
  cn_csi_500: { en: "CSI 500", zh: "中证500" },
  hk_hang_seng: { en: "Hang Seng Index", zh: "恒生指数" },
  hk_hang_seng_tech: { en: "Hang Seng Tech Index", zh: "恒生科技" },
  us_sp_500: { en: "S&P 500", zh: "标普500" },
  us_nasdaq_composite: { en: "Nasdaq Composite", zh: "纳斯达克" },
  us_dow_jones: { en: "Dow Jones Industrial Average", zh: "道琼斯" },
};

export function decodeInstrumentSymbol(symbol: string): string {
  try {
    return decodeURIComponent(symbol);
  } catch {
    return symbol;
  }
}

export function getInstrumentDisplayName(symbol: string, locale: string): string {
  const decodedSymbol = decodeInstrumentSymbol(symbol);
  const displayNames = MARKET_INDEX_DISPLAY_NAMES[decodedSymbol.toLowerCase()];
  if (displayNames === undefined) {
    return decodedSymbol;
  }

  return locale.startsWith("zh") ? displayNames.zh : displayNames.en;
}
