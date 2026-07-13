"use client";

import * as React from "react";
import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  CircleMinus,
  CirclePlus,
  Database,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  DAILY_RESEARCH_SHORTLIST_PUBLISHED_EVENT,
  type DailyResearchDiagnostic,
  type DailyResearchFactor,
  type DailyResearchGap,
  type DailyResearchInvalidation,
  type DailyResearchShortlistPayload,
  type GenerateDailyResearchShortlistRequest,
} from "@/lib/daily-research-shortlist";
import { Link } from "@/src/i18n/routing";

type DailyResearchShortlistPanelProps = {
  locale: string;
  initialPayload: DailyResearchShortlistPayload | null;
  initialLoadFailed?: boolean;
  profileId?: string;
};

export function DailyResearchShortlistPanel({
  locale,
  initialPayload,
  initialLoadFailed = false,
  profileId = "balanced_research",
}: DailyResearchShortlistPanelProps) {
  const t = useTranslations("DailyResearchShortlist");
  const router = useRouter();
  const [payload, setPayload] = React.useState(initialPayload);
  const [generating, setGenerating] = React.useState(false);
  const [generationError, setGenerationError] = React.useState<string | null>(null);

  async function generateShortlist() {
    setGenerating(true);
    setGenerationError(null);
    try {
      const requestPayload: GenerateDailyResearchShortlistRequest = {
        profile_id: profileId,
        market: "CN",
        asset_type: "stock",
        shortlist_limit: 10,
        locale: locale === "zh" ? "zh" : "en",
        use_llm: true,
        overrides: {},
      };
      const response = await fetch("/api/research-shortlists/generate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(requestPayload),
      });
      const responsePayload = (await response.json()) as DailyResearchShortlistPayload & {
        detail?: unknown;
      };
      if (!response.ok) {
        throw new Error(localizeGenerationError(response.status, responsePayload.detail));
      }
      if (responsePayload.run?.id) {
        window.dispatchEvent(
          new CustomEvent(DAILY_RESEARCH_SHORTLIST_PUBLISHED_EVENT, {
            detail: { runId: responsePayload.run.id },
          }),
        );
      }
      setPayload(responsePayload);
      router.refresh();
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : t("generateFailed"));
    } finally {
      setGenerating(false);
    }
  }

  function handoffSymbol(symbol: string) {
    window.dispatchEvent(
      new CustomEvent("stock-discovery:select-symbol", { detail: { symbol } }),
    );
    document.getElementById("ai-research-desk")?.scrollIntoView({ behavior: "smooth" });
  }

  const run = payload?.run ?? null;
  const items = payload?.items ?? [];
  const counts = run?.counts ?? run?.coverage ?? null;
  const evidenceCoverage = Object.entries(run?.coverage?.evidence ?? {});
  const hasSnapshot = Boolean(run && items.length > 0);
  const factorLabels: Record<string, string> = {
    max_pe_ratio: t("factorMaxPeRatio"),
    min_revenue_growth: t("factorMinRevenueGrowth"),
    min_net_margin: t("factorMinNetMargin"),
    min_rsi: t("factorMinRsi"),
    max_rsi: t("factorMaxRsi"),
    require_price_above_ma: t("factorPriceAboveMa"),
    price_above_ma: t("factorPriceAboveMa"),
    required_pattern_codes: t("factorRequiredPatterns"),
    min_mfi: t("factorMinMfi"),
    max_mfi: t("factorMaxMfi"),
    min_william_r: t("factorMinWilliamR"),
    max_william_r: t("factorMaxWilliamR"),
    min_chip_benefit_ratio: t("factorMinChipBenefitRatio"),
    max_chip_benefit_ratio: t("factorMaxChipBenefitRatio"),
    min_latest_volume: t("factorMinLatestVolume"),
    min_traded_amount: t("factorMinTradedAmount"),
    min_news_article_count: t("factorMinNewsArticleCount"),
    required_news_sentiment: t("factorRequiredNewsSentiment"),
    min_news_sentiment_confidence: t("factorMinNewsSentimentConfidence"),
  };

  function localizeGap(value: DailyResearchGap): string {
    if (typeof value === "string") {
      return t("gapUnknown", { code: t("unavailable") });
    }
    switch (value.code) {
      case "TECHNICAL_AS_OF_UNAVAILABLE":
        return t("gapTechnicalAsOfUnavailable");
      case "TECHNICAL_BEFORE_DECISION_DATE":
        return t("gapTechnicalBeforeDecisionDate", {
          asOf: formatUnknown(value.as_of, t("unavailable")),
          decisionDate: formatUnknown(value.decision_date, t("unavailable")),
        });
      case "FUNDAMENTALS_UNAVAILABLE":
        return t("gapFundamentalsUnavailable");
      case "FUNDAMENTALS_BEFORE_DECISION_DATE":
        return t("gapFundamentalsBeforeDecisionDate", {
          asOf: formatUnknown(value.as_of, t("unavailable")),
          decisionDate: formatUnknown(value.decision_date, t("unavailable")),
        });
      case "NEWS_NOT_EVALUATED_BY_PROFILE":
        return t("gapNewsNotEvaluatedByProfile");
      default:
        return t("gapUnknown", {
          code: formatUnknown(value.code ?? value.source, t("unavailable")),
        });
    }
  }

  function localizeInvalidation(value: DailyResearchInvalidation): string {
    if (typeof value === "string") {
      return t("invalidationUnknown", { code: t("unavailable") });
    }
    const ruleCode = typeof value.rule === "string" ? value.rule : value.code;
    const ruleLabel = ruleCode ? factorLabels[ruleCode] : undefined;
    if (!ruleLabel) {
      return t("invalidationUnknown", {
        code: formatUnknown(ruleCode ?? value.field, t("unavailable")),
      });
    }
    if (value.operator !== undefined && value.threshold !== undefined) {
      return t("invalidationTemplate", {
        rule: ruleLabel,
        operator: formatUnknown(value.operator, t("unavailable")),
        threshold: formatUnknown(value.threshold, t("unavailable")),
      });
    }
    return t("invalidationRuleOnly", { rule: ruleLabel });
  }

  function localizeStatus(status: string): string {
    switch (status) {
      case "ok":
      case "ready":
      case "committed":
        return t("statusReady");
      case "no_data":
        return t("statusNoData");
      case "degraded":
      case "partial":
        return t("statusDegraded");
      case "conflict":
        return t("statusConflict");
      case "unavailable":
        return t("statusUnavailable");
      case "error":
      case "failed":
        return t("statusFailed");
      default:
        return t("statusUnknown", { status });
    }
  }

  function localizeGenerationError(status: number, detail: unknown): string {
    const code = getStructuredCode(detail);
    if (status === 409) {
      switch (code) {
        case "NO_IN_SCOPE_DAILY_BARS":
          return t("readinessNoDailyBars");
        case "EVIDENCE_COVERAGE_NOT_READY":
          return t("readinessCoverageNotReady");
        case "NO_DECISION_DATE_ALIGNED_CANDIDATES":
          return t("readinessNoAlignedCandidates");
        case "ENTRY_BAR_CHANGED_DURING_GENERATION":
          return t("readinessEntryBarChanged");
        default:
          return t("readinessUnknown", { code: code ?? t("unavailable") });
      }
    }
    return status === 400 ? t("invalidRequest") : t("generateFailed");
  }

  function localizeDiagnostic(diagnostic: DailyResearchDiagnostic): string {
    const count = formatCount(diagnostic.count ?? 1);
    switch (diagnostic.code) {
      case "MISSING_DAILY_BAR":
        return t("diagnosticMissingDailyBar", { count });
      case "MISSING_FUNDAMENTALS":
        return t("diagnosticMissingFundamentals", { count });
      case "SELECTION_RULE_NOT_MATCHED": {
        const ruleCode =
          typeof diagnostic.rule === "string"
            ? diagnostic.rule
            : typeof diagnostic.dimension === "string"
              ? diagnostic.dimension
              : null;
        return t("diagnosticRuleNotMatched", {
          count,
          rule: ruleCode ? factorLabels[ruleCode] ?? humanize(ruleCode) : t("unavailable"),
        });
      }
      case "POST_DECISION_EVIDENCE":
        return t("diagnosticPostDecisionEvidence", { count });
      case "STALE_ENTRY_BAR":
        return t("diagnosticStaleEntryBar", { count });
      default:
        return t("diagnosticUnknown", {
          code: diagnostic.code ?? t("unavailable"),
        });
    }
  }

  return (
    <FinancialTerminalCard aria-busy={generating}>
      <FinancialTerminalCardHeader>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="font-mono text-[10px] uppercase">
                {t("badge")}
              </Badge>
              <Badge variant="outline">
                <ShieldCheck className="h-3 w-3" />
                {t("researchOnly")}
              </Badge>
              {payload?.status ? (
                <Badge variant="secondary">{localizeStatus(payload.status)}</Badge>
              ) : null}
            </div>
            <CardTitle
              className="flex items-center gap-2 text-lg"
              role="heading"
              aria-level={2}
            >
              <CalendarDays className="h-5 w-5 text-primary" />
              {t("title")}
            </CardTitle>
            <CardDescription className="mt-1 max-w-4xl">{t("description")}</CardDescription>
          </div>
          <Button
            type="button"
            size="sm"
            onClick={() => void generateShortlist()}
            disabled={generating}
          >
            <RefreshCw className={generating ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            {generating ? t("generating") : run ? t("regenerate") : t("generate")}
          </Button>
        </div>
      </FinancialTerminalCardHeader>

      <FinancialTerminalCardContent className="space-y-4">
        <div aria-live="polite" className="sr-only">
          {generating ? t("generating") : generationError ?? ""}
        </div>

        {generationError ? (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{generationError}</span>
          </div>
        ) : null}

        {run ? (
          <>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
              <Metric label={t("decisionDate")} value={run.decision_date} />
              <Metric label={t("generatedAt")} value={formatDateTime(run.generated_at, locale)} />
              <Metric label={t("profile")} value={run.profile_id} />
              <Metric label={t("evaluated")} value={formatCount(counts?.evaluated_count)} />
              <Metric label={t("matched")} value={formatCount(counts?.matched_count)} />
              <Metric label={t("returned")} value={formatCount(counts?.returned_count ?? items.length)} />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={isCoverageReady(run.coverage) ? "default" : "destructive"}>
                <Database className="h-3 w-3" />
                {isCoverageReady(run.coverage) ? t("coverageReady") : t("coverageNotReady")}
              </Badge>
              <Badge variant="outline">{run.scoring_model}</Badge>
              <Badge variant={run.model?.used_llm ? "secondary" : "outline"}>
                {run.model?.used_llm ? t("aiExplanation") : t("deterministicExplanation")}
              </Badge>
              {evidenceCoverage.map(([source, coverage]) => (
                <Badge key={source} variant="outline">
                  {humanize(source)} {formatPercent(coverage.coverage_ratio)}
                </Badge>
              ))}
            </div>
          </>
        ) : null}

        {hasSnapshot && run ? (
          <>
            <FinancialTerminalSurface
              className="overflow-x-auto p-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              role="region"
              aria-label={t("comparisonTable")}
              tabIndex={0}
            >
              <Table className="min-w-[1120px] table-fixed">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">{t("rank")}</TableHead>
                    <TableHead className="w-48">{t("candidate")}</TableHead>
                    <TableHead className="w-28">{t("score")}</TableHead>
                    <TableHead className="w-72">{t("researchCase")}</TableHead>
                    <TableHead className="w-64">{t("gapsAndInvalidation")}</TableHead>
                    <TableHead className="w-60">{t("evidenceAndActions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => {
                    const score = item.total_score ?? item.score ?? 0;
                    return (
                      <TableRow key={item.id || item.symbol} className="align-top">
                        <TableCell className="font-mono text-base font-semibold">
                          {item.rank}
                        </TableCell>
                        <TableCell>
                          <div className="font-mono font-semibold">{item.symbol}</div>
                          <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                            {item.name || t("unnamed")}
                          </div>
                          <div className="mt-2 text-[11px] text-muted-foreground">
                            {formatEntryObservation(item.entry_observation, t("unavailable"))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="font-mono text-base font-semibold tabular-nums">
                            {formatScore(score)}
                          </div>
                          <div className="mt-1 text-[11px] text-muted-foreground">
                            {t("minimumBuffer", {
                              value: formatPercent(item.minimum_rule_buffer),
                            })}
                          </div>
                        </TableCell>
                        <TableCell>
                          <FactorList
                            icon={<CirclePlus className="h-3.5 w-3.5 text-emerald-600" />}
                            label={t("supportingFactors")}
                            factors={item.supporting_factors ?? []}
                            emptyLabel={t("noSupportingFactors")}
                            factorLabels={factorLabels}
                          />
                          <FactorList
                            className="mt-3"
                            icon={<CircleMinus className="h-3.5 w-3.5 text-amber-600" />}
                            label={t("opposingFactors")}
                            factors={item.opposing_factors ?? []}
                            emptyLabel={t("noOpposingFactors")}
                            factorLabels={factorLabels}
                          />
                        </TableCell>
                        <TableCell>
                          <RecordList
                            label={t("dataGaps")}
                            values={item.data_gaps ?? []}
                            emptyLabel={t("noDataGaps")}
                            formatValue={localizeGap}
                          />
                          <RecordList
                            className="mt-3"
                            label={t("invalidation")}
                            values={item.invalidation_conditions ?? []}
                            emptyLabel={t("noInvalidation")}
                            formatValue={localizeInvalidation}
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                            {t("evidenceCount", {
                              count: item.evidence_count ?? item.evidence_citations?.length ?? 0,
                            })}
                          </div>
                          <div className="mt-3 flex flex-col gap-2">
                            <Button size="sm" variant="outline" asChild>
                              <Link
                                href={`/instruments/${item.symbol}?research_snapshot_id=${run.id}`}
                              >
                                {t("deepAnalysis")}
                                <ArrowRight className="h-3.5 w-3.5" />
                              </Link>
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => handoffSymbol(item.symbol)}
                            >
                              {t("useInDesk")}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </FinancialTerminalSurface>

            <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_360px]">
              <FinancialTerminalSurface className="p-3">
                <div className="text-sm font-semibold">{t("explanation")}</div>
                {normalizeLocale(run.locale) === normalizeLocale(locale) ? (
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-6 text-muted-foreground">
                    {run.explanation_markdown || t("noExplanation")}
                  </pre>
                ) : (
                  <p role="status" className="mt-2 text-sm leading-6 text-muted-foreground">
                    {run.locale
                      ? t("explanationLocaleMismatch", {
                          language:
                            normalizeLocale(run.locale) === "zh"
                              ? t("languageChinese")
                              : t("languageEnglish"),
                        })
                      : t("explanationLocaleUnavailable")}
                  </p>
                )}
              </FinancialTerminalSurface>
              <FinancialTerminalSurface className="p-3">
                <div className="text-sm font-semibold">{t("diagnostics")}</div>
                {(run.diagnostics ?? []).length > 0 ? (
                  <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                    {(run.diagnostics ?? []).slice(0, 8).map((diagnostic, index) => (
                      <li key={`${diagnostic.code ?? "diagnostic"}-${index}`}>
                        {localizeDiagnostic(diagnostic)}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-xs text-muted-foreground">{t("noDiagnostics")}</p>
                )}
              </FinancialTerminalSurface>
            </div>
          </>
        ) : null}

        {!run && initialLoadFailed ? (
          <div role="alert">
            <ErrorState title={t("loadFailed")} description={t("loadFailedDescription")} />
          </div>
        ) : null}

        {!run && !initialLoadFailed ? (
          <EmptyState title={t("emptyTitle")} description={t("emptyDescription")} />
        ) : null}

        {run && items.length === 0 ? (
          <EmptyState title={t("emptyRunTitle")} description={t("emptyRunDescription")} />
        ) : null}

        <FinancialTerminalSurface className="flex items-start gap-2 border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <span>{t("safetyBoundary")}</span>
        </FinancialTerminalSurface>
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <FinancialTerminalSurface className="min-w-0 p-3">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className="mt-1 truncate font-mono text-sm font-semibold" title={value}>
        {value}
      </div>
    </FinancialTerminalSurface>
  );
}

function FactorList({
  label,
  factors,
  emptyLabel,
  icon,
  className,
  factorLabels,
}: {
  label: string;
  factors: DailyResearchFactor[];
  emptyLabel: string;
  icon: React.ReactNode;
  className?: string;
  factorLabels: Record<string, string>;
}) {
  return (
    <div className={className}>
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase text-muted-foreground">
        {icon}
        {label}
      </div>
      {factors.length > 0 ? (
        <ul className="mt-1.5 space-y-1 text-xs">
          {factors.slice(0, 3).map((factor, index) => (
            <li key={`${factor.code ?? factor.rule_code ?? "factor"}-${index}`} className="line-clamp-2">
              {describeFactor(factor, factorLabels)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1.5 text-xs text-muted-foreground">{emptyLabel}</p>
      )}
    </div>
  );
}

function RecordList({
  label,
  values,
  emptyLabel,
  className,
  formatValue,
}: {
  label: string;
  values: Array<DailyResearchGap | DailyResearchInvalidation>;
  emptyLabel: string;
  className?: string;
  formatValue: (value: DailyResearchGap | DailyResearchInvalidation) => string;
}) {
  return (
    <div className={className}>
      <div className="text-[11px] font-semibold uppercase text-muted-foreground">{label}</div>
      {values.length > 0 ? (
        <ul className="mt-1.5 space-y-1 text-xs">
          {values.slice(0, 3).map((value, index) => (
            <li key={index} className="line-clamp-2">
              {formatValue(value)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1.5 text-xs text-muted-foreground">{emptyLabel}</p>
      )}
    </div>
  );
}

function describeFactor(
  factor: DailyResearchFactor,
  factorLabels: Record<string, string>,
): string {
  const code = factor.code ?? factor.rule_code ?? factor.field ?? "factor";
  const label = factorLabels[code] ?? humanize(code);
  if (typeof factor.buffer === "number") {
    return `${String(label)} (${formatPercent(factor.buffer)})`;
  }
  return String(label);
}

function formatUnknown(value: unknown, unavailable: string): string {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(", ") || unavailable;
  }
  if (value === null || value === undefined || value === "") {
    return unavailable;
  }
  return String(value);
}

function formatEntryObservation(
  observation: { trade_date?: string | null; close?: number | null } | null | undefined,
  unavailable: string,
): string {
  if (!observation?.trade_date || typeof observation.close !== "number") {
    return unavailable;
  }
  return `${observation.trade_date} / ${observation.close.toLocaleString(undefined, { maximumFractionDigits: 4 })}`;
}

function formatDateTime(value: string, locale: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Shanghai",
  }).format(date);
}

function formatCount(value: number | null | undefined): string {
  return typeof value === "number" ? value.toLocaleString() : "-";
}

function formatScore(value: number): string {
  return Number.isFinite(value) ? value.toFixed(4) : "-";
}

function formatPercent(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${Math.round(value * 100)}%`
    : "-";
}

function isCoverageReady(coverage: { ready?: boolean; status?: string | null } | null | undefined): boolean {
  if (typeof coverage?.ready === "boolean") {
    return coverage.ready;
  }
  return coverage?.status === "ok" || coverage?.status === "ready";
}

function getStructuredCode(detail: unknown): string | null {
  if (detail && typeof detail === "object" && "code" in detail) {
    const code = (detail as { code?: unknown }).code;
    return typeof code === "string" && code.trim() ? code : null;
  }
  return null;
}

function normalizeLocale(locale: string | null | undefined): "en" | "zh" | null {
  if (locale?.toLowerCase().startsWith("zh")) {
    return "zh";
  }
  if (locale?.toLowerCase().startsWith("en")) {
    return "en";
  }
  return null;
}

function humanize(value: string): string {
  return value.replaceAll("_", " ");
}
