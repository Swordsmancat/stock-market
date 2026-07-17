import { Activity, ArrowLeftRight, ChartCandlestick, FileText, Settings } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
} from "@/components/financial-terminal-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { backendFetch } from "@/lib/backend-api";
import {
  decodeInstrumentKlinePayload,
  type InstrumentAssetType,
  type InstrumentKlinePayload,
} from "@/lib/instrument-kline";
import { Link } from "@/src/i18n/routing";

const PAGE_SIZE = 25;
const ASSET_TYPES: InstrumentAssetType[] = ["stock", "etf", "index"];

type InstrumentsPageProps = {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<{ q?: string; asset_type?: string; page?: string }>;
};

function parsePage(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : 1;
}

function parseAssetType(value: string | undefined): InstrumentAssetType | "" {
  return ASSET_TYPES.includes(value as InstrumentAssetType) ? (value as InstrumentAssetType) : "";
}

function pageHref(page: number, options: { q?: string; asset_type?: string }): string {
  const params = new URLSearchParams();
  if (options.q?.trim()) params.set("q", options.q.trim());
  if (options.asset_type) params.set("asset_type", options.asset_type);
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `/instruments?${query}` : "/instruments";
}

function klineHref(item: { symbol: string; market: string; assetType: string }): string {
  return `/instruments/kline?${new URLSearchParams({ asset_type: item.assetType, symbol: item.symbol, market: item.market }).toString()}`;
}

async function loadCatalog(options: { q?: string; asset_type?: string; page?: string }): Promise<InstrumentKlinePayload | null> {
  const params = new URLSearchParams({
    period: "3m",
    limit: String(PAGE_SIZE),
    offset: String((parsePage(options.page) - 1) * PAGE_SIZE),
  });
  if (options.q?.trim()) params.set("q", options.q.trim());
  const assetType = parseAssetType(options.asset_type);
  if (assetType) params.set("asset_type", assetType);
  try {
    const response = await backendFetch(`/instrument-kline?${params.toString()}`, { cache: "no-store" });
    if (!response.ok) return null;
    return decodeInstrumentKlinePayload(await response.json());
  } catch {
    return null;
  }
}

function formatClose(value: number | null | undefined, currency: string | null, locale: string, unavailable: string): string {
  if (value === null || value === undefined) return unavailable;
  const safeCurrency = currency && /^[A-Z]{3}$/.test(currency) ? currency : "CNY";
  return new Intl.NumberFormat(locale, { style: "currency", currency: safeCurrency }).format(value);
}

export default async function InstrumentsPage({ params, searchParams = Promise.resolve({}) }: InstrumentsPageProps) {
  const [{ locale }, resolved, t] = await Promise.all([params, searchParams, getTranslations("Instruments")]);
  const page = parsePage(resolved.page);
  const assetType = parseAssetType(resolved.asset_type);
  const payload = await loadCatalog(resolved);
  const hasFilters = Boolean(resolved.q?.trim() || assetType);

  if (payload === null) {
    return (
      <div className="space-y-6">
        <FinancialPageHeader
          title={t("title")}
          description={t("storedDescription")}
          badges={[]}
          metrics={[{ label: t("visibleInstruments"), value: 0 }, { label: t("withStoredSeries"), value: 0 }, { label: t("withoutStoredSeries"), value: 0 }]}
          actions={<Button variant="outline" asChild><Link href="/settings"><Settings className="mr-2 h-4 w-4" />{t("goToSettings")}</Link></Button>}
        />
        <FinancialTerminalCard><FinancialTerminalCardContent className="p-4"><ErrorState title={t("loadFailed")} description={t("loadFailedHint")} /></FinancialTerminalCardContent></FinancialTerminalCard>
      </div>
    );
  }

  const items = payload.catalog;
  const withSeries = items.filter((item) => item.hasSeries).length;
  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={t("title")}
        description={t("storedDescription")}
        badges={[{ label: t("storedOnly"), variant: "secondary" }]}
        metrics={[
          { label: t("visibleInstruments"), value: items.length, description: t("tableDescription", { visible: items.length, total: payload.total }) },
          { label: t("withStoredSeries"), value: withSeries },
          { label: t("withoutStoredSeries"), value: items.length - withSeries },
        ]}
        actions={
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button variant="outline" asChild><Link href="/instruments/kline"><ChartCandlestick className="mr-2 h-4 w-4" />{t("klineWorkspace")}</Link></Button>
            <Button variant="outline" asChild><Link href="/instruments/compare"><ArrowLeftRight className="mr-2 h-4 w-4" />{t("compareStocks")}</Link></Button>
            <Button variant="outline" asChild><Link href="/task-runs"><Activity className="mr-2 h-4 w-4" />{t("goToTaskRuns")}</Link></Button>
          </div>
        }
      />

      <FinancialTerminalCard>
        <FinancialTerminalCardContent>
          <form className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,10rem)_auto_auto]">
            <Input name="q" defaultValue={resolved.q ?? ""} placeholder={t("searchPlaceholder")} />
            <select name="asset_type" defaultValue={assetType} aria-label={t("assetType")} className="flex h-10 rounded-sm border border-input bg-background px-3 py-2 text-sm">
              <option value="">{t("allAssetTypes")}</option>
              {ASSET_TYPES.map((value) => <option key={value} value={value}>{t(`assetType${value}`)}</option>)}
            </select>
            <Button type="submit">{t("search")}</Button>
            <Button variant="outline" asChild><Link href="/instruments">{t("reset")}</Link></Button>
          </form>
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <CardTitle>{t("tableTitle")}</CardTitle>
          <CardDescription>{t("tableDescription", { visible: items.length, total: payload.total })}</CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent className="p-0">
          {items.length === 0 ? (
            <div className="p-4">
              <EmptyState title={hasFilters ? t("noMatches") : t("noData")} description={hasFilters ? t("noMatchesHint") : t("storedEmptyHint")} />
              {hasFilters ? <div className="flex justify-center"><Button variant="outline" size="sm" asChild><Link href="/instruments">{t("reset")}</Link></Button></div> : null}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader><TableRow>
                  <TableHead>{t("symbol")}</TableHead><TableHead>{t("name")}</TableHead><TableHead>{t("assetType")}</TableHead>
                  <TableHead>{t("market")}</TableHead><TableHead>{t("latestClose")}</TableHead><TableHead>{t("asOf")}</TableHead>
                  <TableHead>{t("storedBarsLabel")}</TableHead><TableHead className="text-right">{t("actions")}</TableHead>
                </TableRow></TableHeader>
                <TableBody>{items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono font-medium"><Link href={`/instruments/${encodeURIComponent(item.symbol)}?market=${encodeURIComponent(item.market)}` as any} className="hover:underline">{item.symbol}</Link></TableCell>
                    <TableCell><div>{item.name}</div><div className="text-xs text-muted-foreground">{[item.exchange, item.currency].filter(Boolean).join(" / ")}</div></TableCell>
                    <TableCell><Badge variant="outline">{t(`assetType${item.assetType}`)}</Badge></TableCell>
                    <TableCell><Badge variant="secondary">{item.market}</Badge></TableCell>
                    <TableCell className="font-mono">{formatClose(item.latestBar?.close, item.currency, locale, t("unavailableShort"))}</TableCell>
                    <TableCell>{item.latestBar?.timestamp ?? t("unavailableShort")}</TableCell>
                    <TableCell><span className="font-mono">{item.storedBarCount}</span><div className="text-xs text-muted-foreground">{item.hasSeries ? t("seriesAvailable") : t("seriesUnavailable")}</div></TableCell>
                    <TableCell className="text-right"><div className="flex justify-end gap-2">
                      <Button variant="outline" size="sm" asChild><Link href={klineHref(item) as any}><ChartCandlestick className="mr-2 h-4 w-4" />{t("viewKline")}</Link></Button>
                      <Button variant="ghost" size="sm" asChild><Link href={`/reports?symbol=${encodeURIComponent(item.symbol)}` as any}><FileText className="mr-2 h-4 w-4" />{t("viewReports")}</Link></Button>
                    </div></TableCell>
                  </TableRow>
                ))}</TableBody>
              </Table>
            </div>
          )}
          <div className="flex flex-col gap-3 border-t border-border/70 px-3 py-3 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <span>{t("pageStatus", { page, visible: items.length, total: payload.total })}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} asChild={page > 1}>{page > 1 ? <Link href={pageHref(page - 1, resolved) as any}>{t("previousPage")}</Link> : <span>{t("previousPage")}</span>}</Button>
              <Button variant="outline" size="sm" disabled={!payload.hasMore} asChild={payload.hasMore}>{payload.hasMore ? <Link href={pageHref(page + 1, resolved) as any}>{t("nextPage")}</Link> : <span>{t("nextPage")}</span>}</Button>
            </div>
          </div>
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>
    </div>
  );
}
