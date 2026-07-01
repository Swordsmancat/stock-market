export function getMarketDataProvider(): string {
  return process.env.NEXT_PUBLIC_MARKET_DATA_PROVIDER ?? "yfinance";
}

export function withProviderQuery(path: string, provider = getMarketDataProvider()): string {
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}provider=${encodeURIComponent(provider)}`;
}
