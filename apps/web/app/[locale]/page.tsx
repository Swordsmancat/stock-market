import { Link } from "@/src/i18n/routing";
import { TrendingUp, Activity, Briefcase, Newspaper, FileText, List, Bell } from "lucide-react";

import { AnalysisTriggerForm } from "@/components/analysis-trigger-form";
import { IngestionTriggerForm } from "@/components/ingestion-trigger-form";
import { FlashBanner } from "@/components/flash-banner";
import { MarketTicker } from "@/components/market-ticker";
import { MarketOverviewClient } from "@/components/market-overview-client";
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
  valuation_indicators: {
    items: DashboardValuationIndicatorItem[];
  };
  diagnostics: Array<Record<string, unknown>>;
};

type MarketOverviewLoadResult =
  | { status: "loaded"; payload: MarketOverviewPayload }
  | { status: "failed" };

const DASHBOARD_HEALTH_SAMPLE_LIMIT = 25;
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

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

async function fetchOptionalJson<T>(path: string, fallback: T): Promise<T> {
  const response = await backendFetch(`${path}`, { cache: "no-store" });
  if (!response.ok) {
    return fallback;
  }
  return response.json() as Promise<T>;
}

async function fetchLatestBarResult(symbol: string, provider: string): Promise<LatestBarLoadResult> {
  try {
    const response = await backendFetch(
      withProviderQuery(`/market-data/${encodeURIComponent(symbol)}/latest`, provider),
      { cache: "no-store" },
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
  }
}

async function fetchPlatformProvider(): Promise<string> {
  const settings = await getPlatformSettings();
  return settings.market_data_provider;
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
  return parsedTimestamp === null ? unavailableLabel : parsedTimestamp.toLocaleDateString(locale);
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
  try {
    const response = await backendFetch(
      withProviderQuery("/dashboard/market-overview", provider),
      { cache: "no-store" },
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
  return Number.isNaN(parsedDate.getTime()) ? unavailableLabel : parsedDate.toLocaleDateString(locale);
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
  const { locale } = await params;
  const flash = await searchParams;
  const { recent, analysis } = getDashboardDateRanges();
  const provider = await fetchPlatformProvider();
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
  const dashboardHealthLatestBars = await Promise.all(
    dashboardHealth.instruments.map((instrument) => fetchLatestBarResult(instrument.symbol, provider)),
  );
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
  const marketOverviewPayload = marketOverviewResult.status === "loaded" ? marketOverviewResult.payload : null;
  const marketOverviewIndices = marketOverviewPayload?.indices.items ?? [];
  const marketOverviewFollowedItems = marketOverviewPayload?.followed.items ?? [];
  const marketOverviewValuationItems = marketOverviewPayload?.valuation_indicators.items ?? [];
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
  }));

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

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">
            {t("description")}
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button variant="outline" asChild>
            <Link href="/task-runs">{t("viewTaskRuns")}</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/settings">{t("providerSettings")}</Link>
          </Button>
        </div>
      </div>

      <section className="space-y-4">
        <Card className="border-primary/20 bg-muted/20">
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{t("marketDashboardBadge")}</Badge>
              <Badge variant="outline">{t("activeProvider", { provider })}</Badge>
              {marketOverviewPayload ? (
                <Badge variant="outline">
                  {t("marketDashboardRange", {
                    start: formatDashboardDate(marketOverviewPayload.range.start, locale, t("unavailableShort")),
                    end: formatDashboardDate(marketOverviewPayload.range.end, locale, t("unavailableShort")),
                  })}
                </Badge>
              ) : null}
            </div>
            <CardTitle className="text-2xl">{t("marketDashboardTitle")}</CardTitle>
            <CardDescription>{t("marketDashboardDesc")}</CardDescription>
          </CardHeader>
          {marketOverviewResult.status === "failed" ? (
            <CardContent>
              <div className="rounded-lg border bg-background p-4">
                <div className="font-medium">{t("marketDashboardUnavailableTitle")}</div>
                <p className="mt-1 text-sm text-muted-foreground">{t("marketDashboardUnavailableDesc")}</p>
              </div>
            </CardContent>
          ) : null}
        </Card>

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
                      const changeColor = changeValue >= 0 ? "text-green-500" : "text-red-500";
                      
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
              {marketOverviewValuationItems.length > 0 ? (
                <div className="space-y-2">
                  {marketOverviewValuationItems.map((item) => (
                    <div key={item.code} className="rounded-none border p-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-semibold text-sm">{item.name}</div>
                          <div className="text-[10px] text-muted-foreground">{item.region ?? t("unavailableShort")}</div>
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
