import { Link } from "@/src/i18n/routing";
import type { ReactNode } from "react";
import { Activity, ArrowRight, Newspaper, Search, Settings2, ShieldCheck, CircleAlert, Plus, BarChart3, Gauge, LineChart } from "lucide-react";

import { FlashBanner } from "@/components/flash-banner";
import { FinancialDashboardHero } from "@/components/financial-dashboard-hero";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { withProviderQuery } from "@/lib/market-data";
import { getMarketMovementTextClass, type MarketColorScheme } from "@/lib/market-color-classes";
import {
  DEFAULT_FAVORITE_HOME_INDEX_CODES,
  DEFAULT_FAVORITE_MACRO_INDICATOR_CODES,
  getPlatformSettings,
  type HomeIndexDisplayField,
  type NewsSearchProviderCapability,
} from "@/lib/platform-settings-store";
import { backendFetch } from "@/lib/backend-api";

type Instrument = {
  symbol: string;
  name: string;
  market: string;
};

type InstrumentsPayload = {
  items: Instrument[];
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

type WatchlistPayload = {
  items: Array<{
    symbol: string;
    market: string;
    alert_status?: { triggered?: boolean };
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

function formatSignedDashboardNumber(value: number | null | undefined, locale: string, unavailableLabel: string): string {
  if (value === null || value === undefined) {
    return unavailableLabel;
  }
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

function formatCompactDashboardNumber(value: number | null | undefined, locale: string, unavailableLabel: string): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return unavailableLabel;
  }
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 1,
    notation: "compact",
  }).format(value);
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
      className="mt-1.5 h-6 w-full overflow-visible"
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

function TerminalActionLink({
  href,
  label,
  icon,
}: {
  href: string;
  label: string;
  icon?: ReactNode;
}) {
  return (
    <Button
      variant="outline"
      size="sm"
      asChild
      className="border-border/80 bg-background/60 px-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      <Link href={href} className="gap-1.5">
        <span>{label}</span>
        {icon ?? <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />}
      </Link>
    </Button>
  );
}

function TerminalPanel({
  title,
  description,
  icon,
  action,
  children,
  className = "",
  contentClassName = "",
  titleId,
}: {
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  titleId?: string;
}) {
  return (
    <Card className={`flex flex-col overflow-hidden rounded-md border border-border/80 bg-card/95 shadow-[0_0_0_1px_hsl(var(--primary)/0.04)] ${className}`}>
      <CardHeader className="!space-y-0 border-b border-border/70 bg-background/60 !px-3 !py-2">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <CardTitle id={titleId} className="flex items-center gap-2 text-sm">
              {icon}
              <span className="truncate">{title}</span>
            </CardTitle>
            {description ? <CardDescription className="mt-1 text-xs xl:hidden">{description}</CardDescription> : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
      </CardHeader>
      <CardContent className={`min-h-0 flex-1 p-0 ${contentClassName}`}>{children}</CardContent>
    </Card>
  );
}

function getDashboardIndexName(item: DashboardHomeIndexItem, requestedLocale: string): string {
  return requestedLocale === "zh" ? item.name_zh ?? item.name : item.name;
}

function IndexTickerCard({
  item,
  requestedLocale,
  locale,
  unavailableLabel,
  colorScheme,
  shouldShowField,
  missingMessage,
}: {
  item: DashboardHomeIndexItem;
  requestedLocale: string;
  locale: string;
  unavailableLabel: string;
  colorScheme: MarketColorScheme;
  shouldShowField: (field: HomeIndexDisplayField) => boolean;
  missingMessage: string;
}) {
  const movement = item.latest?.movement ?? null;
  const movementValue = movement?.absolute_change ?? 0;
  const movementClassName = getMarketMovementTextClass(colorScheme, movementValue);
  const indexName = getDashboardIndexName(item, requestedLocale);
  const providerLabel = item.effective_provider ?? item.provider ?? item.source ?? unavailableLabel;

  return (
    <div className="min-h-[4.85rem] min-w-[8.4rem] rounded-sm border border-border/70 bg-background/55 p-1.5 font-mono transition-colors hover:border-primary/35 hover:bg-accent/35">
      <div className="flex items-start justify-between gap-2 font-sans">
        <div className="min-w-0">
          <div className="truncate text-xs font-semibold text-foreground">{indexName}</div>
          {shouldShowField("region") ? (
            <div className="mt-0.5 text-[10px] text-muted-foreground">{item.region}</div>
          ) : null}
        </div>
        {shouldShowField("freshness") ? (
          <span className="rounded-sm border border-border/70 px-1 py-0.5 text-[10px] text-muted-foreground">
            {coerceFreshnessStatus(item.freshness)}
          </span>
        ) : null}
      </div>
      {shouldShowField("latest_close") ? (
        <div className="mt-1 text-sm font-semibold leading-none tabular-nums">
          {formatDashboardNumber(item.latest?.close, locale, unavailableLabel)}
        </div>
      ) : null}
      {shouldShowField("percent_change") ? (
        <div className={`mt-0.5 text-[10px] tabular-nums ${movementClassName}`}>
          {movement
            ? `${formatSignedDashboardNumber(movement.absolute_change, locale, unavailableLabel)} ${formatSignedPercent(movement.percent_change ?? null, locale, unavailableLabel)}`
            : unavailableLabel}
        </div>
      ) : null}
      <MiniSparkline bars={item.bars} movementValue={movementValue} />
      <div className="mt-0.5 flex flex-wrap gap-x-2 gap-y-1 font-sans text-[10px] text-muted-foreground">
        {shouldShowField("as_of") ? (
          <span>{formatDashboardDate(item.latest?.timestamp, locale, unavailableLabel)}</span>
        ) : null}
        {shouldShowField("provider") ? <span>{providerLabel}</span> : null}
      </div>
      {item.isConfiguredMissing ? (
        <p className="mt-1 line-clamp-2 font-sans text-[10px] leading-4 text-muted-foreground">{missingMessage}</p>
      ) : null}
    </div>
  );
}

function HomepageMarketBand({
  items,
  requestedLocale,
  locale,
  unavailableLabel,
  colorScheme,
  shouldShowField,
  t,
}: {
  items: DashboardHomeIndexItem[];
  requestedLocale: string;
  locale: string;
  unavailableLabel: string;
  colorScheme: MarketColorScheme;
  shouldShowField: (field: HomeIndexDisplayField) => boolean;
  t: (key: any, values?: Record<string, string | number>) => string;
}) {
  const selectedItems = items.slice(0, 5);
  const cnItems = items.filter((item) => item.region === "CN").slice(0, 5);
  const aShareItems = cnItems.length > 0 ? cnItems : items.slice(0, 5);

  return (
    <section className="overflow-hidden rounded-md border border-border/80 bg-card/95 shadow-[0_0_0_1px_hsl(var(--primary)/0.06)]" aria-labelledby="home-market-band-heading">
      <div className="grid gap-2 border-b border-border/70 bg-background/65 px-3 py-2 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:items-center">
        <div className="flex min-w-0 flex-wrap items-center gap-1">
          <Link href="/instruments" className="rounded-sm border border-primary/45 bg-primary/15 px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/20">
            {t("marketFilterAll")}
          </Link>
          <Link href="/instruments" className="rounded-sm border border-border/70 bg-background/70 px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent">
            {t("marketFilterCn")}
          </Link>
          <Link href="/settings" className="rounded-sm border border-border/70 bg-background/70 px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent">
            {t("homeMarketBandEdit")}
          </Link>
        </div>
        <div className="min-w-0 text-center">
          <h1 id="home-market-band-heading" className="truncate text-sm font-semibold text-foreground">
            {t("homeMarketBandTitle")}
          </h1>
          <div className="mt-0.5 text-[10px] text-muted-foreground">{t("homeOverviewTitle")}</div>
        </div>
        <div className="flex flex-wrap justify-start gap-1.5 lg:justify-end">
          <TerminalActionLink href="/instruments" label={t("terminalActionMore")} />
          <Button variant="outline" size="sm" asChild>
            <Link href="/settings" className="gap-2">
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              {t("homeAddIndicator")}
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-1.5 p-1.5 xl:grid-cols-2">
        <TickerLane
          title={t("homeSelectedMarketGroup")}
          items={selectedItems}
          requestedLocale={requestedLocale}
          locale={locale}
          unavailableLabel={unavailableLabel}
          colorScheme={colorScheme}
          shouldShowField={shouldShowField}
          getMissingMessage={(code) => t("homeIndexPayloadMissing", { code })}
        />
        <TickerLane
          title={t("homeAshareMarketGroup")}
          items={aShareItems}
          requestedLocale={requestedLocale}
          locale={locale}
          unavailableLabel={unavailableLabel}
          colorScheme={colorScheme}
          shouldShowField={shouldShowField}
          getMissingMessage={(code) => t("homeIndexPayloadMissing", { code })}
        />
      </div>
    </section>
  );
}

function TickerLane({
  title,
  items,
  requestedLocale,
  locale,
  unavailableLabel,
  colorScheme,
  shouldShowField,
  getMissingMessage,
}: {
  title: string;
  items: DashboardHomeIndexItem[];
  requestedLocale: string;
  locale: string;
  unavailableLabel: string;
  colorScheme: MarketColorScheme;
  shouldShowField: (field: HomeIndexDisplayField) => boolean;
  getMissingMessage: (code: string) => string;
}) {
  return (
    <div className="min-w-0 rounded-sm border border-border/70 bg-background/35 p-1.5">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <div className="text-xs font-semibold text-foreground">{title}</div>
        <div className="text-[10px] text-muted-foreground">{items.length}</div>
      </div>
      <div className="flex min-w-0 gap-2 overflow-x-auto pb-1 scrollbar-thin">
        {items.map((item) => (
          <IndexTickerCard
            key={`${title}-${item.code}`}
            item={item}
            requestedLocale={requestedLocale}
            locale={locale}
            unavailableLabel={unavailableLabel}
            colorScheme={colorScheme}
            shouldShowField={shouldShowField}
            missingMessage={getMissingMessage(item.code)}
          />
        ))}
      </div>
    </div>
  );
}

function MacroIndicatorsPanel({
  rows,
  locale,
  unavailableLabel,
  t,
}: {
  rows: DashboardFavoriteMacroIndicatorRow[];
  locale: string;
  unavailableLabel: string;
  t: (key: any, values?: Record<string, string | number>) => string;
}) {
  return (
    <TerminalPanel
      title={t("terminalMacroTitle")}
      description={t("terminalMacroDesc")}
      titleId="terminal-macro-heading"
      icon={<Activity className="h-3.5 w-3.5 text-primary" aria-hidden="true" />}
      className="h-[15.5rem]"
      action={
        <div className="flex flex-wrap justify-end gap-1.5">
          <TerminalActionLink
            href="/settings#favorite_macro_indicator_codes"
            label={t("terminalActionAddCustomIndicator")}
            icon={<Plus className="h-3.5 w-3.5" aria-hidden="true" />}
          />
          <TerminalActionLink href="/evidence" label={t("terminalActionMore")} />
        </div>
      }
      contentClassName="flex min-h-0 flex-col"
    >
      <div className="grid shrink-0 grid-cols-[minmax(0,1.35fr)_5.5rem_4.5rem_5.5rem] border-b border-border/70 bg-background/40 px-3 py-2 text-[10px] uppercase text-muted-foreground">
        <span>{t("terminalIndicator")}</span>
        <span className="text-right">{t("terminalLatestValue")}</span>
        <span className="text-right">{t("terminalTrend")}</span>
        <span className="text-right">{t("terminalUpdated")}</span>
      </div>
      <div className="min-h-0 flex-1 divide-y divide-border/65 overflow-y-auto scrollbar-thin">
        {rows.map(({ code, item }) => {
          const isAvailable = item?.status === "ok";
          const displayName = item?.name ?? code;
          return (
            <div key={code} className="grid min-h-[2.25rem] grid-cols-[minmax(0,1.35fr)_5.5rem_4.5rem_5.5rem] items-center gap-2 px-3 py-1.5 text-xs">
              <div className="min-w-0">
                <div className="truncate font-medium text-foreground">{displayName}</div>
                <div className="mt-0.5 truncate text-[10px] text-muted-foreground">{code}</div>
              </div>
              <div className="text-right font-mono tabular-nums">
                {item ? formatValuationIndicatorValue(item, locale, unavailableLabel) : unavailableLabel}
              </div>
              <div className={`text-right text-[11px] ${isAvailable ? "text-positive" : "text-warning"}`}>
                {isAvailable ? t("available") : t("no_data")}
              </div>
              <div className="text-right text-[10px] text-muted-foreground">
                {item ? formatDashboardDate(item.as_of, locale, unavailableLabel) : unavailableLabel}
              </div>
            </div>
          );
        })}
      </div>
    </TerminalPanel>
  );
}

function resolveHotSectorFlowValue(sector: HotSectorItem): number | null {
  const directValue = sector.net_flow_amount ?? sector.fund_flow_amount;
  return directValue === null || directValue === undefined || Number.isNaN(directValue) ? null : directValue;
}

function resolveHotSectorChange(sector: HotSectorItem): number | null {
  return sector.change_percent === null || sector.change_percent === undefined || Number.isNaN(sector.change_percent)
    ? null
    : sector.change_percent;
}

function HotSectorTablePanel({
  sectors,
  locale,
  colorScheme,
  unavailableLabel,
  t,
}: {
  sectors: HotSectorItem[];
  locale: string;
  colorScheme: MarketColorScheme;
  unavailableLabel: string;
  t: (key: any, values?: Record<string, string | number>) => string;
}) {
  return (
    <TerminalPanel
      title={t("terminalHotSectorsTitle")}
      description={t("terminalHotSectorsDesc")}
      titleId="terminal-hot-sectors-heading"
      icon={<BarChart3 className="h-3.5 w-3.5 text-primary" aria-hidden="true" />}
      className="h-[15.5rem]"
      action={<TerminalActionLink href="/instruments" label={t("terminalActionMore")} />}
      contentClassName="flex min-h-0 flex-col"
    >
      <div className="grid shrink-0 grid-cols-[2.25rem_minmax(0,1fr)_4.5rem_5rem_3.5rem] border-b border-border/70 bg-background/40 px-3 py-2 text-[10px] uppercase text-muted-foreground">
        <span>{t("terminalRank")}</span>
        <span>{t("terminalSector")}</span>
        <span className="text-right">{t("terminalChange")}</span>
        <span className="text-right">{t("terminalMainFlow")}</span>
        <span className="text-right">{t("terminalAiHeat")}</span>
      </div>
      {sectors.length > 0 ? (
        <div className="min-h-0 flex-1 divide-y divide-border/65 overflow-y-auto scrollbar-thin">
          {sectors.map((sector, index) => {
            const change = resolveHotSectorChange(sector);
            const flowValue = resolveHotSectorFlowValue(sector);
            const heat = Math.min(99, Math.max(35, Math.round(Math.abs(change ?? 0) * 12 + (flowValue !== null && flowValue > 0 ? 35 : 28))));
            const movementClassName = getMarketMovementTextClass(colorScheme, change ?? 0);
            return (
              <div key={sector.sector_id ?? `${sector.name}-${index}`} className="grid min-h-[2.25rem] grid-cols-[2.25rem_minmax(0,1fr)_4.5rem_5rem_3.5rem] items-center gap-2 px-3 py-1.5 text-xs">
                <div className="font-mono text-[11px] text-muted-foreground">{sector.rank ?? index + 1}</div>
                <div className="min-w-0">
                  <div className="truncate font-medium text-foreground">{sector.name}</div>
                  <div className="mt-0.5 truncate text-[10px] text-muted-foreground">{sector.leader_symbol ?? sector.leader?.symbol ?? sector.market ?? unavailableLabel}</div>
                </div>
                <div className={`text-right font-mono text-[11px] tabular-nums ${movementClassName}`}>
                  {change === null ? unavailableLabel : formatSignedPercent(change / 100, locale, unavailableLabel)}
                </div>
                <div className={`text-right font-mono text-[11px] tabular-nums ${flowValue !== null && flowValue >= 0 ? "text-positive" : "text-negative"}`}>
                  {formatCompactDashboardNumber(flowValue, locale, unavailableLabel)}
                </div>
                <div className="text-right font-mono text-[11px] text-warning tabular-nums">{heat}</div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 items-center p-4 text-sm text-muted-foreground">{t("hotSectorsEmptyLive")}</div>
      )}
    </TerminalPanel>
  );
}

function LatestNewsSentimentPanel({
  items,
  moreHref,
  unavailableLabel,
  t,
}: {
  items: NewsPayload["items"];
  moreHref: string;
  unavailableLabel: string;
  t: (key: any, values?: Record<string, string | number>) => string;
}) {
  const newsRows = items.slice(0, 6);
  return (
    <TerminalPanel
      title={t("terminalLatestNewsTitle")}
      description={t("terminalLatestNewsDesc")}
      titleId="terminal-latest-news-heading"
      icon={<Newspaper className="h-3.5 w-3.5 text-primary" aria-hidden="true" />}
      className="h-[15.5rem]"
      action={<TerminalActionLink href={moreHref} label={t("terminalActionMore")} />}
      contentClassName="flex min-h-0 flex-col"
    >
      {newsRows.length > 0 ? (
        <div className="min-h-0 flex-1 divide-y divide-border/65 overflow-y-auto scrollbar-thin">
          {newsRows.map((item, index) => {
            const sentimentClassName =
              item.sentiment === "positive"
                ? "border-positive/35 bg-positive/10 text-positive"
                : item.sentiment === "negative"
                  ? "border-negative/35 bg-negative/10 text-negative"
                  : "border-primary/35 bg-primary/10 text-primary";
            return (
              <div key={`${item.title}-${index}`} className="grid min-h-[2.65rem] grid-cols-[2rem_minmax(0,1fr)_4.25rem] items-start gap-2 px-3 py-1.5 text-xs">
                <div className="font-mono text-[11px] font-semibold text-primary">{index + 1}</div>
                <div className="min-w-0">
                  <div className="line-clamp-1 font-medium text-foreground">{item.title}</div>
                  <div className="mt-1 text-[10px] text-muted-foreground">
                    {t("confidence", { score: Math.round(item.confidence * 100) })}
                  </div>
                </div>
                <div className={`rounded-sm border px-1.5 py-1 text-center text-[10px] ${sentimentClassName}`}>
                  {item.sentiment || unavailableLabel}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 items-center p-4 text-sm text-muted-foreground">{t("noNews")}</div>
      )}
    </TerminalPanel>
  );
}

function MarketOverviewChartPanel({
  items,
  requestedLocale,
  locale,
  colorScheme,
  unavailableLabel,
  t,
}: {
  items: DashboardHomeIndexItem[];
  requestedLocale: string;
  locale: string;
  colorScheme: MarketColorScheme;
  unavailableLabel: string;
  t: (key: any, values?: Record<string, string | number>) => string;
}) {
  const series = items.filter((item) => item.bars.length > 1).slice(0, 3);
  const width = 420;
  const height = 142;
  const chartHeight = 100;
  const chartTop = 14;
  const colors = ["text-positive", "text-primary", "text-warning"];

  return (
    <TerminalPanel
      title={t("terminalMarketOverviewTitle")}
      description={t("terminalMarketOverviewDesc")}
      titleId="terminal-market-overview-heading"
      icon={<LineChart className="h-3.5 w-3.5 text-primary" aria-hidden="true" />}
      className="xl:h-[14.25rem]"
      action={<TerminalActionLink href="/instruments" label={t("terminalActionMore")} />}
      contentClassName="p-3"
    >
      {series.length > 0 ? (
        <>
          <svg className="h-28 w-full overflow-visible" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t("terminalMarketOverviewTitle")}>
            <path d={`M0,${chartTop + chartHeight} L${width},${chartTop + chartHeight}`} className="stroke-border" strokeWidth="1" strokeDasharray="3 7" />
            <path d={`M0,${chartTop + chartHeight / 2} L${width},${chartTop + chartHeight / 2}`} className="stroke-border/60" strokeWidth="1" strokeDasharray="2 8" />
            {series.map((item, index) => {
              const path = buildSparklinePath(item.bars.map((bar) => bar.close), width, chartHeight);
              return path ? (
                <path
                  key={item.code}
                  d={path}
                  className={colors[index] ?? "text-primary"}
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  transform={`translate(0 ${chartTop})`}
                />
              ) : null;
            })}
          </svg>
          <div className="grid gap-2 sm:grid-cols-3">
            {series.map((item, index) => {
              const movement = item.latest?.movement ?? null;
              const movementValue = movement?.absolute_change ?? 0;
              const movementClassName = getMarketMovementTextClass(colorScheme, movementValue);
              return (
                <div key={item.code} className="rounded-sm border border-border/70 bg-background/45 p-2">
                  <div className={`truncate text-xs font-medium ${colors[index] ?? "text-primary"}`}>{getDashboardIndexName(item, requestedLocale)}</div>
                  <div className="mt-1 font-mono text-[11px] tabular-nums text-muted-foreground">
                    {formatDashboardNumber(item.latest?.close, locale, unavailableLabel)}
                  </div>
                  <div className={`mt-0.5 font-mono text-[11px] tabular-nums ${movementClassName}`}>
                    {movement ? formatSignedPercent(movement.percent_change ?? null, locale, unavailableLabel) : unavailableLabel}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className="text-sm text-muted-foreground">{t("noMarketChartData")}</div>
      )}
    </TerminalPanel>
  );
}

function FundFlowPanel({
  sectors,
  locale,
  unavailableLabel,
  t,
}: {
  sectors: HotSectorItem[];
  locale: string;
  unavailableLabel: string;
  t: (key: any, values?: Record<string, string | number>) => string;
}) {
  const rows = sectors
    .map((sector) => ({
      name: sector.name,
      value: resolveHotSectorFlowValue(sector),
    }))
    .filter((row): row is { name: string; value: number } => row.value !== null)
    .slice(0, 8);
  const width = 420;
  const height = 142;
  const baseline = 72;
  const maxAbs = Math.max(...rows.map((row) => Math.abs(row.value)), 1);
  const barWidth = rows.length > 0 ? Math.max(18, Math.floor((width - 32) / rows.length) - 8) : 20;

  return (
    <TerminalPanel
      title={t("terminalFundFlowTitle")}
      description={t("terminalFundFlowDesc")}
      titleId="terminal-fund-flow-heading"
      icon={<BarChart3 className="h-3.5 w-3.5 text-primary" aria-hidden="true" />}
      className="xl:h-[14.25rem]"
      action={<TerminalActionLink href="/instruments" label={t("terminalActionMore")} />}
      contentClassName="p-3"
    >
      {rows.length > 0 ? (
        <>
          <svg className="h-28 w-full overflow-visible" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t("terminalFundFlowTitle")}>
            <path d={`M0,${baseline} L${width},${baseline}`} className="stroke-border" strokeWidth="1" strokeDasharray="3 7" />
            {rows.map((row, index) => {
              const normalizedHeight = Math.max(8, Math.abs(row.value) / maxAbs * 54);
              const x = 18 + index * ((width - 36) / rows.length);
              const y = row.value >= 0 ? baseline - normalizedHeight : baseline;
              return (
                <g key={`${row.name}-${index}`}>
                  <rect
                    x={x}
                    y={y}
                    width={barWidth}
                    height={normalizedHeight}
                    rx="2"
                    className={row.value >= 0 ? "fill-positive" : "fill-negative"}
                    opacity="0.88"
                  />
                </g>
              );
            })}
          </svg>
          <div className="grid gap-1">
            {rows.slice(0, 4).map((row) => (
              <div key={row.name} className="flex items-center justify-between gap-3 rounded-sm bg-background/45 px-2 py-1.5 text-xs">
                <span className="truncate text-muted-foreground">{row.name}</span>
                <span className={`font-mono tabular-nums ${row.value >= 0 ? "text-positive" : "text-negative"}`}>
                  {formatCompactDashboardNumber(row.value, locale, unavailableLabel)}
                </span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="text-sm text-muted-foreground">{t("noFundFlowData")}</div>
      )}
    </TerminalPanel>
  );
}

function buildAiSentimentSummary({
  newsItems,
  healthCounts,
  checkedInstrumentCount,
  sectors,
  providers,
}: {
  newsItems: NewsPayload["items"];
  healthCounts: DashboardHealthCounts;
  checkedInstrumentCount: number;
  sectors: HotSectorItem[];
  providers: NewsSearchProviderCapability[];
}) {
  const newsScore = newsItems.length === 0
    ? 50
    : newsItems.reduce((total, item) => {
        if (item.sentiment === "positive") return total + 50 + item.confidence * 45;
        if (item.sentiment === "negative") return total + 50 - item.confidence * 45;
        return total + 50;
      }, 0) / newsItems.length;
  const sectorChanges = sectors
    .map((sector) => resolveHotSectorChange(sector))
    .filter((value): value is number => value !== null);
  const sectorScore = sectorChanges.length === 0
    ? 50
    : Math.min(95, Math.max(5, 50 + sectorChanges.reduce((sum, value) => sum + value, 0) / sectorChanges.length * 4));
  const dataHealthScore = checkedInstrumentCount === 0
    ? 50
    : (healthCounts.fresh * 100 + healthCounts.stale * 55 + healthCounts.no_data * 20) / checkedInstrumentCount;
  const providerScore = providers.length === 0
    ? 50
    : providers.filter((provider) => provider.enabled && (!provider.credential_required || provider.credential_configured)).length / providers.length * 100;
  const score = Math.round(newsScore * 0.4 + sectorScore * 0.25 + dataHealthScore * 0.2 + providerScore * 0.15);
  const labelKey = score >= 66 ? "aiSentimentOptimistic" : score <= 42 ? "aiSentimentCautious" : "aiSentimentNeutral";
  const toneClassName = score >= 66 ? "text-positive" : score <= 42 ? "text-negative" : "text-warning";

  return {
    score: Math.max(0, Math.min(100, score)),
    labelKey,
    toneClassName,
    newsScore: Math.round(newsScore),
    dataHealthScore: Math.round(dataHealthScore),
    providerScore: Math.round(providerScore),
  };
}

function AiSentimentPanel({
  summary,
  t,
}: {
  summary: ReturnType<typeof buildAiSentimentSummary>;
  t: (key: any, values?: Record<string, string | number>) => string;
}) {
  return (
    <TerminalPanel
      title={t("terminalAiSentimentTitle")}
      description={t("terminalAiSentimentDesc")}
      titleId="terminal-ai-sentiment-heading"
      icon={<Gauge className="h-3.5 w-3.5 text-primary" aria-hidden="true" />}
      className="xl:h-[14.25rem]"
      action={<TerminalActionLink href="/ai-research" label={t("terminalActionMore")} />}
      contentClassName="p-3"
    >
      <div className="grid gap-3 md:grid-cols-[10rem_minmax(0,1fr)] md:items-center">
        <div className="relative mx-auto h-32 w-40">
          <svg className="h-full w-full" viewBox="0 0 200 120" role="img" aria-label={t("terminalAiSentimentTitle")}>
            <path d="M30 96 A70 70 0 0 1 170 96" className="stroke-muted" fill="none" strokeWidth="18" strokeLinecap="round" pathLength={100} />
            <path
              d="M30 96 A70 70 0 0 1 170 96"
              className={summary.score >= 66 ? "stroke-positive" : summary.score <= 42 ? "stroke-negative" : "stroke-warning"}
              fill="none"
              strokeWidth="18"
              strokeLinecap="round"
              pathLength={100}
              strokeDasharray={`${summary.score} 100`}
            />
          </svg>
          <div className="absolute inset-x-0 bottom-4 text-center">
            <div className="font-mono text-3xl font-semibold tabular-nums text-foreground">{summary.score}</div>
            <div className={`text-xs font-medium ${summary.toneClassName}`}>{t(summary.labelKey)}</div>
          </div>
        </div>
        <div className="grid gap-2">
          <SentimentMetric label={t("aiSentimentNewsSignal")} value={summary.newsScore} />
          <SentimentMetric label={t("aiSentimentDataHealth")} value={summary.dataHealthScore} />
          <SentimentMetric label={t("aiSentimentProviderReadiness")} value={summary.providerScore} />
          <div className="rounded-sm border border-border/70 bg-background/45 px-2 py-1.5 text-[10px] text-muted-foreground xl:truncate">
            {t("aiSentimentResearchOnly")}
          </div>
        </div>
      </div>
    </TerminalPanel>
  );
}

function SentimentMetric({ label, value }: { label: string; value: number }) {
  const className = value >= 66 ? "text-positive" : value <= 42 ? "text-negative" : "text-warning";
  return (
    <div className="flex items-center justify-between gap-3 rounded-sm border border-border/70 bg-background/45 px-2 py-1.5 text-xs">
      <span className="truncate text-muted-foreground">{label}</span>
      <span className={`font-mono tabular-nums ${className}`}>{value}</span>
    </div>
  );
}

function NewsProviderStatusStrip({
  providers,
  t,
}: {
  providers: NewsSearchProviderCapability[];
  t: (key: any, values?: Record<string, string | number>) => string;
}) {
  return (
    <TerminalPanel
      title={t("newsProviderStripTitle")}
      description={t("newsProviderStripDesc")}
      titleId="terminal-news-provider-heading"
      icon={<Search className="h-3.5 w-3.5 text-primary" aria-hidden="true" />}
      action={<TerminalActionLink href="/settings" label={t("terminalActionMore")} icon={<Settings2 className="h-3.5 w-3.5" aria-hidden="true" />} />}
      contentClassName="p-2"
    >
      {providers.length > 0 ? (
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          {providers.map((capability) => {
            const statusKey = getNewsProviderStatusKey(capability);
            const statusClassName = getNewsProviderStatusClassName(capability);
            return (
              <div
                key={capability.provider}
                className={`min-h-[4.75rem] rounded-sm border bg-background/55 p-2 ${statusClassName}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-xs font-semibold text-foreground">{capability.display_name}</div>
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
                <div className="mt-2 flex flex-wrap gap-1">
                  <Badge variant="outline" className="px-1 py-0 text-[10px]">
                    {t(statusKey as any)}
                  </Badge>
                  {capability.enabled ? (
                    <Badge variant="outline" className="px-1 py-0 text-[10px]">
                      {t("newsProviderEnabled")}
                    </Badge>
                  ) : null}
                </div>
                <div className="mt-1 truncate text-[10px] text-muted-foreground">
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
    newsPayload,
    watchlistPayload,
    marketOverviewResult,
  ] =
    await Promise.all([
      fetchOptionalJson<NewsPayload>(
        `/news/${primaryInstrument.symbol}`,
        {
          source: "unavailable",
          items: [],
        },
      ),
      fetchOptionalJson<WatchlistPayload>("/watchlist", { items: [] }),
      fetchMarketOverviewResult(provider),
    ]);

  const dashboardHealth = buildDashboardHealthInstruments(instrumentsPayload.items, watchlistPayload.items);
  const marketOverviewPayload = marketOverviewResult.status === "loaded" ? marketOverviewResult.payload : null;
  const marketOverviewIndices = marketOverviewPayload?.indices.items ?? [];
  const marketOverviewValuationItems =
    marketOverviewPayload?.macro_indicators?.items ?? marketOverviewPayload?.valuation_indicators.items ?? [];
  const favoriteMacroIndicatorRows = buildFavoriteMacroIndicatorRows(
    marketOverviewValuationItems,
    platformSettings.favorite_macro_indicator_codes,
  );
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
  const hotSectors = hotSectorsPayload.items ?? [];

  const homeIndexDisplayFields = new Set<HomeIndexDisplayField>(platformSettings.home_index_display_fields);
  const shouldShowHomeIndexField = (field: HomeIndexDisplayField) => homeIndexDisplayFields.has(field);
  const coreMarketIndexItems = buildHomeIndexItems(
    marketOverviewIndices,
    platformSettings.favorite_home_index_codes,
  );

  const hotSectorItemsForHome = hotSectors.slice(0, 6);
  const newsSearchProviderCapabilities = platformSettings.news_search_provider_capabilities ?? [];
  const newsItemsForHome = newsPayload.items.slice(0, 6);
  const aiSentimentSummary = buildAiSentimentSummary({
    newsItems: newsItemsForHome,
    healthCounts: dashboardHealthCounts,
    checkedInstrumentCount,
    sectors: hotSectorItemsForHome,
    providers: newsSearchProviderCapabilities,
  });

  return (
    <div className="space-y-3 overflow-x-hidden">
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

        {marketOverviewResult.status === "failed" ? (
          <div className="rounded-md border bg-card p-4">
            <div className="font-medium">{t("marketDashboardUnavailableTitle")}</div>
            <p className="mt-1 text-sm text-muted-foreground">{t("marketDashboardUnavailableDesc")}</p>
          </div>
        ) : null}

        <HomepageMarketBand
          items={coreMarketIndexItems}
          requestedLocale={requestedLocale}
          locale={locale}
          unavailableLabel={t("unavailableShort")}
          colorScheme={platformSettings.color_scheme}
          shouldShowField={shouldShowHomeIndexField}
          t={t}
        />

        <div className="grid gap-2 xl:grid-cols-3">
          <MacroIndicatorsPanel
            rows={favoriteMacroIndicatorRows}
            locale={locale}
            unavailableLabel={t("unavailableShort")}
            t={t}
          />
          <HotSectorTablePanel
            sectors={hotSectorItemsForHome}
            locale={locale}
            colorScheme={platformSettings.color_scheme}
            unavailableLabel={t("unavailableShort")}
            t={t}
          />
          <LatestNewsSentimentPanel
            items={newsItemsForHome}
            moreHref={`/instruments/${primaryInstrument.symbol}`}
            unavailableLabel={t("unavailableShort")}
            t={t}
          />
          <MarketOverviewChartPanel
            items={coreMarketIndexItems}
            requestedLocale={requestedLocale}
            locale={locale}
            colorScheme={platformSettings.color_scheme}
            unavailableLabel={t("unavailableShort")}
            t={t}
          />
          <FundFlowPanel
            sectors={hotSectorItemsForHome}
            locale={locale}
            unavailableLabel={t("unavailableShort")}
            t={t}
          />
          <AiSentimentPanel summary={aiSentimentSummary} t={t} />
        </div>

        <NewsProviderStatusStrip providers={newsSearchProviderCapabilities} t={t} />
      </div>
    </div>
  );
}
