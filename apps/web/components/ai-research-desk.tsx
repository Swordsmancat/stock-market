"use client";

import { FormEvent, useMemo, useState } from "react";
import { FileSearch, Plus, Sparkles, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { MarketAssistantCard } from "@/components/market-assistant-card";
import { FinancialPageHeader } from "@/components/financial-page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Link } from "@/src/i18n/routing";

export type AiResearchWatchlistItem = {
  symbol: string;
  market?: string | null;
  name?: string | null;
  latest_price?: number | null;
  rsi?: number | null;
  alert_status?: { triggered?: boolean | null } | null;
};

export type AiResearchFollowedItem = {
  symbol: string;
  name?: string | null;
  market?: string | null;
  freshness?: string | null;
  status?: string | null;
  latest?: {
    timestamp?: string | null;
    close?: number | null;
  } | null;
};

export type AiResearchRecommendation = {
  symbol: string;
  type: "breakout" | "volume_anomaly" | "oversold_rebound" | "strong_momentum" | string;
  title: string;
  reason: string;
  confidence?: number | null;
  timestamp?: string | null;
};

export type AiResearchMacroIndicator = {
  code: string;
  name: string;
  region?: string | null;
  category?: string | null;
  status?: string | null;
  value?: number | null;
  unit?: string | null;
  as_of?: string | null;
  source?: string | null;
  no_data_reason?: string | null;
};

export type AiResearchDiagnostic = {
  source?: string | null;
  status?: string | null;
  severity?: string | null;
  code?: string | null;
  message?: string | null;
};

export type AiResearchOfficialSourceProvider = {
  provider: string;
  label: string;
  status?: string | null;
  configured?: boolean | null;
  can_refresh_from_browser?: boolean | null;
  credential_required?: boolean | null;
  evidence_count?: number | null;
  latest_as_of?: string | null;
  source_frequency?: string | null;
  indicator_codes?: string[] | null;
  missing_indicator_codes?: string[] | null;
  recommended_next_action?: string | null;
  citation_policy?: string | null;
};

export type AiResearchOfficialSourceStatus = {
  status?: string | null;
  citation_policy?: string | null;
  providers?: AiResearchOfficialSourceProvider[];
};

type AiResearchDeskProps = {
  locale: string;
  provider: string;
  generatedAt?: string | null;
  watchlistItems: AiResearchWatchlistItem[];
  followedItems: AiResearchFollowedItem[];
  recommendations: AiResearchRecommendation[];
  recommendationStatus?: string | null;
  recommendationDiagnostics: AiResearchDiagnostic[];
  macroIndicators: AiResearchMacroIndicator[];
  officialSourceStatus?: AiResearchOfficialSourceStatus | null;
  overviewDiagnostics: AiResearchDiagnostic[];
};

type CandidateSymbol = {
  symbol: string;
  market?: string | null;
  name?: string | null;
  source: "watchlist" | "signal" | "followed";
  detail?: string | null;
};

const SELECTED_SYMBOL_LIMIT = 5;
const DISPLAY_CANDIDATE_LIMIT = 8;
const DISPLAY_MACRO_LIMIT = 8;
const DISPLAY_GAP_LIMIT = 8;

export function AiResearchDesk({
  locale,
  provider,
  generatedAt = null,
  watchlistItems,
  followedItems,
  recommendations,
  recommendationStatus = null,
  recommendationDiagnostics,
  macroIndicators,
  officialSourceStatus = null,
  overviewDiagnostics,
}: AiResearchDeskProps) {
  const t = useTranslations("AiResearchDesk");
  const candidates = useMemo(
    () => buildCandidateSymbols(watchlistItems, followedItems, recommendations),
    [watchlistItems, followedItems, recommendations],
  );
  const initialSelectedSymbols = useMemo(
    () => candidates.slice(0, Math.min(3, SELECTED_SYMBOL_LIMIT)).map((candidate) => candidate.symbol),
    [candidates],
  );
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(initialSelectedSymbols);
  const [activeSymbol, setActiveSymbol] = useState(initialSelectedSymbols[0] ?? "");
  const [manualSymbol, setManualSymbol] = useState("");

  const activeSelectedSymbol = selectedSymbols.includes(activeSymbol)
    ? activeSymbol
    : selectedSymbols[0] ?? "";
  const prioritizedMacroIndicators = useMemo(() => prioritizeMacroIndicators(macroIndicators), [macroIndicators]);
  const officialSourceProviders = officialSourceStatus?.providers ?? [];
  const sourceGaps = useMemo(
    () => buildSourceGaps(prioritizedMacroIndicators, overviewDiagnostics, recommendationDiagnostics),
    [overviewDiagnostics, prioritizedMacroIndicators, recommendationDiagnostics],
  );
  const activeSignal = recommendations.find(
    (recommendation) => normalizeSymbol(recommendation.symbol) === activeSelectedSymbol,
  );
  const assistantInitialQuestion = activeSelectedSymbol
    ? t("assistantQuestion", {
        symbol: activeSelectedSymbol,
        signal: activeSignal?.title ?? t("noActiveSignal"),
        macro: buildMacroQuestionContext(prioritizedMacroIndicators, t("macroUnavailable")),
        sources: buildOfficialSourceQuestionContext(
          officialSourceProviders,
          t("sourceStatusNoAction"),
          t("sourceStatusQuestionNoMissing"),
          t("sourceStatusQuestionReview"),
        ),
      })
    : "";

  function addSymbol(rawSymbol: string) {
    const normalizedSymbol = normalizeSymbol(rawSymbol);
    if (!normalizedSymbol) {
      return;
    }
    setSelectedSymbols((currentSymbols) => {
      if (currentSymbols.includes(normalizedSymbol)) {
        return currentSymbols;
      }
      return [...currentSymbols, normalizedSymbol].slice(0, SELECTED_SYMBOL_LIMIT);
    });
    setActiveSymbol(normalizedSymbol);
  }

  function removeSymbol(symbol: string) {
    setSelectedSymbols((currentSymbols) => {
      const nextSymbols = currentSymbols.filter((item) => item !== symbol);
      if (activeSelectedSymbol === symbol) {
        setActiveSymbol(nextSymbols[0] ?? "");
      }
      return nextSymbols;
    });
  }

  function submitManualSymbol(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    for (const symbol of parseSymbols(manualSymbol)) {
      addSymbol(symbol);
    }
    setManualSymbol("");
  }

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[
          { label: t("badge"), variant: "secondary" },
          { label: t("provider", { provider }) },
          ...(generatedAt ? [{ label: t("generatedAt", { date: generatedAt }) }] : []),
        ]}
        metrics={[
          { label: t("metricSelected"), value: String(selectedSymbols.length), description: t("metricSelectedDesc") },
          { label: t("metricSignals"), value: String(recommendations.length), description: t("metricSignalsDesc") },
          { label: t("metricMacro"), value: String(macroIndicators.length), description: t("metricMacroDesc") },
          { label: t("metricGaps"), value: String(sourceGaps.length), description: t("metricGapsDesc") },
        ]}
        actions={
          <>
            <Button size="sm" variant="outline" asChild>
              <Link href="/watchlist">{t("openWatchlist")}</Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/evidence">{t("openMacroResearch")}</Link>
            </Button>
          </>
        }
        warningPanel={
          <div className="border border-warning/35 bg-warning/10 px-3 py-2 text-sm text-foreground">
            {t("researchBoundary")}
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("basketTitle")}</CardTitle>
              <CardDescription>{t("basketDesc", { limit: SELECTED_SYMBOL_LIMIT })}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <form className="flex gap-2" onSubmit={submitManualSymbol}>
                <Input
                  value={manualSymbol}
                  onChange={(event) => setManualSymbol(event.target.value)}
                  placeholder={t("manualPlaceholder")}
                  aria-label={t("manualLabel")}
                />
                <Button type="submit" disabled={parseSymbols(manualSymbol).length === 0}>
                  <Plus className="mr-2 h-4 w-4" />
                  {t("addSymbol")}
                </Button>
              </form>

              {selectedSymbols.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {selectedSymbols.map((symbol) => (
                    <div
                      key={symbol}
                      className={`flex items-center gap-1 rounded-md border px-2 py-1 text-sm ${
                        symbol === activeSelectedSymbol ? "border-primary bg-primary/10" : "bg-background"
                      }`}
                    >
                      <button
                        type="button"
                        className="font-mono font-semibold"
                        onClick={() => setActiveSymbol(symbol)}
                      >
                        {symbol}
                      </button>
                      <button
                        type="button"
                        className="rounded-sm p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                        aria-label={t("removeSymbol", { symbol })}
                        title={t("removeSymbol", { symbol })}
                        onClick={() => removeSymbol(symbol)}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("emptyBasket")}</p>
              )}
            </CardContent>
          </Card>

          <CandidatePanel
            title={t("watchlistCandidates")}
            emptyText={t("noWatchlistCandidates")}
            candidates={candidates.filter((candidate) => candidate.source === "watchlist").slice(0, DISPLAY_CANDIDATE_LIMIT)}
            activeSymbol={activeSelectedSymbol}
            onUseSymbol={addSymbol}
            onActivateSymbol={setActiveSymbol}
          />

          <CandidatePanel
            title={t("followedCandidates")}
            emptyText={t("noFollowedCandidates")}
            candidates={candidates.filter((candidate) => candidate.source === "followed").slice(0, DISPLAY_CANDIDATE_LIMIT)}
            activeSymbol={activeSelectedSymbol}
            onUseSymbol={addSymbol}
            onActivateSymbol={setActiveSymbol}
          />
        </div>

        <div className="space-y-4">
          <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="space-y-4">
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <CardTitle className="text-base">{t("activeSymbolTitle")}</CardTitle>
                      <CardDescription>{t("activeSymbolDesc")}</CardDescription>
                    </div>
                    {activeSelectedSymbol ? (
                      <Badge variant="secondary" className="font-mono">
                        {activeSelectedSymbol}
                      </Badge>
                    ) : null}
                  </div>
                </CardHeader>
                <CardContent>
                  {activeSelectedSymbol ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      <ContextLine label={t("activeSignal")} value={activeSignal?.title ?? t("noActiveSignal")} />
                      <ContextLine
                        label={t("activeMacroContext")}
                        value={buildMacroQuestionContext(prioritizedMacroIndicators, t("macroUnavailable"))}
                      />
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">{t("selectSymbolFirst")}</p>
                  )}
                </CardContent>
              </Card>

              {activeSelectedSymbol ? (
                <MarketAssistantCard
                  key={`${activeSelectedSymbol}-${assistantInitialQuestion}`}
                  symbol={activeSelectedSymbol}
                  locale={locale}
                  provider={provider}
                  initialQuestion={assistantInitialQuestion}
                />
              ) : null}
            </div>

            <div className="space-y-4">
              <ResearchSignalPanel
                recommendations={recommendations}
                recommendationStatus={recommendationStatus}
                activeSymbol={activeSelectedSymbol}
                onUseSymbol={addSymbol}
                onActivateSymbol={setActiveSymbol}
              />
              <MacroContextPanel macroIndicators={prioritizedMacroIndicators.slice(0, DISPLAY_MACRO_LIMIT)} />
              <OfficialSourceStatusPanel
                providers={officialSourceProviders}
                citationPolicy={officialSourceStatus?.citation_policy ?? null}
              />
              <SourceGapPanel sourceGaps={sourceGaps.slice(0, DISPLAY_GAP_LIMIT)} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function CandidatePanel({
  title,
  emptyText,
  candidates,
  activeSymbol,
  onUseSymbol,
  onActivateSymbol,
}: {
  title: string;
  emptyText: string;
  candidates: CandidateSymbol[];
  activeSymbol: string;
  onUseSymbol: (symbol: string) => void;
  onActivateSymbol: (symbol: string) => void;
}) {
  const t = useTranslations("AiResearchDesk");

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {candidates.length > 0 ? (
          <div className="space-y-2">
            {candidates.map((candidate) => (
              <div
                key={`${candidate.source}-${candidate.symbol}`}
                className="flex items-center justify-between gap-3 rounded-md border p-2"
              >
                <button
                  type="button"
                  className="min-w-0 text-left"
                  onClick={() => onActivateSymbol(candidate.symbol)}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold">{candidate.symbol}</span>
                    {candidate.market ? <Badge variant="outline">{candidate.market}</Badge> : null}
                  </div>
                  <div className="truncate text-xs text-muted-foreground">{candidate.name ?? candidate.detail ?? candidate.symbol}</div>
                </button>
                <Button
                  type="button"
                  variant={candidate.symbol === activeSymbol ? "secondary" : "outline"}
                  size="sm"
                  onClick={() => onUseSymbol(candidate.symbol)}
                >
                  {candidate.symbol === activeSymbol ? t("active") : t("useSymbol")}
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{emptyText}</p>
        )}
      </CardContent>
    </Card>
  );
}

function ResearchSignalPanel({
  recommendations,
  recommendationStatus,
  activeSymbol,
  onUseSymbol,
  onActivateSymbol,
}: {
  recommendations: AiResearchRecommendation[];
  recommendationStatus?: string | null;
  activeSymbol: string;
  onUseSymbol: (symbol: string) => void;
  onActivateSymbol: (symbol: string) => void;
}) {
  const t = useTranslations("AiResearchDesk");

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4" />
              {t("signalsTitle")}
            </CardTitle>
            <CardDescription>{t("signalsDesc")}</CardDescription>
          </div>
          {recommendationStatus ? <Badge variant="outline">{recommendationStatus}</Badge> : null}
        </div>
      </CardHeader>
      <CardContent>
        {recommendations.length > 0 ? (
          <ScrollArea className="h-[300px] pr-3">
            <div className="space-y-3">
              {recommendations.map((recommendation, index) => (
                <div key={`${recommendation.symbol}-${recommendation.type}-${index}`} className="rounded-md border p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-semibold">{recommendation.title}</div>
                      <div className="mt-1 flex flex-wrap gap-2">
                        <Badge variant="secondary">{formatSignalType(recommendation.type, t)}</Badge>
                        <Badge variant="outline">{recommendation.symbol}</Badge>
                        {recommendation.confidence !== null && recommendation.confidence !== undefined ? (
                          <Badge variant="outline">
                            {t("confidence", { value: Math.round(recommendation.confidence * 100) })}
                          </Badge>
                        ) : null}
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant={recommendation.symbol === activeSymbol ? "secondary" : "outline"}
                      size="sm"
                      onClick={() => {
                        onUseSymbol(recommendation.symbol);
                        onActivateSymbol(normalizeSymbol(recommendation.symbol));
                      }}
                    >
                      {recommendation.symbol === activeSymbol ? t("active") : t("useSymbol")}
                    </Button>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{recommendation.reason}</p>
                </div>
              ))}
            </div>
          </ScrollArea>
        ) : (
          <p className="text-sm text-muted-foreground">{t("noSignals")}</p>
        )}
      </CardContent>
    </Card>
  );
}

function MacroContextPanel({ macroIndicators }: { macroIndicators: AiResearchMacroIndicator[] }) {
  const t = useTranslations("AiResearchDesk");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileSearch className="h-4 w-4" />
          {t("macroTitle")}
        </CardTitle>
        <CardDescription>{t("macroDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        {macroIndicators.length > 0 ? (
          <div className="space-y-2">
            {macroIndicators.map((indicator) => {
              const citable = isMacroIndicatorCitable(indicator);
              return (
                <div key={indicator.code} className="rounded-md border p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{indicator.name}</div>
                      <div className="font-mono text-xs text-muted-foreground">{indicator.code}</div>
                    </div>
                    <Badge variant={citable ? "secondary" : "outline"}>
                      {citable ? t("macroCitable") : t("macroGap")}
                    </Badge>
                  </div>
                  <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                    <div>{t("macroValue", { value: formatMacroValue(indicator, t("unavailable")) })}</div>
                    <div>{t("macroAsOf", { date: indicator.as_of ?? t("unavailable") })}</div>
                    <div>{t("macroRegion", { region: indicator.region ?? t("unavailable") })}</div>
                    <div>{t("macroSource", { source: indicator.source ?? indicator.no_data_reason ?? t("unavailable") })}</div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t("noMacro")}</p>
        )}
      </CardContent>
    </Card>
  );
}

function OfficialSourceStatusPanel({
  providers,
  citationPolicy,
}: {
  providers: AiResearchOfficialSourceProvider[];
  citationPolicy?: string | null;
}) {
  const t = useTranslations("AiResearchDesk");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("sourceStatusTitle")}</CardTitle>
        <CardDescription>{t("sourceStatusDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        {providers.length > 0 ? (
          <div className="space-y-2">
            {providers.map((provider) => (
              <div key={provider.provider} className="rounded-md border p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{provider.label}</div>
                    <div className="font-mono text-xs text-muted-foreground">{provider.provider}</div>
                  </div>
                  <Badge variant={provider.status === "ok" ? "secondary" : "outline"}>
                    {formatSourceStatus(provider.status, t("unavailable"))}
                  </Badge>
                </div>
                <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                  <div>
                    {t("sourceStatusEvidence", {
                      count: provider.evidence_count ?? 0,
                    })}
                  </div>
                  <div>{t("sourceStatusLatest", { date: provider.latest_as_of ?? t("unavailable") })}</div>
                  <div>
                    {t("sourceStatusMissing", {
                      codes: formatCodeList(provider.missing_indicator_codes, t("unavailable")),
                    })}
                  </div>
                  <div>
                    {provider.can_refresh_from_browser
                      ? t("sourceStatusRefreshReady")
                      : t("sourceStatusRefreshBlocked")}
                  </div>
                </div>
                {provider.recommended_next_action ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {t("sourceStatusNextAction", { action: provider.recommended_next_action })}
                  </p>
                ) : null}
                <p className="mt-2 text-xs text-muted-foreground">
                  {t("sourceStatusCitationPolicy", {
                    policy: provider.citation_policy ?? citationPolicy ?? t("unavailable"),
                  })}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t("sourceStatusUnavailable")}</p>
        )}
      </CardContent>
    </Card>
  );
}

function SourceGapPanel({ sourceGaps }: { sourceGaps: AiResearchDiagnostic[] }) {
  const t = useTranslations("AiResearchDesk");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("gapsTitle")}</CardTitle>
        <CardDescription>{t("gapsDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        {sourceGaps.length > 0 ? (
          <div className="space-y-2">
            {sourceGaps.map((gap, index) => (
              <div key={`${gap.source ?? "gap"}-${gap.code ?? gap.status ?? index}`} className="rounded-md border p-3 text-sm">
                <div className="flex flex-wrap gap-2">
                  {gap.source ? <Badge variant="outline">{gap.source}</Badge> : null}
                  {gap.code ? <Badge variant="secondary">{gap.code}</Badge> : null}
                  {gap.status ? <Badge variant="outline">{gap.status}</Badge> : null}
                </div>
                <p className="mt-2 text-muted-foreground">{getGapMessage(gap, t)}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t("noGaps")}</p>
        )}
      </CardContent>
    </Card>
  );
}

function ContextLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-muted/20 p-3">
      <div className="text-xs font-medium uppercase text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm">{value}</div>
    </div>
  );
}

function buildCandidateSymbols(
  watchlistItems: AiResearchWatchlistItem[],
  followedItems: AiResearchFollowedItem[],
  recommendations: AiResearchRecommendation[],
): CandidateSymbol[] {
  const candidates = new Map<string, CandidateSymbol>();

  for (const item of watchlistItems) {
    const symbol = normalizeSymbol(item.symbol);
    if (!symbol) {
      continue;
    }
    candidates.set(symbol, {
      symbol,
      market: item.market,
      name: item.name,
      source: "watchlist",
      detail: item.alert_status?.triggered ? "alert" : null,
    });
  }

  for (const recommendation of recommendations) {
    const symbol = normalizeSymbol(recommendation.symbol);
    if (!symbol || candidates.has(symbol)) {
      continue;
    }
    candidates.set(symbol, {
      symbol,
      source: "signal",
      detail: recommendation.title,
    });
  }

  for (const item of followedItems) {
    const symbol = normalizeSymbol(item.symbol);
    if (!symbol || candidates.has(symbol)) {
      continue;
    }
    candidates.set(symbol, {
      symbol,
      market: item.market,
      name: item.name,
      source: "followed",
      detail: item.freshness ?? item.status ?? null,
    });
  }

  return [...candidates.values()];
}

function prioritizeMacroIndicators(indicators: AiResearchMacroIndicator[]): AiResearchMacroIndicator[] {
  return [...indicators].sort((left, right) => {
    const leftBuffett = left.code.includes("buffett") ? 0 : 1;
    const rightBuffett = right.code.includes("buffett") ? 0 : 1;
    if (leftBuffett !== rightBuffett) {
      return leftBuffett - rightBuffett;
    }
    const leftCitable = isMacroIndicatorCitable(left) ? 0 : 1;
    const rightCitable = isMacroIndicatorCitable(right) ? 0 : 1;
    if (leftCitable !== rightCitable) {
      return leftCitable - rightCitable;
    }
    return left.code.localeCompare(right.code);
  });
}

function buildSourceGaps(
  macroIndicators: AiResearchMacroIndicator[],
  overviewDiagnostics: AiResearchDiagnostic[],
  recommendationDiagnostics: AiResearchDiagnostic[],
): AiResearchDiagnostic[] {
  const macroGaps = macroIndicators
    .filter((indicator) => !isMacroIndicatorCitable(indicator))
    .map((indicator) => ({
      source: "macro_indicators",
      status: indicator.status ?? "no_data",
      code: indicator.code,
      message: indicator.no_data_reason ?? `${indicator.name} is not available as citable local evidence yet.`,
    }));

  return [...macroGaps, ...overviewDiagnostics, ...recommendationDiagnostics].filter(
    (diagnostic) => diagnostic.message || diagnostic.code || diagnostic.status,
  );
}

function buildMacroQuestionContext(indicators: AiResearchMacroIndicator[], fallback: string): string {
  const contexts = indicators.slice(0, 3).map((indicator) => {
    const value = formatMacroValue(indicator, "unavailable");
    return `${indicator.name}: ${value}`;
  });
  return contexts.length > 0 ? contexts.join("; ") : fallback;
}

function buildOfficialSourceQuestionContext(
  providers: AiResearchOfficialSourceProvider[],
  fallback: string,
  noMissingCodesLabel: string,
  reviewSourceStatusLabel: string,
): string {
  const contexts = providers
    .filter((provider) => provider.status !== "ok" || (provider.missing_indicator_codes?.length ?? 0) > 0)
    .slice(0, 2)
    .map((provider) => {
      const missingCodes = formatCodeList(provider.missing_indicator_codes, noMissingCodesLabel);
      const action = provider.recommended_next_action ?? provider.status ?? reviewSourceStatusLabel;
      return `${provider.label}: ${missingCodes}; ${action}`;
    });
  return contexts.length > 0 ? contexts.join("; ") : fallback;
}

function isMacroIndicatorCitable(indicator: AiResearchMacroIndicator): boolean {
  return indicator.value !== null && indicator.value !== undefined && Boolean(indicator.as_of) && Boolean(indicator.source);
}

function formatMacroValue(indicator: AiResearchMacroIndicator, unavailableLabel: string): string {
  if (indicator.value === null || indicator.value === undefined) {
    return unavailableLabel;
  }
  const formattedValue = indicator.value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return indicator.unit ? `${formattedValue}${indicator.unit === "percent" ? "%" : ` ${indicator.unit}`}` : formattedValue;
}

function formatSourceStatus(status: string | null | undefined, unavailableLabel: string): string {
  if (!status) {
    return unavailableLabel;
  }
  return status.replaceAll("_", " ");
}

function formatCodeList(codes: string[] | null | undefined, fallback: string): string {
  return codes && codes.length > 0 ? codes.join(", ") : fallback;
}

function formatSignalType(
  type: AiResearchRecommendation["type"],
  t: (key: "signalBreakout" | "signalVolume" | "signalOversold" | "signalMomentum") => string,
): string {
  if (type === "breakout") {
    return t("signalBreakout");
  }
  if (type === "volume_anomaly") {
    return t("signalVolume");
  }
  if (type === "oversold_rebound") {
    return t("signalOversold");
  }
  if (type === "strong_momentum") {
    return t("signalMomentum");
  }
  return String(type);
}

function normalizeSymbol(symbol: string): string {
  return symbol.trim().toUpperCase();
}

function parseSymbols(input: string): string[] {
  return input
    .split(/[\s,，]+/)
    .map(normalizeSymbol)
    .filter(Boolean);
}

function getGapMessage(gap: AiResearchDiagnostic, t: (key: "marketOverviewUnavailable" | "unknownGap") => string): string {
  if (gap.code === "MARKET_OVERVIEW_UNAVAILABLE") {
    return t("marketOverviewUnavailable");
  }
  return gap.message ?? t("unknownGap");
}
