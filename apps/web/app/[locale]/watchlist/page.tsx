import { getTranslations } from "next-intl/server";
import { Link } from "@/src/i18n/routing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExternalLink } from "lucide-react";
import { FlashBanner } from "@/components/flash-banner";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import {
  WatchlistAddForm,
  WatchlistEditAlertRulesForm,
  WatchlistRemoveButton,
} from "@/components/watchlist-forms";
import { backendFetch } from "@/lib/backend-api";

type AlertRuleStatus = {
  key: string;
  threshold: number;
  value?: number | null;
  triggered: boolean;
};

type WatchlistItem = {
  symbol: string;
  market: string;
  name: string;
  is_active: boolean;
  alert_rules?: Record<string, number>;
  latest_price?: number | null;
  rsi?: number | null;
  alert_status?: {
    triggered: boolean;
    rules: AlertRuleStatus[];
  };
};

type WatchlistPayload = {
  name: string;
  source: string;
  items: WatchlistItem[];
};

type WatchlistLoadResult =
  | { status: "loaded"; payload: WatchlistPayload }
  | { status: "failed" };

const MARKET_CURRENCY = {
  CN: "CNY",
  HK: "HKD",
  US: "USD",
} as const;

async function fetchWatchlist(): Promise<WatchlistLoadResult> {
  try {
    const response = await backendFetch("/watchlist");
    if (!response.ok) {
      return { status: "failed" };
    }

    return {
      status: "loaded",
      payload: (await response.json()) as WatchlistPayload,
    };
  } catch {
    return { status: "failed" };
  }
}

function hasAvailablePrice(price: number | null | undefined): price is number {
  return typeof price === "number" && Number.isFinite(price);
}

function formatWatchlistPrice(price: number, market: string, locale: string): string {
  const normalizedMarket = market.trim().toUpperCase() as keyof typeof MARKET_CURRENCY;
  const currency = MARKET_CURRENCY[normalizedMarket];

  return new Intl.NumberFormat(
    locale,
    currency
      ? { style: "currency", currency }
      : { minimumFractionDigits: 2, maximumFractionDigits: 2 },
  ).format(price);
}

function formatRuleLabel(
  rule: AlertRuleStatus,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  if (rule.key === "price_above") {
    return t("priceAboveRule", { value: rule.threshold });
  }
  if (rule.key === "rsi_below") {
    return t("rsiBelowRule", { value: rule.threshold });
  }
  return `${rule.key} ${rule.threshold}`;
}

export default async function WatchlistPage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<{ op?: string; reason?: string }>;
}) {
  const { locale } = await params;
  const { op, reason } = await searchParams;
  const watchlistResult = await fetchWatchlist();
  const t = await getTranslations("Watchlist");
  const payload = watchlistResult.status === "loaded" ? watchlistResult.payload : null;
  const summaryMetrics = payload
    ? [
        {
          label: t("summaryTotal"),
          value: payload.items.length,
          description: t("summarySource", { source: payload.source }),
        },
        {
          label: t("summaryActive"),
          value: payload.items.filter((item) => item.is_active).length,
          description: t("summaryMarkets", {
            count: new Set(payload.items.map((item) => item.market)).size,
          }),
        },
        {
          label: t("summaryTriggered"),
          value: payload.items.filter((item) => item.alert_status?.triggered).length,
          description: t("alertRules"),
        },
        {
          label: t("summaryPriced"),
          value: payload.items.filter((item) => hasAvailablePrice(item.latest_price)).length,
          description: t("price"),
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {op === "added" ? <FlashBanner variant="success" message={t("addSuccess")} /> : null}
      {op === "removed" ? <FlashBanner variant="success" message={t("removeSuccess")} /> : null}
      {op === "alerts_updated" ? <FlashBanner variant="success" message={t("updateAlertSuccess")} /> : null}
      {op === "error" ? (
        <FlashBanner variant="error" message={t("operationFailed", { reason: reason ?? "unknown" })} />
      ) : null}

      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={
          payload
            ? [
                { label: t("summaryTotal"), variant: "secondary" },
                { label: t("summarySource", { source: payload.source }) },
              ]
            : [{ label: t("loadFailedTitle"), variant: "destructive" }]
        }
        metrics={summaryMetrics}
      />

      <Card className="overflow-hidden rounded-md border-primary/10 shadow-none">
        <CardHeader className="border-b bg-muted/20 p-3">
          <CardTitle>{t("title")}</CardTitle>
          {payload ? (
            <CardDescription>{t("itemsCount", { count: payload.items.length })}</CardDescription>
          ) : null}
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="h-9 px-3 text-xs">{t("symbol")}</TableHead>
                <TableHead className="h-9 px-3 text-xs">{t("name")}</TableHead>
                <TableHead className="h-9 px-3 text-xs">{t("market")}</TableHead>
                <TableHead className="h-9 px-3 text-right text-xs">{t("price")}</TableHead>
                <TableHead className="h-9 px-3 text-right text-xs">{t("rsi")}</TableHead>
                <TableHead className="h-9 px-3 text-xs">{t("alertRules")}</TableHead>
                <TableHead className="h-9 px-3 text-right text-xs">{t("actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {watchlistResult.status === "failed" ? (
                <TableRow>
                  <TableCell colSpan={7} className="p-6">
                    <div className="space-y-4">
                      <ErrorState
                        title={t("loadFailedTitle")}
                        description={t("loadFailedDescription")}
                      />
                      <div className="flex justify-center">
                        <Button size="sm" variant="outline" asChild>
                          <Link href="/watchlist">{t("reload")}</Link>
                        </Button>
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              ) : watchlistResult.payload.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="p-6">
                    <div className="space-y-4">
                      <EmptyState title={t("noData")} description={t("emptyHint")} />
                      <div className="flex flex-wrap justify-center gap-2">
                        <Button size="sm" asChild>
                          <Link href="/ai-research">{t("discoverCandidates")}</Link>
                        </Button>
                        <Button size="sm" variant="outline" asChild>
                          <Link href="/instruments">{t("browseInstruments")}</Link>
                        </Button>
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                watchlistResult.payload.items.map((item) => (
                  <TableRow key={`${item.market}-${item.symbol}`} className="hover:bg-muted/30">
                    <TableCell className="px-3 py-2 font-medium">
                      <div className="flex items-center gap-2">
                        <Link
                          href={
                            `/instruments/${encodeURIComponent(item.symbol)}?market=${encodeURIComponent(item.market)}` as any
                          }
                          className="hover:underline"
                        >
                          {item.symbol}
                        </Link>
                        {item.alert_status?.triggered ? (
                          <Badge variant="destructive">{t("alertTriggered")}</Badge>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="px-3 py-2 text-sm text-muted-foreground">{item.name}</TableCell>
                    <TableCell className="px-3 py-2">
                      <Badge variant="outline">{item.market}</Badge>
                    </TableCell>
                    <TableCell className="px-3 py-2 text-right font-mono">
                      {hasAvailablePrice(item.latest_price) ? (
                        <span className="font-medium">
                          {formatWatchlistPrice(item.latest_price, item.market, locale)}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">{t("priceUnavailable")}</span>
                      )}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-right font-mono">
                      {item.rsi !== undefined && item.rsi !== null ? (
                        <span>{item.rsi.toFixed(1)}</span>
                      ) : (
                        <span className="text-muted-foreground">{t("rsiUnavailable")}</span>
                      )}
                    </TableCell>
                    <TableCell className="px-3 py-2">
                      {item.alert_status?.rules?.length ? (
                        <div className="flex flex-wrap gap-1">
                          {item.alert_status.rules.map((rule) => (
                            <Badge
                              key={`${item.symbol}-${rule.key}`}
                              variant={rule.triggered ? "destructive" : "secondary"}
                            >
                              {formatRuleLabel(rule, t)}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">{t("noAlertRules")}</span>
                      )}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="icon" asChild>
                          <Link
                            href={
                              `/instruments/${encodeURIComponent(item.symbol)}?market=${encodeURIComponent(item.market)}` as any
                            }
                            title={t("viewDetails")}
                          >
                            <ExternalLink className="h-4 w-4" />
                            <span className="sr-only">{t("viewDetails")}</span>
                          </Link>
                        </Button>
                        <WatchlistRemoveButton locale={locale} symbol={item.symbol} market={item.market} />
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <details className="rounded-md border border-dashed border-border/80 bg-card/95 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-foreground">
          {t("advancedControls")}
        </summary>
        <div className="mt-4 space-y-4">
          <div className="flex flex-col gap-3 border-b border-border/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
            <WatchlistAddForm locale={locale} className="w-full lg:max-w-3xl" />
            <Button size="sm" variant="outline" asChild>
              <Link href="/alerts">{t("viewAlertHistory")}</Link>
            </Button>
          </div>
          {payload && payload.items.length > 0 ? (
            <div className="grid gap-3 xl:grid-cols-2">
              {payload.items.map((item) => (
                <div
                  key={`alert-editor-${item.market}-${item.symbol}`}
                  className="space-y-3 rounded-md border border-border/70 bg-background/60 p-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-mono text-sm font-semibold">{item.symbol}</div>
                      <div className="text-xs text-muted-foreground">{item.name}</div>
                    </div>
                    <Badge variant="outline">{item.market}</Badge>
                  </div>
                  <WatchlistEditAlertRulesForm
                    locale={locale}
                    symbol={item.symbol}
                    market={item.market}
                    name={item.name}
                    alertRules={item.alert_rules}
                  />
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </details>
    </div>
  );
}
