import { backendFetch } from "@/lib/backend-api";

const DETAIL_BARS_LOOKBACK_DAYS = 180;
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

const MARKET_INDEX_PROVIDER_SYMBOLS: Record<string, Record<string, string>> = {
  cn_shanghai_composite: { mock: "SH000001", yfinance: "000001.SS", akshare: "000001", tushare: "000001" },
  cn_shenzhen_component: { mock: "SZ399001", yfinance: "399001.SZ", akshare: "399001", tushare: "399001" },
  cn_chinext: { mock: "SZ399006", yfinance: "399006.SZ", akshare: "399006", tushare: "399006" },
  cn_csi_300: { mock: "CSI300", yfinance: "000300.SS", akshare: "000300", tushare: "000300" },
  cn_csi_500: { mock: "CSI500", yfinance: "000905.SS", akshare: "000905", tushare: "000905" },
  hk_hang_seng: { mock: "HSI", yfinance: "^HSI", akshare: "HSI", tushare: "HSI" },
  hk_hang_seng_tech: { mock: "HSTECH", yfinance: "^HSTECH", akshare: "HSTECH", tushare: "HSTECH" },
  us_sp_500: { mock: "SPX", yfinance: "^GSPC", akshare: "SPX", tushare: "SPX" },
  us_nasdaq_composite: { mock: "IXIC", yfinance: "^IXIC", akshare: "IXIC", tushare: "IXIC" },
  us_dow_jones: { mock: "DJI", yfinance: "^DJI", akshare: "DJI", tushare: "DJI" },
};

export type InstrumentBar = {
  timestamp?: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
};

export type InstrumentIntradayItem = {
  timestamp?: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  price?: number;
  average_price?: number | null;
  volume?: number | null;
  amount?: number | null;
};

export type InstrumentIntradayPayload = {
  symbol: string;
  timeframe: "1m";
  date: string;
  source: string;
  provider?: string | null;
  requested_provider?: string | null;
  effective_provider?: string | null;
  status: "ok" | "no_data" | "degraded";
  previous_close?: number | null;
  items?: InstrumentIntradayItem[];
  availability?: {
    status: "ok" | "no_data" | "degraded";
    reason?: string | null;
    is_realtime?: boolean;
    is_delayed?: boolean;
    delay_minutes?: number | null;
  };
};

export type InstrumentDetailPayload = {
  symbol: string;
  request_symbol: string;
  latest: {
    item?: {
      timestamp?: string;
      close?: number;
    } | null;
    status?: string;
  };
  bars: {
    items?: InstrumentBar[];
    status?: string;
    source?: string;
  };
  intraday?: InstrumentIntradayPayload;
  range: {
    timeframe: "1d";
    start: string;
    end: string;
  };
};

export type InstrumentDetailFetchResult =
  | { status: "loaded"; payload: InstrumentDetailPayload }
  | { status: "failed"; responseStatus: number; body: string; headers: HeadersInit };

function formatDateParameter(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function getDetailBarsDateRange(currentDate = new Date()): { start: string; end: string } {
  const endDate = new Date(Date.UTC(
    currentDate.getUTCFullYear(),
    currentDate.getUTCMonth(),
    currentDate.getUTCDate(),
  ));
  const startDate = new Date(endDate.getTime() - DETAIL_BARS_LOOKBACK_DAYS * MILLISECONDS_PER_DAY);
  return {
    start: formatDateParameter(startDate),
    end: formatDateParameter(endDate),
  };
}

export function normalizeInstrumentDetailProvider(providerName: string | null | undefined): string {
  return providerName?.trim().toLowerCase() || "yfinance";
}

export function resolveInstrumentDetailRequestSymbol(symbol: string, providerName: string): string {
  const normalizedSymbol = symbol.trim().toLowerCase();
  const providerSymbols = MARKET_INDEX_PROVIDER_SYMBOLS[normalizedSymbol];
  return providerSymbols?.[providerName] ?? providerSymbols?.mock ?? symbol;
}

export function buildProviderQuerySuffix(providerName: string): string {
  return providerName ? `&provider=${encodeURIComponent(providerName)}` : "";
}

async function readResponseBody(response: Response): Promise<string> {
  const body = await response.text();
  return body || JSON.stringify({ detail: "Instrument market data request failed" });
}

function copyContentType(response: Response): HeadersInit {
  const contentType = response.headers.get("content-type");
  return contentType ? { "content-type": contentType } : {};
}

function buildUnavailableIntradayPayload({
  requestSymbol,
  providerName,
  date,
  reason,
}: {
  requestSymbol: string;
  providerName: string;
  date: string;
  reason: string;
}): InstrumentIntradayPayload {
  return {
    symbol: requestSymbol,
    timeframe: "1m",
    date,
    source: "none",
    provider: providerName,
    requested_provider: providerName,
    effective_provider: providerName,
    status: "degraded",
    previous_close: null,
    items: [],
    availability: {
      status: "degraded",
      reason,
      is_realtime: false,
      is_delayed: false,
      delay_minutes: null,
    },
  };
}

export async function fetchInstrumentDetailPayload({
  symbol,
  providerName,
}: {
  symbol: string;
  providerName: string;
}): Promise<InstrumentDetailFetchResult> {
  const { start, end } = getDetailBarsDateRange();
  const normalizedProviderName = normalizeInstrumentDetailProvider(providerName);
  const providerQuerySuffix = buildProviderQuerySuffix(normalizedProviderName);
  const requestSymbol = resolveInstrumentDetailRequestSymbol(symbol, normalizedProviderName);
  const encodedSymbol = encodeURIComponent(requestSymbol);

  const [latestResult, barsResult, intradayResult] = await Promise.allSettled([
    backendFetch(`/market-data/${encodedSymbol}/latest${providerQuerySuffix.replace("&", "?")}`, {
      cache: "no-store",
    }),
    backendFetch(
      `/market-data/${encodedSymbol}/bars?timeframe=1d&start=${start}&end=${end}${providerQuerySuffix}`,
      { cache: "no-store" },
    ),
    backendFetch(
      `/market-data/${encodedSymbol}/intraday?date=${end}&timeframe=1m${providerQuerySuffix}`,
      { cache: "no-store" },
    ),
  ]);

  if (barsResult.status === "rejected") {
    return {
      status: "failed",
      responseStatus: 502,
      body: JSON.stringify({ detail: "Failed to fetch instrument bars" }),
      headers: { "content-type": "application/json" },
    };
  }

  const barsResponse = barsResult.value;

  if (!barsResponse.ok) {
    return {
      status: "failed",
      responseStatus: barsResponse.status,
      body: await readResponseBody(barsResponse),
      headers: copyContentType(barsResponse),
    };
  }

  const barsData = await barsResponse.json();
  const latestData = latestResult.status === "fulfilled" && latestResult.value.ok
    ? await latestResult.value.json()
    : { status: "unavailable", item: null };
  const intradayData = intradayResult.status === "fulfilled" && intradayResult.value.ok
    ? await intradayResult.value.json()
    : buildUnavailableIntradayPayload({
        requestSymbol,
        providerName: normalizedProviderName,
        date: end,
        reason: "Intraday data is unavailable for this provider.",
      });

  return {
    status: "loaded",
    payload: {
      symbol,
      request_symbol: requestSymbol,
      latest: latestData,
      bars: barsData,
      intraday: intradayData,
      range: { timeframe: "1d", start, end },
    },
  };
}
