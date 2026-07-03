import { Activity, FileText, Settings } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { withProviderQuery } from "@/lib/market-data";
import { getPlatformSettings } from "@/lib/platform-settings-store";
import { Link } from "@/src/i18n/routing";

const MAX_LATEST_DAILY_BAR_REQUESTS = 25;
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

type InstrumentsLoadResult =
  | { status: "loaded"; payload: InstrumentsPayload }
  | { status: "failed" };

type LatestDailyBarLoadResult =
  | { status: "loaded"; payload: LatestDailyBarPayload }
  | { status: "failed" };

type FreshnessStatus = "fresh" | "stale" | "no_data" | "unavailable";

type LatestDailyBarHealthCounts = Record<FreshnessStatus, number>;

type InstrumentsPageProps = {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<{
    q?: string;
    market?: string;
  }>;
};

async function fetchInstrumentsPayload(searchParams: { q?: string; market?: string }): Promise<InstrumentsLoadResult> {
  const upstreamParams = new URLSearchParams();
  const query = searchParams.q?.trim();
  const market = searchParams.market?.trim();

  if (query) {
    upstreamParams.set("q", query);
  }
  if (market) {
    upstreamParams.set("market", market);
  }

  const queryString = upstreamParams.toString();
  const requestPath = queryString ? `/instruments?${queryString}` : "/instruments";

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

async function fetchLatestDailyBar(
  symbol: string,
  provider: string,
): Promise<LatestDailyBarLoadResult> {
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
      payload: (await response.json()) as LatestDailyBarPayload,
    };
  } catch {
    return { status: "failed" };
  }
}

function getCurrencyCode(instrument: Instrument): string {
  const normalizedCurrency = instrument.currency?.trim().toUpperCase();
  return normalizedCurrency && /^[A-Z]{3}$/.test(normalizedCurrency) ? normalizedCurrency : "USD";
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

function parseLatestTimestamp(latestDailyBar: LatestDailyBarLoadResult): Date | null {
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
  return parsedTimestamp === null ? unavailableLabel : parsedTimestamp.toLocaleDateString(locale);
}

function getFreshnessStatus(latestDailyBar: LatestDailyBarLoadResult): FreshnessStatus {
  if (latestDailyBar.status === "failed") {
    return "unavailable";
  }

  if (latestDailyBar.payload.status === "no_data" || latestDailyBar.payload.item == null) {
    return "no_data";
  }

  const parsedTimestamp = parseLatestTimestamp(latestDailyBar);
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

function countLatestDailyBarHealth(latestDailyBars: LatestDailyBarLoadResult[]): LatestDailyBarHealthCounts {
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

function getLatestSource(latestDailyBar: LatestDailyBarLoadResult, instrument: Instrument): string {
  if (latestDailyBar.status === "failed") {
    return "unavailable";
  }
  return latestDailyBar.payload.source || instrument.source || "unavailable";
}

function getLatestProvider(latestDailyBar: LatestDailyBarLoadResult): string | null {
  if (latestDailyBar.status === "failed") {
    return null;
  }
  return latestDailyBar.payload.effective_provider ?? latestDailyBar.payload.provider ?? null;
}

function getLatestAvailabilityLabel(
  latestDailyBar: LatestDailyBarLoadResult,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string | null {
  if (latestDailyBar.status === "failed") {
    return t("latestUnavailable");
  }
  if (latestDailyBar.payload.status === "no_data" || latestDailyBar.payload.item == null) {
    return t("noLatestDailyBar");
  }
  return null;
}

export default async function InstrumentsPage({
  params,
  searchParams = Promise.resolve({}),
}: InstrumentsPageProps) {
  const [{ locale }, resolvedSearchParams] = await Promise.all([params, searchParams]);
  const [t, platformSettings, instrumentsResult] = await Promise.all([
    getTranslations("Instruments"),
    getPlatformSettings(),
    fetchInstrumentsPayload(resolvedSearchParams),
  ]);

  const activeProvider = platformSettings.market_data_provider;

  if (instrumentsResult.status === "failed") {
    return (
      <div className="space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
            <p className="text-muted-foreground">{t("description")}</p>
          </div>
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
        </div>
        <Card>
          <CardContent className="pt-6">
            <ErrorState title={t("loadFailed")} description={t("loadFailedHint")} />
          </CardContent>
        </Card>
      </div>
    );
  }

  const instruments = instrumentsResult.payload.items;
  const visibleInstruments = instruments.slice(0, MAX_LATEST_DAILY_BAR_REQUESTS);
  const latestDailyBars = await Promise.all(
    visibleInstruments.map((instrument) => fetchLatestDailyBar(instrument.symbol, activeProvider)),
  );
  const latestDailyBarHealthCounts = countLatestDailyBarHealth(latestDailyBars);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">{t("dataSource", { source: instrumentsResult.payload.source })}</Badge>
            <Badge variant="outline">{t("activeProvider", { provider: activeProvider })}</Badge>
          </div>
        </div>
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
      </div>

      <Card>
        <CardContent className="pt-6">
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
              className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("healthSummaryTitle")}</CardTitle>
          <CardDescription>
            {t("healthSummaryDesc", {
              visible: visibleInstruments.length,
              total: instruments.length,
              provider: activeProvider,
            })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-lg border p-3">
              <div className="text-xs text-muted-foreground">{t("visibleInstruments")}</div>
              <div className="text-2xl font-bold">{visibleInstruments.length}</div>
            </div>
            <div className="rounded-lg border p-3">
              <div className="text-xs text-muted-foreground">{t("fresh")}</div>
              <div className="text-2xl font-bold">{latestDailyBarHealthCounts.fresh}</div>
            </div>
            <div className="rounded-lg border p-3">
              <div className="text-xs text-muted-foreground">{t("stale")}</div>
              <div className="text-2xl font-bold">{latestDailyBarHealthCounts.stale}</div>
            </div>
            <div className="rounded-lg border p-3">
              <div className="text-xs text-muted-foreground">{t("no_data")}</div>
              <div className="text-2xl font-bold">{latestDailyBarHealthCounts.no_data}</div>
            </div>
            <div className="rounded-lg border p-3">
              <div className="text-xs text-muted-foreground">{t("unavailable")}</div>
              <div className="text-2xl font-bold">{latestDailyBarHealthCounts.unavailable}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("tableTitle")}</CardTitle>
          <CardDescription>
            {t("tableDescription", {
              visible: visibleInstruments.length,
              total: instruments.length,
            })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {instruments.length === 0 ? (
            <EmptyState title={t("noData")} description={t("emptyHint")} />
          ) : (
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
                  const latestAvailabilityLabel = getLatestAvailabilityLabel(latestDailyBar, t);
                  const latestProvider = getLatestProvider(latestDailyBar);

                  return (
                    <TableRow key={`${instrument.market}-${instrument.symbol}`}>
                      <TableCell className="font-medium">
                        <Link href={`/instruments/${instrument.symbol}` as any} className="hover:underline">
                          {instrument.symbol}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div>{instrument.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {[instrument.exchange, instrument.asset_type, instrument.currency]
                            .filter(Boolean)
                            .join(" / ")}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{instrument.market}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium">
                          {formatLatestClose(latestDailyBar, instrument, locale, t("unavailableShort"))}
                        </div>
                        {latestAvailabilityLabel ? (
                          <div className="text-xs text-muted-foreground">{latestAvailabilityLabel}</div>
                        ) : null}
                      </TableCell>
                      <TableCell>
                        {formatLatestTimestamp(latestDailyBar, locale, t("unavailableShort"))}
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {t("sourceValue", { source: getLatestSource(latestDailyBar, instrument) })}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {latestProvider
                            ? t("providerValue", { provider: latestProvider })
                            : t("providerUnavailable")}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getFreshnessBadgeVariant(freshnessStatus)}>
                          {t(freshnessStatus)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="sm" asChild>
                            <Link href={`/instruments/${instrument.symbol}` as any}>{t("viewDetails")}</Link>
                          </Button>
                          <Button variant="ghost" size="sm" asChild>
                            <Link href={`/reports?symbol=${encodeURIComponent(instrument.symbol)}` as any}>
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
          )}
        </CardContent>
      </Card>
    </div>
  );
}
