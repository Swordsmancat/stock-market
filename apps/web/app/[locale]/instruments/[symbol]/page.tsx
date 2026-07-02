import { getTranslations } from "next-intl/server";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TrendingUp, FileText, Activity, Briefcase, Newspaper } from "lucide-react";
import { PriceChart } from "@/components/price-chart";
import { Link } from "@/src/i18n/routing";
import { InstrumentQuickActions } from "@/components/instrument-actions";
import { InstrumentWatchlistForm } from "@/components/instrument-watchlist-form";
import { FlashBanner } from "@/components/flash-banner";
import { getInstrumentDateRange, getDashboardDateRanges, parseInstrumentRange, type InstrumentRange } from "@/lib/dates";
import { getPlatformSettings } from "@/lib/platform-settings-store";
import { withProviderQuery } from "@/lib/market-data";
import { backendFetch } from "@/lib/backend-api";

type BarsPayload = {
  source: string;
  provider?: string | null;
  requested_provider?: string | null;
  effective_provider?: string | null;
  status?: "ok" | "no_data" | string;
  no_data_reason?: string | null;
  items: Array<{
    timestamp: string;
    open?: number;
    high?: number;
    low?: number;
    close: number;
    volume?: number;
  }>;
};

type BarsLoadResult =
  | { status: "loaded"; payload: BarsPayload }
  | { status: "failed" };

type FreshnessStatus = "fresh" | "stale" | "no_data" | "unavailable";

const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;
const RECENT_OHLCV_ROW_LIMIT = 10;

const RANGE_OPTIONS: InstrumentRange[] = ["5d", "20d", "1m", "3m", "1y"];

type ReportPayload = {
  content_markdown: string;
  citations?: string[];
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

type InstrumentsPayload = {
  items: Array<{ symbol: string; name: string; market: string }>;
};

async function fetchOptionalJson<T>(path: string, fallback: T): Promise<T> {
  const response = await backendFetch(`${path}`, { cache: "no-store" });
  if (!response.ok) {
    return fallback;
  }
  return response.json() as Promise<T>;
}

async function fetchBarsPayload(path: string): Promise<BarsLoadResult> {
  try {
    const response = await backendFetch(path, { cache: "no-store" });
    if (!response.ok) {
      return { status: "failed" };
    }

    return {
      status: "loaded",
      payload: (await response.json()) as BarsPayload,
    };
  } catch {
    return { status: "failed" };
  }
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

function getDailyBarItems(barsResult: BarsLoadResult): BarsPayload["items"] {
  return barsResult.status === "loaded" ? barsResult.payload.items : [];
}

function parseDailyBarTimestamp(timestamp: string | undefined): Date | null {
  if (!timestamp) {
    return null;
  }

  const parsedTimestamp = new Date(timestamp);
  return Number.isNaN(parsedTimestamp.getTime()) ? null : parsedTimestamp;
}

function formatDailyBarDate(timestamp: string | undefined, locale: string, unavailableLabel: string): string {
  const parsedTimestamp = parseDailyBarTimestamp(timestamp);
  return parsedTimestamp === null ? unavailableLabel : parsedTimestamp.toLocaleDateString(locale);
}

function formatNumberValue(value: number | undefined, locale: string, unavailableLabel: string): string {
  if (typeof value !== "number") {
    return unavailableLabel;
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatVolumeValue(value: number | undefined, locale: string, unavailableLabel: string): string {
  if (typeof value !== "number") {
    return unavailableLabel;
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 0,
  }).format(value);
}

function getFreshnessStatus(barsResult: BarsLoadResult): FreshnessStatus {
  if (barsResult.status === "failed") {
    return "unavailable";
  }

  const latestDailyBar = barsResult.payload.items.at(-1);
  if (barsResult.payload.status === "no_data" || latestDailyBar === undefined) {
    return "no_data";
  }

  const parsedTimestamp = parseDailyBarTimestamp(latestDailyBar.timestamp);
  if (parsedTimestamp === null) {
    return "unavailable";
  }

  const daysSinceLatestDailyBar = (Date.now() - parsedTimestamp.getTime()) / MILLISECONDS_PER_DAY;
  return daysSinceLatestDailyBar <= 3 ? "fresh" : "stale";
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

function getDailyBarSource(barsResult: BarsLoadResult): string {
  return barsResult.status === "loaded" ? barsResult.payload.source : "unavailable";
}

function getDailyBarProvider(barsResult: BarsLoadResult, configuredProvider: string): string {
  if (barsResult.status === "failed") {
    return configuredProvider;
  }

  return barsResult.payload.effective_provider ?? barsResult.payload.provider ?? configuredProvider;
}

function formatChartRange(dailyBars: BarsPayload["items"], locale: string, unavailableLabel: string): string {
  const firstDailyBar = dailyBars[0];
  const latestDailyBar = dailyBars.at(-1);
  if (firstDailyBar === undefined || latestDailyBar === undefined) {
    return unavailableLabel;
  }

  return `${formatDailyBarDate(firstDailyBar.timestamp, locale, unavailableLabel)} - ${formatDailyBarDate(
    latestDailyBar.timestamp,
    locale,
    unavailableLabel,
  )}`;
}

export default async function InstrumentDetailPage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ symbol: string; locale: string }>;
  searchParams?: Promise<{ range?: string; watchlist?: string; reason?: string; analysis?: string; report?: string; msg?: string }>;
}) {
  const { symbol, locale } = await params;
  const { range, watchlist, reason, analysis: analysisStatus, report, msg } = await searchParams;
  const decodedSymbol = decodeURIComponent(symbol).toUpperCase();
  const selectedRange = parseInstrumentRange(range);
  const dateRange = getInstrumentDateRange(selectedRange);
  const { analysis } = getDashboardDateRanges();
  const settings = await getPlatformSettings();
  const provider = settings.market_data_provider;
  const t = await getTranslations("InstrumentDetail");

  const instrumentsPayload = await fetchOptionalJson<InstrumentsPayload>("/instruments", { items: [] });
  const instrumentMeta = instrumentsPayload.items.find(
    (item) => item.symbol.toUpperCase() === decodedSymbol,
  );

  const [
    barsResult,
    reportPayload,
    indicatorsPayload,
    fundamentalsPayload,
    newsPayload,
  ] = await Promise.all([
    fetchBarsPayload(
      withProviderQuery(
        `/market-data/${decodedSymbol}/bars?timeframe=1d&start=${dateRange.start}&end=${dateRange.end}`,
        provider,
      ),
    ),
    fetchOptionalJson<ReportPayload>(
      `/reports/${decodedSymbol}/stock?start=${dateRange.start}&end=${dateRange.end}`,
      { content_markdown: "", citations: [] }
    ),
    fetchOptionalJson<IndicatorsPayload>(`/indicators/${decodedSymbol}`, {
      source: "unavailable",
      indicators: {},
    }),
    fetchOptionalJson<FundamentalsPayload>(`/fundamentals/${decodedSymbol}`, {
      source: "unavailable",
      item: null,
    }),
    fetchOptionalJson<NewsPayload>(`/news/${decodedSymbol}`, {
      source: "unavailable",
      items: [],
    }),
  ]);

  const dailyBars = getDailyBarItems(barsResult);
  const latestDailyBar = dailyBars.at(-1);
  const latestClose = latestDailyBar?.close;
  const unavailableLabel = t("unavailableShort");
  const freshnessStatus = getFreshnessStatus(barsResult);
  const dailyBarProvider = getDailyBarProvider(barsResult, provider);
  const dailyBarSource = getDailyBarSource(barsResult);
  const latestCloseLabel = latestClose === undefined ? unavailableLabel : `$${formatNumberValue(latestClose, locale, unavailableLabel)}`;
  const latestDailyBarDateLabel = formatDailyBarDate(latestDailyBar?.timestamp, locale, unavailableLabel);
  const chartRangeLabel = formatChartRange(dailyBars, locale, unavailableLabel);
  const dailyBarCountLabel = new Intl.NumberFormat(locale).format(dailyBars.length);
  const recentDailyBars = dailyBars.slice(-RECENT_OHLCV_ROW_LIMIT).reverse();
  const chartLabels = {
    candles: t("chartCandles"),
    movingAverage: t("chartMovingAverage"),
    bollingerBands: t("chartBollingerBands"),
    rsi: t("chartRsi"),
    volume: t("chartVolume"),
    empty: t("chartEmpty"),
    open: t("openShort"),
    high: t("highShort"),
    low: t("lowShort"),
    close: t("closeShort"),
    movingAverageShort: t("chartMovingAverageShort"),
    volumeShort: t("volumeShort"),
  };
  const fundamentalSummary = fundamentalsPayload.item?.summary;
  const reportCitations = reportPayload.citations ?? [];

  return (
    <div className="space-y-6">
      {watchlist === "added" ? <FlashBanner variant="success" message={t("watchlistAdded")} /> : null}
      {watchlist === "error" ? (
        <FlashBanner variant="error" message={t("watchlistFailedDetail", { reason: reason ?? "unknown" })} />
      ) : null}
      {analysisStatus === "ok" ? (
        <FlashBanner variant="success" message={t("analysisSuccess", { symbol: decodedSymbol })} />
      ) : null}
      {analysisStatus === "error" ? (
        <FlashBanner variant="error" message={t("analysisFailedDetail", { reason: msg ?? "unknown" })} />
      ) : null}
      {report === "ok" ? <FlashBanner variant="success" message={t("reportSuccess")} /> : null}
      {report === "error" ? <FlashBanner variant="error" message={t("reportFailed")} /> : null}

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            {decodedSymbol}
            {instrumentMeta?.name ? (
              <span className="text-lg font-normal text-muted-foreground">{instrumentMeta.name}</span>
            ) : null}
            <Badge variant="outline" className="text-lg px-3 py-1">
              {latestCloseLabel}
            </Badge>
            {instrumentMeta?.market ? (
              <Badge variant="secondary">{instrumentMeta.market}</Badge>
            ) : null}
          </h1>
          <p className="text-muted-foreground">{t("latestPrice")}</p>
        </div>
        <InstrumentQuickActions
          locale={locale}
          symbol={decodedSymbol}
          market={instrumentMeta?.market ?? "US"}
          analysisStart={analysis.start}
          analysisEnd={analysis.end}
          provider={provider}
          watchlistForm={
            <InstrumentWatchlistForm
              locale={locale}
              symbol={decodedSymbol}
              market={instrumentMeta?.market ?? "US"}
              name={instrumentMeta?.name ?? ""}
            />
          }
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("dailyBarSummary")}</CardTitle>
          <CardDescription>{t("dailyBarSummaryDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border p-4">
              <div className="text-sm font-medium text-muted-foreground mb-1">{t("latestClose")}</div>
              <div className="text-2xl font-bold">{latestCloseLabel}</div>
              <div className="mt-1 text-xs text-muted-foreground">{t("latestDailyBarAsOf", { date: latestDailyBarDateLabel })}</div>
            </div>
            <div className="rounded-lg border p-4">
              <div className="text-sm font-medium text-muted-foreground mb-1">{t("sourceProvider")}</div>
              <div className="text-sm font-semibold">{t("sourceValue", { source: dailyBarSource })}</div>
              <div className="mt-1 text-xs text-muted-foreground">{t("providerValue", { provider: dailyBarProvider })}</div>
            </div>
            <div className="rounded-lg border p-4">
              <div className="text-sm font-medium text-muted-foreground mb-1">{t("freshness")}</div>
              <Badge variant={getFreshnessBadgeVariant(freshnessStatus)}>{t(freshnessStatus)}</Badge>
            </div>
            <div className="rounded-lg border p-4">
              <div className="text-sm font-medium text-muted-foreground mb-1">{t("barCoverage")}</div>
              <div className="text-sm font-semibold">{t("barCount", { count: dailyBarCountLabel })}</div>
              <div className="mt-1 text-xs text-muted-foreground">{t("chartRange", { range: chartRangeLabel })}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4 md:w-auto md:inline-grid">
          <TabsTrigger value="overview">{t("overview")}</TabsTrigger>
          <TabsTrigger value="technical">{t("technical")}</TabsTrigger>
          <TabsTrigger value="fundamentals">{t("fundamentals")}</TabsTrigger>
          <TabsTrigger value="news">{t("news")}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6 space-y-6">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                {t("priceHistory")}
              </CardTitle>
              <div className="mt-3 flex flex-wrap gap-2">
                {RANGE_OPTIONS.map((option) => (
                  <Button
                    key={option}
                    variant={selectedRange === option ? "default" : "outline"}
                    size="sm"
                    asChild
                  >
                    <Link href={`/instruments/${decodedSymbol}?range=${option}` as any}>
                      {option.toUpperCase()}
                    </Link>
                  </Button>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              {barsResult.status === "failed" ? (
                <ErrorState title={t("barsLoadFailed")} description={t("barsLoadFailedHint")} />
              ) : dailyBars.length === 0 ? (
                <EmptyState title={t("noDailyBars")} description={t("noDailyBarsHint")} />
              ) : (
                <PriceChart data={dailyBars} labels={chartLabels} />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("recentOhlcv")}</CardTitle>
              <CardDescription>{t("recentOhlcvDesc")}</CardDescription>
            </CardHeader>
            <CardContent>
              {barsResult.status === "failed" ? (
                <ErrorState title={t("barsLoadFailed")} description={t("barsLoadFailedHint")} />
              ) : recentDailyBars.length === 0 ? (
                <EmptyState title={t("noDailyBars")} description={t("noDailyBarsHint")} />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("date")}</TableHead>
                      <TableHead className="text-right">{t("open")}</TableHead>
                      <TableHead className="text-right">{t("high")}</TableHead>
                      <TableHead className="text-right">{t("low")}</TableHead>
                      <TableHead className="text-right">{t("close")}</TableHead>
                      <TableHead className="text-right">{t("volume")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentDailyBars.map((dailyBar) => (
                      <TableRow key={dailyBar.timestamp}>
                        <TableCell>{formatDailyBarDate(dailyBar.timestamp, locale, unavailableLabel)}</TableCell>
                        <TableCell className="text-right">{formatNumberValue(dailyBar.open, locale, unavailableLabel)}</TableCell>
                        <TableCell className="text-right">{formatNumberValue(dailyBar.high, locale, unavailableLabel)}</TableCell>
                        <TableCell className="text-right">{formatNumberValue(dailyBar.low, locale, unavailableLabel)}</TableCell>
                        <TableCell className="text-right font-medium">{formatNumberValue(dailyBar.close, locale, unavailableLabel)}</TableCell>
                        <TableCell className="text-right">{formatVolumeValue(dailyBar.volume, locale, unavailableLabel)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                {t("aiReport")}
              </CardTitle>
              <CardDescription>{t("aiReportDesc")}</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px] w-full rounded-md border p-4">
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
        </TabsContent>

        <TabsContent value="technical" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                {t("technicalIndicators")}
              </CardTitle>
              <CardDescription>{t("technicalIndicatorsDesc")}</CardDescription>
            </CardHeader>
            <CardContent>
              {hasTechnicalIndicators(indicatorsPayload) ? (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {indicatorsPayload.indicators.ma && (
                    <div className="rounded-lg border p-4">
                      <div className="text-sm font-medium text-muted-foreground mb-1">MA</div>
                      <div className="text-2xl font-bold">{indicatorsPayload.indicators.ma.toFixed(2)}</div>
                    </div>
                  )}
                  {indicatorsPayload.indicators.rsi && (
                    <div className="rounded-lg border p-4">
                      <div className="text-sm font-medium text-muted-foreground mb-1">RSI</div>
                      <div className="text-2xl font-bold">{indicatorsPayload.indicators.rsi.toFixed(2)}</div>
                    </div>
                  )}
                  {indicatorsPayload.indicators.atr && (
                    <div className="rounded-lg border p-4">
                      <div className="text-sm font-medium text-muted-foreground mb-1">ATR</div>
                      <div className="text-2xl font-bold">{indicatorsPayload.indicators.atr.toFixed(2)}</div>
                    </div>
                  )}
                  {indicatorsPayload.indicators.bollinger && (
                    <div className="rounded-lg border p-4 sm:col-span-2 lg:col-span-4">
                      <div className="text-sm font-medium text-muted-foreground mb-3">{t("bollingerBands")}</div>
                      <div className="grid grid-cols-3 gap-4 text-center">
                        <div>
                          <div className="text-sm text-muted-foreground">{t("upper")}</div>
                          <div className="text-lg font-semibold">{indicatorsPayload.indicators.bollinger.upper.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t("middle")}</div>
                          <div className="text-lg font-semibold">{indicatorsPayload.indicators.bollinger.middle.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t("lower")}</div>
                          <div className="text-lg font-semibold">{indicatorsPayload.indicators.bollinger.lower.toFixed(2)}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-8 text-center">{t("noTechnicalIndicators")}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="fundamentals" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Briefcase className="h-5 w-5" />
                {t("fundamentalsSummary")}
              </CardTitle>
              <CardDescription>{t("fundamentalsDesc")}</CardDescription>
            </CardHeader>
            <CardContent>
              {fundamentalSummary ? (
                <div className="prose dark:prose-invert max-w-none">
                  <p className="text-sm leading-relaxed">{fundamentalSummary}</p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-8 text-center">{t("noFundamentals")}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="news" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Newspaper className="h-5 w-5" />
                {t("latestNews")}
              </CardTitle>
              <CardDescription>{t("latestNewsDesc")}</CardDescription>
            </CardHeader>
            <CardContent>
              {newsPayload.items.length > 0 ? (
                <div className="space-y-6">
                  {newsPayload.items.map((news, index) => (
                    <div key={index} className="flex flex-col gap-2 border-b pb-4 last:border-0 last:pb-0">
                      <p className="font-medium leading-tight">{news.title}</p>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            news.sentiment === "positive"
                              ? "default"
                              : news.sentiment === "negative"
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {news.sentiment}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {t("confidence", { score: (news.confidence * 100).toFixed(0) })}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-8 text-center">{t("noNews")}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
