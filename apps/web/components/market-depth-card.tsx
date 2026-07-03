"use client";

import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  InstrumentLargeOrderItem,
  InstrumentMarketDepthLevel,
  InstrumentMarketDepthPayload,
  InstrumentRecentTradeItem,
} from "@/lib/instrument-detail";

type MarketDepthCardProps = {
  marketDepth?: InstrumentMarketDepthPayload | null;
  className?: string;
};

type MarketDepthStatus = InstrumentMarketDepthPayload["status"];

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function getStatusBadgeVariant(status: MarketDepthStatus): "default" | "secondary" | "outline" {
  if (status === "ok") {
    return "default";
  }
  if (status === "no_data") {
    return "secondary";
  }
  return "outline";
}

function getStatusLabel(status: MarketDepthStatus, t: ReturnType<typeof useTranslations>): string {
  if (status === "ok") {
    return t("marketDepthStatusOk");
  }
  if (status === "no_data") {
    return t("marketDepthStatusNoData");
  }
  return t("marketDepthStatusDegraded");
}

function formatNumber(
  value: number | null | undefined,
  locale: string,
  unavailableLabel: string,
  maximumFractionDigits = 2,
): string {
  if (!isFiniteNumber(value)) {
    return unavailableLabel;
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits,
  }).format(value);
}

function formatMarketDepthLevelValue(
  value: number | null | undefined,
  locale: string,
  unavailableLabel: string,
): string {
  return formatNumber(value, locale, unavailableLabel, 4);
}

function renderMarketDepthRows({
  levels,
  locale,
  unavailableLabel,
  emptyLabel,
}: {
  levels: InstrumentMarketDepthLevel[];
  locale: string;
  unavailableLabel: string;
  emptyLabel: string;
}) {
  if (levels.length === 0) {
    return (
      <TableRow>
        <TableCell colSpan={4} className="text-center text-muted-foreground">
          {emptyLabel}
        </TableCell>
      </TableRow>
    );
  }

  return levels.map((level, levelIndex) => (
    <TableRow key={`${level.price ?? "level"}-${levelIndex}`}>
      <TableCell className="font-medium">{formatMarketDepthLevelValue(level.price, locale, unavailableLabel)}</TableCell>
      <TableCell>{formatNumber(level.volume, locale, unavailableLabel, 0)}</TableCell>
      <TableCell>{formatNumber(level.amount, locale, unavailableLabel, 2)}</TableCell>
      <TableCell>{formatNumber(level.order_count, locale, unavailableLabel, 0)}</TableCell>
    </TableRow>
  ));
}

function renderRecentTradeRows({
  trades,
  locale,
  unavailableLabel,
  emptyLabel,
}: {
  trades: InstrumentRecentTradeItem[];
  locale: string;
  unavailableLabel: string;
  emptyLabel: string;
}) {
  if (trades.length === 0) {
    return (
      <TableRow>
        <TableCell colSpan={5} className="text-center text-muted-foreground">
          {emptyLabel}
        </TableCell>
      </TableRow>
    );
  }

  return trades.map((trade, tradeIndex) => (
    <TableRow key={`${trade.timestamp ?? "trade"}-${tradeIndex}`}>
      <TableCell>{trade.timestamp ?? unavailableLabel}</TableCell>
      <TableCell>{trade.side ?? unavailableLabel}</TableCell>
      <TableCell className="font-medium">{formatMarketDepthLevelValue(trade.price, locale, unavailableLabel)}</TableCell>
      <TableCell>{formatNumber(trade.volume, locale, unavailableLabel, 0)}</TableCell>
      <TableCell>{formatNumber(trade.amount, locale, unavailableLabel, 2)}</TableCell>
    </TableRow>
  ));
}

function renderLargeOrderRows({
  largeOrders,
  locale,
  unavailableLabel,
  emptyLabel,
}: {
  largeOrders: InstrumentLargeOrderItem[];
  locale: string;
  unavailableLabel: string;
  emptyLabel: string;
}) {
  if (largeOrders.length === 0) {
    return (
      <TableRow>
        <TableCell colSpan={5} className="text-center text-muted-foreground">
          {emptyLabel}
        </TableCell>
      </TableRow>
    );
  }

  return largeOrders.map((largeOrder, largeOrderIndex) => (
    <TableRow key={`${largeOrder.timestamp ?? "large-order"}-${largeOrderIndex}`}>
      <TableCell>{largeOrder.timestamp ?? unavailableLabel}</TableCell>
      <TableCell>{largeOrder.side ?? unavailableLabel}</TableCell>
      <TableCell className="font-medium">{formatMarketDepthLevelValue(largeOrder.price, locale, unavailableLabel)}</TableCell>
      <TableCell>{formatNumber(largeOrder.volume, locale, unavailableLabel, 0)}</TableCell>
      <TableCell>{formatNumber(largeOrder.amount, locale, unavailableLabel, 2)}</TableCell>
    </TableRow>
  ));
}

export function MarketDepthCard({ marketDepth, className }: MarketDepthCardProps) {
  const locale = useLocale();
  const t = useTranslations("InstrumentDetail");
  const unavailableLabel = t("unavailableShort");
  const status = marketDepth?.status ?? "degraded";
  const statusLabel = getStatusLabel(status, t);
  const providerLabel = marketDepth?.effective_provider ?? marketDepth?.provider ?? marketDepth?.requested_provider ?? unavailableLabel;
  const availabilityReason = marketDepth?.availability?.reason ?? marketDepth?.order_book?.reason ?? t("marketDepthUnavailable");
  const depthLevels = marketDepth?.order_book.depth_levels ?? 5;
  const bidLevels = (marketDepth?.order_book.bids ?? []).slice(0, depthLevels);
  const askLevels = (marketDepth?.order_book.asks ?? []).slice(0, depthLevels);
  const recentTrades = marketDepth?.recent_trades.items ?? [];
  const largeOrders = marketDepth?.large_orders.items ?? [];
  const thresholdAmount = marketDepth?.large_orders.threshold_amount ?? null;
  const fundFlow = marketDepth?.fund_flow;
  const capabilities = marketDepth?.availability?.capabilities;

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>{t("marketDepthTitle")}</CardTitle>
            <CardDescription>{t("marketDepthDescription")}</CardDescription>
          </div>
          <Badge variant={getStatusBadgeVariant(status)}>{statusLabel}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 text-sm text-muted-foreground md:grid-cols-3">
          <div>
            <span className="font-medium text-foreground">{t("marketDepthProvider")}: </span>
            {providerLabel}
          </div>
          <div>
            <span className="font-medium text-foreground">{t("marketDepthAsOf")}: </span>
            {marketDepth?.as_of ?? unavailableLabel}
          </div>
          <div>
            <span className="font-medium text-foreground">{t("marketDepthDelay")}: </span>
            {marketDepth?.is_realtime
              ? t("marketDepthRealtime")
              : marketDepth?.is_delayed
                ? t("marketDepthDelayed", { minutes: marketDepth.delay_minutes ?? 0 })
                : unavailableLabel}
          </div>
        </div>

        <p className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">{availabilityReason}</p>

        {capabilities ? (
          <div className="flex flex-wrap gap-2" aria-label={t("marketDepthCapabilities")}>
            {Object.entries(capabilities).map(([capabilityName, isAvailable]) => (
              <Badge key={capabilityName} variant={isAvailable ? "default" : "outline"}>
                {t(`marketDepthCapability${capabilityName}` as never)}: {isAvailable ? t("marketDepthCapabilityAvailable") : t("marketDepthCapabilityUnavailable")}
              </Badge>
            ))}
          </div>
        ) : null}

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-semibold">{t("marketDepthOrderBookTitle")}</h3>
            <span className="text-sm text-muted-foreground">
              {t("marketDepthLevels", { count: depthLevels })}
            </span>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-green-600">{t("marketDepthBids")}</h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("marketDepthPrice")}</TableHead>
                    <TableHead>{t("marketDepthVolume")}</TableHead>
                    <TableHead>{t("marketDepthAmount")}</TableHead>
                    <TableHead>{t("marketDepthOrders")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {renderMarketDepthRows({
                    levels: bidLevels,
                    locale,
                    unavailableLabel,
                    emptyLabel: t("marketDepthNoOrderBook"),
                  })}
                </TableBody>
              </Table>
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-red-600">{t("marketDepthAsks")}</h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("marketDepthPrice")}</TableHead>
                    <TableHead>{t("marketDepthVolume")}</TableHead>
                    <TableHead>{t("marketDepthAmount")}</TableHead>
                    <TableHead>{t("marketDepthOrders")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {renderMarketDepthRows({
                    levels: askLevels,
                    locale,
                    unavailableLabel,
                    emptyLabel: t("marketDepthNoOrderBook"),
                  })}
                </TableBody>
              </Table>
            </div>
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="text-base font-semibold">{t("marketDepthRecentTradesTitle")}</h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("marketDepthTime")}</TableHead>
                <TableHead>{t("marketDepthSide")}</TableHead>
                <TableHead>{t("marketDepthPrice")}</TableHead>
                <TableHead>{t("marketDepthVolume")}</TableHead>
                <TableHead>{t("marketDepthAmount")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {renderRecentTradeRows({
                trades: recentTrades,
                locale,
                unavailableLabel,
                emptyLabel: t("marketDepthNoRecentTrades"),
              })}
            </TableBody>
          </Table>
        </section>

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-semibold">{t("marketDepthLargeOrdersTitle")}</h3>
            <span className="text-sm text-muted-foreground">
              {t("marketDepthLargeOrderThreshold", {
                amount: formatNumber(thresholdAmount, locale, unavailableLabel, 2),
              })}
            </span>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("marketDepthTime")}</TableHead>
                <TableHead>{t("marketDepthSide")}</TableHead>
                <TableHead>{t("marketDepthPrice")}</TableHead>
                <TableHead>{t("marketDepthVolume")}</TableHead>
                <TableHead>{t("marketDepthAmount")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {renderLargeOrderRows({
                largeOrders,
                locale,
                unavailableLabel,
                emptyLabel: t("marketDepthNoLargeOrders"),
              })}
            </TableBody>
          </Table>
        </section>

        <section className="space-y-3">
          <h3 className="text-base font-semibold">{t("marketDepthFundFlowTitle")}</h3>
          <div className="grid gap-3 text-sm md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-md border p-3">
              <div className="text-muted-foreground">{t("marketDepthNetInflow")}</div>
              <div className="font-semibold">{formatNumber(fundFlow?.net_inflow, locale, unavailableLabel, 2)}</div>
            </div>
            <div className="rounded-md border p-3">
              <div className="text-muted-foreground">{t("marketDepthMainNetInflow")}</div>
              <div className="font-semibold">{formatNumber(fundFlow?.main_net_inflow, locale, unavailableLabel, 2)}</div>
            </div>
            <div className="rounded-md border p-3">
              <div className="text-muted-foreground">{t("marketDepthRetailNetInflow")}</div>
              <div className="font-semibold">{formatNumber(fundFlow?.retail_net_inflow, locale, unavailableLabel, 2)}</div>
            </div>
            <div className="rounded-md border p-3">
              <div className="text-muted-foreground">{t("marketDepthSourceDefinition")}</div>
              <div className="font-semibold">{fundFlow?.source_definition ?? unavailableLabel}</div>
            </div>
          </div>
        </section>
      </CardContent>
    </Card>
  );
}
