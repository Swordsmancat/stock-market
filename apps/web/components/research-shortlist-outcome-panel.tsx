"use client";

import * as React from "react";
import { Activity, AlertTriangle, BarChart3, RefreshCw, ShieldCheck } from "lucide-react";
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
import { DAILY_RESEARCH_SHORTLIST_PUBLISHED_EVENT } from "@/lib/daily-research-shortlist";
import {
  RESEARCH_OUTCOME_HORIZONS,
  type ResearchCandidateHorizonOutcome,
  type ResearchOutcomeDiagnostic,
  type ResearchOutcomeHorizon,
  type ResearchOutcomeSummary,
  type ResearchShortlistOutcomePayload,
  type ResearchShortlistOutcomeTrackingPayload,
} from "@/lib/research-shortlist-outcomes";

type ResearchShortlistOutcomePanelProps = {
  locale: string;
  initialPayload: ResearchShortlistOutcomeTrackingPayload | null;
  initialLoadFailed?: boolean;
};

export function ResearchShortlistOutcomePanel({
  locale,
  initialPayload,
  initialLoadFailed = false,
}: ResearchShortlistOutcomePanelProps) {
  const t = useTranslations("ResearchShortlistOutcomes");
  const router = useRouter();
  const [tracking, setTracking] = React.useState(initialPayload);
  const [updating, setUpdating] = React.useState(false);
  const [updateFailed, setUpdateFailed] = React.useState(false);
  const [awaitingRunId, setAwaitingRunId] = React.useState<string | null>(null);
  const currentRunId = tracking?.latest?.run.id ?? null;
  const latest = awaitingRunId ? null : tracking?.latest ?? null;

  React.useEffect(() => {
    setTracking(initialPayload);
    setAwaitingRunId(null);
  }, [initialPayload]);

  React.useEffect(() => {
    function handlePublished(event: Event) {
      const runId = (event as CustomEvent<{ runId?: unknown }>).detail?.runId;
      if (typeof runId !== "string" || !runId || runId === currentRunId) {
        return;
      }
      setUpdateFailed(false);
      setAwaitingRunId(runId);
    }

    window.addEventListener(DAILY_RESEARCH_SHORTLIST_PUBLISHED_EVENT, handlePublished);
    return () => {
      window.removeEventListener(DAILY_RESEARCH_SHORTLIST_PUBLISHED_EVENT, handlePublished);
    };
  }, [currentRunId]);

  async function updateOutcomes() {
    if (!latest || updating) {
      return;
    }
    setUpdating(true);
    setUpdateFailed(false);
    try {
      const response = await fetch(
        `/api/research-shortlists/${encodeURIComponent(latest.run.id)}/outcomes/evaluate`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: "{}",
        },
      );
      if (!response.ok) {
        throw new Error("outcome evaluation failed");
      }
      const next = (await response.json()) as ResearchShortlistOutcomePayload;
      if (!next.run?.id || next.run.id !== latest.run.id) {
        throw new Error("outcome evaluation returned a different cohort");
      }
      setTracking((current) => current ? {
        ...current,
        latest: next,
        history: current.history.map((entry) => entry.run.id === next.run.id
          ? { run: next.run, summaries: next.summaries }
          : entry),
      } : current);
      router.refresh();
    } catch {
      setUpdateFailed(true);
    } finally {
      setUpdating(false);
    }
  }

  function localizeDiagnostic(code: string | null): string {
    switch (code) {
      case "ENTRY_BAR_MISSING":
        return t("diagnosticEntryBarMissing");
      case "ENTRY_BAR_REVISED":
        return t("diagnosticEntryBarRevised");
      case "ENTRY_ADJUSTMENT_UNKNOWN":
        return t("diagnosticEntryAdjustmentUnknown");
      case "ENTRY_BAR_INCOMPLETE":
        return t("diagnosticEntryBarIncomplete");
      case "INCOMPLETE_FORWARD_BAR_IGNORED":
        return t("diagnosticIncompleteForwardBar");
      case "FORWARD_PRICE_INVALID":
        return t("diagnosticForwardPriceInvalid");
      case "FORWARD_OHLC_INVALID":
        return t("diagnosticForwardOhlcInvalid");
      case "FORWARD_ADJUSTMENT_UNKNOWN":
        return t("diagnosticForwardAdjustmentUnknown");
      case "FORWARD_ADJUSTMENT_MISMATCH":
        return t("diagnosticForwardAdjustmentMismatch");
      case "INSTRUMENT_INACTIVE":
        return t("diagnosticInstrumentInactive");
      case "BENCHMARK_INSTRUMENT_MISSING":
        return t("diagnosticBenchmarkInstrumentMissing");
      case "BENCHMARK_ENTRY_MISSING":
        return t("diagnosticBenchmarkEntryMissing");
      case "BENCHMARK_EXIT_MISSING":
        return t("diagnosticBenchmarkExitMissing");
      case "BENCHMARK_PRICE_INVALID":
        return t("diagnosticBenchmarkPriceInvalid");
      case "BENCHMARK_ADJUSTMENT_UNKNOWN":
        return t("diagnosticBenchmarkAdjustmentUnknown");
      case "BENCHMARK_ADJUSTMENT_MISMATCH":
        return t("diagnosticBenchmarkAdjustmentMismatch");
      case "QFQ_PROXY_BASIS":
        return t("diagnosticQfqProxyBasis");
      case "PROVENANCE_ADJUSTMENT_CORRECTED":
        return t("diagnosticAdjustmentCorrected");
      default:
        return t("diagnosticUnknown", { code: code ?? t("unavailable") });
    }
  }

  function renderDiagnostics(diagnostics: ResearchOutcomeDiagnostic[] | undefined) {
    const codes = diagnosticCodes(diagnostics);
    if (codes.length === 0) {
      return null;
    }
    return (
      <ul className="space-y-0.5 text-[11px] text-muted-foreground">
        {codes.map((code) => (
          <li key={code ?? "unstructured"}>{localizeDiagnostic(code)}</li>
        ))}
      </ul>
    );
  }

  function renderHorizon(outcome: ResearchCandidateHorizonOutcome | undefined) {
    if (!outcome) {
      return <span className="text-xs text-muted-foreground">{t("unavailable")}</span>;
    }
    if (outcome.status === "pending") {
      return (
        <div className="space-y-1.5">
          <Badge variant="outline">{t("statusPending")}</Badge>
          <div className="font-mono text-xs tabular-nums">
            {t("pendingProgress", {
              available: Math.min(outcome.available_forward_bars, outcome.horizon_sessions),
              horizon: outcome.horizon_sessions,
            })}
          </div>
          {outcome.ready_for_evaluation ? (
            <div className="text-[11px] font-medium text-primary">{t("readyForEvaluation")}</div>
          ) : null}
          {renderDiagnostics(outcome.diagnostics)}
        </div>
      );
    }
    if (outcome.status === "blocked") {
      return (
        <div className="space-y-1.5">
          <Badge variant="destructive">{t("statusBlocked")}</Badge>
          {renderDiagnostics(outcome.diagnostics) ?? (
            <div className="text-xs text-muted-foreground">{localizeDiagnostic(null)}</div>
          )}
        </div>
      );
    }
    const benchmark = outcome.benchmark;
    return (
      <div className="space-y-1">
        <Badge variant="secondary">{t("statusEvaluated")}</Badge>
        <div className="font-mono text-xs tabular-nums">
          {t("returnValue", { value: formatSignedRatio(outcome.return_ratio, locale) })}
        </div>
        <div className="font-mono text-xs tabular-nums text-muted-foreground">
          {t("drawdownValue", { value: formatSignedRatio(outcome.drawdown_ratio, locale) })}
        </div>
        {benchmark?.status === "evaluated" && benchmark.excess_return_ratio !== null && benchmark.excess_return_ratio !== undefined ? (
          <div className="font-mono text-xs tabular-nums text-muted-foreground">
            {t("benchmarkExcessValue", {
              value: formatSignedRatio(benchmark.excess_return_ratio, locale),
            })}
          </div>
        ) : (
          <div className="text-[11px] text-muted-foreground">
            <div>{t("benchmarkUnavailable")}</div>
            {renderDiagnostics(benchmark?.diagnostics)}
          </div>
        )}
        {renderDiagnostics(outcome.diagnostics)}
      </div>
    );
  }

  return (
    <FinancialTerminalCard aria-busy={updating}>
      <FinancialTerminalCardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="font-mono text-[10px] uppercase">
                {t("badge")}
              </Badge>
              <Badge variant="outline">
                <ShieldCheck className="h-3 w-3" />
                {t("researchOnly")}
              </Badge>
            </div>
            <CardTitle className="flex items-center gap-2 text-lg" role="heading" aria-level={2}>
              <Activity className="h-5 w-5 text-primary" />
              {t("title")}
            </CardTitle>
            <CardDescription className="mt-1 max-w-4xl">{t("description")}</CardDescription>
          </div>
          {latest ? (
            <Button
              type="button"
              size="sm"
              disabled={updating}
              onClick={() => void updateOutcomes()}
            >
              <RefreshCw className={updating ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
              {updating ? t("updating") : t("update")}
            </Button>
          ) : null}
        </div>
      </FinancialTerminalCardHeader>

      <FinancialTerminalCardContent className="space-y-4">
        <div aria-live="polite" className="sr-only">
          {updating ? t("updating") : updateFailed ? t("updateFailed") : ""}
        </div>

        {updateFailed ? (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <div className="font-medium">{t("updateFailed")}</div>
              <div className="mt-0.5 text-xs">{t("updateFailedDescription")}</div>
            </div>
          </div>
        ) : null}

        {awaitingRunId ? (
          <FinancialTerminalSurface
            role="status"
            className="flex items-center gap-2 p-3 text-sm text-muted-foreground"
          >
            <RefreshCw className="h-4 w-4 animate-spin text-primary" />
            {t("refreshingCohort")}
          </FinancialTerminalSurface>
        ) : null}

        {!awaitingRunId && initialLoadFailed ? (
          <div role="alert">
            <ErrorState title={t("loadFailed")} description={t("loadFailedDescription")} />
          </div>
        ) : null}

        {!awaitingRunId && !initialLoadFailed && !latest ? (
          <EmptyState title={t("emptyTitle")} description={t("emptyDescription")} />
        ) : null}

        {latest ? (
          <>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              <Metric label={t("decisionDate")} value={latest.run.decision_date} />
              <Metric label={t("asOf")} value={latest.as_of} />
              <Metric label={t("candidateCount")} value={String(latest.items.length)} />
              <Metric label={t("profile")} value={latest.run.profile_id} />
            </div>

            <div role="region" aria-label={t("summaryTitle")} className="grid gap-2 lg:grid-cols-3">
              {RESEARCH_OUTCOME_HORIZONS.map((horizon) => (
                <SummarySurface
                  key={horizon}
                  horizon={horizon}
                  locale={locale}
                  summary={findSummary(latest.summaries, horizon)}
                  labels={{
                    horizon: t("horizonLabel", { horizon }),
                    unavailable: t("unavailable"),
                    counts: (summary) => t("summaryCounts", {
                      total: summary.total_count,
                      evaluated: summary.evaluated_count,
                      pending: summary.pending_count,
                      blocked: summary.blocked_count,
                    }),
                    meanReturn: (value) => t("meanReturn", { value }),
                    medianReturn: (value) => t("medianReturn", { value }),
                    positiveReturns: (value) => t("positiveReturns", { value }),
                    meanDrawdown: (value) => t("meanDrawdown", { value }),
                    meanExcess: (value) => t("meanExcess", { value }),
                    samples: (sample, benchmark) => t("samples", { sample, benchmark }),
                  }}
                />
              ))}
            </div>

            <Table
              containerClassName="rounded-md border border-border/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              containerProps={{
                role: "region",
                "aria-label": t("candidateMatrix"),
                tabIndex: 0,
              }}
              className="min-w-[880px] table-fixed"
            >
              <TableHeader>
                  <TableRow>
                    <TableHead className="w-48">{t("candidate")}</TableHead>
                    {RESEARCH_OUTCOME_HORIZONS.map((horizon) => (
                      <TableHead key={horizon} className="w-56">
                        {t("horizonLabel", { horizon })}
                      </TableHead>
                    ))}
                  </TableRow>
              </TableHeader>
              <TableBody>
                  {latest.items.map((item) => (
                    <TableRow key={item.candidate_id} className="align-top">
                      <TableCell>
                        <div className="font-mono font-semibold">#{item.rank} {item.symbol}</div>
                        <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                          {item.name || t("unnamed")}
                        </div>
                        <div className="mt-1 text-[11px] text-muted-foreground">
                          {t("entryDate", { date: item.entry_trade_date })}
                        </div>
                      </TableCell>
                      {RESEARCH_OUTCOME_HORIZONS.map((horizon) => (
                        <TableCell key={horizon} className="align-top">
                          {renderHorizon(findHorizon(item.horizons, horizon))}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
              </TableBody>
            </Table>

            <div
              className="overflow-hidden rounded-md border border-border/70"
            >
              <div className="flex items-center gap-2 border-b border-border/70 bg-background/60 px-3 py-2 text-sm font-semibold">
                <BarChart3 className="h-4 w-4 text-primary" />
                {t("historyTitle")}
              </div>
              <Table
                containerClassName="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                containerProps={{
                  role: "region",
                  "aria-label": t("historyTitle"),
                  tabIndex: 0,
                }}
                className="min-w-[720px] table-fixed"
              >
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-40">{t("decisionDate")}</TableHead>
                    {RESEARCH_OUTCOME_HORIZONS.map((horizon) => (
                      <TableHead key={horizon}>{t("horizonLabel", { horizon })}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(tracking?.history ?? []).map((entry) => (
                    <TableRow key={entry.run.id}>
                      <TableCell className="font-mono">{entry.run.decision_date}</TableCell>
                      {RESEARCH_OUTCOME_HORIZONS.map((horizon) => {
                        const summary = findSummary(entry.summaries, horizon);
                        return (
                          <TableCell key={horizon}>
                            {summary ? (
                              <div className="space-y-0.5 text-xs">
                                <div className="font-mono tabular-nums">
                                  {t("historySamples", {
                                    sample: summary.return_sample_size,
                                    total: summary.total_count,
                                  })}
                                </div>
                                <div className="text-muted-foreground">
                                  {t("historyMean", {
                                    value: formatSignedRatio(summary.mean_return_ratio, locale),
                                  })}
                                </div>
                              </div>
                            ) : (
                              t("unavailable")
                            )}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                  {(tracking?.history ?? []).length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="py-6 text-center text-sm text-muted-foreground">
                        {t("historyEmpty")}
                      </TableCell>
                    </TableRow>
                  ) : null}
                </TableBody>
              </Table>
            </div>
          </>
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
      <div className="mt-1 truncate font-mono text-sm font-semibold" title={value}>{value}</div>
    </FinancialTerminalSurface>
  );
}

function SummarySurface({
  horizon,
  locale,
  summary,
  labels,
}: {
  horizon: ResearchOutcomeHorizon;
  locale: string;
  summary: ResearchOutcomeSummary | undefined;
  labels: {
    horizon: string;
    unavailable: string;
    counts: (summary: ResearchOutcomeSummary) => string;
    meanReturn: (value: string) => string;
    medianReturn: (value: string) => string;
    positiveReturns: (value: string) => string;
    meanDrawdown: (value: string) => string;
    meanExcess: (value: string) => string;
    samples: (sample: number, benchmark: number) => string;
  };
}) {
  return (
    <FinancialTerminalSurface className="min-w-0 p-3" data-horizon={horizon}>
      <div className="font-mono text-sm font-semibold">{labels.horizon}</div>
      {summary ? (
        <div className="mt-2 space-y-1 text-xs">
          <div className="text-muted-foreground">{labels.counts(summary)}</div>
          <div className="font-mono tabular-nums">
            {labels.meanReturn(formatSignedRatio(summary.mean_return_ratio, locale))}
          </div>
          <div className="font-mono tabular-nums text-muted-foreground">
            {labels.medianReturn(formatSignedRatio(summary.median_return_ratio, locale))}
          </div>
          <div className="font-mono tabular-nums text-muted-foreground">
            {labels.positiveReturns(formatUnsignedRatio(summary.positive_return_ratio, locale))}
          </div>
          <div className="font-mono tabular-nums text-muted-foreground">
            {labels.meanDrawdown(formatSignedRatio(summary.mean_drawdown_ratio, locale))}
          </div>
          <div className="font-mono tabular-nums text-muted-foreground">
            {labels.meanExcess(formatSignedRatio(summary.mean_excess_return_ratio, locale))}
          </div>
          <div className="text-muted-foreground">
            {labels.samples(summary.return_sample_size, summary.benchmark_sample_size)}
          </div>
        </div>
      ) : (
        <div className="mt-2 text-xs text-muted-foreground">{labels.unavailable}</div>
      )}
    </FinancialTerminalSurface>
  );
}

function findSummary(summaries: ResearchOutcomeSummary[], horizon: ResearchOutcomeHorizon) {
  return summaries.find((summary) => summary.horizon_sessions === horizon);
}

function findHorizon(outcomes: ResearchCandidateHorizonOutcome[], horizon: ResearchOutcomeHorizon) {
  return outcomes.find((outcome) => outcome.horizon_sessions === horizon);
}

const STRUCTURED_DIAGNOSTIC_CODE = /^[A-Z][A-Z0-9_]*$/;

function diagnosticCodes(
  diagnostics: ResearchOutcomeDiagnostic[] | undefined,
): Array<string | null> {
  const codes = (diagnostics ?? []).flatMap<string | null>((diagnostic) => {
    const code = typeof diagnostic === "string" ? diagnostic : diagnostic.code;
    if (!code) {
      return [];
    }
    return [STRUCTURED_DIAGNOSTIC_CODE.test(code) ? code : null];
  });
  return [...new Set(codes)];
}

function formatSignedRatio(value: number | null | undefined, locale: string): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
    signDisplay: "always",
  }).format(value);
}

function formatUnsignedRatio(value: number | null | undefined, locale: string): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}
