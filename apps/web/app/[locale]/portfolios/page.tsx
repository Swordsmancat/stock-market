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
import { Briefcase } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { FlashBanner } from "@/components/flash-banner";
import {
  PortfolioAddPositionForm,
  PortfolioCreateForm,
  PortfolioDeleteButton,
  PortfolioRemovePositionButton,
  PortfolioRenameForm,
} from "@/components/portfolio-forms";
import { backendFetch } from "@/lib/backend-api";

type PortfolioPosition = {
  symbol: string;
  market: string;
  quantity: number;
  avg_cost: number;
  latest_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_return_pct?: number;
  weight?: number;
};

type PortfolioPayload = {
  id: string;
  name: string;
  base_currency: string;
  source: string;
  is_default?: boolean;
  summary?: {
    total_cost: number;
    total_market_value: number;
    unrealized_pnl: number;
    unrealized_return_pct: number;
  };
  positions: PortfolioPosition[];
  recommendation?: {
    status: string;
    risk_summary: string;
    actions: Array<{ symbol: string; action: string; target_weight: number; reason: string }>;
  };
};

type PortfolioListPayload = {
  items: Array<{ id: string; name: string; base_currency: string; is_default?: boolean }>;
};

function withComputedPositionMetrics(
  pos: PortfolioPosition,
  totalValue: number,
): PortfolioPosition {
  const quantity = pos.quantity ?? 0;
  const avgCost = pos.avg_cost ?? 0;
  const latestPrice = pos.latest_price ?? avgCost;
  const marketValue = pos.market_value ?? latestPrice * quantity;
  const costBasis = avgCost * quantity;
  const unrealizedPnl = pos.unrealized_pnl ?? marketValue - costBasis;
  const unrealizedReturnPct =
    pos.unrealized_return_pct ?? (costBasis ? unrealizedPnl / costBasis : 0);
  const weight = pos.weight ?? (totalValue ? marketValue / totalValue : 0);

  return {
    ...pos,
    quantity,
    avg_cost: avgCost,
    latest_price: latestPrice,
    market_value: marketValue,
    unrealized_pnl: unrealizedPnl,
    unrealized_return_pct: unrealizedReturnPct,
    weight,
  };
}

async function fetchPortfolio(portfolioId: string): Promise<PortfolioPayload | null> {
  const response = await backendFetch(`/portfolios/${portfolioId}`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return response.json() as Promise<PortfolioPayload>;
}

async function fetchPortfolioList(): Promise<PortfolioListPayload> {
  const response = await backendFetch(`/portfolios`, { cache: "no-store" });
  if (!response.ok) {
    return { items: [] };
  }
  return response.json() as Promise<PortfolioListPayload>;
}

export default async function PortfoliosPage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<{ portfolio?: string; op?: string; reason?: string }>;
} = {}) {
  const { locale } = await params;
  const query = await searchParams;
  const selectedPortfolioId = query.portfolio ?? "demo";
  const { op, reason } = query;
  const [payload, portfolioList] = await Promise.all([
    fetchPortfolio(selectedPortfolioId),
    fetchPortfolioList(),
  ]);
  const t = await getTranslations("Portfolios");

  const positions = payload?.positions ?? [];
  const totalValue =
    payload?.summary?.total_market_value ??
    positions.reduce((sum, pos) => sum + (pos.market_value ?? 0), 0);
  const totalCost =
    payload?.summary?.total_cost ??
    positions.reduce((sum, pos) => sum + (pos.avg_cost ?? 0) * (pos.quantity ?? 0), 0);
  const unrealizedPnl = payload?.summary?.unrealized_pnl ?? totalValue - totalCost;
  const unrealizedReturnPct =
    payload?.summary?.unrealized_return_pct ?? (totalCost ? unrealizedPnl / totalCost : 0);

  return (
    <div className="space-y-6">
      {op === "created" ? <FlashBanner variant="success" message={t("createSuccess")} /> : null}
      {op === "position_added" ? <FlashBanner variant="success" message={t("addPositionSuccess")} /> : null}
      {op === "position_removed" ? <FlashBanner variant="success" message={t("removePositionSuccess")} /> : null}
      {op === "renamed" ? <FlashBanner variant="success" message={t("renameSuccess")} /> : null}
      {op === "deleted" ? <FlashBanner variant="success" message={t("deleteSuccess")} /> : null}
      {op === "error" ? (
        <FlashBanner variant="error" message={t("operationFailedDetail", { reason: reason ?? "unknown" })} />
      ) : null}

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <PortfolioCreateForm locale={locale} className="w-full md:w-auto" />
      </div>

      {portfolioList.items.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("portfolioList")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {portfolioList.items.map((portfolio) => (
              <Button
                key={portfolio.id}
                variant={portfolio.id === selectedPortfolioId ? "default" : "outline"}
                size="sm"
                asChild
              >
                <Link href={`/portfolios?portfolio=${portfolio.id}` as any}>{portfolio.name}</Link>
              </Button>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {!payload ? (
        <Card>
          <CardContent className="pt-6">
            <ErrorState title={t("loadFailed")} description={t("emptyHint")} />
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <PortfolioRenameForm
              locale={locale}
              portfolioId={payload.id}
              currentName={payload.name}
              isDefault={payload.is_default ?? payload.id === "demo"}
            />
            <PortfolioDeleteButton
              locale={locale}
              portfolioId={payload.id}
              isDefault={payload.is_default ?? payload.id === "demo"}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{t("totalValue")}</CardTitle>
                <Briefcase className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">${totalValue.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  {t("baseCurrency", { currency: payload.base_currency })}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{t("unrealizedPnl")}</CardTitle>
                <Briefcase className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div
                  className={
                    unrealizedPnl < 0
                      ? "text-2xl font-bold text-destructive"
                      : "text-2xl font-bold text-emerald-600"
                  }
                >
                  ${unrealizedPnl.toLocaleString()}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{t("returnPct")}</CardTitle>
                <Briefcase className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div
                  className={
                    unrealizedReturnPct < 0
                      ? "text-2xl font-bold text-destructive"
                      : "text-2xl font-bold text-emerald-600"
                  }
                >
                  {(unrealizedReturnPct * 100).toFixed(2)}%
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t("positions")}</CardTitle>
              <CardDescription>{payload.name}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <PortfolioAddPositionForm locale={locale} portfolioId={payload.id} />
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("symbol")}</TableHead>
                    <TableHead>{t("market")}</TableHead>
                    <TableHead className="text-right">{t("quantity")}</TableHead>
                    <TableHead className="text-right">{t("averageCost")}</TableHead>
                    <TableHead className="text-right">{t("marketValue")}</TableHead>
                    <TableHead className="text-right">{t("unrealizedPnl")}</TableHead>
                    <TableHead className="text-right">{t("returnPct")}</TableHead>
                    <TableHead className="text-right">{t("weight")}</TableHead>
                    <TableHead className="text-right">{t("actions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {positions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9}>
                        <EmptyState title={t("noData")} description={t("emptyHint")} />
                      </TableCell>
                    </TableRow>
                  ) : (
                    positions.map((rawPos) => {
                      const pos = withComputedPositionMetrics(rawPos, totalValue);
                      return (
                        <TableRow key={`${pos.market}-${pos.symbol}`}>
                          <TableCell className="font-medium">
                            <Link href={`/instruments/${pos.symbol}` as any} className="hover:underline">
                              {pos.symbol}
                            </Link>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{pos.market}</Badge>
                          </TableCell>
                          <TableCell className="text-right">{pos.quantity}</TableCell>
                          <TableCell className="text-right">${pos.avg_cost.toFixed(2)}</TableCell>
                          <TableCell className="text-right font-medium">
                            ${pos.market_value.toLocaleString()}
                          </TableCell>
                          <TableCell
                            className={
                              pos.unrealized_pnl < 0
                                ? "text-right text-destructive"
                                : "text-right text-emerald-600"
                            }
                          >
                            ${pos.unrealized_pnl.toLocaleString()}
                          </TableCell>
                          <TableCell
                            className={
                              pos.unrealized_return_pct < 0
                                ? "text-right text-destructive"
                                : "text-right text-emerald-600"
                            }
                          >
                            {(pos.unrealized_return_pct * 100).toFixed(2)}%
                          </TableCell>
                          <TableCell className="text-right">
                            {(pos.weight * 100).toFixed(2)}%
                          </TableCell>
                          <TableCell className="text-right">
                            <PortfolioRemovePositionButton
                              locale={locale}
                              portfolioId={payload.id}
                              symbol={pos.symbol}
                              market={pos.market}
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {payload.recommendation ? (
            <Card>
              <CardHeader>
                <CardTitle>{t("recommendation")}</CardTitle>
                <CardDescription>{payload.recommendation.risk_summary}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {payload.recommendation.actions.map((action) => (
                    <div key={action.symbol} className="flex flex-wrap items-center gap-2 text-sm">
                      <Badge variant="outline">{action.symbol}</Badge>
                      <span>{action.action}</span>
                      <span className="text-muted-foreground">
                        {(action.target_weight * 100).toFixed(1)}% — {action.reason}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : null}
        </>
      )}
    </div>
  );
}
