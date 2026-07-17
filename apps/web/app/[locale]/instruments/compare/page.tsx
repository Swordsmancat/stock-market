import { ArrowLeft, Database, Plus, Search, X } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { ComparisonTool, type ComparisonToolLabels } from "@/components/comparison-tool";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { backendFetch } from "@/lib/backend-api";
import {
  decodeMarketComparisonPayload,
  toComparisonInstruments,
  type ComparisonPeriod,
  type MarketComparisonPayload,
} from "@/lib/market-comparison";
import { Link } from "@/src/i18n/routing";

type SearchParams = Record<string, string | string[] | undefined>;

type StockComparisonPageProps = {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<SearchParams>;
};

const PERIODS: ComparisonPeriod[] = ["1m", "3m", "6m", "1y"];

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function parseSymbols(value: string | undefined): string[] {
  const seen = new Set<string>();
  return (value ?? "").split(",").flatMap((rawSymbol) => {
    const symbol = rawSymbol.trim().toUpperCase();
    if (!symbol || seen.has(symbol)) return [];
    seen.add(symbol);
    return [symbol];
  });
}

function parsePeriod(value: string | undefined): ComparisonPeriod {
  return PERIODS.includes(value as ComparisonPeriod)
    ? (value as ComparisonPeriod)
    : "3m";
}

function comparisonHref({
  symbols,
  period,
  query,
}: {
  symbols: string[];
  period: ComparisonPeriod;
  query?: string;
}): string {
  const params = new URLSearchParams();
  if (symbols.length > 0) params.set("symbols", symbols.join(","));
  if (period !== "3m") params.set("period", period);
  if (query?.trim()) params.set("q", query.trim());
  const queryString = params.toString();
  return queryString ? `/instruments/compare?${queryString}` : "/instruments/compare";
}

async function loadComparison({
  symbols,
  period,
  query,
}: {
  symbols: string[];
  period: ComparisonPeriod;
  query?: string;
}): Promise<MarketComparisonPayload | null> {
  const params = new URLSearchParams({ market: "CN", period, search_limit: "8" });
  if (symbols.length > 0) params.set("symbols", symbols.join(","));
  if (query?.trim()) params.set("q", query.trim());

  try {
    const response = await backendFetch(`/market-comparison?${params.toString()}`, {
      cache: "no-store",
    });
    if (!response.ok) return null;
    return decodeMarketComparisonPayload(await response.json());
  } catch {
    return null;
  }
}

export default async function StockComparisonPage({
  params,
  searchParams = Promise.resolve({}),
}: StockComparisonPageProps) {
  const [{ locale }, resolvedSearchParams, t] = await Promise.all([
    params,
    searchParams,
    getTranslations("StockComparison"),
  ]);
  const symbols = parseSymbols(first(resolvedSearchParams.symbols));
  const period = parsePeriod(first(resolvedSearchParams.period));
  const query = first(resolvedSearchParams.q)?.trim() ?? "";
  const payload = await loadComparison({ symbols, period, query });
  const itemsBySymbol = new Map(payload?.items.map((item) => [item.symbol, item]));
  const comparisonInstruments = toComparisonInstruments(payload?.items ?? []);

  const comparisonLabels: ComparisonToolLabels = {
    title: t("analysisTitle"),
    description: t("analysisDescription"),
    insufficientTitle: t("insufficientTitle"),
    insufficientDescription: t("insufficientDescription"),
    insufficientBody: t("insufficientBody"),
    exportReport: t("exportReport"),
    selectAtLeastTwo: t("selectAtLeastTwo"),
    returnsTitle: t("returnsTitle"),
    correlationTitle: t("correlationTitle"),
    instrument: t("instrument"),
    startClose: t("startClose"),
    latestClose: t("latestClose"),
    intervalReturn: t("intervalReturn"),
    volatility: t("volatility"),
    report: {
      title: t("reportTitle"),
      generatedAt: t("reportGeneratedAt"),
      selectedInstruments: t("reportSelectedInstruments"),
      summaryMetrics: t("reportSummaryMetrics"),
      correlationMatrix: t("reportCorrelationMatrix"),
      instrument: t("instrument"),
      name: t("name"),
      market: t("market"),
      startClose: t("startClose"),
      latestClose: t("latestClose"),
      intervalReturn: t("intervalReturn"),
      volatility: t("volatility"),
    },
  };

  return (
    <div className="space-y-4">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[
          { label: t("storedOnly"), variant: "secondary" },
          { label: t("researchOnly") },
        ]}
        metrics={[
          { label: t("selectedCount"), value: payload?.requestedCount ?? symbols.length },
          { label: t("comparableCount"), value: payload?.comparableCount ?? 0 },
          { label: t("sharedDates"), value: payload?.sharedDateCount ?? 0 },
          { label: t("anchorDate"), value: payload?.anchorDate ?? t("unavailable") },
        ]}
        actions={
          <Button variant="outline" size="sm" asChild>
            <Link href="/instruments">
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t("backToInstruments")}
            </Link>
          </Button>
        }
      />

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)]">
        <div className="grid min-w-0 gap-4">
          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle className="text-base">{t("selectionTitle")}</CardTitle>
              <CardDescription>{t("selectionDescription")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="space-y-4">
              <form className="flex flex-col gap-2 sm:flex-row">
                {symbols.length > 0 ? (
                  <input type="hidden" name="symbols" value={symbols.join(",")} />
                ) : null}
                {period !== "3m" ? <input type="hidden" name="period" value={period} /> : null}
                <Input
                  name="q"
                  defaultValue={query}
                  placeholder={t("searchPlaceholder")}
                  aria-label={t("searchPlaceholder")}
                />
                <Button type="submit">
                  <Search className="mr-2 h-4 w-4" />
                  {t("search")}
                </Button>
              </form>

              <div className="space-y-2">
                <div className="text-xs font-medium uppercase text-muted-foreground">
                  {t("selectedTitle")}
                </div>
                {symbols.length === 0 ? (
                  <p className="text-sm text-muted-foreground">{t("emptySelectionHint")}</p>
                ) : (
                  symbols.map((symbol) => {
                    const item = itemsBySymbol.get(symbol);
                    const remainingSymbols = symbols.filter((value) => value !== symbol);
                    return (
                      <FinancialTerminalSurface key={symbol} className="flex items-start justify-between gap-3 p-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            {item ? (
                              <Link
                                href={`/instruments/${encodeURIComponent(symbol)}?market=CN` as any}
                                className="font-mono font-semibold hover:underline"
                              >
                                {symbol}
                              </Link>
                            ) : (
                              <span className="font-mono font-semibold">{symbol}</span>
                            )}
                            <span className="truncate text-sm">{item?.name}</span>
                            {!item ? <Badge variant="destructive">{t("missing")}</Badge> : null}
                          </div>
                          {item ? (
                            <div className="mt-1 text-xs text-muted-foreground">
                              {item.status === "ok"
                                ? t("provenance", {
                                    provider: item.provider ?? t("unavailable"),
                                    adjustment: item.adjustment ?? t("unavailable"),
                                    firstDate: item.firstDate ?? t("unavailable"),
                                    lastDate: item.lastDate ?? t("unavailable"),
                                  })
                                : t("selectedNoData")}
                            </div>
                          ) : null}
                        </div>
                        <Button variant="ghost" size="icon" asChild>
                          <Link
                            href={comparisonHref({ symbols: remainingSymbols, period, query }) as any}
                            title={t("removeSymbol", { symbol })}
                            aria-label={t("removeSymbol", { symbol })}
                          >
                            <X className="h-4 w-4" />
                          </Link>
                        </Button>
                      </FinancialTerminalSurface>
                    );
                  })
                )}
              </div>

              <div className="space-y-2">
                <div className="text-xs font-medium uppercase text-muted-foreground">
                  {t("periodTitle")}
                </div>
                <div className="flex flex-wrap gap-2" role="group" aria-label={t("periodTitle")}>
                  {PERIODS.map((candidatePeriod) => (
                    <Button
                      key={candidatePeriod}
                      variant={candidatePeriod === period ? "default" : "outline"}
                      size="sm"
                      asChild
                    >
                      <Link
                        href={comparisonHref({ symbols, period: candidatePeriod, query }) as any}
                        aria-current={candidatePeriod === period ? "page" : undefined}
                      >
                        {t(`period${candidatePeriod}`)}
                      </Link>
                    </Button>
                  ))}
                </div>
              </div>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          {query && payload !== null ? (
            <FinancialTerminalCard>
              <FinancialTerminalCardHeader>
                <CardTitle className="text-base">{t("searchResultsTitle")}</CardTitle>
                <CardDescription>{t("searchResultsDescription", { query })}</CardDescription>
              </FinancialTerminalCardHeader>
              <FinancialTerminalCardContent className="space-y-2">
                {(payload?.searchResults.length ?? 0) === 0 ? (
                  <p className="text-sm text-muted-foreground">{t("noSearchResults")}</p>
                ) : (
                  payload?.searchResults.map((result) => {
                    const atLimit = symbols.length >= 4;
                    return (
                      <FinancialTerminalSurface key={result.id} className="flex items-center justify-between gap-3 p-3">
                        <div className="min-w-0">
                          <div className="font-mono text-sm font-semibold">{result.symbol}</div>
                          <div className="truncate text-xs text-muted-foreground">{result.name}</div>
                        </div>
                        <Button variant="outline" size="sm" disabled={atLimit} asChild={!atLimit}>
                          {atLimit ? (
                            <span>{t("limitReached")}</span>
                          ) : (
                            <Link
                              href={comparisonHref({
                                symbols: [...symbols, result.symbol],
                                period,
                                query,
                              }) as any}
                            >
                              <Plus className="mr-2 h-4 w-4" />
                              {t("add")}
                            </Link>
                          )}
                        </Button>
                      </FinancialTerminalSurface>
                    );
                  })
                )}
              </FinancialTerminalCardContent>
            </FinancialTerminalCard>
          ) : null}
        </div>

        <div className="grid min-w-0 gap-4">
          {payload === null ? (
            <FinancialTerminalCard>
              <FinancialTerminalCardContent className="p-4">
                <ErrorState title={t("loadFailed")} description={t("loadFailedDescription")} />
              </FinancialTerminalCardContent>
            </FinancialTerminalCard>
          ) : payload.status === "empty_selection" ? (
            <FinancialTerminalCard>
              <FinancialTerminalCardContent className="p-4">
                <EmptyState title={t("emptyTitle")} description={t("emptyDescription")} />
              </FinancialTerminalCardContent>
            </FinancialTerminalCard>
          ) : payload.status === "insufficient_selection" ? (
            <FinancialTerminalCard>
              <FinancialTerminalCardContent className="p-4">
                <EmptyState title={t("insufficientTitle")} description={t("insufficientDescription")} />
              </FinancialTerminalCardContent>
            </FinancialTerminalCard>
          ) : payload.status === "no_data" ? (
            <FinancialTerminalCard>
              <FinancialTerminalCardContent className="p-4">
                <EmptyState title={t("noDataTitle")} description={t("noDataDescription")} />
              </FinancialTerminalCardContent>
            </FinancialTerminalCard>
          ) : (
            <>
              <FinancialTerminalSurface className="flex flex-wrap items-center gap-2 p-3 text-xs text-muted-foreground">
                <Database className="h-4 w-4" />
                <span>{t("sharedWindow", {
                  firstDate: payload.items.find((item) => item.status === "ok")?.firstDate ?? t("unavailable"),
                  lastDate: payload.items.find((item) => item.status === "ok")?.lastDate ?? t("unavailable"),
                  count: payload.sharedDateCount,
                })}</span>
              </FinancialTerminalSurface>
              <ComparisonTool
                instruments={comparisonInstruments}
                labels={comparisonLabels}
                locale={locale}
                showInstrumentSelection={false}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
