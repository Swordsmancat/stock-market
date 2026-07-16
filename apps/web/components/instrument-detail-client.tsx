"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowLeft, ExternalLink, LoaderCircle, RefreshCw, Settings2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/src/i18n/routing";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
  financialTerminalCardClassName,
} from "@/components/financial-terminal-section";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { AdvancedCandlestickChart } from "@/components/advanced-candlestick-chart";
import { IntradayPriceChart } from "@/components/intraday-price-chart";
import { InstrumentWatchlistForm } from "@/components/instrument-watchlist-form";
import { MarketAssistantCard } from "@/components/market-assistant-card";
import { MarketDepthCard } from "@/components/market-depth-card";
import { DataTrustBadge } from "@/components/data-trust-badge";
import { FinancialPageHeader } from "@/components/financial-page-header";
import { useMarketColorsContext } from "@/context/market-colors-context";
import { createDataTrustSignal } from "@/lib/data-trust";
import {
  decodeInstrumentSymbol,
  getInstrumentDisplayName,
} from "@/lib/instrument-display";
import type {
  InstrumentBar,
  InstrumentDetailContext,
  InstrumentDetailPayload,
} from "@/lib/instrument-detail";
import {
  isNewsRefreshPayload,
  type NewsRefreshPayload,
} from "@/lib/news-payload";

type ChartBarData = InstrumentBar & {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

type NewsRecoveryState =
  | "idle"
  | "recovering"
  | "recovered"
  | "no_data"
  | "provider_error"
  | "unsupported";

type NewsRecoverySessionValue =
  | "attempted"
  | "no_data"
  | "provider_error"
  | "unsupported";

const NEWS_DIAGNOSTIC_PRIORITY = [
  "PROVIDER_ERROR",
  "PROVIDER_TIMEOUT",
  "PERSISTENCE_ERROR",
  "UNSUPPORTED_IDENTITY",
  "UNSUPPORTED_MARKET",
  "MISSING_CREDENTIALS",
  "PROVIDER_DISABLED",
  "NO_PERSISTABLE_CANDIDATES",
  "EMPTY_RESPONSE",
  "DATABASE_FALLBACK_EMPTY",
  "PROVIDER_PERSISTED",
  "DATABASE_HIT",
] as const;

const SUPPORTED_ASSISTANT_MARKET_DATA_PROVIDERS = new Set([
  "mock",
  "yfinance",
  "akshare",
  "tushare",
]);

function resolveAssistantProvider(
  ...candidates: Array<string | null | undefined>
): string | null {
  for (const candidate of candidates) {
    const normalizedCandidate = candidate?.trim().toLowerCase();
    if (
      normalizedCandidate &&
      SUPPORTED_ASSISTANT_MARKET_DATA_PROVIDERS.has(normalizedCandidate)
    ) {
      return normalizedCandidate;
    }
  }
  return null;
}

function isChartBarData(bar: InstrumentBar): bar is ChartBarData {
  return (
    typeof bar.timestamp === "string" &&
    Number.isFinite(bar.open) &&
    Number.isFinite(bar.high) &&
    Number.isFinite(bar.low) &&
    Number.isFinite(bar.close)
  );
}

function getLocalDateKey(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getNewsRecoverySessionKey(identity: {
  market: string;
  symbol: string;
}): string {
  return `news-fallback:v1:${identity.market}:${identity.symbol}:${getLocalDateKey()}`;
}

function readNewsRecoverySessionValue(
  sessionKey: string,
): NewsRecoverySessionValue | null {
  try {
    const value = window.sessionStorage.getItem(sessionKey);
    return value === "attempted" ||
      value === "no_data" ||
      value === "provider_error" ||
      value === "unsupported"
      ? value
      : null;
  } catch {
    return null;
  }
}

function writeNewsRecoverySessionValue(
  sessionKey: string,
  value: NewsRecoverySessionValue,
) {
  try {
    window.sessionStorage.setItem(sessionKey, value);
  } catch {
    // The in-memory guard still prevents duplicate attempts when storage is unavailable.
  }
}

function clearTransientNewsRecoveryAttempt(sessionKey: string | null) {
  if (!sessionKey) {
    return;
  }
  try {
    if (window.sessionStorage.getItem(sessionKey) === "attempted") {
      window.sessionStorage.removeItem(sessionKey);
    }
  } catch {
    // The in-memory guard remains authoritative when storage is unavailable.
  }
}

function selectNewsDiagnosticCode(
  diagnostics: NewsRefreshPayload["diagnostics"],
): string | null {
  const codes = new Set(
    (diagnostics ?? [])
      .map((diagnostic) => diagnostic.code)
      .filter((code): code is string => typeof code === "string"),
  );
  return (
    NEWS_DIAGNOSTIC_PRIORITY.find((code) => codes.has(code)) ??
    codes.values().next().value ??
    null
  );
}

function formatDetailDate(
  value: string | null | undefined,
  locale: string,
  unavailableLabel: string,
): string {
  if (!value) {
    return unavailableLabel;
  }

  const parsedDate = new Date(value);
  return Number.isNaN(parsedDate.getTime())
    ? unavailableLabel
    : parsedDate.toLocaleDateString(locale);
}

function formatDetailNumber(
  value: number | null | undefined,
  locale: string,
  unavailableLabel: string,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return unavailableLabel;
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatPercentMetric(
  value: number | null | undefined,
  locale: string,
  unavailableLabel: string,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return unavailableLabel;
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
    style: "percent",
  }).format(value);
}

function cleanMarkdownPreviewLine(line: string): string {
  return line
    .replace(/^#{1,6}\s*/, "")
    .replace(/^[-*]\s+/, "")
    .replace(/\[([^\]]+)]\([^)]*\)/g, "$1")
    .replace(/[*_`]/g, "")
    .trim();
}

function extractMarkdownPreview(
  contentMarkdown: string | null | undefined,
  fallback: string,
): string {
  if (!contentMarkdown) {
    return fallback;
  }

  const meaningfulLine = contentMarkdown
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line.length > 0);
  if (!meaningfulLine) {
    return fallback;
  }

  return cleanMarkdownPreviewLine(meaningfulLine) || fallback;
}

function formatIndicatorValue(
  value: unknown,
  locale: string,
  unavailableLabel: string,
): string {
  if (typeof value === "number") {
    return formatDetailNumber(value, locale, unavailableLabel);
  }
  if (typeof value === "string") {
    return value;
  }
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(
        ([key, nestedValue]) =>
          `${key}: ${formatIndicatorValue(nestedValue, locale, unavailableLabel)}`,
      )
      .join(" / ");
  }
  return unavailableLabel;
}

function ContextMetric({ label, value }: { label: string; value: string }) {
  return (
    <FinancialTerminalSurface className="p-3">
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-sm font-semibold">{value}</div>
    </FinancialTerminalSurface>
  );
}

interface InstrumentDetailClientProps {
  symbol: string;
  locale: string;
  initialData?: InstrumentDetailPayload | null;
  initialError?: string | null;
  detailContext?: InstrumentDetailContext | null;
  researchSnapshotId?: string | null;
}

export function InstrumentDetailClient({
  symbol,
  locale,
  initialData = null,
  initialError = null,
  detailContext = null,
  researchSnapshotId = null,
}: InstrumentDetailClientProps) {
  const router = useRouter();
  const t = useTranslations("InstrumentDetail");
  const { getMovementColor } = useMarketColorsContext();
  const [data, setData] = useState<InstrumentDetailPayload | null>(initialData);
  const [loading, setLoading] = useState(
    initialData === null && initialError === null,
  );
  const [error, setError] = useState<string | null>(initialError);
  const [newsRecoveryState, setNewsRecoveryState] =
    useState<NewsRecoveryState>(
      initialData?.news_load_status === "failed" ? "provider_error" : "idle",
    );
  const [manualNewsRetryUsed, setManualNewsRetryUsed] = useState(false);
  const [newsDiagnosticCode, setNewsDiagnosticCode] = useState<string | null>(null);
  const automaticNewsRecoveryAttempted = useRef(false);
  const detailIdentityKey = detailContext?.identity
    ? `${detailContext.identity.market.trim().toUpperCase()}:${detailContext.identity.symbol.trim().toUpperCase()}`
    : `UNKNOWN:${symbol.trim().toUpperCase()}`;
  const previousDetailIdentityKey = useRef(detailIdentityKey);
  const activeDetailIdentityKey = useRef(detailIdentityKey);
  const detailRequestController = useRef<AbortController | null>(null);
  const newsRequestController = useRef<AbortController | null>(null);
  const newsRequestSessionKey = useRef<string | null>(null);
  activeDetailIdentityKey.current = detailIdentityKey;

  useEffect(() => {
    if (previousDetailIdentityKey.current === detailIdentityKey) {
      return;
    }

    previousDetailIdentityKey.current = detailIdentityKey;
    detailRequestController.current?.abort();
    newsRequestController.current?.abort();
    clearTransientNewsRecoveryAttempt(newsRequestSessionKey.current);
    newsRequestController.current = null;
    newsRequestSessionKey.current = null;
    automaticNewsRecoveryAttempted.current = false;
    setData(initialData);
    setLoading(initialData === null && initialError === null);
    setError(initialError);
    setNewsRecoveryState(
      initialData?.news_load_status === "failed" ? "provider_error" : "idle",
    );
    setManualNewsRetryUsed(false);
    setNewsDiagnosticCode(null);
  }, [detailIdentityKey, initialData, initialError]);

  async function refreshNews() {
    const identity = detailContext?.identity;
    if (!identity) {
      setNewsRecoveryState("unsupported");
      return;
    }

    const requestIdentityKey = detailIdentityKey;
    const sessionKey = getNewsRecoverySessionKey(identity);
    const controller = new AbortController();
    newsRequestController.current?.abort();
    clearTransientNewsRecoveryAttempt(newsRequestSessionKey.current);
    newsRequestController.current = controller;
    newsRequestSessionKey.current = sessionKey;
    setNewsRecoveryState("recovering");
    setNewsDiagnosticCode(null);
    try {
      const query = new URLSearchParams({ market: identity.market });
      const response = await fetch(
        `/api/news/${encodeURIComponent(identity.symbol)}/refresh?${query.toString()}`,
        { method: "POST", signal: controller.signal },
      );
      const payload = (await response.json()) as unknown;
      if (
        controller.signal.aborted ||
        activeDetailIdentityKey.current !== requestIdentityKey
      ) {
        return;
      }
      if (!response.ok) {
        const terminalState =
          response.status >= 400 && response.status < 500
            ? "unsupported"
            : "provider_error";
        setNewsRecoveryState(terminalState);
        writeNewsRecoverySessionValue(sessionKey, terminalState);
        return;
      }

      if (!isNewsRefreshPayload(payload, identity.symbol, identity.market)) {
        setNewsRecoveryState("provider_error");
        writeNewsRecoverySessionValue(sessionKey, "provider_error");
        return;
      }

      setNewsDiagnosticCode(selectNewsDiagnosticCode(payload.diagnostics));

      setData((currentData) =>
        currentData
          ? {
              ...currentData,
              news: payload.news,
              news_load_status: "loaded",
            }
          : currentData,
      );

      if (payload.status === "database_hit" || payload.status === "refreshed") {
        setNewsRecoveryState("recovered");
      } else if (
        payload.status === "no_data" ||
        payload.status === "provider_error" ||
        payload.status === "unsupported"
      ) {
        setNewsRecoveryState(payload.status);
        writeNewsRecoverySessionValue(sessionKey, payload.status);
      } else {
        setNewsRecoveryState("provider_error");
        writeNewsRecoverySessionValue(sessionKey, "provider_error");
      }
    } catch {
      if (
        controller.signal.aborted ||
        activeDetailIdentityKey.current !== requestIdentityKey
      ) {
        return;
      }
      setNewsRecoveryState("provider_error");
      writeNewsRecoverySessionValue(sessionKey, "provider_error");
    } finally {
      if (newsRequestController.current === controller) {
        if (controller.signal.aborted) {
          clearTransientNewsRecoveryAttempt(sessionKey);
        }
        newsRequestController.current = null;
        newsRequestSessionKey.current = null;
      }
    }
  }

  function retryNews() {
    if (manualNewsRetryUsed || newsRecoveryState === "recovering") {
      return;
    }
    setManualNewsRetryUsed(true);
    void refreshNews();
  }

  useEffect(() => {
    return () => {
      newsRequestController.current?.abort();
      clearTransientNewsRecoveryAttempt(newsRequestSessionKey.current);
      newsRequestController.current = null;
      newsRequestSessionKey.current = null;
    };
  }, []);

  useEffect(() => {
    if (initialData !== null || initialError !== null) {
      return;
    }

    const requestIdentityKey = detailIdentityKey;
    const controller = new AbortController();
    detailRequestController.current?.abort();
    detailRequestController.current = controller;

    async function fetchData() {
      try {
        setLoading(true);
        const query = new URLSearchParams();
        const market = detailContext?.identity?.market;
        if (market) {
          query.set("market", market);
        }
        const querySuffix = query.size > 0 ? `?${query.toString()}` : "";
        const response = await fetch(
          `/api/instruments/${encodeURIComponent(symbol)}${querySuffix}`,
          { signal: controller.signal },
        );

        if (!response.ok) {
          throw new Error("Failed to fetch instrument data");
        }

        const result = await response.json();
        if (
          controller.signal.aborted ||
          activeDetailIdentityKey.current !== requestIdentityKey
        ) {
          return;
        }
        setData(result);
      } catch (err) {
        if (
          controller.signal.aborted ||
          activeDetailIdentityKey.current !== requestIdentityKey
        ) {
          return;
        }
        console.error("Fetch error:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        if (
          !controller.signal.aborted &&
          activeDetailIdentityKey.current === requestIdentityKey
        ) {
          setLoading(false);
        }
      }
    }

    void fetchData();
    return () => {
      controller.abort();
      if (detailRequestController.current === controller) {
        detailRequestController.current = null;
      }
    };
  }, [detailContext?.identity?.market, detailIdentityKey, initialData, initialError, symbol]);

  useEffect(() => {
    const identity = detailContext?.identity;
    const hasStoredNews = (data?.news?.items?.length ?? 0) > 0;
    const hasInitialStoredNews = (initialData?.news?.items?.length ?? 0) > 0;
    if (hasInitialStoredNews) {
      return;
    }
    if (data?.news_load_status === "failed") {
      setNewsRecoveryState("provider_error");
      return;
    }
    if (
      !identity ||
      !data ||
      hasStoredNews ||
      automaticNewsRecoveryAttempted.current
    ) {
      return;
    }

    automaticNewsRecoveryAttempted.current = true;
    const sessionKey = getNewsRecoverySessionKey(identity);
    const sessionValue = readNewsRecoverySessionValue(sessionKey);
    if (
      sessionValue === "no_data" ||
      sessionValue === "provider_error" ||
      sessionValue === "unsupported"
    ) {
      setNewsRecoveryState(sessionValue);
      return;
    }
    if (sessionValue === "attempted") {
      setNewsRecoveryState("provider_error");
      return;
    }
    writeNewsRecoverySessionValue(sessionKey, "attempted");

    void refreshNews();
  }, [data, detailContext, initialData]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("back")}
        </Button>
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("back")}
        </Button>
        <FinancialTerminalCard>
          <FinancialTerminalCardContent className="p-6">
            <p className="text-center text-destructive">
              {t("loadFailed", { reason: error ?? t("unavailableShort") })}
            </p>
          </FinancialTerminalCardContent>
        </FinancialTerminalCard>
      </div>
    );
  }

  const bars = data.bars?.items ?? [];
  const chartBars = bars.filter(isChartBarData);
  const latestBar = bars.at(-1) ?? data.latest?.item ?? null;
  const prevBar = bars.at(-2) ?? null;

  const latestBarClose = latestBar?.close;
  const latestQuoteClose = data.latest?.item?.close;
  const currentPrice = Number.isFinite(latestBarClose)
    ? (latestBarClose as number)
    : Number.isFinite(latestQuoteClose)
      ? (latestQuoteClose as number)
      : null;
  const previousBarClose = prevBar?.close;
  const prevPrice = Number.isFinite(previousBarClose)
    ? (previousBarClose as number)
    : null;
  const change = currentPrice !== null && prevPrice !== null
    ? currentPrice - prevPrice
    : null;
  const changePercent = change !== null && prevPrice !== null && prevPrice !== 0
    ? change / prevPrice
    : null;
  const formattedChange = change === null
    ? t("unavailableShort")
    : `${change >= 0 ? "+" : ""}${change.toFixed(2)}`;
  const formattedChangePercent = changePercent === null
    ? t("unavailableShort")
    : `${changePercent >= 0 ? "+" : ""}${(changePercent * 100).toFixed(2)}%`;
  const decodedSymbol = decodeInstrumentSymbol(symbol);
  const displayName = getInstrumentDisplayName(symbol, locale);
  const subtitle =
    displayName === decodedSymbol
      ? t("detailSubtitle")
      : `${decodedSymbol} · ${t("detailSubtitle")}`;
  const providerRequestSymbol = data.request_symbol?.trim();
  const usesProviderSpecificSymbol =
    data.provider_symbol_mapped === true &&
    providerRequestSymbol !== undefined &&
    providerRequestSymbol.length > 0;
  const assistantSymbol = usesProviderSpecificSymbol
    ? providerRequestSymbol
    : detailContext?.identity?.symbol ?? data.symbol ?? symbol;
  const assistantMarket = usesProviderSpecificSymbol
    ? null
    : detailContext?.identity?.market ?? data.market ?? null;
  const assistantProvider = resolveAssistantProvider(
    data.bars?.effective_provider,
    data.bars?.provider,
    data.bars?.requested_provider,
    data.latest?.effective_provider,
    data.latest?.provider,
    data.latest?.requested_provider,
  );
  const requestedDailyProvider =
    data.bars?.requested_provider ?? data.latest?.requested_provider ?? null;
  const dailyProviderChanged = Boolean(
    requestedDailyProvider?.trim() &&
      assistantProvider?.trim() &&
      requestedDailyProvider.trim().toLowerCase() !==
        assistantProvider.trim().toLowerCase(),
  );
  const showDailySourceSwitch = Boolean(
    data.bars?.fallback_used || dailyProviderChanged,
  );
  const dailySource =
    data.bars?.upstream_source ?? data.bars?.source ?? "-";
  const latestTrustSignal = createDataTrustSignal({
    status: data.latest?.status,
    source: data.latest?.source,
    provider: data.latest?.provider,
    requested_provider: data.latest?.requested_provider,
    effective_provider: data.latest?.effective_provider,
    as_of: data.latest?.item?.timestamp,
    no_data_reason: data.latest?.no_data_reason,
  });
  const barsTrustSignal = createDataTrustSignal({
    status: data.bars?.status,
    source: data.bars?.source,
    provider: data.bars?.provider,
    requested_provider: data.bars?.requested_provider,
    effective_provider: data.bars?.effective_provider,
    as_of: latestBar?.timestamp,
    no_data_reason: data.bars?.no_data_reason,
  });
  const indicatorEntries = Object.entries(data.indicators?.indicators ?? {});
  const latestReport = data.latest_daily_report ?? null;
  const latestReportHasContent = Boolean(latestReport?.content_markdown);
  const reportHistoryItems = data.daily_report_history?.items ?? [];
  const fundamentalsItem = data.fundamentals?.item ?? null;
  const fundamentalsCompany = fundamentalsItem?.company ?? null;
  const newsItems = data.news?.items ?? [];
  const latestNews = newsItems[0] ?? null;
  const newsDiagnosticMessages: Record<string, string> = {
    DATABASE_HIT: t("newsDiagnosticDatabaseHit"),
    MISSING_CREDENTIALS: t("newsDiagnosticMissingCredentials"),
    PROVIDER_DISABLED: t("newsDiagnosticProviderDisabled"),
    PROVIDER_TIMEOUT: t("newsDiagnosticProviderTimeout"),
    PROVIDER_ERROR: t("newsDiagnosticProviderError"),
    PERSISTENCE_ERROR: t("newsDiagnosticPersistenceError"),
    EMPTY_RESPONSE: t("newsDiagnosticEmptyResponse"),
    NO_PERSISTABLE_CANDIDATES: t("newsDiagnosticNoPersistableCandidates"),
    PROVIDER_PERSISTED: t("newsDiagnosticProviderPersisted"),
    UNSUPPORTED_IDENTITY: t("newsDiagnosticUnsupportedIdentity"),
    UNSUPPORTED_MARKET: t("newsDiagnosticUnsupportedMarket"),
    DATABASE_FALLBACK_EMPTY: t("newsDiagnosticDatabaseFallbackEmpty"),
  };
  const newsDiagnosticMessage = newsDiagnosticCode
    ? newsDiagnosticMessages[newsDiagnosticCode] ?? t("newsDiagnosticUnknown")
    : null;

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={displayName}
        description={subtitle}
        badges={[
          { label: decodedSymbol, variant: "secondary" },
          {
            label: `provider: ${assistantProvider ?? data.latest?.effective_provider ?? data.latest?.provider ?? "none"}`,
          },
          { label: `${data.range?.start ?? "-"} / ${data.range?.end ?? "-"}` },
        ]}
        metrics={[
          {
            label: t("latestPriceCard"),
            value: formatDetailNumber(
              currentPrice,
              locale,
              t("unavailableShort"),
            ),
            description: (
              <DataTrustBadge signal={latestTrustSignal} mode="summary" />
            ),
          },
          {
            label: t("priceChange"),
            value: formattedChange,
            className: change === null ? undefined : getMovementColor(change),
          },
          {
            label: t("priceChangePercent"),
            value: formattedChangePercent,
            className: change === null ? undefined : getMovementColor(change),
          },
          {
            label: t("klineTitle"),
            value: chartBars.length,
            description: (
              <DataTrustBadge signal={barsTrustSignal} mode="summary" />
            ),
          },
        ]}
        actions={
          <>
            {detailContext?.identity ? (
              <InstrumentWatchlistForm
                symbol={detailContext.identity.symbol}
                market={detailContext.identity.market}
                name={detailContext.identity.name}
                membership={detailContext.watchlistMembership}
              />
            ) : null}
            <Button
              variant="outline"
              size="sm"
              className="min-h-11"
              onClick={() => router.back()}
            >
              <ArrowLeft className="h-4 w-4" />
              {t("back")}
            </Button>
          </>
        }
      />

      {showDailySourceSwitch ? (
        <div
          role="status"
          className="border-l-2 border-primary bg-primary/5 px-3 py-2 text-sm text-foreground"
        >
          {t("dailyBarSourceSwitched", {
            requestedProvider: requestedDailyProvider ?? "-",
            effectiveProvider: assistantProvider ?? "-",
            source: dailySource,
          })}
        </div>
      ) : null}

      <MarketAssistantCard
        key={`${assistantSymbol}:${assistantMarket ?? "unknown-market"}:${assistantProvider ?? "unknown-provider"}:${researchSnapshotId ?? "no-snapshot"}`}
        symbol={assistantSymbol}
        locale={locale}
        market={assistantMarket}
        provider={assistantProvider}
        start={data.range?.start ?? null}
        end={data.range?.end ?? null}
        researchSnapshotId={researchSnapshotId}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <FinancialTerminalCard>
          <FinancialTerminalCardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle>{t("aiReport")}</CardTitle>
                <CardDescription>{t("aiReportDesc")}</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link
                  href={`/reports?symbol=${encodeURIComponent(symbol)}` as any}
                >
                  <ExternalLink className="h-4 w-4" />
                  {t("viewReports")}
                </Link>
              </Button>
            </div>
          </FinancialTerminalCardHeader>
          <FinancialTerminalCardContent className="space-y-4">
            {latestReportHasContent ? (
              <>
                <div className="flex flex-wrap gap-2">
                  {latestReport?.as_of ? (
                    <Badge variant="secondary">
                      {t("reportAsOf", {
                        date: formatDetailDate(
                          latestReport.as_of,
                          locale,
                          t("unavailableShort"),
                        ),
                      })}
                    </Badge>
                  ) : null}
                  <Badge variant="outline">
                    {t("reportCitations", {
                      count: latestReport?.citations?.length ?? 0,
                    })}
                  </Badge>
                  {latestReport?.task_run_id ? (
                    <Button variant="ghost" size="sm" asChild>
                      <Link
                        href={`/task-runs/${latestReport.task_run_id}` as any}
                      >
                        {t("reportTaskRun", {
                          id: latestReport.task_run_id.slice(0, 8),
                        })}
                      </Link>
                    </Button>
                  ) : null}
                </div>
                <p className="text-sm leading-6 text-muted-foreground">
                  {extractMarkdownPreview(
                    latestReport?.content_markdown,
                    t("noReport"),
                  )}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">{t("noReport")}</p>
            )}

            {reportHistoryItems.length > 0 ? (
              <div className="border-t pt-3">
                <div className="mb-2 text-sm font-semibold">
                  {t("reportHistory")}
                </div>
                <div className="space-y-2">
                  {reportHistoryItems.slice(0, 3).map((report, index) => (
                    <FinancialTerminalSurface
                      key={`${report.as_of ?? "report"}-${index}`}
                      className="p-3 text-sm"
                    >
                      <div className="font-medium">
                        {report.as_of
                          ? t("reportAsOf", {
                              date: formatDetailDate(
                                report.as_of,
                                locale,
                                t("unavailableShort"),
                              ),
                            })
                          : t("aiReport")}
                      </div>
                      <div className="mt-1 line-clamp-2 text-muted-foreground">
                        {extractMarkdownPreview(
                          report.content_markdown,
                          t("noReport"),
                        )}
                      </div>
                    </FinancialTerminalSurface>
                  ))}
                </div>
              </div>
            ) : null}
          </FinancialTerminalCardContent>
        </FinancialTerminalCard>

        <div className="grid gap-4">
          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle>{t("technicalIndicators")}</CardTitle>
              <CardDescription>
                {t("technicalIndicatorsDesc")}{" "}
                {data.indicators?.as_of
                  ? t("indicatorAsOf", {
                      date: formatDetailDate(
                        data.indicators.as_of,
                        locale,
                        t("unavailableShort"),
                      ),
                    })
                  : null}
              </CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent>
              {indicatorEntries.length > 0 ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  {indicatorEntries.map(([code, value]) => (
                    <FinancialTerminalSurface key={code} className="p-3">
                      <div className="font-mono text-xs text-muted-foreground">
                        {code}
                      </div>
                      <div className="mt-1 text-sm font-medium">
                        {formatIndicatorValue(
                          value,
                          locale,
                          t("unavailableShort"),
                        )}
                      </div>
                    </FinancialTerminalSurface>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t("noTechnicalIndicators")}
                </p>
              )}
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle>{t("fundamentalsSummary")}</CardTitle>
              <CardDescription>{t("fundamentalsDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="space-y-3">
              {fundamentalsItem ? (
                <>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <ContextMetric
                      label={t("fundamentalPeRatio")}
                      value={formatDetailNumber(
                        fundamentalsItem.pe_ratio,
                        locale,
                        t("unavailableShort"),
                      )}
                    />
                    <ContextMetric
                      label={t("fundamentalRevenueGrowth")}
                      value={formatPercentMetric(
                        fundamentalsItem.revenue_growth,
                        locale,
                        t("unavailableShort"),
                      )}
                    />
                    <ContextMetric
                      label={t("fundamentalNetMargin")}
                      value={formatPercentMetric(
                        fundamentalsItem.net_margin,
                        locale,
                        t("unavailableShort"),
                      )}
                    />
                    <ContextMetric
                      label={t("fundamentalDebtToAssets")}
                      value={formatPercentMetric(
                        fundamentalsItem.debt_to_assets,
                        locale,
                        t("unavailableShort"),
                      )}
                    />
                  </div>
                  {fundamentalsItem.summary ? (
                    <p className="text-sm leading-6 text-muted-foreground">
                      {fundamentalsItem.summary}
                    </p>
                  ) : null}
                  {fundamentalsCompany &&
                  Object.values(fundamentalsCompany).some(Boolean) ? (
                    <section className="space-y-3 border-t pt-3">
                      <h3 className="text-sm font-medium">
                        {t("fundamentalCompanyContext")}
                      </h3>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {fundamentalsCompany.name ? (
                          <ContextMetric
                            label={t("fundamentalCompanyName")}
                            value={fundamentalsCompany.name}
                          />
                        ) : null}
                        {fundamentalsCompany.industry ? (
                          <ContextMetric
                            label={t("fundamentalCompanyIndustry")}
                            value={fundamentalsCompany.industry}
                          />
                        ) : null}
                      </div>
                      {fundamentalsCompany.business_scope ? (
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground">
                            {t("fundamentalBusinessScope")}
                          </p>
                          <p className="text-sm leading-6">
                            {fundamentalsCompany.business_scope}
                          </p>
                        </div>
                      ) : null}
                      {fundamentalsCompany.profile ? (
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground">
                            {t("fundamentalCompanyProfile")}
                          </p>
                          <p className="text-sm leading-6 text-muted-foreground">
                            {fundamentalsCompany.profile}
                          </p>
                        </div>
                      ) : null}
                    </section>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">
                      {t("sourceValue", {
                        source:
                          data.fundamentals?.source ?? t("unavailableShort"),
                      })}
                    </Badge>
                    {data.fundamentals?.as_of ? (
                      <Badge variant="outline">
                        {t("fundamentalAsOf", {
                          date: formatDetailDate(
                            data.fundamentals.as_of,
                            locale,
                            t("unavailableShort"),
                          ),
                        })}
                      </Badge>
                    ) : null}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t("noFundamentals")}
                </p>
              )}
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle>{t("latestNews")}</CardTitle>
              <CardDescription>{t("latestNewsDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="space-y-3">
              {newsRecoveryState === "recovering" ? (
                <div
                  role="status"
                  className="flex items-center gap-2 border bg-muted/20 p-3 text-sm text-muted-foreground"
                >
                  <LoaderCircle className="h-4 w-4 shrink-0 animate-spin" aria-hidden="true" />
                  {t("newsRecoveryRecovering")}
                </div>
              ) : null}
              {newsRecoveryState === "provider_error" ? (
                <div
                  role="alert"
                  className="flex flex-wrap items-center justify-between gap-3 border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
                >
                  <span className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
                    {t("newsRecoveryProviderError")}
                  </span>
                  {!manualNewsRetryUsed ? (
                    <Button type="button" variant="outline" size="sm" onClick={retryNews}>
                      <RefreshCw className="h-4 w-4" aria-hidden="true" />
                      {t("newsRecoveryRetry")}
                    </Button>
                  ) : null}
                </div>
              ) : null}
              {newsRecoveryState === "no_data" ? (
                <div
                  role="status"
                  className="flex flex-wrap items-center justify-between gap-3 border bg-muted/20 p-3 text-sm text-muted-foreground"
                >
                  <span>{t("newsRecoveryNoData")}</span>
                  {!manualNewsRetryUsed ? (
                    <Button type="button" variant="outline" size="sm" onClick={retryNews}>
                      <RefreshCw className="h-4 w-4" aria-hidden="true" />
                      {t("newsRecoveryRetry")}
                    </Button>
                  ) : null}
                </div>
              ) : null}
              {newsRecoveryState === "unsupported" ? (
                <div
                  role="status"
                  className="flex flex-wrap items-center justify-between gap-3 border bg-muted/20 p-3 text-sm text-muted-foreground"
                >
                  <span>{t("newsRecoveryUnsupported")}</span>
                  <Button type="button" variant="outline" size="sm" asChild>
                    <Link href="/settings">
                      <Settings2 className="h-4 w-4" aria-hidden="true" />
                      {t("newsRecoveryConfigure")}
                    </Link>
                  </Button>
                </div>
              ) : null}
              {newsRecoveryState === "recovered" ? (
                <p role="status" className="text-xs text-muted-foreground">
                  {t("newsRecoveryRecovered")}
                </p>
              ) : null}
              {newsRecoveryState !== "recovering" && newsDiagnosticMessage ? (
                <p className="text-xs text-muted-foreground">
                  {newsDiagnosticMessage}
                </p>
              ) : null}
              {latestNews ? (
                <>
                  <FinancialTerminalSurface className="space-y-2 p-3">
                    <div className="font-medium leading-6">
                      {latestNews.title}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {latestNews.sentiment ? (
                        <Badge variant="secondary">
                          {latestNews.sentiment}
                        </Badge>
                      ) : null}
                      {typeof latestNews.confidence === "number" ? (
                        <Badge variant="outline">
                          {t("confidence", {
                            score: Math.round(latestNews.confidence * 100),
                          })}
                        </Badge>
                      ) : null}
                      {latestNews.published_at ? (
                        <Badge variant="outline">
                          {formatDetailDate(
                            latestNews.published_at,
                            locale,
                            t("unavailableShort"),
                          )}
                        </Badge>
                      ) : null}
                    </div>
                    {latestNews.summary ? (
                      <p className="text-sm text-muted-foreground">
                        {latestNews.summary}
                      </p>
                    ) : null}
                    {latestNews.url ? (
                      <a
                        href={latestNews.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                      >
                        {t("readNews")}
                        <ExternalLink className="h-3 w-3" aria-hidden="true" />
                      </a>
                    ) : null}
                  </FinancialTerminalSurface>
                  {newsItems.length > 1 ? (
                    <div className="text-xs text-muted-foreground">
                      {t("newsArticleCount", { count: newsItems.length })}
                    </div>
                  ) : null}
                </>
              ) : newsRecoveryState === "idle" ? (
                <p className="text-sm text-muted-foreground">{t("noNews")}</p>
              ) : null}
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>
        </div>
      </div>

      <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <CardTitle>{t("intradayTitle")}</CardTitle>
          <CardDescription>{t("intradayDescription")}</CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent>
          <IntradayPriceChart
            points={data.intraday?.items ?? []}
            previousClose={data.intraday?.previous_close ?? null}
            status={data.intraday?.status ?? "degraded"}
            reason={data.intraday?.availability?.reason ?? null}
            source={data.intraday?.source ?? null}
            provider={data.intraday?.provider ?? null}
            requestedProvider={data.intraday?.requested_provider ?? null}
            effectiveProvider={data.intraday?.effective_provider ?? null}
            availability={data.intraday?.availability ?? null}
            freshness={data.intraday?.freshness ?? null}
            session={data.intraday?.session ?? null}
            height={280}
          />
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <CardTitle>{t("klineTitle")}</CardTitle>
          <CardDescription>{t("interactiveKlineDescription")}</CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent>
          <div className="mb-4">
            <DataTrustBadge signal={barsTrustSignal} mode="summary" />
          </div>
          {chartBars.length > 0 ? (
            <AdvancedCandlestickChart
              data={chartBars}
              symbol={symbol}
              height={500}
              showMA={true}
              showVolume={true}
            />
          ) : (
            <FinancialTerminalSurface className="flex h-96 items-center justify-center text-muted-foreground">
              {t("noKlineData")}
            </FinancialTerminalSurface>
          )}
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      <details className="rounded-md border border-dashed border-border/80 bg-card/95 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-foreground">
          {t("advancedMarketDataSummary")}
        </summary>
        <div className="mt-4">
          <MarketDepthCard
            marketDepth={data.market_depth ?? null}
            className={financialTerminalCardClassName}
          />
        </div>
      </details>
    </div>
  );
}
