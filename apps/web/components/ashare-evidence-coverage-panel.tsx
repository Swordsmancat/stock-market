"use client";

import * as React from "react";
import { Activity, Database, Play, RefreshCw, RotateCcw, XCircle } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { ErrorState } from "@/components/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Link } from "@/src/i18n/routing";

const EVIDENCE_KINDS = ["daily_bars", "technical_indicators", "fundamentals"] as const;
const ACTIVE_STATUSES = new Set(["queued", "running", "cancel_requested"]);

type EvidenceKind = (typeof EVIDENCE_KINDS)[number];

type CoverageDimension = {
  ready_count: number;
  missing_count: number;
  total_count: number;
  coverage_ratio: number;
  threshold: number;
  passes_threshold: boolean;
  by_exchange: Record<string, { ready_count: number; total_count: number; coverage_ratio: number }>;
};

type LatestRun = {
  id: string;
  task_run_id?: string | null;
  run_kind: string;
  status: string;
  phase?: string | null;
  cursor: number;
  phase_total: number;
  processed_count: number;
  heartbeat_at?: string | null;
  finished_at?: string | null;
  retry?: Record<string, { count: number; preview: string[] }>;
  diagnostics?: Array<{ code?: string; message?: string; symbol?: string; phase?: string }>;
};

export type EvidenceCoveragePayload = {
  status: string;
  market: string;
  provider: string;
  as_of: string;
  universe: { active_count: number; exchange_counts: Record<string, number> };
  evidence: Record<EvidenceKind, CoverageDimension>;
  latest_run?: LatestRun | null;
};

type MutationPayload = {
  detail?: string;
  backfill?: { id?: string; task_run_id?: string; status?: string };
  id?: string;
  status?: string;
};

export function AshareEvidenceCoveragePanel({
  initialCoverage,
}: {
  initialCoverage: EvidenceCoveragePayload | null;
}) {
  const t = useTranslations("AshareEvidenceCoverage");
  const locale = useLocale();
  const [coverage, setCoverage] = React.useState(initialCoverage);
  const [pendingAction, setPendingAction] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const latestRun = coverage?.latest_run ?? null;
  const isActive = Boolean(latestRun && ACTIVE_STATUSES.has(latestRun.status));

  const refreshCoverage = React.useCallback(async () => {
    const response = await fetch("/api/stock-selection/evidence-coverage", { cache: "no-store" });
    const payload = (await response.json()) as EvidenceCoveragePayload & { detail?: string };
    if (!response.ok) {
      throw new Error(payload.detail ?? t("refreshFailed"));
    }
    setCoverage(payload);
  }, [t]);

  React.useEffect(() => {
    if (!isActive) return;
    const timer = window.setInterval(() => {
      void refreshCoverage().catch((refreshError: unknown) => {
        setError(refreshError instanceof Error ? refreshError.message : t("refreshFailed"));
      });
    }, 5_000);
    return () => window.clearInterval(timer);
  }, [isActive, refreshCoverage, t]);

  async function manualRefresh() {
    setPendingAction("refresh");
    setError(null);
    try {
      await refreshCoverage();
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : t("refreshFailed"));
    } finally {
      setPendingAction(null);
    }
  }

  async function startRun(runKind: "canary" | "baseline") {
    if (runKind === "baseline" && !window.confirm(t("confirmBaseline"))) return;
    await mutate("start", "/api/ingestion/a-share-evidence-backfills", {
      run_kind: runKind,
      market: "CN",
      provider: "akshare",
      evidence_kinds: EVIDENCE_KINDS,
      batch_size: 25,
      ...(runKind === "canary" ? { cohort_size: 50 } : {}),
    });
  }

  async function runAction(action: "resume" | "retry-failed" | "cancel") {
    if (!latestRun) return;
    if (action === "cancel" && !window.confirm(t("confirmCancel"))) return;
    await mutate(action, `/api/ingestion/a-share-evidence-backfills/${latestRun.id}/${action}`);
  }

  async function mutate(action: string, url: string, body?: object) {
    setPendingAction(action);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: body ? { "content-type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      const payload = (await response.json()) as MutationPayload;
      if (!response.ok) throw new Error(payload.detail ?? t("actionFailed"));
      setMessage(t(`action${action.replace("-", "_")}`));
      await refreshCoverage();
    } catch (mutationError) {
      setError(mutationError instanceof Error ? mutationError.message : t("actionFailed"));
    } finally {
      setPendingAction(null);
    }
  }

  if (!coverage) {
    return (
      <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <h2 className="text-base font-semibold leading-tight tracking-normal">{t("title")}</h2>
          <CardDescription>{t("unavailable")}</CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent className="text-center">
          <ErrorState title={t("unavailable")} description={error ?? t("unavailableHint")} />
          <Button onClick={() => void manualRefresh()} variant="outline" disabled={pendingAction !== null}>
            <RefreshCw aria-hidden="true" /> {t("refresh")}
          </Button>
          {error ? <p role="alert" className="sr-only">{error}</p> : null}
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>
    );
  }

  const exchanges = Object.keys(coverage.universe.exchange_counts).sort();

  return (
    <FinancialTerminalCard>
      <FinancialTerminalCardHeader className="gap-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="flex items-center gap-2 text-base font-semibold leading-tight tracking-normal">
                <Database className="size-5" aria-hidden="true" /> {t("title")}
              </h2>
              <Badge variant={coverage.status === "ok" ? "default" : "secondary"}>
                {t(`coverageStatus_${coverage.status}`)}
              </Badge>
              {isActive ? <Badge variant="outline">{t("autoRefreshing")}</Badge> : null}
            </div>
            <CardDescription>{t("description")}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" disabled={pendingAction !== null || isActive} onClick={() => void startRun("canary")}>
              <Play aria-hidden="true" /> {t("startCanary")}
            </Button>
            <Button size="sm" disabled={pendingAction !== null || isActive} onClick={() => void startRun("baseline")}>
              <Database aria-hidden="true" /> {t("startBaseline")}
            </Button>
            <Button size="sm" variant="ghost" disabled={pendingAction !== null} onClick={() => void manualRefresh()}>
              <RefreshCw aria-hidden="true" /> {t("refresh")}
            </Button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">{t("safety")}</p>
        <div aria-live="polite" className="min-h-5 text-sm">
          {message ? <p className="text-primary">{message}</p> : null}
          {error ? <p role="alert" className="text-destructive">{error}</p> : null}
        </div>
      </FinancialTerminalCardHeader>

      <FinancialTerminalCardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <Metric label={t("provider")} value={coverage.provider} />
          <Metric label={t("asOf")} value={coverage.as_of} />
          <Metric label={t("activeInstruments")} value={formatInteger(coverage.universe.active_count, locale)} />
          {exchanges.map((exchange) => (
            <Metric key={exchange} label={exchange} value={formatInteger(coverage.universe.exchange_counts[exchange], locale)} />
          ))}
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          {EVIDENCE_KINDS.map((kind) => {
            const dimension = coverage.evidence[kind];
            const percent = Math.round(dimension.coverage_ratio * 100);
            return (
              <FinancialTerminalSurface key={kind} className="space-y-3 p-3">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold">{t(`kind_${kind}`)}</h3>
                  <Badge variant={dimension.passes_threshold ? "default" : "outline"}>
                    {dimension.passes_threshold ? t("thresholdPassed") : t("thresholdMissing")}
                  </Badge>
                </div>
                <div
                  role="progressbar"
                  aria-label={t("coverageFor", { kind: t(`kind_${kind}`) })}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={percent}
                  className="h-2 overflow-hidden rounded-full bg-muted"
                >
                  <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${percent}%` }} />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{t("ready", { count: formatInteger(dimension.ready_count, locale) })}</span>
                  <span>{percent}% / {Math.round(dimension.threshold * 100)}%</span>
                  <span>{t("missing", { count: formatInteger(dimension.missing_count, locale) })}</span>
                </div>
              </FinancialTerminalSurface>
            );
          })}
        </div>

        <FinancialTerminalSurface className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("exchange")}</TableHead>
                <TableHead className="text-right">{t("universe")}</TableHead>
                {EVIDENCE_KINDS.map((kind) => <TableHead key={kind} className="text-right">{t(`kind_${kind}`)}</TableHead>)}
              </TableRow>
            </TableHeader>
            <TableBody>
              {exchanges.map((exchange) => (
                <TableRow key={exchange}>
                  <TableCell className="font-medium">{exchange}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatInteger(coverage.universe.exchange_counts[exchange], locale)}</TableCell>
                  {EVIDENCE_KINDS.map((kind) => {
                    const item = coverage.evidence[kind].by_exchange[exchange];
                    return <TableCell key={kind} className="text-right tabular-nums">{item ? `${Math.round(item.coverage_ratio * 100)}% (${item.ready_count}/${item.total_count})` : t("unavailableValue")}</TableCell>;
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </FinancialTerminalSurface>

        {latestRun ? (
          <LatestRunPanel
            run={latestRun}
            locale={locale}
            pending={pendingAction !== null}
            onAction={runAction}
            t={t}
          />
        ) : (
          <FinancialTerminalSurface className="p-3 text-sm text-muted-foreground">{t("noRuns")}</FinancialTerminalSurface>
        )}
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}

function LatestRunPanel({ run, locale, pending, onAction, t }: {
  run: LatestRun;
  locale: string;
  pending: boolean;
  onAction: (action: "resume" | "retry-failed" | "cancel") => Promise<void>;
  t: (key: string, values?: Record<string, string | number>) => string;
}) {
  const progress = run.phase_total > 0 ? Math.min(100, Math.round((run.cursor / run.phase_total) * 100)) : 0;
  const retryEntries = Object.entries(run.retry ?? {}).filter(([, item]) => item.count > 0);
  const terminal = !ACTIVE_STATUSES.has(run.status);

  return (
    <FinancialTerminalSurface className="space-y-3 p-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold"><Activity className="size-4" aria-hidden="true" /> {t("latestRun")}</h3>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{run.id}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{run.run_kind}</Badge>
          <Badge variant={ACTIVE_STATUSES.has(run.status) ? "secondary" : "outline"}>{runStatusLabel(run.status, t)}</Badge>
          {run.task_run_id ? <Button asChild size="sm" variant="outline"><Link href={`/task-runs/${run.task_run_id}`}>{t("openTaskRun")}</Link></Button> : null}
        </div>
      </div>
      <div role="progressbar" aria-label={t("runProgress")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} className="h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${progress}%` }} />
      </div>
      <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-5">
        <Metric label={t("phase")} value={run.phase ?? t("unavailableValue")} />
        <Metric label={t("phaseProgress")} value={`${formatInteger(run.cursor, locale)} / ${formatInteger(run.phase_total, locale)}`} />
        <Metric label={t("processed")} value={formatInteger(run.processed_count, locale)} />
        <Metric label={t("heartbeat")} value={formatDate(run.heartbeat_at, locale)} />
        <Metric label={t("finishedAt")} value={formatDate(run.finished_at, locale)} />
      </div>
      <div className="flex flex-wrap gap-2">
        {["failed", "cancelled"].includes(run.status) ? <Button size="sm" variant="outline" disabled={pending} onClick={() => void onAction("resume")}><RotateCcw aria-hidden="true" /> {t("resume")}</Button> : null}
        {terminal && retryEntries.length > 0 ? <Button size="sm" variant="outline" disabled={pending} onClick={() => void onAction("retry-failed")}><RefreshCw aria-hidden="true" /> {t("retryFailed")}</Button> : null}
        {ACTIVE_STATUSES.has(run.status) ? <Button size="sm" variant="destructive" disabled={pending || run.status === "cancel_requested"} onClick={() => void onAction("cancel")}><XCircle aria-hidden="true" /> {t("cancel")}</Button> : null}
      </div>
      {retryEntries.length > 0 ? (
        <div className="text-xs text-muted-foreground">
          <p className="font-medium text-foreground">{t("retryQueue")}</p>
          {retryEntries.map(([kind, item]) => <p key={kind}>{t(`kind_${kind}`)}: {item.count} ({item.preview.join(", ")})</p>)}
        </div>
      ) : null}
      {(run.diagnostics ?? []).length > 0 ? (
        <div className="text-xs text-muted-foreground">
          <p className="font-medium text-foreground">{t("diagnostics")}</p>
          {(run.diagnostics ?? []).slice(0, 5).map((item, index) => <p key={`${item.code ?? "diagnostic"}-${index}`}>{[item.code, item.symbol, item.message].filter(Boolean).join(" · ")}</p>)}
        </div>
      ) : null}
    </FinancialTerminalSurface>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-1 font-mono text-sm font-semibold tabular-nums">{value}</p></div>;
}

function formatInteger(value: number, locale: string) {
  return new Intl.NumberFormat(locale).format(value);
}

function formatDate(value: string | null | undefined, locale: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "medium" }).format(new Date(value));
}

function runStatusLabel(status: string, t: (key: string) => string) {
  if (["queued", "running", "cancel_requested", "cancelled", "succeeded", "completed", "failed", "partial"].includes(status)) {
    return t(`runStatus_${status}`);
  }
  return status;
}
