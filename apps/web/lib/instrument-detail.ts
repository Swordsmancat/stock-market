import { backendFetch } from "@/lib/backend-api";

const DETAIL_BARS_LOOKBACK_DAYS = 180;
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;
const DEFAULT_MARKET_DEPTH_LEVELS = 5;
const DEFAULT_LARGE_ORDER_THRESHOLD_AMOUNT = 1000000;
const INSTRUMENT_IDENTITY_LOOKUP_LIMIT = 10;

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

export type InstrumentDailyBarSourceAttempt = {
  provider?: string | null;
  source?: string | null;
  status?: string | null;
  row_count?: number | null;
  exception_type?: string | null;
  code?: string | null;
};

export type InstrumentDailyBarDiagnostic = {
  source?: string | null;
  status?: string | null;
  severity?: string | null;
  code?: string | null;
  message?: string | null;
  dropped_row_count?: number | null;
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
  freshness?: {
    status?: string | null;
    reason?: string | null;
    cache_status?: string | null;
    data_as_of?: string | null;
    fetched_at?: string | null;
    cached_at?: string | null;
  } | null;
  session?: {
    status?: string | null;
    reason?: string | null;
  } | null;
};

type InstrumentMarketDepthStatus = "ok" | "no_data" | "degraded";

export type InstrumentMarketDepthLevel = {
  price?: number | null;
  volume?: number | null;
  amount?: number | null;
  order_count?: number | null;
};

export type InstrumentRecentTradeItem = {
  timestamp?: string;
  price?: number | null;
  volume?: number | null;
  amount?: number | null;
  side?: string | null;
};

export type InstrumentLargeOrderItem = InstrumentRecentTradeItem & {
  threshold_amount?: number | null;
  threshold_volume?: number | null;
};

export type InstrumentMarketDepthPayload = {
  symbol: string;
  source: string;
  provider?: string | null;
  requested_provider?: string | null;
  effective_provider?: string | null;
  status: InstrumentMarketDepthStatus;
  as_of?: string | null;
  is_realtime?: boolean;
  is_delayed?: boolean;
  delay_minutes?: number | null;
  order_book: {
    status: InstrumentMarketDepthStatus;
    reason?: string | null;
    as_of?: string | null;
    depth_levels: number;
    bids: InstrumentMarketDepthLevel[];
    asks: InstrumentMarketDepthLevel[];
  };
  recent_trades: {
    status: InstrumentMarketDepthStatus;
    reason?: string | null;
    as_of?: string | null;
    items: InstrumentRecentTradeItem[];
  };
  large_orders: {
    status: InstrumentMarketDepthStatus;
    reason?: string | null;
    threshold_amount?: number | null;
    threshold_volume?: number | null;
    currency?: string | null;
    as_of?: string | null;
    items: InstrumentLargeOrderItem[];
  };
  fund_flow: {
    status: InstrumentMarketDepthStatus;
    reason?: string | null;
    as_of?: string | null;
    currency?: string | null;
    net_inflow?: number | null;
    main_net_inflow?: number | null;
    retail_net_inflow?: number | null;
    source_definition?: string | null;
  };
  availability?: {
    status: InstrumentMarketDepthStatus;
    reason?: string | null;
    capabilities?: {
      order_book?: boolean;
      recent_trades?: boolean;
      large_orders?: boolean;
      fund_flow?: boolean;
    };
  };
};

export type InstrumentIndicatorsPayload = {
  symbol: string;
  source?: string | null;
  as_of?: string | null;
  indicators?: Record<string, unknown>;
};

export type InstrumentFundamentalsPayload = {
  symbol: string;
  source?: string | null;
  as_of?: string | null;
  citation?: string | null;
  item?: {
    currency?: string | null;
    pe_ratio?: number | null;
    revenue_growth?: number | null;
    net_margin?: number | null;
    debt_to_assets?: number | null;
    summary?: string | null;
  } | null;
};

export type InstrumentNewsPayload = {
  symbol: string;
  source?: string | null;
  summary?: {
    latest_sentiment?: string | null;
    article_count?: number | null;
  } | null;
  items?: Array<{
    title: string;
    url?: string | null;
    source?: string | null;
    published_at?: string | null;
    summary?: string | null;
    sentiment?: string | null;
    confidence?: number | null;
  }>;
};

export type InstrumentDailyReportPayload = {
  symbol: string;
  report_type?: string | null;
  as_of?: string | null;
  source?: string | null;
  content_markdown?: string | null;
  citations?: string[];
  task_run_id?: string | null;
  source_summary?: Record<string, unknown> | null;
  items?: unknown[];
};

export type InstrumentDailyReportHistoryPayload = {
  symbol: string;
  source?: string | null;
  items?: InstrumentDailyReportPayload[];
};

export type InstrumentDetailPayload = {
  symbol: string;
  market?: string | null;
  request_symbol: string;
  provider_symbol_mapped?: boolean;
  latest: {
    item?: {
      timestamp?: string;
      close?: number;
    } | null;
    status?: string;
    source?: string | null;
    provider?: string | null;
    requested_provider?: string | null;
    effective_provider?: string | null;
    upstream_source?: string | null;
    adjustment?: string | null;
    provenance_known?: boolean | null;
    provenance_corrected?: boolean;
    fallback_used?: boolean;
    source_attempts?: InstrumentDailyBarSourceAttempt[];
    diagnostics?: InstrumentDailyBarDiagnostic[];
    no_data_reason?: string | null;
  };
  bars: {
    items?: InstrumentBar[];
    status?: string;
    source?: string | null;
    provider?: string | null;
    requested_provider?: string | null;
    effective_provider?: string | null;
    upstream_source?: string | null;
    adjustment?: string | null;
    provenance_known?: boolean | null;
    provenance_corrected?: boolean;
    fallback_used?: boolean;
    source_attempts?: InstrumentDailyBarSourceAttempt[];
    diagnostics?: InstrumentDailyBarDiagnostic[];
    no_data_reason?: string | null;
  };
  intraday?: InstrumentIntradayPayload;
  market_depth?: InstrumentMarketDepthPayload;
  indicators?: InstrumentIndicatorsPayload;
  fundamentals?: InstrumentFundamentalsPayload;
  news?: InstrumentNewsPayload;
  latest_daily_report?: InstrumentDailyReportPayload;
  daily_report_history?: InstrumentDailyReportHistoryPayload;
  range: {
    timeframe: "1d";
    start: string;
    end: string;
  };
};

export type InstrumentDetailFetchResult =
  | { status: "loaded"; payload: InstrumentDetailPayload }
  | { status: "failed"; responseStatus: number; body: string; headers: HeadersInit };

export type InstrumentDetailIdentity = {
  symbol: string;
  market: string;
  name: string;
};

export type InstrumentWatchlistMembership =
  | "watched"
  | "not_watched"
  | "unavailable";

export type InstrumentDetailContext = {
  identity: InstrumentDetailIdentity | null;
  watchlistMembership: InstrumentWatchlistMembership;
};

type InstrumentIdentityLookupPayload = {
  items?: Array<{
    symbol?: unknown;
    market?: unknown;
    name?: unknown;
  }>;
};

type WatchlistMembershipPayload = {
  status?: unknown;
};

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

export async function fetchInstrumentDetailContext(
  symbol: string,
  market?: string | null,
): Promise<InstrumentDetailContext> {
  const normalizedSymbol = symbol.trim().toUpperCase();
  const normalizedMarket = market?.trim().toUpperCase() || null;
  if (!normalizedSymbol) {
    return { identity: null, watchlistMembership: "unavailable" };
  }

  const query = new URLSearchParams({
    q: normalizedSymbol,
  });
  if (normalizedMarket) {
    query.set("market", normalizedMarket);
  }
  query.set("limit", String(INSTRUMENT_IDENTITY_LOOKUP_LIMIT));

  let identity: InstrumentDetailIdentity | null = null;
  try {
    const response = await backendFetch(`/instruments?${query.toString()}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return { identity: null, watchlistMembership: "unavailable" };
    }

    const payload = (await response.json()) as InstrumentIdentityLookupPayload;
    const matches = (Array.isArray(payload.items) ? payload.items : []).filter(
      (item) => {
        const itemSymbol =
          typeof item.symbol === "string"
            ? item.symbol.trim().toUpperCase()
            : "";
        const itemMarket =
          typeof item.market === "string"
            ? item.market.trim().toUpperCase()
            : "";
        return (
          itemSymbol === normalizedSymbol &&
          (!normalizedMarket || itemMarket === normalizedMarket)
        );
      },
    );

    if (matches.length !== 1) {
      return { identity: null, watchlistMembership: "unavailable" };
    }

    const match = matches[0];
    const resolvedMarket =
      typeof match.market === "string"
        ? match.market.trim().toUpperCase()
        : "";
    if (!resolvedMarket) {
      return { identity: null, watchlistMembership: "unavailable" };
    }

    identity = {
      symbol: normalizedSymbol,
      market: resolvedMarket,
      name: typeof match.name === "string" ? match.name.trim() : "",
    };
  } catch {
    return { identity: null, watchlistMembership: "unavailable" };
  }

  try {
    const membershipQuery = new URLSearchParams({
      symbol: identity.symbol,
      market: identity.market,
    });
    const response = await backendFetch(
      `/watchlist/items?${membershipQuery.toString()}`,
      { cache: "no-store" },
    );
    if (!response.ok) {
      return { identity, watchlistMembership: "unavailable" };
    }

    const payload = (await response.json()) as WatchlistMembershipPayload;
    if (payload.status === "watched" || payload.status === "not_watched") {
      return { identity, watchlistMembership: payload.status };
    }
  } catch {
    return { identity, watchlistMembership: "unavailable" };
  }

  return { identity, watchlistMembership: "unavailable" };
}

async function readResponseBody(response: Response): Promise<string> {
  const body = await response.text();
  return body || JSON.stringify({ detail: "Instrument market data request failed" });
}

function copyContentType(response: Response): HeadersInit {
  const contentType = response.headers.get("content-type");
  return contentType ? { "content-type": contentType } : {};
}

async function fetchOptionalBackendJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await backendFetch(path, { cache: "no-store" });
    if (!response.ok) {
      return fallback;
    }
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
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

function buildUnavailableMarketDepthPayload({
  requestSymbol,
  providerName,
  reason,
}: {
  requestSymbol: string;
  providerName: string;
  reason: string;
}): InstrumentMarketDepthPayload {
  return {
    symbol: requestSymbol,
    source: "none",
    provider: providerName,
    requested_provider: providerName,
    effective_provider: providerName,
    status: "degraded",
    as_of: null,
    is_realtime: false,
    is_delayed: false,
    delay_minutes: null,
    order_book: {
      status: "degraded",
      reason,
      as_of: null,
      depth_levels: DEFAULT_MARKET_DEPTH_LEVELS,
      bids: [],
      asks: [],
    },
    recent_trades: {
      status: "degraded",
      reason: "Recent trades are unavailable for this provider.",
      as_of: null,
      items: [],
    },
    large_orders: {
      status: "degraded",
      reason: "Large order detection is unavailable because recent trades are unavailable.",
      threshold_amount: DEFAULT_LARGE_ORDER_THRESHOLD_AMOUNT,
      threshold_volume: null,
      currency: null,
      as_of: null,
      items: [],
    },
    fund_flow: {
      status: "degraded",
      reason: "Fund-flow data is unavailable for this provider.",
      as_of: null,
      currency: null,
      net_inflow: null,
      main_net_inflow: null,
      retail_net_inflow: null,
      source_definition: null,
    },
    availability: {
      status: "degraded",
      reason,
      capabilities: {
        order_book: false,
        recent_trades: false,
        large_orders: false,
        fund_flow: false,
      },
    },
  };
}

function deriveLatestFromBars(
  bars: InstrumentDetailPayload["bars"],
): InstrumentDetailPayload["latest"] {
  const items = Array.isArray(bars.items) ? bars.items : [];
  const latestItem = items.at(-1) ?? null;

  return {
    item: latestItem,
    status: bars.status ?? (latestItem ? "ok" : "no_data"),
    source: bars.source,
    provider: bars.provider,
    requested_provider: bars.requested_provider,
    effective_provider: bars.effective_provider,
    upstream_source: bars.upstream_source,
    adjustment: bars.adjustment,
    provenance_known: bars.provenance_known,
    provenance_corrected: bars.provenance_corrected,
    fallback_used: bars.fallback_used,
    source_attempts: bars.source_attempts,
    diagnostics: bars.diagnostics,
    no_data_reason: latestItem ? null : bars.no_data_reason,
  };
}

export async function fetchInstrumentDetailPayload({
  symbol,
  providerName,
  market = null,
}: {
  symbol: string;
  providerName: string;
  market?: string | null;
}): Promise<InstrumentDetailFetchResult> {
  const { start, end } = getDetailBarsDateRange();
  const normalizedProviderName = normalizeInstrumentDetailProvider(providerName);
  const providerQuerySuffix = buildProviderQuerySuffix(normalizedProviderName);
  const normalizedMarket = market?.trim().toUpperCase() || null;
  const requestSymbol = resolveInstrumentDetailRequestSymbol(symbol, normalizedProviderName);
  const usesProviderSpecificSymbol =
    requestSymbol.trim().toUpperCase() !== symbol.trim().toUpperCase();
  const dailyMarketQuerySuffix = normalizedMarket && !usesProviderSpecificSymbol
    ? `&market=${encodeURIComponent(normalizedMarket)}`
    : "";
  const encodedSymbol = encodeURIComponent(requestSymbol);
  const encodedOriginalSymbol = encodeURIComponent(symbol);
  const barsPath = `/market-data/${encodedSymbol}/bars?timeframe=1d&start=${start}&end=${end}${providerQuerySuffix}${dailyMarketQuerySuffix}`;

  const [
    marketDataResults,
    indicatorsData,
    fundamentalsData,
    newsData,
    latestDailyReportData,
    dailyReportHistoryData,
  ] = await Promise.all([
    Promise.allSettled([
      backendFetch(barsPath, { cache: "no-store" }),
      backendFetch(
        `/market-data/${encodedSymbol}/intraday?date=${end}&timeframe=1m${providerQuerySuffix}`,
        { cache: "no-store" },
      ),
      backendFetch(
        `/market-data/${encodedSymbol}/depth?depth_levels=${DEFAULT_MARKET_DEPTH_LEVELS}&large_order_threshold_amount=${DEFAULT_LARGE_ORDER_THRESHOLD_AMOUNT}${providerQuerySuffix}`,
        { cache: "no-store" },
      ),
    ]),
    fetchOptionalBackendJson<InstrumentIndicatorsPayload>(`/indicators/${encodedOriginalSymbol}`, {
      symbol,
      source: "database",
      indicators: {},
    }),
    fetchOptionalBackendJson<InstrumentFundamentalsPayload>(`/fundamentals/${encodedOriginalSymbol}`, {
      symbol,
      source: null,
      item: null,
    }),
    fetchOptionalBackendJson<InstrumentNewsPayload>(`/news/${encodedOriginalSymbol}`, {
      symbol,
      source: null,
      summary: { latest_sentiment: null, article_count: 0 },
      items: [],
    }),
    fetchOptionalBackendJson<InstrumentDailyReportPayload>(`/reports/${encodedOriginalSymbol}/daily/latest`, {
      symbol,
      report_type: "stock_daily",
      source: "database",
      items: [],
    }),
    fetchOptionalBackendJson<InstrumentDailyReportHistoryPayload>(
      `/reports/${encodedOriginalSymbol}/daily/history?limit=5`,
      {
        symbol,
        source: "database",
        items: [],
      },
    ),
  ]);
  const [barsResult, intradayResult, marketDepthResult] = marketDataResults;

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

  const barsData = (await barsResponse.json()) as InstrumentDetailPayload["bars"];
  const latestData = deriveLatestFromBars(barsData);
  const intradayData = intradayResult.status === "fulfilled" && intradayResult.value.ok
    ? await intradayResult.value.json()
    : buildUnavailableIntradayPayload({
        requestSymbol,
        providerName: normalizedProviderName,
        date: end,
        reason: "Intraday data is unavailable for this provider.",
      });
  const marketDepthData = marketDepthResult.status === "fulfilled" && marketDepthResult.value.ok
    ? await marketDepthResult.value.json()
    : buildUnavailableMarketDepthPayload({
        requestSymbol,
        providerName: normalizedProviderName,
        reason: "Market depth data is unavailable for this provider.",
      });

  return {
    status: "loaded",
    payload: {
      symbol,
      market: normalizedMarket,
      request_symbol: requestSymbol,
      provider_symbol_mapped: usesProviderSpecificSymbol,
      latest: latestData,
      bars: barsData,
      intraday: intradayData,
      market_depth: marketDepthData,
      indicators: indicatorsData,
      fundamentals: fundamentalsData,
      news: newsData,
      latest_daily_report: latestDailyReportData,
      daily_report_history: dailyReportHistoryData,
      range: { timeframe: "1d", start, end },
    },
  };
}
