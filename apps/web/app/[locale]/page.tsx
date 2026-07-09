import { Link } from "@/src/i18n/routing";
import type { ReactNode } from "react";
import { TrendingUp, Activity, Newspaper, Bell, Search, Settings2, ShieldCheck, CircleAlert } from "lucide-react";

import { FlashBanner } from "@/components/flash-banner";
import { FinancialDashboardHero } from "@/components/financial-dashboard-hero";
import { MarketTicker } from "@/components/market-ticker";
import { HotSectors } from "@/components/hot-sectors";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { getDashboardDateRanges } from "@/lib/dates";
import { withProviderQuery } from "@/lib/market-data";
import { getMarketMovementTextClass } from "@/lib/market-color-classes";
import {
  DEFAULT_FAVORITE_HOME_INDEX_CODES,
  DEFAULT_FAVORITE_MACRO_INDICATOR_CODES,
  getPlatformSettings,
  type HomeIndexDisplayField,
  type NewsSearchProviderCapability,
} from "@/lib/platform-settings-store";
import { backendFetch } from "@/lib/backend-api";
import type {
  OfficialMacroSourceStatusPayload,
  OfficialMacroSourceStatusProvider,
} from "@/lib/market-overview-payload";

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
const FRED_OFFICIAL_MACRO_CODES = new Set([
  "us_10y_yield",
  "us_2y_yield",
  "us_10y_2y_spread",
  "us_cpi_yoy",
  "us_m2_yoy",
]);
const WORLD_BANK_BUFFETT_CODES = new Set([
  "buffett_indicator_us",
  "buffett_indicator_cn",
  "buffett_indicator_hk",
]);

type FreshnessStatus = "fresh" | "stale" | "no_data" | "unavailable";

type LatestBarLoadResult =
  | { status: "loaded"; payload: LatestBarPayload }
  | { status: "failed" };

type DashboardHealthScope = "watchlist" | "default_sample";

type DashboardHealthInstrument = Instrument & {
  alertTriggered?: boolean;
};

type DashboardHealthCounts = Record<FreshnessStatus, number>;

type DashboardFavoriteMacroIndicatorRow = {
  code: string;
  item: DashboardValuationIndicatorItem | null;
};

type DashboardHomeIndexItem = DashboardIndexItem & {
  isConfiguredMissing?: boolean;
};

const FAVORITE_MACRO_INDICATOR_LIMIT = 8;

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

function buildFavoriteMacroIndicatorRows(
  items: DashboardValuationIndicatorItem[],
  favoriteCodes: string[],
): DashboardFavoriteMacroIndicatorRow[] {
  const availableByCode = new Map(items.map((item) => [item.code, item]));
  const requestedCodes =
    favoriteCodes.length > 0 ? favoriteCodes : Array.from(DEFAULT_FAVORITE_MACRO_INDICATOR_CODES);
  const requestedRows = requestedCodes
    .slice(0, FAVORITE_MACRO_INDICATOR_LIMIT)
    .map((code) => ({ code, item: availableByCode.get(code) ?? null }));

  if (requestedRows.some((row) => row.item !== null) || items.length === 0) {
    return requestedRows;
  }

  return items
    .slice(0, FAVORITE_MACRO_INDICATOR_LIMIT)
    .map((item) => ({ code: item.code, item }));
}

function buildMissingDashboardIndexItem(code: string): DashboardHomeIndexItem {
  return {
    code,
    name: code,
    name_zh: code,
    region: "N/A",
    market: "N/A",
    currency: "",
    provider_symbol: code,
    status: "no_data",
    freshness: "no_data",
    latest: null,
    bars: [],
    source: null,
    provider: null,
    requested_provider: null,
    effective_provider: null,
    no_data_reason: null,
    isConfiguredMissing: true,
  };
}

function buildHomeIndexItems(
  indices: DashboardIndexItem[],
  favoriteCodes: string[],
): DashboardHomeIndexItem[] {
  const availableByCode = new Map(indices.map((item) => [item.code, item]));
  const requestedCodes = favoriteCodes.length > 0
    ? favoriteCodes
    : Array.from(DEFAULT_FAVORITE_HOME_INDEX_CODES);

  return requestedCodes.map((code) => availableByCode.get(code) ?? buildMissingDashboardIndexItem(code));
}

function buildSparklinePath(values: number[], width: number, height: number): string | null {
  const points = values.filter((value) => Number.isFinite(value));
  if (points.length < 2) {
    return null;
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  return points
    .map((value, index) => {
      const x = (index / (points.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function MiniSparkline({
  bars,
  movementValue,
}: {
  bars: DashboardBarItem[];
  movementValue: number;
}) {
  const width = 148;
  const height = 42;
  const path = buildSparklinePath(bars.map((bar) => bar.close), width, height);
  const strokeClassName = movementValue < 0 ? "stroke-negative" : movementValue > 0 ? "stroke-positive" : "stroke-muted-foreground";

  return (
    <svg
      className="mt-3 h-11 w-full overflow-visible"
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden="true"
      focusable="false"
    >
      <path d={`M0,${height - 4} L${width},${height - 4}`} className="stroke-border" strokeWidth="1" strokeDasharray="3 6" />
      {path ? (
        <path
          d={path}
          className={strokeClassName}
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.7"
        />
      ) : null}
    </svg>
  );
}

function TerminalPanel({
  title,
  description,
  icon,
  action,
  children,
  className = "",
  titleId,
}: {
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  titleId?: string;
}) {
  return (
    <Card className={`overflow-hidden rounded-md border bg-card/95 shadow-[0_0_0_1px_hsl(var(--primary)/0.04)] ${className}`}>
      <CardHeader className="border-b bg-background/55 px-3 py-2.5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <CardTitle id={titleId} className="flex items-center gap-2 text-base">
              {icon}
              <span className="truncate">{title}</span>
            </CardTitle>
            {description ? <CardDescription className="mt-1 text-xs">{description}</CardDescription> : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
      </CardHeader>
      <CardContent className="p-3">{children}</CardContent>
    </Card>
  );
}

function getNewsProviderStatusKey(capability: NewsSearchProviderCapability): string {
  if (!capability.enabled) {
    return "newsProviderStatusDisabled";
  }
  if (capability.credential_required && !capability.credential_configured) {
    return "newsProviderStatusNeedsSetup";
  }
  if (["implemented", "existing", "mock"].includes(capability.implementation_status)) {
    return "newsProviderStatusReady";
  }
  return "newsProviderStatusRegistered";
}

function getNewsProviderStatusClassName(capability: NewsSearchProviderCapability): string {
  if (!capability.enabled) {
    return "border-muted text-muted-foreground";
  }
  if (capability.credential_required && !capability.credential_configured) {
    return "border-warning/40 bg-warning/10 text-warning";
  }
  if (["implemented", "existing", "mock"].includes(capability.implementation_status)) {
    return "border-positive/40 bg-positive/10 text-positive";
  }
  return "border-primary/35 bg-primary/10 text-primary";
}

function getOfficialMacroProviderStatus(
  payload: OfficialMacroSourceStatusPayload | null,
  provider: "fred" | "world_bank",
): OfficialMacroSourceStatusProvider | null {
  return payload?.providers.find((item) => item.provider === provider) ?? null;
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
  const { recent } = getDashboardDateRanges();
  const platformSettings = await fetchDashboardPlatformSettings();
  const provider = platformSettings.market_data_provider;
  const { getTranslations } = await import("next-intl/server");
  const t = await getTranslations("Dashboard");

  const instrumentsPayload = await fetchOptionalJson<InstrumentsPayload>("/instruments", { items: [] });
  if (instrumentsPayload.items.length === 0) {
    return (
      <div className="space-y-6">
        <FinancialDashboardHero
          title={t("title")}
          description={t("description")}
          badges={[
            { label: t("marketDashboardBadge"), variant: "secondary" },
            { label: t("activeProvider", { provider }) },
          ]}
          metrics={[
            { label: t("marketOverview"), value: "0", description: t("noInstrumentsHint") },
            { label: t("portfolioValue"), value: t("unavailableShort"), description: t("marketDashboardUnavailableTitle") },
          ]}
        />
        <EmptyState title={t("noInstruments")} description={t("noInstrumentsHint")} />
      </div>
    );
  }

  const primaryInstrument = instrumentsPayload.items[0];
  const [
    latestBarPayload,
    barsPayload,
    newsPayload,
    taskRunPayload,
    watchlistPayload,
    alertTriggersPayload,
    marketOverviewResult,
    officialMacroSourceStatusPayload,
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
      fetchOptionalJson<OfficialMacroSourceStatusPayload | null>(
        "/market-indicators/official-sources/status",
        null,
      ),
    ]);

  const latestClose =
    latestBarPayload.item?.close ?? barsPayload.items.at(-1)?.close;
  const triggeredWatchlistCount = watchlistPayload.items.filter(
    (item) => item.alert_status?.triggered,
  ).length;
  const latestNews = newsPayload.items[0];
  const dashboardHealth = buildDashboardHealthInstruments(instrumentsPayload.items, watchlistPayload.items);
  const marketOverviewPayload = marketOverviewResult.status === "loaded" ? marketOverviewResult.payload : null;
  const marketOverviewIndices = marketOverviewPayload?.indices.items ?? [];
  const marketOverviewValuationItems =
    marketOverviewPayload?.macro_indicators?.items ?? marketOverviewPayload?.valuation_indicators.items ?? [];
  const favoriteMacroIndicatorRows = buildFavoriteMacroIndicatorRows(
    marketOverviewValuationItems,
    platformSettings.favorite_macro_indicator_codes,
  );
  const fredOfficialSourceStatus = getOfficialMacroProviderStatus(officialMacroSourceStatusPayload, "fred");
  const getFavoriteMacroNextAction = (code: string, item: DashboardValuationIndicatorItem | null): string | null => {
    if (item?.status === "ok") {
      return null;
    }
    if (FRED_OFFICIAL_MACRO_CODES.has(code)) {
      return fredOfficialSourceStatus?.configured === false
        ? t("favoriteMacroGuidanceFredConfigure")
        : t("favoriteMacroGuidanceFredRefresh");
    }
    if (WORLD_BANK_BUFFETT_CODES.has(code)) {
      return t("favoriteMacroGuidanceWorldBankRefresh");
    }
    if (code === "cn_m2_yoy") {
      return t("favoriteMacroGuidanceManualChina");
    }
    return t("favoriteMacroGuidanceMacroResearch");
  };
  const [dashboardHealthLatestBars, hotSectorsPayload] = await Promise.all([
    Promise.all(dashboardHealth.instruments.map((instrument) => fetchLatestBarResult(instrument.symbol, provider))),
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
  const hasMissingOrUnavailableData = dashboardHealthCounts.no_data + dashboardHealthCounts.unavailable > 0;
  const hasStaleData = dashboardHealthCounts.stale > 0;
  const hotSectors = hotSectorsPayload.items ?? [];

  const homeIndexDisplayFields = new Set<HomeIndexDisplayField>(platformSettings.home_index_display_fields);
  const shouldShowHomeIndexField = (field: HomeIndexDisplayField) => homeIndexDisplayFields.has(field);
  const coreMarketIndexItems = buildHomeIndexItems(
    marketOverviewIndices,
    platformSettings.favorite_home_index_codes,
  );

  const tickerItems = coreMarketIndexItems.map((item) => ({
    code: item.code,
    name: locale === 'zh' ? (item.name_zh || item.name) : item.name,
    region: item.region,
    close: item.latest?.close ?? null,
    change: item.latest?.movement?.absolute_change ?? null,
    changePercent: item.latest?.movement?.percent_change ?? null,
    sparkline: item.bars.map((bar) => bar.close),
    status: item.status,
    freshness: item.freshness,
    source: item.source ?? null,
    provider: item.provider ?? null,
    requested_provider: item.requested_provider ?? null,
    effective_provider: item.effective_provider ?? null,
    generated_at: marketOverviewPayload?.generated_at ?? null,
    no_data_reason: item.no_data_reason ?? null,
  }));
  const availableMacroCount = favoriteMacroIndicatorRows.filter((row) => row.item?.status === "ok").length;
  const macroTotalCount = favoriteMacroIndicatorRows.length;
  const missingHealthCount = dashboardHealthCounts.no_data + dashboardHealthCounts.unavailable;
  const hotSectorItemsForHome = hotSectors.slice(0, 4);
  const newsSearchProviderCapabilities = platformSettings.news_search_provider_capabilities ?? [];
  const latestNewsConfidence = latestNews ? (latestNews.confidence * 100).toFixed(0) : null;
  const homepageMetrics = [
    {
      label: t("coreIndicesTitle"),
      value: coreMarketIndexItems.length,
      description: t("homeCoreIndicesMetricDesc"),
    },
    {
      label: t("favoriteMacroTitle"),
      value: `${availableMacroCount}/${macroTotalCount}`,
      description: t("homeMacroMetricDesc", { available: availableMacroCount, total: macroTotalCount }),
    },
    {
      label: t("hotSectorsTitle"),
      value: hotSectorItemsForHome.length,
      description: t("homeHotSectorsMetricDesc", { count: hotSectorItemsForHome.length }),
    },
    {
      label: t("latestNews"),
      value: latestNews ? latestNews.sentiment : t("unavailableShort"),
      description: latestNewsConfidence ? t("confidence", { score: latestNewsConfidence }) : t("noNews"),
    },
  ];

  return (
    <div className="space-y-3 overflow-x-hidden">
      {tickerItems.length > 0 && (
        <MarketTicker
          items={tickerItems}
          labels={{
            allMarkets: t("marketFilterAll"),
            cnMarket: t("marketFilterCn"),
            hkMarket: t("marketFilterHk"),
            usMarket: t("marketFilterUs"),
          }}
        />
      )}

      <div className="space-y-3">
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
          <FlashBanner
            variant="error"
            message={flash.msg ? t("ingestFailedDetail", { reason: flash.msg }) : t("ingestFailed")}
          />
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
          <FlashBanner
            variant="error"
            message={flash.msg ? t("analysisFailedDetail", { reason: flash.msg }) : t("analysisFailed")}
          />
        ) : null}

        <FinancialDashboardHero
          title={t("homeOverviewTitle")}
          description={t("homeOverviewDesc")}
          badges={[
            { label: t("marketDashboardBadge"), variant: "secondary" },
            { label: t("activeProvider", { provider }) },
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
          metrics={homepageMetrics}
          actions={
            <>
              <Button variant="outline" size="sm" asChild>
                <Link href="/settings">{t("providerSettings")}</Link>
              </Button>
              <Button variant="outline" size="sm" asChild>
                <Link href="/evidence">{t("favoriteMacroDetailLink")}</Link>
              </Button>
            </>
          }
        />

        {marketOverviewResult.status === "failed" ? (
          <div className="rounded-md border bg-card p-4">
            <div className="font-medium">{t("marketDashboardUnavailableTitle")}</div>
            <p className="mt-1 text-sm text-muted-foreground">{t("marketDashboardUnavailableDesc")}</p>
          </div>
        ) : null}

        <section className="space-y-4" aria-labelledby="core-market-indices-heading">
          <TerminalPanel
            title={t("coreIndicesTitle")}
            titleId="core-market-indices-heading"
            description={t("homeCoreIndicesDesc")}
            icon={<TrendingUp className="h-4 w-4 text-primary" aria-hidden="true" />}
            action={
              <Badge variant="outline" className="w-fit text-[10px]">
                {t("homePrimaryInstrument", { symbol: primaryInstrument.symbol })}
              </Badge>
            }
          >
              {coreMarketIndexItems.length > 0 ? (
                <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                  {coreMarketIndexItems.map((item) => {
                    const movement = item.latest?.movement ?? null;
                    const movementValue = movement?.absolute_change ?? 0;
                    const movementClassName = getMarketMovementTextClass(platformSettings.color_scheme, movementValue);
                    const indexName = locale === "zh" ? item.name_zh ?? item.name : item.name;
                    const providerLabel = item.effective_provider ?? item.provider ?? item.source ?? t("unavailableShort");
                    return (
                      <div key={item.code} className="min-h-[10.5rem] rounded-sm border bg-background/60 p-3 transition-colors hover:border-primary/30 hover:bg-accent/40">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-semibold">{indexName}</div>
                            {shouldShowHomeIndexField("region") ? (
                              <div className="mt-1 text-[10px] text-muted-foreground">
                                {t("homeIndexRegion", { region: item.region })}
                              </div>
                            ) : null}
                          </div>
                          {shouldShowHomeIndexField("freshness") ? (
                            <Badge variant={getFreshnessBadgeVariant(coerceFreshnessStatus(item.freshness))} className="text-[10px]">
                              {t(coerceFreshnessStatus(item.freshness))}
                            </Badge>
                          ) : null}
                        </div>
                        {shouldShowHomeIndexField("latest_close") ? (
                          <div className="mt-3 font-mono text-2xl font-semibold tabular-nums">
                            {formatDashboardNumber(item.latest?.close, locale, t("unavailableShort"))}
                          </div>
                        ) : null}
                        {shouldShowHomeIndexField("percent_change") ? (
                          <div className={`mt-1 font-mono text-sm tabular-nums ${movementClassName}`}>
                            {movement
                              ? formatSignedPercent(movement.percent_change ?? null, locale, t("unavailableShort"))
                              : t("unavailableShort")}
                          </div>
                        ) : null}
                        {shouldShowHomeIndexField("as_of") ? (
                          <div className="mt-2 text-[10px] text-muted-foreground">
                            {t("valuationAsOf", {
                              date: formatDashboardDate(item.latest?.timestamp, locale, t("unavailableShort")),
                            })}
                          </div>
                        ) : null}
                        {shouldShowHomeIndexField("provider") ? (
                          <div className="mt-2 text-[10px] text-muted-foreground">
                            {t("homeIndexProvider", { provider: providerLabel })}
                          </div>
                        ) : null}
                        <MiniSparkline bars={item.bars} movementValue={movementValue} />
                        {item.isConfiguredMissing ? (
                          <p className="mt-2 text-xs text-muted-foreground">
                            {t("homeIndexPayloadMissing", { code: item.code })}
                          </p>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("noCoreIndices")}</p>
              )}
          </TerminalPanel>
        </section>

        <section className="space-y-4" aria-labelledby="macro-watch-heading">
          <TerminalPanel
            title={t("favoriteMacroTitle")}
            titleId="macro-watch-heading"
            description={t("favoriteMacroDesc")}
            icon={<Activity className="h-4 w-4 text-primary" aria-hidden="true" />}
            action={
              <div className="flex flex-wrap justify-end gap-2">
                <Badge variant="outline" className="text-[10px]">
                  {t("homeMacroMetricDesc", { available: availableMacroCount, total: macroTotalCount })}
                </Badge>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/settings">{t("favoriteMacroSettingsLink")}</Link>
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link href="/evidence">{t("favoriteMacroDetailLink")}</Link>
                </Button>
              </div>
            }
          >
            <div className="overflow-hidden rounded-sm border">
              {favoriteMacroIndicatorRows.map(({ code, item }) => {
                const isAvailable = item?.status === "ok";
                const displayName = item?.name ?? code;
                const sourceOrGap = item
                  ? isAvailable
                    ? t("favoriteMacroSource", { source: item.source ?? t("unavailableShort") })
                    : t("favoriteMacroSourceGap", {
                        reason: item.no_data_reason ?? t("indicatorNoData"),
                      })
                  : t("favoriteMacroSourceGap", { reason: t("favoriteMacroPayloadMissing") });
                const nextAction = getFavoriteMacroNextAction(code, item);
                return (
                  <div
                    key={code}
                    className="grid gap-3 border-b bg-background/50 p-3 last:border-b-0 md:grid-cols-[minmax(0,1.4fr)_8rem_minmax(0,1fr)] md:items-center"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">{displayName}</div>
                      <div className="mt-1 text-[10px] text-muted-foreground">
                        {t("favoriteMacroCode", { code })}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {item?.region ? (
                          <Badge variant="outline" className="px-1 py-0 text-[10px]">
                            {t("favoriteMacroRegion", { region: item.region })}
                          </Badge>
                        ) : null}
                        {item?.category ? (
                          <Badge variant="outline" className="px-1 py-0 text-[10px]">
                            {t("favoriteMacroCategory", { category: formatIndicatorCategoryLabel(item.category) })}
                          </Badge>
                        ) : null}
                      </div>
                    </div>
                    <div className="min-w-0">
                      <div className="font-mono text-xl font-semibold tabular-nums">
                        {item ? formatValuationIndicatorValue(item, locale, t("unavailableShort")) : t("unavailableShort")}
                      </div>
                      <div className="mt-1 text-[10px] text-muted-foreground">
                        {t("valuationAsOf", {
                          date: item ? formatDashboardDate(item.as_of, locale, t("unavailableShort")) : t("unavailableShort"),
                        })}
                      </div>
                    </div>
                    <div className="min-w-0">
                      <Badge variant={isAvailable ? "secondary" : "outline"} className="mb-2 text-[10px]">
                        {isAvailable ? t("available") : t("no_data")}
                      </Badge>
                      <p className="line-clamp-2 text-xs text-muted-foreground">{sourceOrGap}</p>
                      {nextAction ? (
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                          <span className="font-semibold text-foreground">{t("favoriteMacroNextAction")}</span>{" "}
                          {nextAction}
                        </p>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </TerminalPanel>
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <HotSectors
            sectors={hotSectorItemsForHome}
            status={hotSectorsPayload.status}
            dataMode={hotSectorsPayload.data_mode}
            message={hotSectorsPayload.message}
            provider={hotSectorsPayload.effective_provider ?? hotSectorsPayload.provider ?? null}
            asOf={hotSectorsPayload.as_of ?? null}
            isRealtime={hotSectorsPayload.is_realtime ?? false}
            isDelayed={hotSectorsPayload.is_delayed ?? false}
            delayMinutes={hotSectorsPayload.delay_minutes ?? null}
            flowDefinition={hotSectorsPayload.flow_definition ?? null}
            className="rounded-md bg-card/95"
          />

          <div className="grid gap-4">
            <TerminalPanel
              title={t("latestNews")}
              description={t("latestNewsDesc", { source: newsPayload.source })}
              icon={<Newspaper className="h-4 w-4 text-primary" aria-hidden="true" />}
            >
                {latestNews ? (
                  <div className="space-y-3 rounded-sm border bg-background/55 p-3">
                    <p className="text-sm font-medium leading-6">{latestNews.title}</p>
                    <div className="flex flex-wrap items-center gap-2">
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
            </TerminalPanel>

            <TerminalPanel
              title={t("importantSignalsTitle")}
              description={t("importantSignalsDesc")}
              icon={<Activity className="h-4 w-4 text-primary" aria-hidden="true" />}
            >
              <div className="space-y-2">
                <div className="rounded-sm border bg-background/55 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold">{t("dataHealthTitle")}</div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {t("dataFreshnessSummary", {
                          fresh: dashboardHealthCounts.fresh,
                          stale: dashboardHealthCounts.stale,
                          missing: missingHealthCount,
                        })}
                      </div>
                    </div>
                    <Badge
                      variant={hasMissingOrUnavailableData ? "destructive" : hasStaleData ? "outline" : "secondary"}
                      className="shrink-0 text-[10px]"
                    >
                      {checkedInstrumentCount}
                    </Badge>
                  </div>
                </div>

                <div className="rounded-sm border bg-background/55 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 text-sm font-semibold">
                        <Bell className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                        {t("activeAlerts")}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {t("triggeredAlertsSummary", { count: triggeredWatchlistCount })}
                      </div>
                    </div>
                    <Button variant="outline" size="sm" asChild>
                      <Link href="/alerts">{t("viewAlerts")}</Link>
                    </Button>
                  </div>
                </div>

                <div className="rounded-sm border bg-background/55 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold">{t("latestTaskRun")}</div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {t("taskRunStatusSummary", { status: taskRunPayload.status })}
                      </div>
                    </div>
                    <Button variant="outline" size="sm" asChild>
                      <Link href={taskRunPayload.id ? (`/task-runs/${taskRunPayload.id}` as any) : "/task-runs"}>
                        {t("viewTaskRuns")}
                      </Link>
                    </Button>
                  </div>
                </div>

                <div className="rounded-sm border bg-background/55 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 text-sm font-semibold">
                        <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                        {primaryInstrument.symbol}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {t("latestPrice", { symbol: primaryInstrument.symbol })}: {formatDashboardNumber(latestClose, locale, t("unavailableShort"))}
                      </div>
                    </div>
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/instruments/${primaryInstrument.symbol}` as any}>{t("openInstrument")}</Link>
                    </Button>
                  </div>
                </div>
              </div>
            </TerminalPanel>
          </div>
        </div>

        <TerminalPanel
          title={t("newsProviderStripTitle")}
          description={t("newsProviderStripDesc")}
          icon={<Search className="h-4 w-4 text-primary" aria-hidden="true" />}
          action={
            <Button variant="outline" size="sm" asChild>
              <Link href="/settings" className="gap-2">
                <Settings2 className="h-3.5 w-3.5" aria-hidden="true" />
                {t("providerSettings")}
              </Link>
            </Button>
          }
        >
          {newsSearchProviderCapabilities.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
              {newsSearchProviderCapabilities.map((capability) => {
                const statusKey = getNewsProviderStatusKey(capability);
                const statusClassName = getNewsProviderStatusClassName(capability);
                return (
                  <div
                    key={capability.provider}
                    className={`min-h-[5.75rem] rounded-sm border bg-background/55 p-2.5 ${statusClassName}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-foreground">{capability.display_name}</div>
                        <div className="mt-1 font-mono text-[10px] text-muted-foreground">
                          {t("newsProviderPriority", { priority: capability.priority })}
                        </div>
                      </div>
                      {capability.configured ? (
                        <ShieldCheck className="h-4 w-4 shrink-0" aria-hidden="true" />
                      ) : (
                        <CircleAlert className="h-4 w-4 shrink-0" aria-hidden="true" />
                      )}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1">
                      <Badge variant="outline" className="px-1 py-0 text-[10px]">
                        {t(statusKey as any)}
                      </Badge>
                      {capability.enabled ? (
                        <Badge variant="outline" className="px-1 py-0 text-[10px]">
                          {t("newsProviderEnabled")}
                        </Badge>
                      ) : null}
                    </div>
                    <div className="mt-2 truncate text-[10px] text-muted-foreground">
                      {capability.implementation_status}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t("newsProviderStripEmpty")}</p>
          )}
        </TerminalPanel>
      </div>
    </div>
  );
}
