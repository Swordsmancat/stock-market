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
import { Briefcase } from "lucide-react";

type PortfolioPosition = {
  symbol: string;
  market: string;
  quantity: number;
  avg_cost: number;
  latest_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_return_pct: number;
  weight: number;
};

type PortfolioPayload = {
  id: string;
  name: string;
  base_currency: string;
  source: string;
  summary?: {
    total_cost: number;
    total_market_value: number;
    unrealized_pnl: number;
    unrealized_return_pct: number;
  };
  positions: PortfolioPosition[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchDemoPortfolio(): Promise<PortfolioPayload | null> {
  const response = await fetch(`${apiBaseUrl}/portfolios/demo`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return response.json() as Promise<PortfolioPayload>;
}

export default async function PortfoliosPage() {
  const payload = await fetchDemoPortfolio();
  const { getTranslations } = await import("next-intl/server");
  const t = await getTranslations("Portfolios");

  const totalValue =
    payload?.summary?.total_market_value ??
    payload?.positions.reduce((sum, pos) => sum + pos.market_value, 0) ??
    0;
  const totalCost =
    payload?.summary?.total_cost ??
    payload?.positions.reduce((sum, pos) => sum + pos.avg_cost * pos.quantity, 0) ??
    0;
  const unrealizedPnl = payload?.summary?.unrealized_pnl ?? totalValue - totalCost;
  const unrealizedReturnPct =
    payload?.summary?.unrealized_return_pct ?? (totalCost ? unrealizedPnl / totalCost : 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("totalValue")}</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {payload ? `$${totalValue.toLocaleString()}` : "N/A"}
            </div>
            {payload && (
              <p className="text-xs text-muted-foreground">
                Base Currency: {payload.base_currency}
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("unrealizedPnl")}</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={payload && unrealizedPnl < 0 ? "text-2xl font-bold text-destructive" : "text-2xl font-bold text-emerald-600"}>
              {payload ? `$${unrealizedPnl.toLocaleString()}` : "N/A"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t("returnPct")}</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={payload && unrealizedReturnPct < 0 ? "text-2xl font-bold text-destructive" : "text-2xl font-bold text-emerald-600"}>
              {payload ? `${(unrealizedReturnPct * 100).toFixed(2)}%` : "N/A"}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("positions")}</CardTitle>
          <CardDescription>
            {payload?.name ?? "Demo Portfolio"}
          </CardDescription>
        </CardHeader>
        <CardContent>
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
              </TableRow>
            </TableHeader>
            <TableBody>
              {!payload || payload.positions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    {t("noData")}
                  </TableCell>
                </TableRow>
              ) : (
                payload.positions.map((pos) => (
                  <TableRow key={`${pos.market}-${pos.symbol}`}>
                    {/*
                      Derived fallbacks keep the UI compatible with older API processes
                      until the backend server is restarted with the richer payload.
                    */}
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
                    <TableCell className={(pos.unrealized_pnl ?? pos.market_value - pos.avg_cost * pos.quantity) < 0 ? "text-right text-destructive" : "text-right text-emerald-600"}>
                      ${(pos.unrealized_pnl ?? pos.market_value - pos.avg_cost * pos.quantity).toLocaleString()}
                    </TableCell>
                    <TableCell className={(pos.unrealized_return_pct ?? ((pos.market_value - pos.avg_cost * pos.quantity) / (pos.avg_cost * pos.quantity))) < 0 ? "text-right text-destructive" : "text-right text-emerald-600"}>
                      {((pos.unrealized_return_pct ?? ((pos.market_value - pos.avg_cost * pos.quantity) / (pos.avg_cost * pos.quantity))) * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right">
                      {((pos.weight ?? (totalValue ? pos.market_value / totalValue : 0)) * 100).toFixed(2)}%
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
