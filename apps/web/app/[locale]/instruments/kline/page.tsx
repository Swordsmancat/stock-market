import { Activity, ArrowLeft, ChartCandlestick, Database, ExternalLink, Search } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { AdvancedCandlestickChart } from "@/components/advanced-candlestick-chart";
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
  decodeInstrumentKlinePayload,
  type InstrumentAssetType,
  type InstrumentKlinePayload,
  type InstrumentKlinePeriod,
} from "@/lib/instrument-kline";
import { Link } from "@/src/i18n/routing";

type SearchParams = Record<string, string | string[] | undefined>;

type InstrumentKlinePageProps = {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<SearchParams>;
};

const PERIODS: InstrumentKlinePeriod[] = ["1m", "3m", "6m", "1y"];
const ASSET_TYPES: InstrumentAssetType[] = ["stock", "etf", "index"];

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function normalizedPeriod(value: string): InstrumentKlinePeriod {
  return PERIODS.includes(value as InstrumentKlinePeriod)
    ? (value as InstrumentKlinePeriod)
    : "3m";
}

function normalizedAssetType(value: string): InstrumentAssetType | "" {
  return ASSET_TYPES.includes(value as InstrumentAssetType)
    ? (value as InstrumentAssetType)
    : "";
}

function workspaceHref(options: {
  q?: string;
  assetType?: string;
  symbol?: string;
  market?: string;
  period?: InstrumentKlinePeriod;
}): string {
  const params = new URLSearchParams();
  if (options.q?.trim()) params.set("q", options.q.trim());
  if (options.assetType) params.set("asset_type", options.assetType);
  if (options.symbol && options.market) {
    params.set("symbol", options.symbol);
    params.set("market", options.market);
  }
  if (options.period && options.period !== "3m") params.set("period", options.period);
  const query = params.toString();
  return query ? `/instruments/kline?${query}` : "/instruments/kline";
}

async function loadPayload(params: URLSearchParams): Promise<InstrumentKlinePayload | null> {
  try {
    const response = await backendFetch(`/instrument-kline?${params.toString()}`, { cache: "no-store" });
    if (!response.ok) return null;
    return decodeInstrumentKlinePayload(await response.json());
  } catch {
    return null;
  }
}

export default async function InstrumentKlinePage({
  params,
  searchParams = Promise.resolve({}),
}: InstrumentKlinePageProps) {
  const [{ locale }, resolvedSearchParams, t] = await Promise.all([
    params,
    searchParams,
    getTranslations("InstrumentKline"),
  ]);
  const q = first(resolvedSearchParams.q).trim();
  const assetType = normalizedAssetType(first(resolvedSearchParams.asset_type));
  const symbol = first(resolvedSearchParams.symbol).trim().toUpperCase();
  const market = first(resolvedSearchParams.market).trim().toUpperCase();
  const period = normalizedPeriod(first(resolvedSearchParams.period));
  const upstreamParams = new URLSearchParams({ period, limit: "20", offset: "0" });
  if (q) upstreamParams.set("q", q);
  if (assetType) upstreamParams.set("asset_type", assetType);
  if (symbol && market) {
    upstreamParams.set("symbol", symbol);
    upstreamParams.set("market", market);
  }
  const payload = await loadPayload(upstreamParams);
  const catalogUncollected = payload?.status === "empty"
    && payload.total === 0
    && Boolean(assetType)
    && !q
    && !symbol
    && !market;
  const selectedAssetTypeLabel = assetType ? t(`assetType${assetType}`) : t("allAssetTypes");

  return (
    <div className="space-y-5">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[
          { label: t("storedOnly"), variant: "secondary" },
          { label: t("researchOnly") },
        ]}
        metrics={[
          { label: t("catalogCount"), value: payload?.total ?? 0 },
          { label: t("selectedType"), value: payload?.selected ? t(`assetType${payload.selected.assetType}`) : t("unavailable") },
          { label: t("barCount"), value: payload?.series?.barCount ?? 0 },
          { label: t("latestDate"), value: payload?.series?.lastDate ?? t("unavailable") },
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

      <FinancialTerminalCard>
        <FinancialTerminalCardContent>
          <form className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,10rem)_auto_auto]">
            <Input name="q" defaultValue={q} placeholder={t("searchPlaceholder")} aria-label={t("searchPlaceholder")} />
            <select
              name="asset_type"
              defaultValue={assetType}
              aria-label={t("assetType")}
              className="flex h-10 rounded-sm border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">{t("allAssetTypes")}</option>
              {ASSET_TYPES.map((value) => <option key={value} value={value}>{t(`assetType${value}`)}</option>)}
            </select>
            <Button type="submit"><Search className="mr-2 h-4 w-4" />{t("search")}</Button>
            <Button variant="outline" asChild><Link href="/instruments/kline">{t("reset")}</Link></Button>
          </form>
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      {payload === null ? (
        <FinancialTerminalCard><FinancialTerminalCardContent className="p-4"><ErrorState title={t("loadFailed")} description={t("loadFailedDescription")} /></FinancialTerminalCardContent></FinancialTerminalCard>
      ) : (
        <div className="grid items-start gap-4 xl:grid-cols-[minmax(16rem,0.55fr)_minmax(0,1.45fr)]">
          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle className="text-base">{t("catalogTitle")}</CardTitle>
              <CardDescription>{t("catalogDescription", { count: payload.total })}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="max-h-[38rem] space-y-2 overflow-y-auto">
              {payload.catalog.length === 0 ? (
                <EmptyState
                  title={catalogUncollected
                    ? t("catalogUncollectedTitle", { assetType: selectedAssetTypeLabel })
                    : q || assetType ? t("noMatches") : t("emptyCatalog")}
                  description={catalogUncollected
                    ? t("catalogUncollectedDescription", { assetType: selectedAssetTypeLabel })
                    : q || assetType ? t("noMatchesDescription") : t("emptyCatalogDescription")}
                />
              ) : payload.catalog.map((item) => {
                const selected = item.symbol === symbol && item.market === market;
                return (
                  <Link
                    key={item.id}
                    href={workspaceHref({ q, assetType, symbol: item.symbol, market: item.market, period }) as any}
                    className="block"
                    aria-current={selected ? "page" : undefined}
                  >
                    <FinancialTerminalSurface className={`p-3 transition-colors hover:bg-accent/50 ${selected ? "border-primary bg-accent/40" : ""}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono font-semibold">{item.symbol}</span>
                            <Badge variant="outline">{t(`assetType${item.assetType}`)}</Badge>
                          </div>
                          <div className="truncate text-sm">{item.name}</div>
                          <div className="mt-1 text-xs text-muted-foreground">{item.market}{item.exchange ? ` / ${item.exchange}` : ""}</div>
                        </div>
                        <div className="shrink-0 text-right text-xs text-muted-foreground">
                          <div>{item.latestBar?.timestamp ?? t("unavailable")}</div>
                          <div>{t("storedBars", { count: item.storedBarCount })}</div>
                        </div>
                      </div>
                    </FinancialTerminalSurface>
                  </Link>
                );
              })}
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <div className="min-w-0 space-y-4">
            {payload.status === "empty" ? (
              <FinancialTerminalCard>
                <FinancialTerminalCardContent className="p-4">
                  {catalogUncollected ? (
                    <div>
                      <EmptyState
                        title={t("catalogUncollectedTitle", { assetType: selectedAssetTypeLabel })}
                        description={t("catalogUncollectedNext", { assetType: selectedAssetTypeLabel })}
                      />
                      <div className="flex flex-wrap justify-center gap-2">
                        <Button variant="outline" size="sm" asChild>
                          <Link href="/storage"><Database className="mr-2 h-4 w-4" />{t("dataStorage")}</Link>
                        </Button>
                        <Button variant="outline" size="sm" asChild>
                          <Link href="/crawler-monitor"><Activity className="mr-2 h-4 w-4" />{t("crawlerMonitor")}</Link>
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <EmptyState title={t("chooseTitle")} description={t("chooseDescription")} />
                  )}
                </FinancialTerminalCardContent>
              </FinancialTerminalCard>
            ) : payload.status === "not_found" ? (
              <FinancialTerminalCard><FinancialTerminalCardContent className="p-4"><EmptyState title={t("notFoundTitle")} description={t("notFoundDescription")} /></FinancialTerminalCardContent></FinancialTerminalCard>
            ) : payload.status === "no_data" ? (
              <FinancialTerminalCard><FinancialTerminalCardContent className="p-4"><EmptyState title={t("noDataTitle")} description={t("noDataDescription")} /></FinancialTerminalCardContent></FinancialTerminalCard>
            ) : payload.selected && payload.series ? (
              <>
                <FinancialTerminalCard>
                  <FinancialTerminalCardHeader>
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                          <ChartCandlestick className="h-4 w-4" />
                          <span className="font-mono">{payload.selected.symbol}</span>
                          <span>{payload.selected.name}</span>
                          <Badge variant="outline">{t(`assetType${payload.selected.assetType}`)}</Badge>
                        </CardTitle>
                        <CardDescription>{payload.selected.market}{payload.selected.exchange ? ` / ${payload.selected.exchange}` : ""}</CardDescription>
                      </div>
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/instruments/${encodeURIComponent(payload.selected.symbol)}?market=${encodeURIComponent(payload.selected.market)}` as any}>
                          {t("openDetails")}<ExternalLink className="ml-2 h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  </FinancialTerminalCardHeader>
                  <FinancialTerminalCardContent className="space-y-4">
                    <div className="flex flex-wrap gap-2" role="group" aria-label={t("period") }>
                      {PERIODS.map((value) => (
                        <Button key={value} variant={value === period ? "default" : "outline"} size="sm" asChild>
                          <Link href={workspaceHref({ q, assetType, symbol: payload.selected?.symbol, market: payload.selected?.market, period: value }) as any} aria-current={value === period ? "page" : undefined}>{t(`period${value}`)}</Link>
                        </Button>
                      ))}
                    </div>
                    <FinancialTerminalSurface className="flex flex-wrap items-center gap-x-4 gap-y-1 p-3 text-xs text-muted-foreground">
                      <Database className="h-4 w-4" />
                      <span>{t("provenance", { provider: payload.series.provider ?? t("unavailable"), adjustment: payload.series.adjustment ?? t("unavailable") })}</span>
                      <span>{t("coverage", { firstDate: payload.series.firstDate, lastDate: payload.series.lastDate, count: payload.series.barCount })}</span>
                    </FinancialTerminalSurface>
                    <AdvancedCandlestickChart data={payload.series.items} symbol={`${payload.selected.market}:${payload.selected.symbol}`} height={430} />
                  </FinancialTerminalCardContent>
                </FinancialTerminalCard>
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
