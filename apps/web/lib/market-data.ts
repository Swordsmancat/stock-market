const STORAGE_KEY = "market_data_provider";

export const MARKET_DATA_PROVIDERS = ["yfinance", "mock"] as const;

export type MarketDataProvider = (typeof MARKET_DATA_PROVIDERS)[number];

export function getDefaultMarketDataProvider(): string {
  return process.env.NEXT_PUBLIC_MARKET_DATA_PROVIDER ?? "yfinance";
}

export function getMarketDataProvider(): string {
  if (typeof window !== "undefined") {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return stored;
    }
  }
  return getDefaultMarketDataProvider();
}

export function setMarketDataProvider(provider: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, provider);
  }
}

export function withProviderQuery(path: string, provider = getMarketDataProvider()): string {
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}provider=${encodeURIComponent(provider)}`;
}
