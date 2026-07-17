import { getTranslations } from "next-intl/server";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
} from "@/components/financial-terminal-section";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { backendFetch } from "@/lib/backend-api";
import {
  decodeMarketMoversPayload,
  type MarketMoversPayload,
} from "@/lib/market-movers";
import { Link } from "@/src/i18n/routing";

type SearchParams = Record<string, string | string[] | undefined>;
type Direction = "gainers" | "losers";
type ExchangeFilter = "all" | "SSE" | "SZSE" | "BSE";
type RowLimit = 10 | 20 | 50;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function parseFilters(searchParams: SearchParams): {
  direction: Direction;
  exchange: ExchangeFilter;
  limit: RowLimit;
} {
  const direction = first(searchParams.direction) === "losers" ? "losers" : "gainers";
  const requestedExchange = first(searchParams.exchange);
  const exchange = (["SSE", "SZSE", "BSE"] as const).includes(
    requestedExchange as "SSE" | "SZSE" | "BSE",
  )
    ? (requestedExchange as ExchangeFilter)
    : "all";
  const requestedLimit = Number(first(searchParams.limit));
  const limit = requestedLimit === 10 || requestedLimit === 50 ? requestedLimit : 20;
  return { direction, exchange, limit };
}

function filterHref(
  current: { direction: Direction; exchange: ExchangeFilter; limit: RowLimit },
  next: Partial<{ direction: Direction; exchange: ExchangeFilter; limit: RowLimit }>,
): string {
  const params = new URLSearchParams({
    direction: next.direction ?? current.direction,
    exchange: next.exchange ?? current.exchange,
    limit: String(next.limit ?? current.limit),
  });
  return `/market-movers?${params.toString()}`;
}

function movementClass(value: number): string {
  if (value > 0) return "text-red-500";
  if (value < 0) return "text-emerald-600";
  return "text-muted-foreground";
}

function signed(value: number, digits = 2): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

async function loadMarketMovers(
  filters: ReturnType<typeof parseFilters>,
): Promise<MarketMoversPayload | null> {
  try {
    const query = new URLSearchParams({
      market: "CN",
      direction: filters.direction,
      exchange: filters.exchange,
      limit: String(filters.limit),
    });
    const response = await backendFetch(`/market-movers?${query.toString()}`, {
      cache: "no-store",
    });
    if (!response.ok) return null;
    return decodeMarketMoversPayload(await response.json());
  } catch {
    return null;
  }
}

export default async function MarketMoversPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const [{ locale }, resolvedSearchParams, t] = await Promise.all([
    params,
    searchParams,
    getTranslations("MarketMovers"),
  ]);
  const filters = parseFilters(resolvedSearchParams);
  const payload = await loadMarketMovers(filters);
  const number = new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", {
    maximumFractionDigits: 2,
  });
  const compact = new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  });

  return (
    <div className="space-y-4">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[
          { label: t("storedBadge"), variant: "secondary" },
          { label: t(filters.direction), variant: "outline" },
        ]}
        metrics={[
          {
            label: t("tradeDate"),
            value: payload?.tradeDate ?? t("unavailable"),
            description: payload?.previousTradeDate
              ? t("comparedWith", { date: payload.previousTradeDate })
              : t("noComparisonDate"),
          },
          {
            label: t("comparable"),
            value: payload?.comparableCount ?? t("unavailable"),
            description: t("comparableDescription"),
          },
          {
            label: t("eligible"),
            value: payload?.eligibleCount ?? t("unavailable"),
            description: t("eligibleDescription", { direction: t(filters.direction) }),
          },
          {
            label: t("provenance"),
            value: payload?.provider ?? t("unavailable"),
            description: payload?.adjustment
              ? t("adjustment", { adjustment: payload.adjustment })
              : t("noProvenance"),
          },
        ]}
      />

      <FinancialTerminalCard>
        <FinancialTerminalCardHeader className="gap-3">
          <div>
            <CardTitle className="text-base">{t("tableTitle")}</CardTitle>
            <CardDescription className="mt-1">
              {t("tableDescription")}
            </CardDescription>
          </div>
          <div className="grid gap-3 lg:grid-cols-[auto_1fr_auto] lg:items-end">
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">{t("direction")}</div>
              <div className="flex gap-2" role="group" aria-label={t("direction")}>
                {(["gainers", "losers"] as const).map((direction) => (
                  <Button key={direction} size="sm" variant={filters.direction === direction ? "default" : "outline"} asChild>
                    <Link
                      href={filterHref(filters, { direction }) as any}
                      aria-current={filters.direction === direction ? "page" : undefined}
                    >
                      {t(direction)}
                    </Link>
                  </Button>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">{t("exchange")}</div>
              <div className="flex flex-wrap gap-2" role="group" aria-label={t("exchange")}>
                {(["all", "SSE", "SZSE", "BSE"] as const).map((exchange) => (
                  <Button key={exchange} size="sm" variant={filters.exchange === exchange ? "secondary" : "outline"} asChild>
                    <Link
                      href={filterHref(filters, { exchange }) as any}
                      aria-current={filters.exchange === exchange ? "page" : undefined}
                    >
                      {exchange === "all" ? t("allExchanges") : exchange}
                    </Link>
                  </Button>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">{t("rowCount")}</div>
              <div className="flex gap-2" role="group" aria-label={t("rowCount")}>
                {([10, 20, 50] as const).map((limit) => (
                  <Button key={limit} size="sm" variant={filters.limit === limit ? "secondary" : "outline"} asChild>
                    <Link
                      href={filterHref(filters, { limit }) as any}
                      aria-current={filters.limit === limit ? "page" : undefined}
                    >
                      {limit}
                    </Link>
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent className="p-0">
          {payload === null ? (
            <ErrorState title={t("loadFailedTitle")} description={t("loadFailedDescription")} />
          ) : payload.items.length === 0 ? (
            <EmptyState title={t("emptyTitle")} description={t("emptyDescription")} />
          ) : (
            <Table containerClassName="overflow-x-hidden">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12 text-center">{t("rank")}</TableHead>
                  <TableHead>{t("instrument")}</TableHead>
                  <TableHead className="text-right">{t("close")}</TableHead>
                  <TableHead className="hidden text-right md:table-cell">{t("previousClose")}</TableHead>
                  <TableHead className="hidden text-right sm:table-cell">{t("change")}</TableHead>
                  <TableHead className="text-right">{t("changePercent")}</TableHead>
                  <TableHead className="hidden text-right lg:table-cell">{t("volume")}</TableHead>
                  <TableHead className="hidden text-right xl:table-cell">{t("amount")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payload.items.map((item) => (
                  <TableRow key={`${item.exchange}:${item.symbol}`}>
                    <TableCell className="text-center font-mono text-muted-foreground">{item.rank}</TableCell>
                    <TableCell className="min-w-0">
                      <Link
                        href={`/instruments/${encodeURIComponent(item.symbol)}?market=CN` as any}
                        className="block min-w-0 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <span className="block truncate font-medium text-foreground hover:text-primary">{item.name}</span>
                        <span className="block truncate font-mono text-xs text-muted-foreground">{item.symbol} · {item.exchange}</span>
                      </Link>
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">{number.format(item.close)}</TableCell>
                    <TableCell className="hidden text-right font-mono tabular-nums md:table-cell">{number.format(item.previousClose)}</TableCell>
                    <TableCell className={`hidden text-right font-mono tabular-nums sm:table-cell ${movementClass(item.change)}`}>{signed(item.change)}</TableCell>
                    <TableCell className={`text-right font-mono font-semibold tabular-nums ${movementClass(item.changePercent)}`}>{signed(item.changePercent)}%</TableCell>
                    <TableCell className="hidden text-right font-mono tabular-nums lg:table-cell">{compact.format(item.volume)}</TableCell>
                    <TableCell className="hidden text-right font-mono tabular-nums xl:table-cell">{item.amount === null ? t("unavailable") : compact.format(item.amount)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>
    </div>
  );
}
