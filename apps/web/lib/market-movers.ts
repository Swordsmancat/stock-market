export type MarketMoverItem = {
  rank: number;
  symbol: string;
  name: string;
  exchange: string;
  close: number;
  previousClose: number;
  change: number;
  changePercent: number;
  volume: number;
  amount: number | null;
  provider: string;
  source: string;
  adjustment: string;
};

export type MarketMoversPayload = {
  status: "ok" | "no_data";
  market: string;
  direction: "gainers" | "losers";
  exchange: "all" | "SSE" | "SZSE" | "BSE";
  limit: 10 | 20 | 50;
  tradeDate: string | null;
  previousTradeDate: string | null;
  provider: string | null;
  adjustment: string | null;
  comparableCount: number;
  eligibleCount: number;
  omittedCount: number;
  items: MarketMoverItem[];
};

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function finiteNumber(value: unknown): number | null {
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) ? number : null;
}

function count(value: unknown): number {
  const number = finiteNumber(value);
  return number !== null && number >= 0 ? Math.floor(number) : 0;
}

function decodeItem(value: unknown): MarketMoverItem | null {
  const item = record(value);
  if (!item) return null;
  const symbol = text(item.symbol);
  const name = text(item.name);
  const exchange = text(item.exchange);
  const close = finiteNumber(item.close);
  const previousClose = finiteNumber(item.previous_close);
  const change = finiteNumber(item.change);
  const changePercent = finiteNumber(item.change_percent);
  const volume = finiteNumber(item.volume);
  if (
    !symbol ||
    !name ||
    !exchange ||
    close === null ||
    previousClose === null ||
    change === null ||
    changePercent === null ||
    volume === null
  ) {
    return null;
  }
  return {
    rank: Math.max(1, count(item.rank)),
    symbol,
    name,
    exchange,
    close,
    previousClose,
    change,
    changePercent,
    volume,
    amount: item.amount === null ? null : finiteNumber(item.amount),
    provider: text(item.provider) ?? "",
    source: text(item.source) ?? "",
    adjustment: text(item.adjustment) ?? "",
  };
}

export function decodeMarketMoversPayload(value: unknown): MarketMoversPayload | null {
  const payload = record(value);
  if (!payload || (payload.status !== "ok" && payload.status !== "no_data")) {
    return null;
  }
  const direction = payload.direction === "losers" ? "losers" : "gainers";
  const allowedExchanges = new Set(["all", "SSE", "SZSE", "BSE"]);
  const exchange = text(payload.exchange) ?? "all";
  const parsedLimit = count(payload.limit);
  const limit = parsedLimit === 10 || parsedLimit === 50 ? parsedLimit : 20;
  return {
    status: payload.status,
    market: text(payload.market) ?? "CN",
    direction,
    exchange: (allowedExchanges.has(exchange) ? exchange : "all") as MarketMoversPayload["exchange"],
    limit,
    tradeDate: text(payload.trade_date),
    previousTradeDate: text(payload.previous_trade_date),
    provider: text(payload.provider),
    adjustment: text(payload.adjustment),
    comparableCount: count(payload.comparable_count),
    eligibleCount: count(payload.eligible_count),
    omittedCount: count(payload.omitted_count),
    items: (Array.isArray(payload.items) ? payload.items : [])
      .map(decodeItem)
      .filter((item): item is MarketMoverItem => item !== null),
  };
}
