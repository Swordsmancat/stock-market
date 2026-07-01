import { getTranslations } from "next-intl/server";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TrendingUp, FileText, Activity, Briefcase, Newspaper } from "lucide-react";
import { PriceChart } from "@/components/price-chart";
import { Link } from "@/src/i18n/routing";
import { InstrumentQuickActions } from "@/components/instrument-actions";
import { InstrumentWatchlistForm } from "@/components/instrument-watchlist-form";
import { FlashBanner } from "@/components/flash-banner";
import { getInstrumentDateRange, getDashboardDateRanges, parseInstrumentRange, type InstrumentRange } from "@/lib/dates";
import { getMarketDataProvider, withProviderQuery } from "@/lib/market-data";
import { backendFetch } from "@/lib/backend-api";

type BarsPayload = {
  source: string;
  items: Array<{
    timestamp: string;
    open?: number;
    high?: number;
    low?: number;
    close: number;
    volume?: number;
  }>;
};

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

export default async function InstrumentDetailPage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ symbol: string; locale: string }>;
  searchParams?: Promise<{ range?: string; watchlist?: string; reason?: string }>;
}) {
  const { symbol, locale } = await params;
  const { range, watchlist, reason } = await searchParams;
  const decodedSymbol = decodeURIComponent(symbol).toUpperCase();
  const selectedRange = parseInstrumentRange(range);
  const dateRange = getInstrumentDateRange(selectedRange);
  const { analysis } = getDashboardDateRanges();
  const provider = getMarketDataProvider();
  const t = await getTranslations("InstrumentDetail");

  const instrumentsPayload = await fetchOptionalJson<InstrumentsPayload>("/instruments", { items: [] });
  const instrumentMeta = instrumentsPayload.items.find(
    (item) => item.symbol.toUpperCase() === decodedSymbol,
  );

  const [
    barsPayload,
    reportPayload,
    indicatorsPayload,
    fundamentalsPayload,
    newsPayload,
  ] = await Promise.all([
    fetchOptionalJson<BarsPayload>(
      withProviderQuery(
        `/market-data/${decodedSymbol}/bars?timeframe=1d&start=${dateRange.start}&end=${dateRange.end}`,
        provider,
      ),
      { source: "unavailable", items: [] }
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

  const latestClose = barsPayload.items.at(-1)?.close;
  const fundamentalSummary = fundamentalsPayload.item?.summary;
  const reportCitations = reportPayload.citations ?? [];

  return (
    <div className="space-y-6">
      {watchlist === "added" ? <FlashBanner variant="success" message={t("watchlistAdded")} /> : null}
      {watchlist === "error" ? (
        <FlashBanner variant="error" message={t("watchlistFailedDetail", { reason: reason ?? "unknown" })} />
      ) : null}

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            {decodedSymbol}
            {instrumentMeta?.name ? (
              <span className="text-lg font-normal text-muted-foreground">{instrumentMeta.name}</span>
            ) : null}
            <Badge variant="outline" className="text-lg px-3 py-1">
              {latestClose ? `$${latestClose.toFixed(2)}` : "N/A"}
            </Badge>
            {instrumentMeta?.market ? (
              <Badge variant="secondary">{instrumentMeta.market}</Badge>
            ) : null}
          </h1>
          <p className="text-muted-foreground">{t("latestPrice")}</p>
        </div>
        <InstrumentQuickActions
          symbol={decodedSymbol}
          market={instrumentMeta?.market ?? "US"}
          analysisStart={analysis.start}
          analysisEnd={analysis.end}
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
              <PriceChart data={barsPayload.items} />
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
