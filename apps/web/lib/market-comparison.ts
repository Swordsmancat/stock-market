import type { ComparisonInstrument } from "@/lib/comparison-utils";

export type ComparisonPeriod = "1m" | "3m" | "6m" | "1y";
export type MarketComparisonStatus =
  | "ok"
  | "empty_selection"
  | "insufficient_selection"
  | "no_data";

export type MarketComparisonSearchResult = {
  id: string;
  symbol: string;
  name: string;
  market: string;
  exchange: string | null;
};

export type MarketComparisonItem = MarketComparisonSearchResult & {
  status: "ok" | "no_data";
  provider: string | null;
  adjustment: string | null;
  firstDate: string | null;
  lastDate: string | null;
  barCount: number;
  bars: ComparisonInstrument["bars"];
};

export type MarketComparisonPayload = {
  status: MarketComparisonStatus;
  market: string;
  symbols: string[];
  period: ComparisonPeriod;
  requestedCount: number;
  anchorDate: string | null;
  periodStart: string | null;
  sharedDateCount: number;
  comparableCount: number;
  missingSymbols: string[];
  diagnostics: string[];
  searchResults: MarketComparisonSearchResult[];
  items: MarketComparisonItem[];
};

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function count(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? Math.floor(parsed) : 0;
}

function strings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.flatMap((item) => (text(item) ? [text(item) as string] : []))
    : [];
}

function decodeIdentity(value: unknown): MarketComparisonSearchResult | null {
  const item = record(value);
  if (!item) return null;
  const id = text(item.id);
  const symbol = text(item.symbol);
  const name = text(item.name);
  const market = text(item.market);
  if (!id || !symbol || !name || !market) return null;
  return {
    id,
    symbol,
    name,
    market,
    exchange: text(item.exchange),
  };
}

function decodeItem(value: unknown): MarketComparisonItem | null {
  const raw = record(value);
  const identity = decodeIdentity(value);
  if (!raw || !identity) return null;
  const status = raw.status === "ok" ? "ok" : "no_data";
  const bars = (Array.isArray(raw.bars) ? raw.bars : []).flatMap((value) => {
    const bar = record(value);
    const timestamp = text(bar?.timestamp);
    const close = typeof bar?.close === "number" ? bar.close : Number(bar?.close);
    return timestamp && Number.isFinite(close) ? [{ timestamp, close }] : [];
  });
  return {
    ...identity,
    status,
    provider: text(raw.provider),
    adjustment: text(raw.adjustment),
    firstDate: text(raw.first_date),
    lastDate: text(raw.last_date),
    barCount: count(raw.bar_count),
    bars,
  };
}

export function decodeMarketComparisonPayload(value: unknown): MarketComparisonPayload | null {
  const payload = record(value);
  const allowedStatuses = new Set([
    "ok",
    "empty_selection",
    "insufficient_selection",
    "no_data",
  ]);
  if (!payload || !allowedStatuses.has(String(payload.status))) return null;
  const period = ["1m", "3m", "6m", "1y"].includes(String(payload.period))
    ? (payload.period as ComparisonPeriod)
    : "3m";
  return {
    status: payload.status as MarketComparisonStatus,
    market: text(payload.market) ?? "CN",
    symbols: strings(payload.symbols),
    period,
    requestedCount: count(payload.requested_count),
    anchorDate: text(payload.anchor_date),
    periodStart: text(payload.period_start),
    sharedDateCount: count(payload.shared_date_count),
    comparableCount: count(payload.comparable_count),
    missingSymbols: strings(payload.missing_symbols),
    diagnostics: strings(payload.diagnostics),
    searchResults: (Array.isArray(payload.search_results) ? payload.search_results : [])
      .map(decodeIdentity)
      .filter((item): item is MarketComparisonSearchResult => item !== null),
    items: (Array.isArray(payload.items) ? payload.items : [])
      .map(decodeItem)
      .filter((item): item is MarketComparisonItem => item !== null),
  };
}

export function toComparisonInstruments(
  items: MarketComparisonItem[],
): ComparisonInstrument[] {
  return items
    .filter((item) => item.status === "ok" && item.bars.length > 0)
    .map((item) => ({
      id: item.id,
      symbol: item.symbol,
      name: item.name,
      market: item.market,
      bars: item.bars,
    }));
}
