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

async function fetchWatchlist(): Promise<WatchlistPayload> {
  const response = await backendFetch("/watchlist");
  if (!response.ok) {
    return { name: "default", source: "error", items: [] };
  }
  return response.json() as Promise<WatchlistPayload>;
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
  const payload = await fetchWatchlist();
  const t = await getTranslations("Watchlist");

  return (
    <div className="space-y-6">
      {op === "added" ? <FlashBanner variant="success" message={t("addSuccess")} /> : null}
      {op === "removed" ? <FlashBanner variant="success" message={t("removeSuccess")} /> : null}
      {op === "alerts_updated" ? <FlashBanner variant="success" message={t("updateAlertSuccess")} /> : null}
      {op === "error" ? (
        <FlashBanner variant="error" message={t("operationFailed", { reason: reason ?? "unknown" })} />
      ) : null}

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <WatchlistAddForm locale={locale} className="w-full md:w-auto" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{payload.items.length} items in your watchlist.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("symbol")}</TableHead>
                <TableHead>{t("name")}</TableHead>
                <TableHead>{t("market")}</TableHead>
                <TableHead>{t("price")}</TableHead>
                <TableHead>{t("rsi")}</TableHead>
                <TableHead>{t("alertRules")}</TableHead>
                <TableHead className="text-right">{t("actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payload.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <EmptyState title={t("noData")} description={t("emptyHint")} />
                  </TableCell>
                </TableRow>
              ) : (
                payload.items.map((item) => (
                  <TableRow key={`${item.market}-${item.symbol}`}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Link href={`/instruments/${item.symbol}` as any} className="hover:underline">
                          {item.symbol}
                        </Link>
                        {item.alert_status?.triggered ? (
                          <Badge variant="destructive">{t("alertTriggered")}</Badge>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>{item.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{item.market}</Badge>
                    </TableCell>
                    <TableCell>
                      {item.latest_price !== undefined && item.latest_price !== null ? (
                        <span className="font-medium">${item.latest_price.toFixed(2)}</span>
                      ) : (
                        <span className="text-muted-foreground">{t("priceUnavailable")}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {item.rsi !== undefined && item.rsi !== null ? (
                        <span>{item.rsi.toFixed(1)}</span>
                      ) : (
                        <span className="text-muted-foreground">{t("rsiUnavailable")}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="space-y-2">
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
                        ) : null}
                        <WatchlistEditAlertRulesForm
                          locale={locale}
                          symbol={item.symbol}
                          market={item.market}
                          name={item.name}
                          alertRules={item.alert_rules}
                        />
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="icon" asChild>
                          <Link href={`/instruments/${item.symbol}` as any} title={t("viewDetails")}>
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
    </div>
  );
}
