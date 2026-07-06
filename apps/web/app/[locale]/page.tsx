import { Link } from "@/src/i18n/routing";
import { TrendingUp, Activity, Briefcase, Newspaper, FileText, List, Bell } from "lucide-react";

import { AnalysisTriggerForm } from "@/components/analysis-trigger-form";
import { IngestionTriggerForm } from "@/components/ingestion-trigger-form";
import { FlashBanner } from "@/components/flash-banner";
import { FinancialDashboardHero } from "@/components/financial-dashboard-hero";
import { MarketTicker } from "@/components/market-ticker";
import { MarketOverviewClient } from "@/components/market-overview-client";
import { HotSectors } from "@/components/hot-sectors";
import { SmartRecommendations } from "@/components/smart-recommendations";
import { ComparisonTool } from "@/components/comparison-tool";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table";
import { MiniPriceChart } from "@/components/mini-price-chart";
import { CompactCandlestickChart } from "@/components/compact-candlestick-chart";
import { EmptyState } from "@/components/empty-state";
import { getDashboardDateRanges } from "@/lib/dates";
import { withProviderQuery } from "@/lib/market-data";
import { getMarketMovementTextClass } from "@/lib/market-color-classes";
import { getPlatformSettings } from "@/lib/platform-settings-store";
import { backendFetch } from "@/lib/backend-api";

type Instrument = {
  symbol: string;
  name: string;
  market: string;
};

type InstrumentsPayload = {
  items: Instrument[];
};

type BarsPayload = {
  source: string;
  items: Array<{ timestamp: string; close: number; volume?: number }>;
};

type LatestBarPayload = {
  source: string;
  provider?: string | null;
  effective_provider?: string | null;
  status?: "ok" | "no_data" | string;
  item?: { timestamp?: string; close: number } | null;
};

type ReportPayload = {
  content_markdown: string;
  citations?: string[];
};

type DailyReportPayload = {
  as_of?: string;
  content_markdown?: string;
  citations?: string[];
};

type DailyReportHistoryPayload = {
  items: Array<{
    as_of: string;
    content_markdown: string;
  }>;
};

type PortfolioPayload = {
  source: string;
  positions: Array<{ market_value: number }>;
};

type IndicatorsPayload = {
  symbol?: string;
  source: string;
  as_of?: string;
  indicators: {
    ma?: number;
    rsi?: number;
    bollinger?: {
      upper: number;
      middle: number;
      lower: number;
    };
    atr?: number;
  };
};

type FundamentalsPayload = {
  source: string;
  item?: {
    summary: string;
  } | null;
};

type NewsPayload = {
  source: string;
  items: Array<{
    title: string;
    sentiment: string;
    confidence: number;
  }>;
};

type TaskRunPayload = {
  id?: string;
  status: string;
  duration_ms?: number;
  result_json?: {
    item_count?: number;
  };
};

type WatchlistPayload = {
  items: Array<{
    symbol: string;
    market: string;
    alert_status?: { triggered?: boolean };
  }>;
};

type AlertTriggersPayload = {
  items: Array<{
    symbol: string;
    market: string;
    rule_key: string;
    threshold: number;
    triggered_at: string;
  }>;
};

type SmartRecommendationItem = {
  symbol: string;
  type: "breakout" | "volume_anomaly" | "oversold_rebound" | "strong_momentum";
  title: string;
  reason: string;
  confidence: number;
  timestamp: string;
  data: Record<string, unknown>;
};

type SmartRecommendationDiagnostic = {
  source?: string | null;
  status?: string | null;
  severity?: string | null;
  code?: string | null;
  message?: string | null;
  category?: string | null;
  provider?: string | null;
};

type SmartRecommendationsPayload = {
  status?: string;
  generated_at?: string;
  source?: string | null;
  provider?: string | null;
  count?: number;
  diagnostics?: SmartRecommendationDiagnostic[];
  items: SmartRecommendationItem[];
};

type HotSectorItem = {
  sector_id?: string;
  name: string;
  name_en: string;
  market?: string | null;
  rank?: number | null;
  change_percent?: number | null;
  fund_flow?: string | null;
  fund_flow_amount?: number | null;
  flow_direction?: "inflow" | "outflow" | "flat" | "unknown" | string | null;
  net_flow_amount?: number | null;
  net_flow_currency?: string | null;
  net_flow_unit?: string | null;
  flow_definition?: string | null;
  leader_symbol?: string | null;
  leader_name?: string | null;
  leader_change_percent?: number | null;
  leader?: {
    symbol: string;
    name: string;
    change_percent?: number | null;
    weight?: number | null;
    net_flow_amount?: number | null;
  } | null;
  symbols_count: number;
  top_constituents?: Array<{
    symbol: string;
    name: string;
    change_percent?: number | null;
    weight?: number | null;
    net_flow_amount?: number | null;
  }>;
  as_of?: string | null;
  provider?: string | null;
  is_verified?: boolean;
};

type HotSectorsStatus = "ok" | "degraded" | "unavailable";
type HotSectorsDataMode = "live" | "delayed" | "demo" | "mock" | "none";

type HotSectorsPayload = {
  status: HotSectorsStatus;
  data_mode: HotSectorsDataMode;
  source?: string;
  provider?: string | null;
  requested_provider?: string | null;
  effective_provider?: string | null;
  as_of?: string | null;
  is_realtime?: boolean;
  is_delayed?: boolean;
  delay_minutes?: number | null;
  flow_definition?: {
    metric?: string | null;
    window?: string | null;
    currency?: string | null;
    unit?: string | null;
    methodology?: string | null;
  } | null;
  message?: string;
  count?: number;
  items: HotSectorItem[];
};

type DashboardBarItem = {
  timestamp: string;
  open?: number;
  high?: number;
  low?: number;
  close: number;
  volume?: number;
  amount?: number | null;
};

type DashboardMovementPayload = {
  direction: "up" | "down" | "flat";
  absolute_change: number;
  percent_change: number | null;
};

type DashboardLatestPayload = {
  timestamp?: string | null;
  close?: number | null;
  movement?: DashboardMovementPayload | null;
} | null;

type DashboardChartItem = {
  status: "ok" | "no_data" | "unavailable" | string;
  freshness: FreshnessStatus;
  latest: DashboardLatestPayload;
  bars: DashboardBarItem[];
  source?: string | null;
  provider?: string | null;
  requested_provider?: string | null;
  effective_provider?: string | null;
  no_data_reason?: string | null;
};

type DashboardFollowedItem = DashboardChartItem & {
  symbol: string;
  name: string;
  market: string;
  currency?: string | null;
  detail_path?: string | null;
};

type DashboardIndexItem = DashboardChartItem & {
  code: string;
  name: string;
  name_zh?: string;
  region: string;
  market: string;
  currency: string;
  provider_symbol: string;
};

type DashboardValuationIndicatorItem = {
  code: string;
  name: string;
  region?: string | null;
  category?: string | null;
  status: "ok" | "no_data" | string;
  value?: number | null;
  unit?: string | null;
  as_of?: string | null;
  source?: string | null;
  components?: Record<string, unknown>;
  no_data_reason?: string | null;
};

type DashboardBriefSection = {
  id: string;
  title: string;
  items: string[];
};

type DashboardBriefNarrativePayload = {
  answer_markdown: string;
  model: {
    provider?: string | null;
    name?: string | null;
    used_llm?: boolean;
    fallback_reason?: string | null;
  };
  context?: {
    source_mix?: {
      macro_citations?: number;
      report_citations?: number;
      news_citations?: number;
      research_source_note_citations?: number;
      information_source_gaps?: number;
    };
  };
};

type DashboardBriefPayload = {
  status: "ok" | "degraded" | string;
  generated_at: string;
  sections: DashboardBriefSection[];
  citations?: Array<{
    id: string;
    label: string;
    source: string;
    source_type?: string | null;
    as_of?: string | null;
    provider?: string | null;
    excerpt?: string | null;
  }>;
  diagnostics?: Array<{
    source?: string;
    status?: string;
    severity?: string;
    code?: string;
    message?: string;
  }>;
  safety?: {
    not_investment_advice?: boolean;
    no_buy_sell_hold?: boolean;
    no_fabricated_macro_data?: boolean;
  };
  narrative?: DashboardBriefNarrativePayload;
};

type InformationSourceItem = {
  id: string;
  label: string;
  category: string;
  authority?: string | null;
  coverage?: string[];
  status: "configured" | "needs_adapter" | "needs_manual_seed" | "no_data" | "future" | string;
  freshness_policy?: string | null;
  ai_usage?: string | null;
  next_action?: string | null;
  evidence_count?: number;
  latest_as_of?: string | null;
  collection_links?: Array<{
    label: string;
    url: string;
    source_type?: string | null;
  }>;
  seed_template?: {
    label: string;
    description?: string | null;
    target_indicator_codes?: string[];
    required_fields?: string[];
    json_template?: Record<string, unknown>;
    csv_header?: string[];
    csv_example_rows?: string[];
    review_checklist?: Array<{
      id: string;
      label: string;
      required?: boolean;
      why?: string | null;
    }>;
    warnings?: string[];
    import_command?: string | null;
    citation_boundary?: string | null;
  } | null;
  collection_note?: string | null;
  citation_policy?: string | null;
};

type InformationSourceGroup = {
  category: string;
  label: string;
  items: InformationSourceItem[];
};

type InformationSourcesPayload = {
  status: "ok" | "degraded" | string;
  summary?: {
    total?: number;
    configured?: number;
    needs_action?: number;
    future?: number;
  };
  groups?: InformationSourceGroup[];
  items?: InformationSourceItem[];
  diagnostics?: Array<Record<string, unknown>>;
};

type MarketOverviewPayload = {
  generated_at: string;
  provider: string;
  range: {
    timeframe: string;
    start: string;
    end: string;
  };
  followed: {
    scope: "watchlist" | "default_sample" | string;
    limit: number;
    items: DashboardFollowedItem[];
  };
  indices: {
    items: DashboardIndexItem[];
  };
  macro_indicators?: {
    items: DashboardValuationIndicatorItem[];
  };
  valuation_indicators: {
    items: DashboardValuationIndicatorItem[];
  };
  dashboard_brief?: DashboardBriefPayload;
  information_sources?: InformationSourcesPayload;
  diagnostics: Array<Record<string, unknown>>;
};

type MarketOverviewLoadResult =
  | { status: "loaded"; payload: MarketOverviewPayload }
  | { status: "failed" };

const DASHBOARD_HEALTH_SAMPLE_LIMIT = 25;
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;
const FALLBACK_DASHBOARD_LOCALE = "en-US";
const OPTIONAL_DASHBOARD_FETCH_TIMEOUT_MS = 5000;

type FreshnessStatus = "fresh" | "stale" | "no_data" | "unavailable";

type LatestBarLoadResult =
  | { status: "loaded"; payload: LatestBarPayload }
  | { status: "failed" };

type DashboardHealthScope = "watchlist" | "default_sample";

type DashboardHealthInstrument = Instrument & {
  alertTriggered?: boolean;
};

type DashboardHealthCounts = Record<FreshnessStatus, number>;

type DailyMovement = {
  direction: "up" | "down" | "flat";
  absoluteChange: number;
  percentChange: number | null;
} | null;

function getSafeDashboardLocale(locale: string): string {
  try {
    const [supportedLocale] = Intl.DateTimeFormat.supportedLocalesOf([locale]);
    return supportedLocale ?? FALLBACK_DASHBOARD_LOCALE;
  } catch {
    return FALLBACK_DASHBOARD_LOCALE;
  }
}

function createDashboardFetchTimeout(timeoutMilliseconds: number): { signal: AbortSignal; clear: () => void } {
  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), timeoutMilliseconds);
  return {
    signal: timeoutController.signal,
    clear: () => clearTimeout(timeoutId),
  };
}

async function fetchOptionalJson<T>(path: string, fallback: T): Promise<T> {
  const timeout = createDashboardFetchTimeout(OPTIONAL_DASHBOARD_FETCH_TIMEOUT_MS);
  try {
    const response = await backendFetch(`${path}`, { cache: "no-store", signal: timeout.signal });
    if (!response.ok) {
      return fallback;
    }
    return response.json() as Promise<T>;
  } catch {
    return fallback;
  } finally {
    timeout.clear();
  }
}

async function fetchLatestBarResult(symbol: string, provider: string): Promise<LatestBarLoadResult> {
  const timeout = createDashboardFetchTimeout(OPTIONAL_DASHBOARD_FETCH_TIMEOUT_MS);
  try {
    const response = await backendFetch(
      withProviderQuery(`/market-data/${encodeURIComponent(symbol)}/latest`, provider),
      { cache: "no-store", signal: timeout.signal },
    );
    if (!response.ok) {
      return { status: "failed" };
    }

    return {
      status: "loaded",
      payload: (await response.json()) as LatestBarPayload,
    };
  } catch {
    return { status: "failed" };
  } finally {
    timeout.clear();
  }
}

async function fetchDashboardPlatformSettings() {
  return getPlatformSettings();
}

function citationUrl(citation: string): string | null {
  return citation.match(/https?:\/\/\S+/)?.[0] ?? null;
}

function renderCitation(citation: string) {
  const url = citationUrl(citation);
  if (url === null) {
    return citation;
  }

  return (
    <a href={url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
      {citation}
    </a>
  );
}

function hasTechnicalIndicators(payload: IndicatorsPayload): boolean {
  const { ma, rsi, bollinger, atr } = payload.indicators;
  return ma !== undefined || rsi !== undefined || bollinger !== undefined || atr !== undefined;
}

function parseLatestBarTimestamp(latestBarResult: LatestBarLoadResult): Date | null {
  if (latestBarResult.status === "failed") {
    return null;
  }

  const timestamp = latestBarResult.payload.item?.timestamp;
  if (!timestamp) {
    return null;
  }

  const parsedTimestamp = new Date(timestamp);
  return Number.isNaN(parsedTimestamp.getTime()) ? null : parsedTimestamp;
}

function getFreshnessStatus(latestBarResult: LatestBarLoadResult): FreshnessStatus {
  if (latestBarResult.status === "failed") {
    return "unavailable";
  }

  if (latestBarResult.payload.status === "no_data" || latestBarResult.payload.item == null) {
    return "no_data";
  }

  const parsedTimestamp = parseLatestBarTimestamp(latestBarResult);
  if (parsedTimestamp === null) {
    return "unavailable";
  }

  const daysSinceLatestBar = (Date.now() - parsedTimestamp.getTime()) / MILLISECONDS_PER_DAY;
  return daysSinceLatestBar <= 3 ? "fresh" : "stale";
}

function getFreshnessBadgeVariant(freshnessStatus: FreshnessStatus): "secondary" | "outline" | "destructive" {
  if (freshnessStatus === "fresh") {
    return "secondary";
  }
  if (freshnessStatus === "stale") {
    return "outline";
  }
  return "destructive";
}

function formatLatestBarDate(latestBarResult: LatestBarLoadResult, locale: string, unavailableLabel: string): string {
  const parsedTimestamp = parseLatestBarTimestamp(latestBarResult);
  return parsedTimestamp === null ? unavailableLabel : parsedTimestamp.toLocaleDateString(getSafeDashboardLocale(locale));
}

function buildDashboardHealthInstruments(
  instruments: Instrument[],
  watchlistItems: WatchlistPayload["items"],
): { scope: DashboardHealthScope; instruments: DashboardHealthInstrument[] } {
  if (watchlistItems.length > 0) {
    const instrumentsBySymbol = new Map(instruments.map((instrument) => [instrument.symbol.toUpperCase(), instrument]));
    return {
      scope: "watchlist",
      instruments: watchlistItems.map((watchlistItem) => {
        const matchedInstrument = instrumentsBySymbol.get(watchlistItem.symbol.toUpperCase());
        return {
          symbol: watchlistItem.symbol,
          name: matchedInstrument?.name ?? watchlistItem.symbol,
          market: watchlistItem.market || matchedInstrument?.market || "US",
          alertTriggered: watchlistItem.alert_status?.triggered,
        };
      }),
    };
  }

  return {
    scope: "default_sample",
    instruments: instruments.slice(0, DASHBOARD_HEALTH_SAMPLE_LIMIT),
  };
}

function countFreshnessStatuses(latestBarResults: LatestBarLoadResult[]): DashboardHealthCounts {
  const initialCounts: DashboardHealthCounts = {
    fresh: 0,
    stale: 0,
    no_data: 0,
    unavailable: 0,
  };

  return latestBarResults.reduce((counts, latestBarResult) => {
    const freshnessStatus = getFreshnessStatus(latestBarResult);
    return {
      ...counts,
      [freshnessStatus]: counts[freshnessStatus] + 1,
    };
  }, initialCounts);
}

function getDailyMovement(items: BarsPayload["items"]): DailyMovement {
  const latestDailyBar = items.at(-1);
  const previousDailyBar = items.at(-2);
  if (latestDailyBar === undefined || previousDailyBar === undefined) {
    return null;
  }

  const absoluteChange = latestDailyBar.close - previousDailyBar.close;
  const percentChange = previousDailyBar.close === 0 ? null : absoluteChange / previousDailyBar.close;
  const direction = absoluteChange > 0 ? "up" : absoluteChange < 0 ? "down" : "flat";

  return {
    direction,
    absoluteChange,
    percentChange,
  };
}

function formatSignedNumber(value: number, locale: string): string {
  const formattedValue = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(Math.abs(value));
  if (value > 0) {
    return `+${formattedValue}`;
  }
  if (value < 0) {
    return `-${formattedValue}`;
  }
  return formattedValue;
}

function formatSignedPercent(value: number | null, locale: string, unavailableLabel: string): string {
  if (value === null) {
    return unavailableLabel;
  }

  const formattedValue = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
    style: "percent",
  }).format(Math.abs(value));
  if (value > 0) {
    return `+${formattedValue}`;
  }
  if (value < 0) {
    return `-${formattedValue}`;
  }
  return formattedValue;
}

async function fetchMarketOverviewResult(provider: string): Promise<MarketOverviewLoadResult> {
  const timeout = createDashboardFetchTimeout(OPTIONAL_DASHBOARD_FETCH_TIMEOUT_MS);
  try {
    const response = await backendFetch(
      withProviderQuery("/dashboard/market-overview", provider),
      { cache: "no-store", signal: timeout.signal },
    );
    if (!response.ok) {
      return { status: "failed" };
    }

    return {
      status: "loaded",
      payload: (await response.json()) as MarketOverviewPayload,
    };
  } catch {
    return { status: "failed" };
  } finally {
    timeout.clear();
  }
}

function coerceFreshnessStatus(value: string | undefined): FreshnessStatus {
  if (value === "fresh" || value === "stale" || value === "no_data" || value === "unavailable") {
    return value;
  }
  return "unavailable";
}

function formatDashboardNumber(value: number | null | undefined, locale: string, unavailableLabel: string): string {
  if (value === null || value === undefined) {
    return unavailableLabel;
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatDashboardDate(value: string | null | undefined, locale: string, unavailableLabel: string): string {
  if (!value) {
    return unavailableLabel;
  }

  const parsedDate = new Date(value);
  return Number.isNaN(parsedDate.getTime())
    ? unavailableLabel
    : parsedDate.toLocaleDateString(getSafeDashboardLocale(locale));
}

function formatDashboardMovement(
  movement: DashboardMovementPayload | null | undefined,
  locale: string,
  unavailableLabel: string,
  labels: {
    up: string;
    down: string;
    flat: string;
    unavailable: string;
    valueFormatter: (values: { direction: string; change: string; percent: string }) => string;
  },
): string {
  if (!movement) {
    return labels.unavailable;
  }

  const directionLabel =
    movement.direction === "up" ? labels.up : movement.direction === "down" ? labels.down : labels.flat;
  return labels.valueFormatter({
    direction: directionLabel,
    change: formatSignedNumber(movement.absolute_change, locale),
    percent: formatSignedPercent(movement.percent_change, locale, unavailableLabel),
  });
}

function formatValuationIndicatorValue(
  item: DashboardValuationIndicatorItem,
  locale: string,
  unavailableLabel: string,
): string {
  if (item.value === null || item.value === undefined) {
    return unavailableLabel;
  }

  const formattedValue = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(item.value);
  return item.unit === "percent" ? `${formattedValue}%` : formattedValue;
}

function formatIndicatorCategoryLabel(value: string | null | undefined): string {
  if (!value) {
    return "Uncategorized";
  }

  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function groupDashboardIndicatorItems(items: DashboardValuationIndicatorItem[]) {
  const groups = new Map<string, DashboardValuationIndicatorItem[]>();
  for (const item of items) {
    const category = item.category ?? "uncategorized";
    groups.set(category, [...(groups.get(category) ?? []), item]);
  }
  return Array.from(groups.entries()).map(([category, groupItems]) => ({
    category,
    label: formatIndicatorCategoryLabel(category),
    items: groupItems,
  }));
}

export default async function HomePage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<{
    ingest?: string;
    analysis?: string;
    bars?: string;
    market?: string;
    symbol?: string;
    msg?: string;
    task_run_id?: string;
  }>;
}) {
  const { locale: requestedLocale } = await params;
  const locale = getSafeDashboardLocale(requestedLocale);
  const flash = await searchParams;
  const { recent, analysis } = getDashboardDateRanges();
  const platformSettings = await fetchDashboardPlatformSettings();
  const provider = platformSettings.market_data_provider;
  const { getTranslations } = await import("next-intl/server");
  const t = await getTranslations("Dashboard");

  const instrumentsPayload = await fetchOptionalJson<InstrumentsPayload>("/instruments", { items: [] });
  if (instrumentsPayload.items.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <EmptyState title={t("noInstruments")} description={t("noInstrumentsHint")} />
      </div>
    );
  }

  const primaryInstrument = instrumentsPayload.items[0];
  const [
    latestBarPayload,
    barsPayload,
    reportPayload,
    dailyReportPayload,
    dailyReportHistoryPayload,
    portfolioPayload,
    indicatorsPayload,
    fundamentalsPayload,
    newsPayload,
    taskRunPayload,
    watchlistPayload,
    alertTriggersPayload,
    marketOverviewResult,
  ] =
    await Promise.all([
      fetchOptionalJson<LatestBarPayload>(
        withProviderQuery(`/market-data/${primaryInstrument.symbol}/latest`, provider),
        { source: "unavailable", item: null },
      ),
      fetchOptionalJson<BarsPayload>(
        withProviderQuery(
          `/market-data/${primaryInstrument.symbol}/bars?timeframe=1d&start=${recent.start}&end=${recent.end}`,
          provider,
        ),
        { source: "unavailable", items: [] },
      ),
      fetchOptionalJson<ReportPayload>(
        `/reports/${primaryInstrument.symbol}/stock?start=${recent.start}&end=${recent.end}`,
        { content_markdown: "", citations: [] },
      ),
      fetchOptionalJson<DailyReportPayload>(`/reports/${primaryInstrument.symbol}/daily/latest`, {}),
      fetchOptionalJson<DailyReportHistoryPayload>(
        `/reports/${primaryInstrument.symbol}/daily/history?limit=5`,
        { items: [] },
      ),
      fetchOptionalJson<PortfolioPayload>("/portfolios/demo", {
        source: "unavailable",
        positions: [],
      }),
      fetchOptionalJson<IndicatorsPayload>(`/indicators/${primaryInstrument.symbol}`, {
        source: "unavailable",
        indicators: {},
      }),
      fetchOptionalJson<FundamentalsPayload>(`/fundamentals/${primaryInstrument.symbol}`, {
        source: "unavailable",
        item: null,
      }),
      fetchOptionalJson<NewsPayload>(
        `/news/${primaryInstrument.symbol}`,
        {
          source: "unavailable",
          items: [],
        },
      ),
      fetchOptionalJson<TaskRunPayload>(
        "/task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis",
        { status: "unknown" },
      ),
      fetchOptionalJson<WatchlistPayload>("/watchlist", { items: [] }),
      fetchOptionalJson<AlertTriggersPayload>("/alerts/triggers/recent?limit=5", { items: [] }),
      fetchMarketOverviewResult(provider),
    ]);

  const latestClose =
    latestBarPayload.item?.close ?? barsPayload.items.at(-1)?.close;
  const priceSource =
    latestBarPayload.item !== undefined && latestBarPayload.item !== null
      ? latestBarPayload.source
      : barsPayload.source;
  const portfolioValue = portfolioPayload.positions.reduce(
    (sum, position) => sum + (position.market_value ?? 0),
    0,
  );
  const triggeredWatchlistCount = watchlistPayload.items.filter(
    (item) => item.alert_status?.triggered,
  ).length;
  const fundamentalSummary = fundamentalsPayload.item?.summary;
  const latestNews = newsPayload.items[0];
  const reportCitations = reportPayload.citations ?? [];
  const dailyReportCitations = dailyReportPayload.citations ?? [];
  const dashboardHealth = buildDashboardHealthInstruments(instrumentsPayload.items, watchlistPayload.items);
  const marketOverviewPayload = marketOverviewResult.status === "loaded" ? marketOverviewResult.payload : null;
  const marketOverviewIndices = marketOverviewPayload?.indices.items ?? [];
  const marketOverviewFollowedItems = marketOverviewPayload?.followed.items ?? [];
  const marketOverviewValuationItems =
    marketOverviewPayload?.macro_indicators?.items ?? marketOverviewPayload?.valuation_indicators.items ?? [];
  const marketOverviewIndicatorGroups = groupDashboardIndicatorItems(marketOverviewValuationItems);
  const dashboardBrief = marketOverviewPayload?.dashboard_brief ?? null;
  const informationSources = marketOverviewPayload?.information_sources ?? null;
  const sourceStatusLabels: Record<string, string> = {
    configured: t("sourceStatusConfigured"),
    needs_adapter: t("sourceStatusNeedsAdapter"),
    needs_manual_seed: t("sourceStatusNeedsManualSeed"),
    no_data: t("sourceStatusNoData"),
    future: t("sourceStatusFuture"),
  };
  const recommendationSymbols = marketOverviewFollowedItems.length > 0
    ? marketOverviewFollowedItems.map((item) => item.symbol).slice(0, 6)
    : instrumentsPayload.items.map((instrument) => instrument.symbol).slice(0, 6);
  const [dashboardHealthLatestBars, recommendationsPayload, hotSectorsPayload] = await Promise.all([
    Promise.all(dashboardHealth.instruments.map((instrument) => fetchLatestBarResult(instrument.symbol, provider))),
    fetchOptionalJson<SmartRecommendationsPayload>(
      `/recommendations?symbols=${encodeURIComponent(recommendationSymbols.join(","))}&limit=5`,
      { status: "unavailable", items: [] },
    ),
    fetchOptionalJson<HotSectorsPayload>(
      "/sectors/hot?limit=5",
      {
        status: "unavailable",
        data_mode: "none",
        message: "Hot sectors are unavailable.",
        count: 0,
        items: [],
      },
    ),
  ]);
  const dashboardHealthCounts = countFreshnessStatuses(dashboardHealthLatestBars);
  const checkedInstrumentCount = dashboardHealth.instruments.length;
  const attentionItems = dashboardHealth.instruments
    .map((instrument, index) => ({
      instrument,
      latestBarResult: dashboardHealthLatestBars[index],
      freshnessStatus: getFreshnessStatus(dashboardHealthLatestBars[index]),
    }))
    .filter((item) => item.freshnessStatus !== "fresh")
    .slice(0, 5);
  const primaryLatestBarResult: LatestBarLoadResult = { status: "loaded", payload: latestBarPayload };
  const primaryFreshnessStatus = getFreshnessStatus(primaryLatestBarResult);
  const latestDailyBarDateLabel = formatLatestBarDate(primaryLatestBarResult, locale, t("unavailableShort"));
  const dailyMovement = getDailyMovement(barsPayload.items);
  const dailyMovementDirectionLabel = dailyMovement
    ? dailyMovement.direction === "up"
      ? t("movementUp")
      : dailyMovement.direction === "down"
      ? t("movementDown")
      : t("movementFlat")
    : t("movementUnavailable");
  const dailyMovementLabel = dailyMovement
    ? t("dailyMovementValue", {
        direction: dailyMovementDirectionLabel,
        change: formatSignedNumber(dailyMovement.absoluteChange, locale),
        percent: formatSignedPercent(dailyMovement.percentChange, locale, t("unavailableShort")),
      })
    : t("dailyMovementUnavailable");
  const primaryProvider = latestBarPayload.effective_provider ?? latestBarPayload.provider ?? provider;
  const hasMissingOrUnavailableData = dashboardHealthCounts.no_data + dashboardHealthCounts.unavailable > 0;
  const hasStaleData = dashboardHealthCounts.stale > 0;
  const primaryActionLabel = hasMissingOrUnavailableData
    ? t("actionIngestMissingData")
    : hasStaleData
    ? t("actionRefreshStaleData")
    : t("actionOpenPrimaryInstrument");
  const smartRecommendations = recommendationsPayload.items ?? [];
  const hotSectors = hotSectorsPayload.items ?? [];
  const marketOverviewScopeLabel =
    marketOverviewPayload?.followed.scope === "watchlist"
      ? t("marketDashboardWatchlistScope")
      : t("marketDashboardDefaultScope");
  const marketDashboardMovementLabels = {
    up: t("movementUp"),
    down: t("movementDown"),
    flat: t("movementFlat"),
    unavailable: t("dailyMovementUnavailable"),
    valueFormatter: (values: { direction: string; change: string; percent: string }) =>
      t("dailyMovementValue", values),
  };

  const tickerItems = marketOverviewIndices.slice(0, 10).map((item) => ({
    code: item.code,
    name: locale === 'zh' ? (item.name_zh || item.name) : item.name,
    region: item.region,
    close: item.latest?.close ?? null,
    change: item.latest?.movement?.absolute_change ?? null,
    changePercent: item.latest?.movement?.percent_change ?? null,
    status: item.status,
    freshness: item.freshness,
    source: item.source ?? null,
    provider: item.provider ?? null,
    requested_provider: item.requested_provider ?? null,
    effective_provider: item.effective_provider ?? null,
    generated_at: marketOverviewPayload?.generated_at ?? null,
    no_data_reason: item.no_data_reason ?? null,
  }));
  const comparisonInstruments = [
    ...marketOverviewFollowedItems.map((item) => ({
      id: `followed:${item.market}:${item.symbol}`,
      symbol: item.symbol,
      name: item.name,
      market: item.market,
      bars: item.bars.map((bar) => ({ timestamp: bar.timestamp, close: bar.close })),
    })),
    ...marketOverviewIndices.map((item) => ({
      id: `index:${item.code}`,
      symbol: item.code,
      name: locale === "zh" ? item.name_zh ?? item.name : item.name,
      market: item.market,
      bars: item.bars.map((bar) => ({ timestamp: bar.timestamp, close: bar.close })),
    })),
  ];
  const heroDailyMovementClass = dailyMovement
    ? getMarketMovementTextClass(platformSettings.color_scheme, dailyMovement.absoluteChange)
    : undefined;
  const heroTaskDescription = t("itemsInTime", {
    count: taskRunPayload.result_json?.item_count ?? 0,
    time: taskRunPayload.duration_ms ?? 0,
  });
  const heroMetrics = [
    {
      label: t("latestPrice", { symbol: primaryInstrument.symbol }),
      value: formatDashboardNumber(latestClose, locale, t("unavailableShort")),
      description: t("source", { source: priceSource }),
    },
    {
      label: t("dailyMovement"),
      value: dailyMovementLabel,
      description: t("latestDailyBarAsOf", { date: latestDailyBarDateLabel }),
      className: heroDailyMovementClass,
    },
    {
      label: t("portfolioValue"),
      value: formatDashboardNumber(portfolioValue, locale, t("unavailableShort")),
      description: t("checkedInstruments"),
    },
    {
      label: t("latestTaskRun"),
      value: taskRunPayload.status,
      description: heroTaskDescription,
    },
  ];

  return (
    <div className="space-y-0">
      {tickerItems.length > 0 && <MarketTicker items={tickerItems} />}
      
      <div className="space-y-6 p-6">
      {flash.ingest === "ok" ? (
        <FlashBanner
          variant="success"
          message={
            <>
              {t("ingestSuccess", {
                market: flash.market ?? primaryInstrument.market,
                count: Number(flash.bars ?? 0),
              })}
              {flash.task_run_id ? (
                <>
                  {" "}
                  <Link href={`/task-runs/${flash.task_run_id}` as any} className="font-medium underline">
                    {t("viewTaskRun")}
                  </Link>
                </>
              ) : null}
            </>
          }
        />
      ) : null}
      {flash.ingest === "error" ? (
        <FlashBanner variant="error" message={flash.msg ? t("ingestFailedDetail", { reason: flash.msg }) : t("ingestFailed")} />
      ) : null}
      {flash.analysis === "ok" ? (
        <FlashBanner
          variant="success"
          message={
            <>
              {t("analysisSuccess", { symbol: flash.symbol ?? primaryInstrument.symbol })}
              {flash.task_run_id ? (
                <>
                  {" "}
                  <Link href={`/task-runs/${flash.task_run_id}` as any} className="font-medium underline">
                    {t("viewTaskRun")}
                  </Link>
                </>
              ) : null}
            </>
          }
        />
      ) : null}
      {flash.analysis === "error" ? (
        <FlashBanner variant="error" message={flash.msg ? t("analysisFailedDetail", { reason: flash.msg }) : t("analysisFailed")} />
      ) : null}

      <section className="space-y-4">
        <FinancialDashboardHero
          title={t("title")}
          description={t("description")}
          badges={[
            { label: t("marketDashboardBadge"), variant: "secondary" },
            { label: t("activeProvider", { provider }) },
            { label: marketOverviewScopeLabel },
            ...(marketOverviewPayload
              ? [
                  {
                    label: t("marketDashboardRange", {
                      start: formatDashboardDate(marketOverviewPayload.range.start, locale, t("unavailableShort")),
                      end: formatDashboardDate(marketOverviewPayload.range.end, locale, t("unavailableShort")),
                    }),
                  },
                ]
              : []),
          ]}
          metrics={heroMetrics}
          actions={
            <>
              <Button variant="outline" size="sm" asChild>
                <Link href="/task-runs">{t("viewTaskRuns")}</Link>
              </Button>
              <Button variant="outline" size="sm" asChild>
                <Link href="/settings">{t("providerSettings")}</Link>
              </Button>
            </>
          }
          warningPanel={
            marketOverviewResult.status === "failed" ? (
              <div className="rounded-lg border bg-background p-4">
                <div className="font-medium">{t("marketDashboardUnavailableTitle")}</div>
                <p className="mt-1 text-sm text-muted-foreground">{t("marketDashboardUnavailableDesc")}</p>
              </div>
            ) : null
          }
        />

        {dashboardBrief ? (
          <Card className="rounded-none border-x-0 border-primary/20">
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={dashboardBrief.status === "ok" ? "secondary" : "outline"} className="text-[10px]">
                  {dashboardBrief.status}
                </Badge>
                <Badge variant="outline" className="text-[10px]">
                  {formatDashboardDate(dashboardBrief.generated_at, locale, t("unavailableShort"))}
                </Badge>
              </div>
              <CardTitle className="text-lg">{t("dashboardBriefTitle")}</CardTitle>
              <CardDescription className="text-xs">{t("dashboardBriefDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {dashboardBrief.narrative?.answer_markdown ? (
                <div className="rounded-none border border-primary/20 bg-primary/5 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-sm font-semibold">{t("dashboardBriefNarrative")}</div>
                    <Badge
                      variant={dashboardBrief.narrative.model.used_llm ? "secondary" : "outline"}
                      className="text-[10px]"
                    >
                      {dashboardBrief.narrative.model.used_llm
                        ? t("dashboardBriefModelGenerated")
                        : t("dashboardBriefModelFallback")}
                    </Badge>
                    {dashboardBrief.narrative.model.name ? (
                      <Badge variant="outline" className="text-[10px]">
                        {t("dashboardBriefModelName", { name: dashboardBrief.narrative.model.name })}
                      </Badge>
                    ) : null}
                  </div>
                  <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground">
                    {dashboardBrief.narrative.answer_markdown}
                  </div>
                  {dashboardBrief.narrative.model.fallback_reason ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      {dashboardBrief.narrative.model.fallback_reason}
                    </p>
                  ) : null}
                  {dashboardBrief.narrative.context?.source_mix ? (
                    <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-5">
                      <div>
                        {t("dashboardBriefMacroEvidence", {
                          count: dashboardBrief.narrative.context.source_mix.macro_citations ?? 0,
                        })}
                      </div>
                      <div>
                        {t("dashboardBriefReportEvidence", {
                          count: dashboardBrief.narrative.context.source_mix.report_citations ?? 0,
                        })}
                      </div>
                      <div>
                        {t("dashboardBriefNewsEvidence", {
                          count: dashboardBrief.narrative.context.source_mix.news_citations ?? 0,
                        })}
                      </div>
                      <div>
                        {t("dashboardBriefSourceNoteEvidence", {
                          count: dashboardBrief.narrative.context.source_mix.research_source_note_citations ?? 0,
                        })}
                      </div>
                      <div>
                        {t("dashboardBriefSourceGaps", {
                          count: dashboardBrief.narrative.context.source_mix.information_source_gaps ?? 0,
                        })}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}
              <div className="grid gap-3 lg:grid-cols-4">
                {dashboardBrief.sections.map((section) => (
                  <div key={section.id} className="rounded-none border bg-background p-3">
                    <div className="text-sm font-semibold">{section.title}</div>
                    <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                      {section.items.map((item, index) => (
                        <li key={`${section.id}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
              {(dashboardBrief.citations?.length ?? 0) > 0 ? (
                <div className="rounded-none border bg-muted/20 p-3">
                  <div className="text-sm font-semibold">{t("dashboardBriefCitations")}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {dashboardBrief.citations?.map((citation) => (
                      <Badge key={citation.id} variant="outline" className="text-[10px]">
                        {citation.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : null}
              {(dashboardBrief.diagnostics?.length ?? 0) > 0 ? (
                <div className="rounded-none border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                  <div className="font-semibold">{t("dashboardBriefDiagnostics")}</div>
                  <ul className="mt-1 list-disc space-y-1 pl-4">
                    {dashboardBrief.diagnostics?.map((diagnostic, index) => (
                      <li key={`${diagnostic.source ?? "diagnostic"}-${diagnostic.code ?? index}`}>
                        {diagnostic.code ? `${diagnostic.code}: ` : null}
                        {diagnostic.message ?? diagnostic.status ?? t("unavailableShort")}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </CardContent>
          </Card>
        ) : null}

        {informationSources ? (
          <Card className="rounded-none border-x-0 border-emerald-200/70 dark:border-emerald-900/60">
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={informationSources.status === "ok" ? "secondary" : "outline"} className="text-[10px]">
                  {informationSources.status}
                </Badge>
                <Badge variant="outline" className="text-[10px]">
                  {t("sourceReadinessConfigured", { count: informationSources.summary?.configured ?? 0 })}
                </Badge>
                <Badge variant="outline" className="text-[10px]">
                  {t("sourceReadinessNeedsAction", { count: informationSources.summary?.needs_action ?? 0 })}
                </Badge>
                <Badge variant="outline" className="text-[10px]">
                  {t("sourceReadinessFuture", { count: informationSources.summary?.future ?? 0 })}
                </Badge>
              </div>
              <CardTitle className="text-lg">{t("sourceReadinessTitle")}</CardTitle>
              <CardDescription className="text-xs">{t("sourceReadinessDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 lg:grid-cols-3">
                {(informationSources.groups ?? []).map((group) => (
                  <div key={group.category} className="rounded-none border bg-background p-3">
                    <div className="text-sm font-semibold">{group.label}</div>
                    <div className="mt-3 space-y-3">
                      {group.items.map((item) => (
                        <div key={item.id} className="border-l-2 border-muted pl-3">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-medium">{item.label}</div>
                              <div className="text-[10px] text-muted-foreground">{item.authority ?? t("unavailableShort")}</div>
                            </div>
                            <Badge variant={item.status === "configured" ? "secondary" : "outline"} className="text-[10px]">
                              {sourceStatusLabels[item.status] ?? item.status}
                            </Badge>
                          </div>
                          {item.coverage && item.coverage.length > 0 ? (
                            <div className="mt-1 flex flex-wrap gap-1">
                              {item.coverage.slice(0, 4).map((coverage) => (
                                <Badge key={`${item.id}-${coverage}`} variant="outline" className="px-1 py-0 text-[10px]">
                                  {coverage}
                                </Badge>
                              ))}
                            </div>
                          ) : null}
                          <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                            <p>{item.ai_usage ?? t("sourceReadinessNoAiUsage")}</p>
                            <p>{item.freshness_policy ?? t("sourceReadinessNoFreshnessPolicy")}</p>
                            <p className="font-medium text-foreground">{item.next_action ?? t("sourceReadinessNoNextAction")}</p>
                          </div>
                          {item.collection_note ? (
                            <div className="mt-3 space-y-1 text-xs">
                              <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                {t("sourceReadinessCollectionNote")}
                              </div>
                              <p className="text-muted-foreground">{item.collection_note}</p>
                            </div>
                          ) : null}
                          {item.citation_policy ? (
                            <div className="mt-3 space-y-1 text-xs">
                              <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                {t("sourceReadinessCitationPolicy")}
                              </div>
                              <p className="text-muted-foreground">{item.citation_policy}</p>
                            </div>
                          ) : null}
                          {item.collection_links && item.collection_links.length > 0 ? (
                            <div className="mt-3 space-y-1 text-xs">
                              <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                {t("sourceReadinessCollectionLinks")}
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {item.collection_links.map((link) => (
                                  <a
                                    key={`${item.id}-${link.url}`}
                                    href={link.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center gap-1 rounded-none border px-2 py-1 text-primary hover:bg-muted hover:underline"
                                  >
                                    <span>{link.label}</span>
                                    {link.source_type ? (
                                      <span
                                        aria-hidden="true"
                                        className="text-[10px] uppercase text-muted-foreground"
                                      >
                                        {link.source_type.replaceAll("_", " ")}
                                      </span>
                                    ) : null}
                                  </a>
                                ))}
                              </div>
                            </div>
                          ) : null}
                          {item.seed_template ? (
                            <div className="mt-3 space-y-2 border-t pt-3 text-xs">
                              <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                {t("sourceReadinessSeedTemplate")}
                              </div>
                              <div>
                                <div className="font-medium text-foreground">{item.seed_template.label}</div>
                                {item.seed_template.description ? (
                                  <p className="mt-1 text-muted-foreground">{item.seed_template.description}</p>
                                ) : null}
                              </div>
                              {item.seed_template.target_indicator_codes &&
                              item.seed_template.target_indicator_codes.length > 0 ? (
                                <div className="space-y-1">
                                  <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                    {t("sourceReadinessTemplateTargetCodes")}
                                  </div>
                                  <div className="flex flex-wrap gap-1">
                                    {item.seed_template.target_indicator_codes.map((code) => (
                                      <Badge key={`${item.id}-${code}`} variant="outline" className="px-1 py-0 text-[10px]">
                                        {code}
                                      </Badge>
                                    ))}
                                  </div>
                                </div>
                              ) : null}
                              {item.seed_template.required_fields && item.seed_template.required_fields.length > 0 ? (
                                <div className="space-y-1">
                                  <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                    {t("sourceReadinessTemplateRequiredFields")}
                                  </div>
                                  <p className="text-muted-foreground">
                                    {item.seed_template.required_fields.join(", ")}
                                  </p>
                                </div>
                              ) : null}
                              {item.seed_template.import_command ? (
                                <div className="space-y-1">
                                  <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                    {t("sourceReadinessTemplateImportCommand")}
                                  </div>
                                  <code className="block break-all rounded-none border bg-muted/40 p-2 font-mono text-[10px] text-foreground">
                                    {item.seed_template.import_command}
                                  </code>
                                </div>
                              ) : null}
                              {item.seed_template.json_template ? (
                                <div className="space-y-1">
                                  <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                    {t("sourceReadinessTemplateJson")}
                                  </div>
                                  <pre className="max-h-32 overflow-auto rounded-none border bg-muted/30 p-2 text-[10px] text-foreground">
                                    {JSON.stringify(item.seed_template.json_template, null, 2)}
                                  </pre>
                                </div>
                              ) : null}
                              {item.seed_template.csv_header || item.seed_template.csv_example_rows ? (
                                <div className="space-y-1">
                                  <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                    {t("sourceReadinessTemplateCsv")}
                                  </div>
                                  <pre className="max-h-24 overflow-auto rounded-none border bg-muted/30 p-2 text-[10px] text-foreground">
                                    {[
                                      item.seed_template.csv_header?.join(","),
                                      ...(item.seed_template.csv_example_rows ?? []),
                                    ]
                                      .filter(Boolean)
                                      .join("\n")}
                                  </pre>
                                </div>
                              ) : null}
                              {item.seed_template.review_checklist &&
                              item.seed_template.review_checklist.length > 0 ? (
                                <div className="space-y-1">
                                  <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                    {t("sourceReadinessTemplateChecklist")}
                                  </div>
                                  <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
                                    {item.seed_template.review_checklist.map((checklistItem) => (
                                      <li key={`${item.id}-${checklistItem.id}`}>
                                        <span className="font-medium text-foreground">{checklistItem.label}</span>
                                        {checklistItem.why ? <span> {checklistItem.why}</span> : null}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}
                              {item.seed_template.warnings && item.seed_template.warnings.length > 0 ? (
                                <div className="space-y-1">
                                  <div className="text-[10px] font-semibold uppercase text-muted-foreground">
                                    {t("sourceReadinessTemplateWarnings")}
                                  </div>
                                  <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
                                    {item.seed_template.warnings.map((warning) => (
                                      <li key={`${item.id}-${warning}`}>{warning}</li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}
                              {item.seed_template.citation_boundary ? (
                                <p className="border-l-2 pl-2 text-muted-foreground">
                                  {item.seed_template.citation_boundary}
                                </p>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : null}

        <MarketOverviewClient
          initialData={marketOverviewPayload as any}
          provider={provider}
          locale={locale}
          labels={{
            coreIndicesTitle: t("coreIndicesTitle"),
            coreIndicesDesc: t("coreIndicesDesc"),
            indexName: t("indexName"),
            change: t("change"),
            changePercent: t("changePercent"),
            trend: t("trend"),
            status: t("status"),
          }}
        />

        <div className="grid gap-4 xl:grid-cols-2">
          <SmartRecommendations
            recommendations={smartRecommendations}
            status={recommendationsPayload.status ?? null}
            generatedAt={recommendationsPayload.generated_at ?? null}
            source={recommendationsPayload.source ?? null}
            provider={recommendationsPayload.provider ?? null}
            diagnostics={recommendationsPayload.diagnostics ?? []}
          />
          <HotSectors
            sectors={hotSectors}
            status={hotSectorsPayload.status}
            dataMode={hotSectorsPayload.data_mode}
            message={hotSectorsPayload.message}
            provider={hotSectorsPayload.effective_provider ?? hotSectorsPayload.provider ?? null}
            asOf={hotSectorsPayload.as_of ?? null}
            isRealtime={hotSectorsPayload.is_realtime ?? false}
            isDelayed={hotSectorsPayload.is_delayed ?? false}
            delayMinutes={hotSectorsPayload.delay_minutes ?? null}
            flowDefinition={hotSectorsPayload.flow_definition ?? null}
          />
        </div>

        <ComparisonTool instruments={comparisonInstruments} />

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,0.8fr)]">
          <Card className="rounded-none border-x-0">
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="text-[10px]">{marketOverviewScopeLabel}</Badge>
                <Badge variant="outline" className="text-[10px]">{t("followedKlineLimit", { limit: marketOverviewPayload?.followed.limit ?? 6 })}</Badge>
              </div>
              <CardTitle className="text-base">{t("followedKlineTitle")}</CardTitle>
              <CardDescription className="text-xs">{t("followedKlineDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {marketOverviewFollowedItems.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead className="h-8 px-4 text-xs font-medium">{t("symbol")}</TableHead>
                      <TableHead className="h-8 px-2 text-right text-xs font-medium">{t("latestClose")}</TableHead>
                      <TableHead className="h-8 px-2 text-right text-xs font-medium">{t("dailyMovement")}</TableHead>
                      <TableHead className="h-8 px-2 text-xs font-medium">{t("chart")}</TableHead>
                      <TableHead className="h-8 px-2 text-xs font-medium">{t("status")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {marketOverviewFollowedItems.map((item) => {
                      const freshnessStatus = coerceFreshnessStatus(item.freshness);
                      const movement = item.latest?.movement;
                      const changeValue = movement?.absolute_change ?? 0;
                      const changeColor = getMarketMovementTextClass(platformSettings.color_scheme, changeValue);
                      
                      return (
                        <TableRow key={`${item.market}-${item.symbol}`} className="border-border hover:bg-muted/30">
                          <TableCell className="py-3 px-4 font-medium">
                            <div className="flex flex-col gap-0.5">
                              <Link href={(item.detail_path ?? `/instruments/${item.symbol}`) as any} className="text-sm font-semibold hover:underline">
                                {item.symbol}
                              </Link>
                              <span className="text-[10px] text-muted-foreground">{item.name}</span>
                            </div>
                          </TableCell>
                          <TableCell className="py-3 px-2 text-right">
                            <div className="text-xl font-bold font-mono">
                              {formatDashboardNumber(item.latest?.close, locale, t("unavailableShort"))}
                            </div>
                          </TableCell>
                          <TableCell className="py-3 px-2 text-right">
                            <div className={`text-sm font-mono ${changeColor}`}>
                              {movement ? (
                                <>
                                  <div>{formatSignedNumber(movement.absolute_change, locale)}</div>
                                  <div className="text-xs">
                                    {movement.percent_change !== null && movement.percent_change !== undefined
                                      ? formatSignedPercent(movement.percent_change, locale, t("unavailableShort"))
                                      : t("unavailableShort")}
                                  </div>
                                </>
                              ) : (
                                t("unavailableShort")
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="py-3 px-2">
                            {item.bars && item.bars.length > 0 ? (
                              <Link 
                                href={(item.detail_path ?? `/instruments/${item.symbol}`) as any}
                                className="block hover:opacity-80 transition-opacity"
                              >
                                <CompactCandlestickChart
                                  data={item.bars}
                                  emptyMessage={item.no_data_reason ?? t("chartUnavailable")}
                                  className="h-16 w-32"
                                />
                              </Link>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                {item.no_data_reason ?? t("chartUnavailable")}
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="py-3 px-2">
                            <Badge variant={getFreshnessBadgeVariant(freshnessStatus)} className="text-[10px] px-1.5 py-0">
                              {t(freshnessStatus)}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground px-4 pb-4">{t("noFollowedKlines")}</p>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-none border-x-0">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t("valuationIndicatorsTitle")}</CardTitle>
              <CardDescription className="text-xs">{t("valuationIndicatorsDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {marketOverviewIndicatorGroups.length > 0 ? (
                <div className="space-y-4">
                  {marketOverviewIndicatorGroups.map((group) => (
                    <div key={group.category} className="space-y-2">
                      <div className="text-[11px] font-semibold uppercase text-muted-foreground">{group.label}</div>
                      {group.items.map((item) => (
                        <div key={item.code} className="rounded-none border p-2">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="font-semibold text-sm">{item.name}</div>
                              <div className="text-[10px] text-muted-foreground">
                                {[item.region, item.category].filter(Boolean).join(" / ") || t("unavailableShort")}
                              </div>
                            </div>
                            <Badge variant={item.status === "ok" ? "secondary" : "outline"} className="text-[10px] px-1.5 py-0">
                              {item.status === "ok" ? t("available") : t("no_data")}
                            </Badge>
                          </div>
                          <div className="mt-2 text-xl font-bold font-mono">
                            {formatValuationIndicatorValue(item, locale, t("unavailableShort"))}
                          </div>
                          <div className="mt-0.5 text-[10px] text-muted-foreground">
                            {t("valuationAsOf", { date: formatDashboardDate(item.as_of, locale, t("unavailableShort")) })}
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {item.status === "ok" ? item.source : item.no_data_reason ?? t("indicatorNoData")}
                          </p>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("noValuationIndicators")}</p>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.95fr)]">
        <Card className="rounded-none border-x-0 border-primary/20 bg-muted/20">
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary" className="text-[10px]">{t("commandCenterBadge")}</Badge>
              <Badge variant="outline" className="text-[10px]">
                {dashboardHealth.scope === "watchlist"
                  ? t("healthScopeWatchlist")
                  : t("healthScopeDefaultSample", { limit: DASHBOARD_HEALTH_SAMPLE_LIMIT })}
              </Badge>
              <Badge variant="outline" className="text-[10px]">{t("activeProvider", { provider })}</Badge>
            </div>
            <CardTitle className="text-lg">{t("dataHealthTitle")}</CardTitle>
            <CardDescription className="text-xs">{t("dataHealthDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
              <div className="rounded-none border bg-background p-2">
                <div className="text-[10px] text-muted-foreground">{t("checkedInstruments")}</div>
                <div className="text-xl font-bold font-mono">{checkedInstrumentCount}</div>
              </div>
              <div className="rounded-none border bg-background p-2">
                <div className="text-[10px] text-muted-foreground">{t("fresh")}</div>
                <div className="text-xl font-bold font-mono">{dashboardHealthCounts.fresh}</div>
              </div>
              <div className="rounded-none border bg-background p-2">
                <div className="text-[10px] text-muted-foreground">{t("stale")}</div>
                <div className="text-xl font-bold font-mono">{dashboardHealthCounts.stale}</div>
              </div>
              <div className="rounded-none border bg-background p-2">
                <div className="text-[10px] text-muted-foreground">{t("no_data")}</div>
                <div className="text-xl font-bold font-mono">{dashboardHealthCounts.no_data}</div>
              </div>
              <div className="rounded-none border bg-background p-2">
                <div className="text-[10px] text-muted-foreground">{t("unavailable")}</div>
                <div className="text-xl font-bold font-mono">{dashboardHealthCounts.unavailable}</div>
              </div>
            </div>
            <div className="flex flex-col gap-2 rounded-none border bg-background p-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-sm font-medium">{t("primaryNextAction")}</div>
                <p className="text-sm text-muted-foreground">
                  {hasMissingOrUnavailableData
                    ? t("missingDataActionHint")
                    : hasStaleData
                    ? t("staleDataActionHint")
                    : t("healthyDataActionHint", { symbol: primaryInstrument.symbol })}
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                {hasMissingOrUnavailableData || hasStaleData ? (
                  <IngestionTriggerForm
                    locale={locale}
                    market={primaryInstrument.market}
                    start={recent.start}
                    end={recent.end}
                    provider={provider}
                    label={primaryActionLabel}
                    buttonVariant="default"
                  />
                ) : (
                  <Button asChild>
                    <Link href={`/instruments/${primaryInstrument.symbol}` as any}>{primaryActionLabel}</Link>
                  </Button>
                )}
                <Button variant="outline" asChild>
                  <Link href={taskRunPayload.id ? (`/task-runs/${taskRunPayload.id}` as any) : "/task-runs"}>
                    {t("inspectTaskRuns")}
                  </Link>
                </Button>
                <Button variant="outline" asChild>
                  <Link href="/settings">{t("providerSettings")}</Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-1">
          <Card className="rounded-none border-x-0">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t("watchlistHealthTitle")}</CardTitle>
              <CardDescription className="text-xs">
                {dashboardHealth.scope === "watchlist"
                  ? t("watchlistHealthDesc")
                  : t("defaultSampleHealthDesc")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {attentionItems.length > 0 ? (
                <div className="space-y-1">
                  {attentionItems.map(({ instrument, freshnessStatus, latestBarResult }) => (
                    <Link
                      key={`${instrument.market}-${instrument.symbol}`}
                      href={`/instruments/${instrument.symbol}` as any}
                      className="flex items-center justify-between rounded-none border p-2 transition-colors hover:bg-muted/50"
                    >
                      <div>
                        <div className="font-medium text-sm">{instrument.symbol}</div>
                        <div className="text-[10px] text-muted-foreground">
                          {t("latestDailyBarAsOf", {
                            date: formatLatestBarDate(latestBarResult, locale, t("unavailableShort")),
                          })}
                        </div>
                      </div>
                      <Badge variant={getFreshnessBadgeVariant(freshnessStatus)} className="text-[10px] px-1.5 py-0">{t(freshnessStatus)}</Badge>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("allCheckedDataFresh")}</p>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-none border-x-0">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t("primaryInstrumentStory", { symbol: primaryInstrument.symbol })}</CardTitle>
              <CardDescription className="text-xs">{t("primaryInstrumentStoryDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-end gap-2">
                <div className="text-2xl font-bold font-mono">{latestClose ? `${latestClose.toFixed(2)}` : t("unavailableShort")}</div>
                <Badge variant={getFreshnessBadgeVariant(primaryFreshnessStatus)} className="text-[10px] px-1.5 py-0">{t(primaryFreshnessStatus)}</Badge>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-none border p-2">
                  <div className="text-[10px] text-muted-foreground">{t("dailyMovement")}</div>
                  <div className="font-semibold text-sm">{dailyMovementLabel}</div>
                </div>
                <div className="rounded-none border p-2">
                  <div className="text-[10px] text-muted-foreground">{t("sourceProvider")}</div>
                  <div className="font-semibold text-sm">{t("source", { source: priceSource })}</div>
                  <div className="text-[10px] text-muted-foreground">{t("providerValue", { provider: primaryProvider })}</div>
                </div>
              </div>
              <MiniPriceChart items={barsPayload.items} className="h-16 w-full" />
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/instruments/${primaryInstrument.symbol}` as any}>{t("openInstrument")}</Link>
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/reports?symbol=${primaryInstrument.symbol}` as any}>{t("viewAllReports")}</Link>
                </Button>
                <AnalysisTriggerForm
                  locale={locale}
                  symbol={primaryInstrument.symbol}
                  market={primaryInstrument.market}
                  start={analysis.start}
                  end={analysis.end}
                  maWindow={3}
                  provider={provider}
                  label={t("refreshAnalysis")}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Row 1: KPIs */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="rounded-none border-x-0">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium">
              {t("latestPrice", { symbol: primaryInstrument.symbol })}
            </CardTitle>
            <TrendingUp className="h-3 w-3 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-xl font-bold font-mono">{latestClose ? `${latestClose.toFixed(2)}` : "N/A"}</div>
            <MiniPriceChart items={barsPayload.items} className="mt-2 h-12 w-full" />
            <p className="mt-1 text-[10px] text-muted-foreground">{t("source", { source: priceSource })}</p>
          </CardContent>
        </Card>
        <Card className="rounded-none border-x-0">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium">{t("portfolioValue")}</CardTitle>
            <Briefcase className="h-3 w-3 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-xl font-bold font-mono">
              {portfolioValue > 0 ? `${portfolioValue.toLocaleString()}` : "N/A"}
            </div>
            <p className="text-[10px] text-muted-foreground">{t("source", { source: portfolioPayload.source })}</p>
            <Link href="/portfolios" className="mt-1 inline-block text-[10px] text-primary hover:underline">
              {t("viewPortfolios")}
            </Link>
          </CardContent>
        </Card>
        <Card className="rounded-none border-x-0">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium">{t("activeAlerts")}</CardTitle>
            <Bell className="h-3 w-3 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-xl font-bold font-mono">{triggeredWatchlistCount}</div>
            <p className="text-[10px] text-muted-foreground">{t("activeAlertsDesc")}</p>
            {alertTriggersPayload.items.length > 0 ? (
              <ul className="mt-2 space-y-0.5 text-[10px] text-muted-foreground">
                {alertTriggersPayload.items.slice(0, 3).map((trigger) => (
                  <li key={`${trigger.symbol}-${trigger.rule_key}-${trigger.triggered_at}`}>
                    <Link href="/alerts" className="hover:underline">
                      {trigger.symbol}
                    </Link>{" "}
                    {trigger.rule_key} @ {trigger.threshold}
                  </li>
                ))}
              </ul>
            ) : null}
            <Link href="/alerts" className="mt-2 inline-block text-xs text-primary hover:underline">
              {t("viewAlerts")}
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("latestTaskRun")}</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{taskRunPayload.status}</div>
            <p className="text-xs text-muted-foreground">
              {t("itemsInTime", {
                count: taskRunPayload.result_json?.item_count ?? 0,
                time: taskRunPayload.duration_ms ?? 0,
              })}
            </p>
            <Link
              href={taskRunPayload.id ? (`/task-runs/${taskRunPayload.id}` as any) : "/task-runs"}
              className="mt-2 inline-block text-xs text-primary hover:underline"
            >
              {t("viewTaskRuns")}
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Daily Report */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {t("dailyReport", { symbol: primaryInstrument.symbol })}
          </CardTitle>
          <CardDescription>
            {dailyReportPayload.as_of
              ? t("dailyReportAsOf", { date: new Date(dailyReportPayload.as_of).toLocaleDateString() })
              : t("dailyReportDesc")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[280px] w-full rounded-md border p-4">
            <pre className="whitespace-pre-wrap font-sans text-sm">
              {dailyReportPayload.content_markdown || t("noDailyReport")}
            </pre>
            {dailyReportCitations.length > 0 && (
              <div className="mt-4 border-t pt-4">
                <h4 className="mb-2 text-sm font-semibold">{t("citations")}</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground">
                  {dailyReportCitations.map((citation) => (
                    <li key={citation}>{renderCitation(citation)}</li>
                  ))}
                </ul>
              </div>
            )}
          </ScrollArea>
          {dailyReportHistoryPayload.items.length > 0 ? (
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-semibold">{t("dailyReportHistory")}</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {dailyReportHistoryPayload.items.map((item) => (
                  <li key={item.as_of} className="rounded-md border p-2">
                    <span className="font-medium text-foreground">
                      {new Date(item.as_of).toLocaleDateString()}
                    </span>
                    <p className="mt-1 line-clamp-2">{item.content_markdown.substring(0, 120)}...</p>
                  </li>
                ))}
              </ul>
              <Link href={`/reports?symbol=${primaryInstrument.symbol}` as any} className="mt-2 inline-block text-xs text-primary hover:underline">
                {t("viewAllReports")}
              </Link>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Row 2: Main Content */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {t("aiReport", { symbol: primaryInstrument.symbol })}
            </CardTitle>
            <CardDescription>{t("aiReportDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px] w-full rounded-md border p-4">
              <div className="prose dark:prose-invert max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-sm">
                  {reportPayload.content_markdown || t("noReport")}
                </pre>
              </div>
              {reportCitations.length > 0 && (
                <div className="mt-6 border-t pt-4">
                  <h4 className="mb-2 text-sm font-semibold">{t("citations")}</h4>
                  <ul className="list-disc pl-5 text-sm text-muted-foreground">
                    {reportCitations.map((citation) => (
                      <li key={citation}>{renderCitation(citation)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <List className="h-5 w-5" />
              {t("marketOverview")}
            </CardTitle>
            <CardDescription>{t("marketOverviewDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {instrumentsPayload.items.map((item) => (
                <Link
                  key={item.symbol}
                  href={`/instruments/${item.symbol}` as any}
                  className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
                >
                  <div>
                    <div className="font-semibold">{item.symbol}</div>
                    <div className="text-sm text-muted-foreground">{item.name}</div>
                  </div>
                  <Badge variant="outline">{item.market}</Badge>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 3: Details */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t("technicalIndicators")}</CardTitle>
            <CardDescription>{t("technicalIndicatorsDesc", { source: indicatorsPayload.source })}</CardDescription>
          </CardHeader>
          <CardContent>
            {hasTechnicalIndicators(indicatorsPayload) ? (
              <div className="space-y-2">
                {indicatorsPayload.indicators.ma && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">MA</span>
                    <span className="font-medium">{indicatorsPayload.indicators.ma.toFixed(2)}</span>
                  </div>
                )}
                {indicatorsPayload.indicators.rsi && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">RSI</span>
                    <span className="font-medium">{indicatorsPayload.indicators.rsi.toFixed(2)}</span>
                  </div>
                )}
                {indicatorsPayload.indicators.atr && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">ATR</span>
                    <span className="font-medium">{indicatorsPayload.indicators.atr.toFixed(2)}</span>
                  </div>
                )}
                {indicatorsPayload.indicators.bollinger && (
                  <div className="flex flex-col gap-1 pt-2 border-t">
                    <span className="text-sm text-muted-foreground">{t("bollingerBands")}</span>
                    <div className="flex justify-between text-sm">
                      <span>{t("upper")}</span>
                      <span>{indicatorsPayload.indicators.bollinger.upper.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>{t("middle")}</span>
                      <span>{indicatorsPayload.indicators.bollinger.middle.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>{t("lower")}</span>
                      <span>{indicatorsPayload.indicators.bollinger.lower.toFixed(2)}</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t("noTechnicalIndicators")}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t("fundamentals")}</CardTitle>
            <CardDescription>{t("fundamentalsDesc", { source: fundamentalsPayload.source })}</CardDescription>
          </CardHeader>
          <CardContent>
            {fundamentalSummary ? (
              <p className="text-sm">{fundamentalSummary}</p>
            ) : (
              <p className="text-sm text-muted-foreground">{t("noFundamentals")}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Newspaper className="h-5 w-5" />
              {t("latestNews")}
            </CardTitle>
            <CardDescription>{t("latestNewsDesc", { source: newsPayload.source })}</CardDescription>
          </CardHeader>
          <CardContent>
            {latestNews ? (
              <div className="space-y-3">
                <p className="text-sm font-medium leading-tight">{latestNews.title}</p>
                <div className="flex items-center gap-2">
                  <Badge
                    variant={
                      latestNews.sentiment === "positive"
                        ? "default"
                        : latestNews.sentiment === "negative"
                        ? "destructive"
                        : "secondary"
                    }
                  >
                    {latestNews.sentiment}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {t("confidence", { score: (latestNews.confidence * 100).toFixed(0) })}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t("noNews")}</p>
            )}
          </CardContent>
        </Card>
      </div>
      </div>
    </div>
  );
}
