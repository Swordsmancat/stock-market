import { Activity, FileText, Settings } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
  financialTerminalCardClassName,
} from "@/components/financial-terminal-section";
import { ComparisonTool } from "@/components/comparison-tool";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { backendFetch } from "@/lib/backend-api";
import { getDashboardDateRanges } from "@/lib/dates";
import { withProviderQuery } from "@/lib/market-data";
import type { ComparisonInstrument } from "@/lib/comparison-utils";
import { getPlatformSettings } from "@/lib/platform-settings-store";
import { Link } from "@/src/i18n/routing";

const INSTRUMENTS_PAGE_SIZE = 25;
const MAX_COMPARISON_BAR_REQUESTS = 8;
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

type Instrument = {
  symbol: string;
  name: string;
  market: string;
  exchange?: string;
  asset_type?: string;
  currency?: string;
  source?: string;
};

type InstrumentsPayload = {
  source: string;
  items: Instrument[];
  total: number;
  limit: number | null;
  offset: number;
  has_more: boolean;
};

type LatestDailyBarPayload = {
  symbol: string;
  source: string;
  provider?: string | null;
  requested_provider?: string | null;
  effective_provider?: string | null;
  status?: "ok" | "no_data" | string;
  no_data_reason?: string | null;
  item?: {
    timestamp?: string;
    close?: number;
  } | null;
};

type ComparisonBarsPayload = {
  items?: Array<{
    timestamp?: string;
    close?: number | null;
  }>;
};

type InstrumentsLoadResult =
  { status: "loaded"; payload: InstrumentsPayload } | { status: "failed" };

type LatestDailyBarLoadResult =
  { status: "loaded"; payload: LatestDailyBarPayload } | { status: "failed" };

type FreshnessStatus = "fresh" | "stale" | "no_data" | "unavailable";

type LatestDailyBarHealthCounts = Record<FreshnessStatus, number>;

type InstrumentsPageProps = {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<{
    q?: string;
    market?: string;
    page?: string;
  }>;
};

async function fetchInstrumentsPayload(searchParams: {
  q?: string;
  market?: string;
  page?: string;
}): Promise<InstrumentsLoadResult> {
  const upstreamParams = new URLSearchParams();
  const query = searchParams.q?.trim();
  const market = searchParams.market?.trim();
  const page = parsePageNumber(searchParams.page);

  if (query) {
    upstreamParams.set("q", query);
  }
  if (market) {
    upstreamParams.set("market", market);
  }
  upstreamParams.set("limit", String(INSTRUMENTS_PAGE_SIZE));
  upstreamParams.set(
    "offset",
    String((page - 1) * INSTRUMENTS_PAGE_SIZE),
  );

  const requestPath = `/instruments?${upstreamParams.toString()}`;

  try {
    const response = await backendFetch(requestPath, { cache: "no-store" });
    if (!response.ok) {
      return { status: "failed" };
    }

    return {
      status: "loaded",
      payload: (await response.json()) as InstrumentsPayload,
    };
  } catch {
    return { status: "failed" };
  }
}

function parsePageNumber(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : 1;
}

function buildPageHref(
  page: number,
  searchParams: { q?: string; market?: string },
): string {
  const params = new URLSearchParams();
  const query = searchParams.q?.trim();
  const market = searchParams.market?.trim();
  if (query) params.set("q", query);
  if (market) params.set("market", market);
  if (page > 1) params.set("page", String(page));
  const queryString = params.toString();
  return queryString ? `/instruments?${queryString}` : "/instruments";
}

async function fetchLatestDailyBar(
  symbol: string,
  provider: string,
): Promise<LatestDailyBarLoadResult> {
  try {
    const response = await backendFetch(
      withProviderQuery(
        `/market-data/${encodeURIComponent(symbol)}/latest`,
        provider,
      ),
      { cache: "no-store" },
    );
    if (!response.ok) {
      return { status: "failed" };
    }

    return {
      status: "loaded",
      payload: (await response.json()) as LatestDailyBarPayload,
    };
  } catch {
    return { status: "failed" };
  }
}

async function fetchComparisonBars(
  symbol: string,
  provider: string,
  range: { start: string; end: string },
): Promise<ComparisonBarsPayload> {
  try {
    const response = await backendFetch(
      withProviderQuery(
        `/market-data/${encodeURIComponent(symbol)}/bars?timeframe=1d&start=${range.start}&end=${range.end}`,
        provider,
      ),
      { cache: "no-store" },
    );
    if (!response.ok) {
      return { items: [] };
    }

    return (await response.json()) as ComparisonBarsPayload;
  } catch {
    return { items: [] };
  }
}

async function buildComparisonInstruments(
  instruments: Instrument[],
  provider: string,
  range: { start: string; end: string },
): Promise<ComparisonInstrument[]> {
  const comparisonCandidates = instruments.slice(
    0,
    MAX_COMPARISON_BAR_REQUESTS,
  );
  const barsPayloads = await Promise.all(
    comparisonCandidates.map((instrument) =>
      fetchComparisonBars(instrument.symbol, provider, range),
    ),
  );

  return comparisonCandidates.map((instrument, index) => ({
    id: `${instrument.market}-${instrument.symbol}`,
    symbol: instrument.symbol,
    name: instrument.name,
    market: instrument.market,
    bars: (barsPayloads[index].items ?? []).flatMap((bar) =>
      typeof bar.timestamp === "string"
        ? [
            {
              timestamp: bar.timestamp,
              close: bar.close ?? null,
            },
          ]
        : [],
    ),
  }));
}

function getCurrencyCode(instrument: Instrument): string {
  const normalizedCurrency = instrument.currency?.trim().toUpperCase();
  return normalizedCurrency && /^[A-Z]{3}$/.test(normalizedCurrency)
    ? normalizedCurrency
    : "USD";
}

function formatLatestClose(
  latestDailyBar: LatestDailyBarLoadResult,
  instrument: Instrument,
  locale: string,
  unavailableLabel: string,
): string {
  if (latestDailyBar.status === "failed") {
    return unavailableLabel;
  }

  const close = latestDailyBar.payload.item?.close;
  if (typeof close !== "number") {
    return unavailableLabel;
  }

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: getCurrencyCode(instrument),
  }).format(close);
}

function parseLatestTimestamp(
  latestDailyBar: LatestDailyBarLoadResult,
): Date | null {
  if (latestDailyBar.status === "failed") {
    return null;
  }

  const timestamp = latestDailyBar.payload.item?.timestamp;
  if (!timestamp) {
    return null;
  }

  const parsedTimestamp = new Date(timestamp);
  return Number.isNaN(parsedTimestamp.getTime()) ? null : parsedTimestamp;
}

function formatLatestTimestamp(
  latestDailyBar: LatestDailyBarLoadResult,
  locale: string,
  unavailableLabel: string,
): string {
  const parsedTimestamp = parseLatestTimestamp(latestDailyBar);
  return parsedTimestamp === null
    ? unavailableLabel
    : parsedTimestamp.toLocaleDateString(locale);
}

function getFreshnessStatus(
  latestDailyBar: LatestDailyBarLoadResult,
): FreshnessStatus {
  if (latestDailyBar.status === "failed") {
    return "unavailable";
  }

  if (
    latestDailyBar.payload.status === "no_data" ||
    latestDailyBar.payload.item == null
  ) {
    return "no_data";
  }

  const parsedTimestamp = parseLatestTimestamp(latestDailyBar);
  if (parsedTimestamp === null) {
    return "unavailable";
  }

  const daysSinceLatestBar =
    (Date.now() - parsedTimestamp.getTime()) / MILLISECONDS_PER_DAY;
  return daysSinceLatestBar <= 3 ? "fresh" : "stale";
}

function getFreshnessBadgeVariant(
  freshnessStatus: FreshnessStatus,
): "secondary" | "outline" | "destructive" {
  if (freshnessStatus === "fresh") {
    return "secondary";
  }
  if (freshnessStatus === "stale") {
    return "outline";
  }
  return "destructive";
}

function countLatestDailyBarHealth(
  latestDailyBars: LatestDailyBarLoadResult[],
): LatestDailyBarHealthCounts {
  const initialCounts: LatestDailyBarHealthCounts = {
    fresh: 0,
    stale: 0,
    no_data: 0,
    unavailable: 0,
  };

  return latestDailyBars.reduce((counts, latestDailyBar) => {
    const freshnessStatus = getFreshnessStatus(latestDailyBar);
    return {
      ...counts,
      [freshnessStatus]: counts[freshnessStatus] + 1,
    };
  }, initialCounts);
}

function getLatestSource(
  latestDailyBar: LatestDailyBarLoadResult,
  instrument: Instrument,
): string {
  if (latestDailyBar.status === "failed") {
    return "unavailable";
  }
  return latestDailyBar.payload.source || instrument.source || "unavailable";
}

function getLatestProvider(
  latestDailyBar: LatestDailyBarLoadResult,
): string | null {
  if (latestDailyBar.status === "failed") {
    return null;
  }
  return (
    latestDailyBar.payload.effective_provider ??
    latestDailyBar.payload.provider ??
    null
  );
}

function getLatestAvailabilityLabel(
  latestDailyBar: LatestDailyBarLoadResult,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string | null {
  if (latestDailyBar.status === "failed") {
    return t("latestUnavailable");
  }
  if (
    latestDailyBar.payload.status === "no_data" ||
    latestDailyBar.payload.item == null
  ) {
    return t("noLatestDailyBar");
  }
  return null;
}

export default async function InstrumentsPage({
  params,
  searchParams = Promise.resolve({}),
}: InstrumentsPageProps) {
  const [{ locale }, resolvedSearchParams] = await Promise.all([
    params,
    searchParams,
  ]);
  const currentPage = parsePageNumber(resolvedSearchParams.page);
  const hasActiveFilters = Boolean(
    resolvedSearchParams.q?.trim() || resolvedSearchParams.market?.trim(),
  );
  const [t, platformSettings, instrumentsResult] = await Promise.all([
    getTranslations("Instruments"),
    getPlatformSettings(),
    fetchInstrumentsPayload(resolvedSearchParams),
  ]);

  const activeProvider = platformSettings.market_data_provider;

  if (instrumentsResult.status === "failed") {
    return (
      <div className="space-y-6">
        <FinancialPageHeader
          title={t("title")}
          description={t("description")}
          badges={[
            {
              label: t("activeProvider", { provider: activeProvider }),
              variant: "secondary",
            },
          ]}
          metrics={[
            { label: t("visibleInstruments"), value: 0 },
            { label: t("fresh"), value: 0 },
            { label: t("stale"), value: 0 },
            { label: t("unavailable"), value: 0 },
          ]}
          actions={
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button variant="outline" asChild>
                <Link href="/settings">
                  <Settings className="mr-2 h-4 w-4" />
                  {t("goToSettings")}
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/task-runs">
                  <Activity className="mr-2 h-4 w-4" />
                  {t("goToTaskRuns")}
                </Link>
              </Button>
            </div>
          }
        />
        <FinancialTerminalCard>
          <FinancialTerminalCardContent className="p-4">
            <ErrorState
              title={t("loadFailed")}
              description={t("loadFailedHint")}
            />
          </FinancialTerminalCardContent>
        </FinancialTerminalCard>
      </div>
    );
  }

  const instruments = instrumentsResult.payload.items;
  const visibleInstruments = instruments.slice(0, INSTRUMENTS_PAGE_SIZE);
  const totalInstruments = instrumentsResult.payload.total;
  const { analysis } = getDashboardDateRanges();
  const latestDailyBars = await Promise.all(
    visibleInstruments.map((instrument) =>
      fetchLatestDailyBar(instrument.symbol, activeProvider),
    ),
  );
  const comparisonInstruments = await buildComparisonInstruments(
    visibleInstruments,
    activeProvider,
    analysis,
  );
  const latestDailyBarHealthCounts = countLatestDailyBarHealth(latestDailyBars);
  const hasPreviousPage = currentPage > 1;
  const hasNextPage = instrumentsResult.payload.has_more;

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[
          {
            label: t("dataSource", {
              source: instrumentsResult.payload.source,
            }),
            variant: "secondary",
          },
          { label: t("activeProvider", { provider: activeProvider }) },
        ]}
        metrics={[
          {
            label: t("visibleInstruments"),
            value: visibleInstruments.length,
            description: t("tableDescription", {
              visible: visibleInstruments.length,
              total: totalInstruments,
            }),
          },
          { label: t("fresh"), value: latestDailyBarHealthCounts.fresh },
          { label: t("stale"), value: latestDailyBarHealthCounts.stale },
          {
            label: t("unavailable"),
            value:
              latestDailyBarHealthCounts.unavailable +
              latestDailyBarHealthCounts.no_data,
          },
        ]}
        actions={
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button variant="outline" asChild>
              <Link href="/settings">
                <Settings className="mr-2 h-4 w-4" />
                {t("goToSettings")}
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/task-runs">
                <Activity className="mr-2 h-4 w-4" />
                {t("goToTaskRuns")}
              </Link>
            </Button>
          </div>
        }
      />

      <FinancialTerminalCard>
        <FinancialTerminalCardContent>
          <form className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,10rem)_auto_auto]">
            <Input
              name="q"
              defaultValue={resolvedSearchParams.q ?? ""}
              placeholder={t("searchPlaceholder")}
            />
            <select
              name="market"
              defaultValue={resolvedSearchParams.market ?? ""}
              aria-label={t("market")}
              className="flex h-10 rounded-sm border border-input bg-background px-3 py-2 text-sm ring-offset-background"
            >
              <option value="">{t("allMarkets")}</option>
              <option value="US">US</option>
              <option value="CN">CN</option>
              <option value="HK">HK</option>
            </select>
            <Button type="submit">{t("search")}</Button>
            <Button variant="outline" asChild>
              <Link href="/instruments">{t("reset")}</Link>
            </Button>
          </form>
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <CardTitle>{t("healthSummaryTitle")}</CardTitle>
          <CardDescription>
            {t("healthSummaryDesc", {
              visible: visibleInstruments.length,
              total: totalInstruments,
              provider: activeProvider,
            })}
          </CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <FinancialTerminalSurface className="p-3">
              <div className="text-xs text-muted-foreground">
                {t("visibleInstruments")}
              </div>
              <div className="font-mono text-2xl font-bold">
                {visibleInstruments.length}
              </div>
            </FinancialTerminalSurface>
            <FinancialTerminalSurface className="p-3">
              <div className="text-xs text-muted-foreground">{t("fresh")}</div>
              <div className="font-mono text-2xl font-bold">
                {latestDailyBarHealthCounts.fresh}
              </div>
            </FinancialTerminalSurface>
            <FinancialTerminalSurface className="p-3">
              <div className="text-xs text-muted-foreground">{t("stale")}</div>
              <div className="font-mono text-2xl font-bold">
                {latestDailyBarHealthCounts.stale}
              </div>
            </FinancialTerminalSurface>
            <FinancialTerminalSurface className="p-3">
              <div className="text-xs text-muted-foreground">
                {t("no_data")}
              </div>
              <div className="font-mono text-2xl font-bold">
                {latestDailyBarHealthCounts.no_data}
              </div>
            </FinancialTerminalSurface>
            <FinancialTerminalSurface className="p-3">
              <div className="text-xs text-muted-foreground">
                {t("unavailable")}
              </div>
              <div className="font-mono text-2xl font-bold">
                {latestDailyBarHealthCounts.unavailable}
              </div>
            </FinancialTerminalSurface>
          </div>
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <CardTitle>{t("tableTitle")}</CardTitle>
          <CardDescription>
            {t("tableDescription", {
              visible: visibleInstruments.length,
              total: totalInstruments,
            })}
          </CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent className="p-0">
          {instruments.length === 0 ? (
            <div className="p-4">
              <EmptyState
                title={hasActiveFilters ? t("noMatches") : t("noData")}
                description={
                  hasActiveFilters ? t("noMatchesHint") : t("emptyHint")
                }
              />
              {hasActiveFilters ? (
                <div className="flex justify-center">
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/instruments">{t("reset")}</Link>
                  </Button>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("symbol")}</TableHead>
                    <TableHead>{t("name")}</TableHead>
                    <TableHead>{t("market")}</TableHead>
                    <TableHead>{t("latestClose")}</TableHead>
                    <TableHead>{t("asOf")}</TableHead>
                    <TableHead>{t("sourceProvider")}</TableHead>
                    <TableHead>{t("freshness")}</TableHead>
                    <TableHead className="text-right">{t("actions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleInstruments.map((instrument, index) => {
                    const latestDailyBar = latestDailyBars[index];
                    const freshnessStatus = getFreshnessStatus(latestDailyBar);
                    const latestAvailabilityLabel = getLatestAvailabilityLabel(
                      latestDailyBar,
                      t,
                    );
                    const latestProvider = getLatestProvider(latestDailyBar);

                    return (
                      <TableRow
                        key={`${instrument.market}-${instrument.symbol}`}
                      >
                        <TableCell className="font-medium">
                          <Link
                            href={`/instruments/${instrument.symbol}` as any}
                            className="hover:underline"
                          >
                            {instrument.symbol}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <div>{instrument.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {[
                              instrument.exchange,
                              instrument.asset_type,
                              instrument.currency,
                            ]
                              .filter(Boolean)
                              .join(" / ")}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{instrument.market}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="font-mono font-medium">
                            {formatLatestClose(
                              latestDailyBar,
                              instrument,
                              locale,
                              t("unavailableShort"),
                            )}
                          </div>
                          {latestAvailabilityLabel ? (
                            <div className="text-xs text-muted-foreground">
                              {latestAvailabilityLabel}
                            </div>
                          ) : null}
                        </TableCell>
                        <TableCell>
                          {formatLatestTimestamp(
                            latestDailyBar,
                            locale,
                            t("unavailableShort"),
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {t("sourceValue", {
                              source: getLatestSource(
                                latestDailyBar,
                                instrument,
                              ),
                            })}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {latestProvider
                              ? t("providerValue", { provider: latestProvider })
                              : t("providerUnavailable")}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={getFreshnessBadgeVariant(freshnessStatus)}
                          >
                            {t(freshnessStatus)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button variant="outline" size="sm" asChild>
                              <Link
                                href={
                                  `/instruments/${instrument.symbol}` as any
                                }
                              >
                                {t("viewDetails")}
                              </Link>
                            </Button>
                            <Button variant="ghost" size="sm" asChild>
                              <Link
                                href={
                                  `/reports?symbol=${encodeURIComponent(instrument.symbol)}` as any
                                }
                              >
                                <FileText className="mr-2 h-4 w-4" />
                                {t("viewReports")}
                              </Link>
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
          <div className="flex flex-col gap-3 border-t border-border/70 px-3 py-3 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <span>
              {t("pageStatus", {
                page: currentPage,
                visible: visibleInstruments.length,
                total: totalInstruments,
              })}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!hasPreviousPage}
                asChild={hasPreviousPage}
              >
                {hasPreviousPage ? (
                  <Link
                    href={
                      buildPageHref(currentPage - 1, resolvedSearchParams) as any
                    }
                  >
                    {t("previousPage")}
                  </Link>
                ) : (
                  <span>{t("previousPage")}</span>
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!hasNextPage}
                asChild={hasNextPage}
              >
                {hasNextPage ? (
                  <Link
                    href={
                      buildPageHref(currentPage + 1, resolvedSearchParams) as any
                    }
                  >
                    {t("nextPage")}
                  </Link>
                ) : (
                  <span>{t("nextPage")}</span>
                )}
              </Button>
            </div>
          </div>
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      <ComparisonTool
        className={financialTerminalCardClassName}
        instruments={comparisonInstruments}
        locale={locale}
        labels={{
          title: t("comparisonTitle"),
          description: t("comparisonDescription"),
          insufficientTitle: t("comparisonInsufficientTitle"),
          insufficientDescription: t("comparisonInsufficientDescription"),
          insufficientBody: t("comparisonInsufficientBody"),
          exportReport: t("comparisonExportReport"),
          selectAtLeastTwo: t("comparisonSelectAtLeastTwo"),
          returnsTitle: t("comparisonReturnsTitle"),
          correlationTitle: t("comparisonCorrelationTitle"),
          instrument: t("comparisonInstrument"),
          startClose: t("comparisonStartClose"),
          latestClose: t("comparisonLatestClose"),
          intervalReturn: t("comparisonIntervalReturn"),
          volatility: t("comparisonVolatility"),
          report: {
            title: t("comparisonReportTitle"),
            generatedAt: t("comparisonReportGeneratedAt"),
            selectedInstruments: t("comparisonReportSelectedInstruments"),
            summaryMetrics: t("comparisonReportSummaryMetrics"),
            correlationMatrix: t("comparisonReportCorrelationMatrix"),
            instrument: t("comparisonInstrument"),
            name: t("name"),
            market: t("market"),
            startClose: t("comparisonStartClose"),
            latestClose: t("comparisonLatestClose"),
            intervalReturn: t("comparisonIntervalReturn"),
            volatility: t("comparisonVolatility"),
          },
        }}
      />
    </div>
  );
}
