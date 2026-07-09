"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/src/i18n/routing";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AdvancedCandlestickChart } from "@/components/advanced-candlestick-chart";
import { IntradayPriceChart } from "@/components/intraday-price-chart";
import { MarketAssistantCard } from "@/components/market-assistant-card";
import { MarketDepthCard } from "@/components/market-depth-card";
import { DataTrustBadge } from "@/components/data-trust-badge";
import { FinancialPageHeader } from "@/components/financial-page-header";
import { useMarketColorsContext } from "@/context/market-colors-context";
import { createDataTrustSignal } from "@/lib/data-trust";
import { decodeInstrumentSymbol, getInstrumentDisplayName } from "@/lib/instrument-display";
import type { InstrumentBar, InstrumentDetailPayload } from "@/lib/instrument-detail";

type ChartBarData = InstrumentBar & {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

function isChartBarData(bar: InstrumentBar): bar is ChartBarData {
  return (
    typeof bar.timestamp === "string" &&
    Number.isFinite(bar.open) &&
    Number.isFinite(bar.high) &&
    Number.isFinite(bar.low) &&
    Number.isFinite(bar.close)
  );
}

function formatDetailDate(value: string | null | undefined, locale: string, unavailableLabel: string): string {
  if (!value) {
    return unavailableLabel;
  }

  const parsedDate = new Date(value);
  return Number.isNaN(parsedDate.getTime()) ? unavailableLabel : parsedDate.toLocaleDateString(locale);
}

function formatDetailNumber(value: number | null | undefined, locale: string, unavailableLabel: string): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return unavailableLabel;
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatPercentMetric(value: number | null | undefined, locale: string, unavailableLabel: string): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return unavailableLabel;
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
    style: "percent",
  }).format(value);
}

function cleanMarkdownPreviewLine(line: string): string {
  return line
    .replace(/^#{1,6}\s*/, "")
    .replace(/^[-*]\s+/, "")
    .replace(/\[([^\]]+)]\([^)]*\)/g, "$1")
    .replace(/[*_`]/g, "")
    .trim();
}

function extractMarkdownPreview(contentMarkdown: string | null | undefined, fallback: string): string {
  if (!contentMarkdown) {
    return fallback;
  }

  const meaningfulLine = contentMarkdown
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line.length > 0);
  if (!meaningfulLine) {
    return fallback;
  }

  return cleanMarkdownPreviewLine(meaningfulLine) || fallback;
}

function formatIndicatorValue(value: unknown, locale: string, unavailableLabel: string): string {
  if (typeof value === "number") {
    return formatDetailNumber(value, locale, unavailableLabel);
  }
  if (typeof value === "string") {
    return value;
  }
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, nestedValue]) => `${key}: ${formatIndicatorValue(nestedValue, locale, unavailableLabel)}`)
      .join(" / ");
  }
  return unavailableLabel;
}

function ContextMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-muted/20 p-3">
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-sm font-semibold">{value}</div>
    </div>
  );
}

interface InstrumentDetailClientProps {
  symbol: string;
  locale: string;
  initialData?: InstrumentDetailPayload | null;
  initialError?: string | null;
}

export function InstrumentDetailClient({
  symbol,
  locale,
  initialData = null,
  initialError = null,
}: InstrumentDetailClientProps) {
  const router = useRouter();
  const t = useTranslations("InstrumentDetail");
  const { getMovementColor } = useMarketColorsContext();
  const [data, setData] = useState<InstrumentDetailPayload | null>(initialData);
  const [loading, setLoading] = useState(initialData === null && initialError === null);
  const [error, setError] = useState<string | null>(initialError);

  useEffect(() => {
    if (initialData !== null || initialError !== null) {
      return;
    }

    async function fetchData() {
      try {
        setLoading(true);
        const response = await fetch(`/api/instruments/${encodeURIComponent(symbol)}`);
        
        if (!response.ok) {
          throw new Error("Failed to fetch instrument data");
        }

        const result = await response.json();
        setData(result);
      } catch (err) {
        console.error("Fetch error:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [symbol]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("back")}
        </Button>
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("back")}
        </Button>
        <Card>
          <CardContent className="p-6">
            <p className="text-center text-destructive">
              {t("loadFailed", { reason: error ?? t("unavailableShort") })}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const bars = data.bars?.items ?? [];
  const chartBars = bars.filter(isChartBarData);
  const latestBar = bars.at(-1) ?? data.latest?.item ?? null;
  const prevBar = bars.at(-2) ?? null;
  
  const currentPrice = latestBar?.close || 0;
  const prevPrice = prevBar?.close || currentPrice;
  const change = currentPrice - prevPrice;
  const changePercent = prevPrice ? change / prevPrice : 0;
  const formattedChange = `${change >= 0 ? "+" : ""}${change.toFixed(2)}`;
  const formattedChangePercent = `${changePercent >= 0 ? "+" : ""}${(changePercent * 100).toFixed(2)}%`;
  const decodedSymbol = decodeInstrumentSymbol(symbol);
  const displayName = getInstrumentDisplayName(symbol, locale);
  const subtitle = displayName === decodedSymbol ? t("detailSubtitle") : `${decodedSymbol} · ${t("detailSubtitle")}`;
  const assistantSymbol = data.request_symbol ?? symbol;
  const assistantProvider = data.market_depth?.effective_provider ?? data.market_depth?.provider ?? null;
  const latestTrustSignal = createDataTrustSignal({
    status: data.latest?.status,
    source: data.latest?.source,
    provider: data.latest?.provider,
    requested_provider: data.latest?.requested_provider,
    effective_provider: data.latest?.effective_provider,
    as_of: data.latest?.item?.timestamp,
    no_data_reason: data.latest?.no_data_reason,
  });
  const barsTrustSignal = createDataTrustSignal({
    status: data.bars?.status,
    source: data.bars?.source,
    provider: data.bars?.provider,
    requested_provider: data.bars?.requested_provider,
    effective_provider: data.bars?.effective_provider,
    as_of: latestBar?.timestamp,
    no_data_reason: data.bars?.no_data_reason,
  });
  const indicatorEntries = Object.entries(data.indicators?.indicators ?? {});
  const latestReport = data.latest_daily_report ?? null;
  const latestReportHasContent = Boolean(latestReport?.content_markdown);
  const reportHistoryItems = data.daily_report_history?.items ?? [];
  const fundamentalsItem = data.fundamentals?.item ?? null;
  const newsItems = data.news?.items ?? [];
  const latestNews = newsItems[0] ?? null;

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={displayName}
        description={subtitle}
        badges={[
          { label: decodedSymbol, variant: "secondary" },
          { label: `provider: ${assistantProvider ?? data.latest?.effective_provider ?? data.latest?.provider ?? "none"}` },
          { label: `${data.range?.start ?? "-"} / ${data.range?.end ?? "-"}` },
        ]}
        metrics={[
          {
            label: t("latestPriceCard"),
            value: currentPrice.toFixed(2),
            description: <DataTrustBadge signal={latestTrustSignal} mode="summary" />,
          },
          {
            label: t("priceChange"),
            value: formattedChange,
            className: getMovementColor(change),
          },
          {
            label: t("priceChangePercent"),
            value: formattedChangePercent,
            className: getMovementColor(change),
          },
          {
            label: t("klineTitle"),
            value: chartBars.length,
            description: <DataTrustBadge signal={barsTrustSignal} mode="summary" />,
          },
        ]}
        actions={
          <Button variant="outline" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
            {t("back")}
          </Button>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.85fr)]">
        <MarketAssistantCard
          symbol={assistantSymbol}
          locale={locale}
          provider={assistantProvider}
          start={data.range?.start ?? null}
          end={data.range?.end ?? null}
        />

        <MarketDepthCard marketDepth={data.market_depth ?? null} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <Card className="rounded-md shadow-none">
          <CardHeader className="border-b bg-muted/20 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle>{t("aiReport")}</CardTitle>
                <CardDescription>{t("aiReportDesc")}</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href={`/reports?symbol=${encodeURIComponent(symbol)}` as any}>
                  <ExternalLink className="h-4 w-4" />
                  {t("viewReports")}
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 p-4">
            {latestReportHasContent ? (
              <>
                <div className="flex flex-wrap gap-2">
                  {latestReport?.as_of ? (
                    <Badge variant="secondary">
                      {t("reportAsOf", { date: formatDetailDate(latestReport.as_of, locale, t("unavailableShort")) })}
                    </Badge>
                  ) : null}
                  <Badge variant="outline">
                    {t("reportCitations", { count: latestReport?.citations?.length ?? 0 })}
                  </Badge>
                  {latestReport?.task_run_id ? (
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/task-runs/${latestReport.task_run_id}` as any}>
                        {t("reportTaskRun", { id: latestReport.task_run_id.slice(0, 8) })}
                      </Link>
                    </Button>
                  ) : null}
                </div>
                <p className="text-sm leading-6 text-muted-foreground">
                  {extractMarkdownPreview(latestReport?.content_markdown, t("noReport"))}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">{t("noReport")}</p>
            )}

            {reportHistoryItems.length > 0 ? (
              <div className="border-t pt-3">
                <div className="mb-2 text-sm font-semibold">{t("reportHistory")}</div>
                <div className="space-y-2">
                  {reportHistoryItems.slice(0, 3).map((report, index) => (
                    <div key={`${report.as_of ?? "report"}-${index}`} className="rounded-md border p-3 text-sm">
                      <div className="font-medium">
                        {report.as_of
                          ? t("reportAsOf", { date: formatDetailDate(report.as_of, locale, t("unavailableShort")) })
                          : t("aiReport")}
                      </div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">
                        {extractMarkdownPreview(report.content_markdown, t("noReport"))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card className="rounded-md shadow-none">
            <CardHeader className="border-b bg-muted/20 p-4">
              <CardTitle>{t("technicalIndicators")}</CardTitle>
              <CardDescription>
                {t("technicalIndicatorsDesc")}{" "}
                {data.indicators?.as_of
                  ? t("indicatorAsOf", {
                      date: formatDetailDate(data.indicators.as_of, locale, t("unavailableShort")),
                    })
                  : null}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4">
              {indicatorEntries.length > 0 ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  {indicatorEntries.map(([code, value]) => (
                    <div key={code} className="rounded-md border p-3">
                      <div className="font-mono text-xs text-muted-foreground">{code}</div>
                      <div className="mt-1 text-sm font-medium">
                        {formatIndicatorValue(value, locale, t("unavailableShort"))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("noTechnicalIndicators")}</p>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-md shadow-none">
            <CardHeader className="border-b bg-muted/20 p-4">
              <CardTitle>{t("fundamentalsSummary")}</CardTitle>
              <CardDescription>{t("fundamentalsDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 p-4">
              {fundamentalsItem ? (
                <>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <ContextMetric label={t("fundamentalPeRatio")} value={formatDetailNumber(fundamentalsItem.pe_ratio, locale, t("unavailableShort"))} />
                    <ContextMetric label={t("fundamentalRevenueGrowth")} value={formatPercentMetric(fundamentalsItem.revenue_growth, locale, t("unavailableShort"))} />
                    <ContextMetric label={t("fundamentalNetMargin")} value={formatPercentMetric(fundamentalsItem.net_margin, locale, t("unavailableShort"))} />
                    <ContextMetric label={t("fundamentalDebtToAssets")} value={formatPercentMetric(fundamentalsItem.debt_to_assets, locale, t("unavailableShort"))} />
                  </div>
                  {fundamentalsItem.summary ? (
                    <p className="text-sm leading-6 text-muted-foreground">{fundamentalsItem.summary}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">
                      {t("sourceValue", { source: data.fundamentals?.source ?? t("unavailableShort") })}
                    </Badge>
                    {data.fundamentals?.as_of ? (
                      <Badge variant="outline">
                        {t("fundamentalAsOf", {
                          date: formatDetailDate(data.fundamentals.as_of, locale, t("unavailableShort")),
                        })}
                      </Badge>
                    ) : null}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">{t("noFundamentals")}</p>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-md shadow-none">
            <CardHeader className="border-b bg-muted/20 p-4">
              <CardTitle>{t("latestNews")}</CardTitle>
              <CardDescription>{t("latestNewsDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 p-4">
              {latestNews ? (
                <>
                  <div className="space-y-2 rounded-md border p-3">
                    <div className="font-medium leading-6">{latestNews.title}</div>
                    <div className="flex flex-wrap gap-2">
                      {latestNews.sentiment ? <Badge variant="secondary">{latestNews.sentiment}</Badge> : null}
                      {typeof latestNews.confidence === "number" ? (
                        <Badge variant="outline">
                          {t("confidence", { score: Math.round(latestNews.confidence * 100) })}
                        </Badge>
                      ) : null}
                      {latestNews.published_at ? (
                        <Badge variant="outline">
                          {formatDetailDate(latestNews.published_at, locale, t("unavailableShort"))}
                        </Badge>
                      ) : null}
                    </div>
                    {latestNews.summary ? (
                      <p className="text-sm text-muted-foreground">{latestNews.summary}</p>
                    ) : null}
                    {latestNews.url ? (
                      <a
                        href={latestNews.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                      >
                        {t("readNews")}
                        <ExternalLink className="h-3 w-3" aria-hidden="true" />
                      </a>
                    ) : null}
                  </div>
                  {newsItems.length > 1 ? (
                    <div className="text-xs text-muted-foreground">
                      {t("newsArticleCount", { count: newsItems.length })}
                    </div>
                  ) : null}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">{t("noNews")}</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Card className="rounded-md shadow-none">
        <CardHeader className="border-b bg-muted/20 p-4">
          <CardTitle>{t("intradayTitle")}</CardTitle>
          <CardDescription>{t("intradayDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="p-4">
          <IntradayPriceChart
            points={data.intraday?.items ?? []}
            previousClose={data.intraday?.previous_close ?? null}
            status={data.intraday?.status ?? "degraded"}
            reason={data.intraday?.availability?.reason ?? null}
            source={data.intraday?.source ?? null}
            provider={data.intraday?.provider ?? null}
            requestedProvider={data.intraday?.requested_provider ?? null}
            effectiveProvider={data.intraday?.effective_provider ?? null}
            availability={data.intraday?.availability ?? null}
            freshness={data.intraday?.freshness ?? null}
            session={data.intraday?.session ?? null}
            height={280}
          />
        </CardContent>
      </Card>

      <Card className="rounded-md shadow-none">
        <CardHeader className="border-b bg-muted/20 p-4">
          <CardTitle>{t("klineTitle")}</CardTitle>
          <CardDescription>{t("interactiveKlineDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="p-4">
          <div className="mb-4">
            <DataTrustBadge signal={barsTrustSignal} mode="summary" />
          </div>
          {chartBars.length > 0 ? (
            <AdvancedCandlestickChart
              data={chartBars}
              symbol={symbol}
              height={500}
              showMA={true}
              showVolume={true}
            />
          ) : (
            <div className="flex items-center justify-center h-96 text-muted-foreground">
              {t("noKlineData")}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
