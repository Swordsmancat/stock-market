export type InstrumentAssetType = "stock" | "etf" | "index";
export type InstrumentKlinePeriod = "1m" | "3m" | "6m" | "1y";
export type InstrumentKlineStatus = "empty" | "not_found" | "no_data" | "ready";

export type StoredLatestBar = {
  timestamp: string;
  close: number | null;
  provider: string | null;
  source: string | null;
  adjustment: string | null;
};

export type InstrumentKlineIdentity = {
  id: string;
  symbol: string;
  name: string;
  market: string;
  exchange: string | null;
  assetType: InstrumentAssetType;
  currency: string | null;
};

export type InstrumentKlineCatalogItem = InstrumentKlineIdentity & {
  storedBarCount: number;
  hasSeries: boolean;
  latestBar: StoredLatestBar | null;
};

export type InstrumentKlineBar = {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

export type InstrumentKlineSeries = {
  provider: string | null;
  adjustment: string | null;
  anchorDate: string;
  periodStart: string;
  firstDate: string;
  lastDate: string;
  barCount: number;
  sources: Array<{ source: string; barCount: number }>;
  items: InstrumentKlineBar[];
};

export type InstrumentKlinePayload = {
  status: InstrumentKlineStatus;
  source: "database";
  catalog: InstrumentKlineCatalogItem[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
  selected: InstrumentKlineIdentity | null;
  series: InstrumentKlineSeries | null;
  diagnostics: string[];
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

function finite(value: unknown): number | null {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function assetType(value: unknown): InstrumentAssetType | null {
  return value === "stock" || value === "etf" || value === "index" ? value : null;
}

function decodeIdentity(value: unknown): InstrumentKlineIdentity | null {
  const item = record(value);
  if (!item) return null;
  const id = text(item.id);
  const symbol = text(item.symbol);
  const name = text(item.name);
  const market = text(item.market);
  const decodedAssetType = assetType(item.asset_type);
  if (!id || !symbol || !name || !market || !decodedAssetType) return null;
  return {
    id,
    symbol,
    name,
    market,
    exchange: text(item.exchange),
    assetType: decodedAssetType,
    currency: text(item.currency),
  };
}

function decodeLatestBar(value: unknown): StoredLatestBar | null {
  const item = record(value);
  const timestamp = text(item?.timestamp);
  if (!item || !timestamp) return null;
  return {
    timestamp,
    close: finite(item.close),
    provider: text(item.provider),
    source: text(item.source),
    adjustment: text(item.adjustment),
  };
}

function decodeCatalogItem(value: unknown): InstrumentKlineCatalogItem | null {
  const item = record(value);
  const identity = decodeIdentity(value);
  if (!item || !identity) return null;
  return {
    ...identity,
    storedBarCount: count(item.stored_bar_count),
    hasSeries: item.has_series === true,
    latestBar: decodeLatestBar(item.latest_bar),
  };
}

function decodeSeries(value: unknown): InstrumentKlineSeries | null {
  const series = record(value);
  if (!series) return null;
  const anchorDate = text(series.anchor_date);
  const periodStart = text(series.period_start);
  const firstDate = text(series.first_date);
  const lastDate = text(series.last_date);
  if (!anchorDate || !periodStart || !firstDate || !lastDate) return null;
  const items = (Array.isArray(series.items) ? series.items : []).flatMap((value) => {
    const item = record(value);
    const timestamp = text(item?.timestamp);
    const open = finite(item?.open);
    const high = finite(item?.high);
    const low = finite(item?.low);
    const close = finite(item?.close);
    const volume = finite(item?.volume);
    return timestamp && open !== null && high !== null && low !== null && close !== null
      ? [{ timestamp, open, high, low, close, ...(volume !== null ? { volume } : {}) }]
      : [];
  });
  return {
    provider: text(series.provider),
    adjustment: text(series.adjustment),
    anchorDate,
    periodStart,
    firstDate,
    lastDate,
    barCount: count(series.bar_count),
    sources: (Array.isArray(series.sources) ? series.sources : []).flatMap((value) => {
      const item = record(value);
      const source = text(item?.source);
      return source ? [{ source, barCount: count(item?.bar_count) }] : [];
    }),
    items,
  };
}

export function decodeInstrumentKlinePayload(value: unknown): InstrumentKlinePayload | null {
  const payload = record(value);
  const allowedStatuses = new Set(["empty", "not_found", "no_data", "ready"]);
  if (!payload || payload.source !== "database" || !allowedStatuses.has(String(payload.status))) {
    return null;
  }
  const selected = payload.selected === null ? null : decodeIdentity(payload.selected);
  const series = payload.series === null ? null : decodeSeries(payload.series);
  if (payload.selected !== null && selected === null) return null;
  if (payload.series !== null && series === null) return null;
  return {
    status: payload.status as InstrumentKlineStatus,
    source: "database",
    catalog: (Array.isArray(payload.catalog) ? payload.catalog : [])
      .map(decodeCatalogItem)
      .filter((item): item is InstrumentKlineCatalogItem => item !== null),
    total: count(payload.total),
    limit: count(payload.limit),
    offset: count(payload.offset),
    hasMore: payload.has_more === true,
    selected,
    series,
    diagnostics: Array.isArray(payload.diagnostics)
      ? payload.diagnostics.flatMap((item) => (text(item) ? [text(item) as string] : []))
      : [],
  };
}
