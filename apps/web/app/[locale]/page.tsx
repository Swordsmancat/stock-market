import { Link } from "@/src/i18n/routing";
import { TrendingUp, Activity, Briefcase, Newspaper, FileText, List, Bell } from "lucide-react";
import { useTranslations } from "next-intl";

import { AnalysisRefreshButton } from "./AnalysisRefreshButton";
import { IngestionButton } from "./IngestionButton";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MiniPriceChart } from "@/components/mini-price-chart";
import { getDashboardDateRanges } from "@/lib/dates";
import { getMarketDataProvider, withProviderQuery } from "@/lib/market-data";

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
  items: Array<{ timestamp: string; close: number }>;
};

type LatestBarPayload = {
  source: string;
  item?: { close: number } | null;
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

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }
  return response.json() as Promise<T>;
}

async function fetchOptionalJson<T>(path: string, fallback: T): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    return fallback;
  }
  return response.json() as Promise<T>;
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

export default async function HomePage() {
  const { recent, analysis } = getDashboardDateRanges();
  const provider = getMarketDataProvider();
  const instrumentsPayload = await fetchJson<InstrumentsPayload>("/instruments");
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
      fetchJson<PortfolioPayload>("/portfolios/demo"),
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
    ]);

  const latestClose =
    latestBarPayload.item?.close ?? barsPayload.items.at(-1)?.close;
  const priceSource =
    latestBarPayload.item !== undefined && latestBarPayload.item !== null
      ? latestBarPayload.source
      : barsPayload.source;
  const portfolioValue = portfolioPayload.positions[0]?.market_value;
  const triggeredWatchlistCount = watchlistPayload.items.filter(
    (item) => item.alert_status?.triggered,
  ).length;
  const fundamentalSummary = fundamentalsPayload.item?.summary;
  const latestNews = newsPayload.items[0];
  const reportCitations = reportPayload.citations ?? [];
  const dailyReportCitations = dailyReportPayload.citations ?? [];

  // We cannot use useTranslations in an async Server Component directly without awaiting it.
  // In next-intl for App Router, we use `getTranslations` for async components.
  // However, for simplicity, we can pass translations or just use the hook in a client component.
  // Since this is a server component, we need to import `getTranslations`
  const { getTranslations } = await import("next-intl/server");
  const t = await getTranslations("Dashboard");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">
            {t("description")}
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <IngestionButton market={primaryInstrument.market} start={recent.start} end={recent.end} />
          <AnalysisRefreshButton
            symbol={primaryInstrument.symbol}
            market={primaryInstrument.market}
            start={analysis.start}
            end={analysis.end}
            maWindow={3}
          />
        </div>
      </div>

      {/* Row 1: KPIs */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("latestPrice", { symbol: primaryInstrument.symbol })}
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{latestClose ? `$${latestClose.toFixed(2)}` : "N/A"}</div>
            <MiniPriceChart items={barsPayload.items} className="mt-3 h-16 w-full" />
            <p className="mt-2 text-xs text-muted-foreground">{t("source", { source: priceSource })}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("portfolioValue")}</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {portfolioValue ? `$${portfolioValue.toLocaleString()}` : "N/A"}
            </div>
            <p className="text-xs text-muted-foreground">{t("source", { source: portfolioPayload.source })}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("activeAlerts")}</CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{triggeredWatchlistCount}</div>
            <p className="text-xs text-muted-foreground">{t("activeAlertsDesc")}</p>
            {alertTriggersPayload.items.length > 0 ? (
              <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
                {alertTriggersPayload.items.slice(0, 3).map((trigger) => (
                  <li key={`${trigger.symbol}-${trigger.rule_key}-${trigger.triggered_at}`}>
                    <Link href="/watchlist" className="hover:underline">
                      {trigger.symbol}
                    </Link>{" "}
                    {trigger.rule_key} @ {trigger.threshold}
                  </li>
                ))}
              </ul>
            ) : null}
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
          </CardContent>
        </Card>
      </div>

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
  );
}
