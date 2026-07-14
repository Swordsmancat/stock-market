"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, Database, RefreshCw, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";

import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type MarketDailyEvidenceDiagnostic = {
  source?: string;
  status?: string;
  severity?: string;
  code?: string;
  message?: string;
};

export type MarketDailyEvidenceCitation = {
  id: string;
  label: string;
  source: string;
  source_type?: string;
  as_of?: string | null;
  provider?: string | null;
};

export type MarketDailyEvidencePayload = {
  items?: Array<{
    id: string;
    event_type: string;
    identity: string;
    identity_name?: string | null;
    trade_date: string;
    provider: string;
    citation_id?: string | null;
  }>;
  citations?: MarketDailyEvidenceCitation[];
  summary?: {
    total?: number;
    returned?: number;
    counts_by_event_type?: Record<string, number>;
    latest_imported_at?: string | null;
    latest_updated_at?: string | null;
    latest_trade_date?: string | null;
  };
  safety?: {
    persisted_rows_only?: boolean;
    not_investment_advice?: boolean;
    no_automated_trading?: boolean;
  };
};

type MarketDailyEvidenceImportResult = {
  status?: string;
  inserted?: number;
  updated?: number;
  skipped?: number;
  provider?: string;
  trade_date?: string;
  diagnostics?: MarketDailyEvidenceDiagnostic[];
};

export type MarketDailyEvidencePanelLabels = {
  title: string;
  description: string;
  maintenanceSummary: string;
  refreshAction: string;
  refreshing: string;
  totalRows: string;
  latestImport: string;
  latestTradeDate: string;
  citationsTitle: string;
  emptyTitle: string;
  emptyDescription: string;
  loadFailedTitle: string;
  loadFailedDescription: string;
  persistedOnly: string;
  notAdvice: string;
  refreshSuccess: string;
  insertedCount: string;
  updatedCount: string;
  skippedCount: string;
  diagnosticsTitle: string;
  diagnosticsEmpty: string;
  refreshFailed: string;
  unavailableShort: string;
  corporateReportPeriod: string;
  refreshCorporateActions: string;
  refreshingCorporateActions: string;
  corporateActionQueued: string;
  openTaskRun: string;
  eventTypeLabels: Record<string, string>;
};

type MarketDailyEvidencePanelProps = {
  initialPayload: MarketDailyEvidencePayload | null;
  loadFailed: boolean;
  labels: MarketDailyEvidencePanelLabels;
};

function formatLabel(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (label, [key, value]) => label.replace(`{${key}}`, String(value)),
    template,
  );
}

async function readJsonSafe(response: Response): Promise<Record<string, unknown>> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function readErrorMessage(payload: Record<string, unknown>, fallback: string): string {
  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const errors = (detail as Record<string, unknown>).errors;
    if (Array.isArray(errors) && errors.length > 0) {
      return errors.map(String).join("; ");
    }
  }
  const diagnostics = payload.diagnostics;
  if (Array.isArray(diagnostics)) {
    const firstMessage = diagnostics.find(
      (item) => item && typeof item === "object" && typeof (item as { message?: unknown }).message === "string",
    ) as { message?: string } | undefined;
    if (firstMessage?.message) {
      return firstMessage.message;
    }
  }
  return fallback;
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export function MarketDailyEvidencePanel({
  initialPayload,
  loadFailed,
  labels,
}: MarketDailyEvidencePanelProps) {
  const [payload, setPayload] = React.useState<MarketDailyEvidencePayload | null>(initialPayload);
  const [result, setResult] = React.useState<MarketDailyEvidenceImportResult | null>(null);
  const [pending, setPending] = React.useState(false);
  const [corporatePending, setCorporatePending] = React.useState(false);
  const [corporateReportPeriod, setCorporateReportPeriod] = React.useState(
    `${new Date().getUTCFullYear() - 1}-12-31`,
  );
  const [corporateTaskRunId, setCorporateTaskRunId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const router = useRouter();

  async function refreshEvidence() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/market-daily-evidence", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ market: "CN", limit: 20 }),
      });
      const responsePayload = await readJsonSafe(response);
      if (!response.ok) {
        setError(readErrorMessage(responsePayload, labels.refreshFailed));
        return;
      }

      const importResult = responsePayload as MarketDailyEvidenceImportResult;
      setResult(importResult);
      if (importResult.status === "failed") {
        setError(readErrorMessage(responsePayload, labels.refreshFailed));
        return;
      }

      const listResponse = await fetch(
        "/api/market-daily-evidence?limit=12&citable_only=true",
        { cache: "no-store" },
      );
      if (listResponse.ok) {
        setPayload((await listResponse.json()) as MarketDailyEvidencePayload);
      }
      router.refresh();
    } catch {
      setError(labels.refreshFailed);
    } finally {
      setPending(false);
    }
  }

  async function refreshCorporateActions() {
    setCorporatePending(true);
    setError(null);
    try {
      const response = await fetch("/api/ingestion/corporate-actions", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          report_period: corporateReportPeriod,
          market: "CN",
          provider: "akshare",
          event_types: ["dividend_bonus", "rights_allotment"],
          cursor: 0,
          batch_size: 50,
        }),
      });
      const responsePayload = await readJsonSafe(response);
      if (!response.ok) {
        setError(readErrorMessage(responsePayload, labels.refreshFailed));
        return;
      }
      const taskRun = responsePayload.task_run;
      if (taskRun && typeof taskRun === "object" && !Array.isArray(taskRun)) {
        const taskRunId = (taskRun as { id?: unknown }).id;
        setCorporateTaskRunId(typeof taskRunId === "string" ? taskRunId : null);
      }
      router.refresh();
    } catch {
      setError(labels.refreshFailed);
    } finally {
      setCorporatePending(false);
    }
  }

  const summary = payload?.summary;
  const total = numberValue(summary?.total);
  const counts = Object.entries(summary?.counts_by_event_type ?? {});
  const citations = payload?.citations ?? [];
  const diagnostics = result?.diagnostics ?? [];
  const latestImport = summary?.latest_imported_at ?? labels.unavailableShort;
  const latestTradeDate = summary?.latest_trade_date ?? labels.unavailableShort;

  return (
    <FinancialTerminalCard>
      <FinancialTerminalCardHeader>
        <CardTitle className="flex items-center gap-2 text-xl">
          <Database className="h-5 w-5" />
          {labels.title}
        </CardTitle>
        <CardDescription className="mt-1">{labels.description}</CardDescription>
      </FinancialTerminalCardHeader>
      <FinancialTerminalCardContent className="space-y-4">
        {loadFailed && payload === null ? (
          <FinancialTerminalSurface className="border-destructive/40 bg-destructive/10 p-3 text-sm">
            <div className="flex items-start gap-2 text-destructive">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <div className="font-semibold">{labels.loadFailedTitle}</div>
                <p className="mt-1">{labels.loadFailedDescription}</p>
              </div>
            </div>
          </FinancialTerminalSurface>
        ) : (
          <>
            <div className="grid gap-2 sm:grid-cols-3">
              <FinancialTerminalSurface className="p-3">
                <div className="text-xs text-muted-foreground">{labels.totalRows}</div>
                <div className="mt-1 font-mono text-xl font-semibold">{total}</div>
              </FinancialTerminalSurface>
              <FinancialTerminalSurface className="p-3">
                <div className="text-xs text-muted-foreground">{labels.latestTradeDate}</div>
                <div className="mt-1 font-mono text-sm font-semibold">{latestTradeDate}</div>
              </FinancialTerminalSurface>
              <FinancialTerminalSurface className="p-3">
                <div className="text-xs text-muted-foreground">{labels.latestImport}</div>
                <div className="mt-1 break-all font-mono text-xs font-semibold">{latestImport}</div>
              </FinancialTerminalSurface>
            </div>

            {counts.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {counts.map(([eventType, count]) => (
                  <Badge key={eventType} variant="outline">
                    {labels.eventTypeLabels[eventType] ?? eventType}: {count}
                  </Badge>
                ))}
              </div>
            ) : null}

            {citations.length > 0 ? (
              <div className="space-y-2">
                <div className="text-sm font-semibold">{labels.citationsTitle}</div>
                <div className="grid gap-2 lg:grid-cols-2">
                  {citations.slice(0, 6).map((citation) => (
                    <FinancialTerminalSurface key={citation.id} className="p-2">
                      <div className="text-xs font-medium">{citation.label}</div>
                      <div className="mt-1 break-all font-mono text-[11px] text-muted-foreground">
                        {citation.id}
                      </div>
                    </FinancialTerminalSurface>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                <div className="text-sm font-semibold">{labels.emptyTitle}</div>
                <p className="mt-1 text-sm text-muted-foreground">{labels.emptyDescription}</p>
              </div>
            )}
          </>
        )}

        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="secondary">
            <ShieldCheck className="h-3 w-3" />
            {labels.persistedOnly}
          </Badge>
          <Badge variant="secondary">{labels.notAdvice}</Badge>
        </div>

        <details className="rounded-md border border-dashed border-border/80 bg-card/95 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-foreground">
            {labels.maintenanceSummary}
          </summary>
          <div className="mt-4 space-y-4">
            <div className="flex flex-col gap-2 sm:items-start">
              <Button type="button" onClick={() => void refreshEvidence()} disabled={pending}>
                <RefreshCw className={pending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
                {pending ? labels.refreshing : labels.refreshAction}
              </Button>
              <div className="flex flex-wrap items-end gap-2">
                <label className="space-y-1 text-xs text-muted-foreground">
                  <span>{labels.corporateReportPeriod}</span>
                  <Input
                    type="date"
                    className="h-9 w-[160px]"
                    value={corporateReportPeriod}
                    onChange={(event) => setCorporateReportPeriod(event.target.value)}
                  />
                </label>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void refreshCorporateActions()}
                  disabled={corporatePending || !corporateReportPeriod}
                >
                  <RefreshCw className={corporatePending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
                  {corporatePending
                    ? labels.refreshingCorporateActions
                    : labels.refreshCorporateActions}
                </Button>
              </div>
            </div>

            {error ? (
              <div className="flex items-start gap-2 border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            ) : null}

            {corporateTaskRunId ? (
              <FinancialTerminalSurface className="flex flex-wrap items-center justify-between gap-2 border-primary/30 bg-primary/5 p-3 text-sm">
                <span>{labels.corporateActionQueued}</span>
                <Button size="sm" variant="outline" asChild>
                  <a href={`/task-runs/${corporateTaskRunId}`}>{labels.openTaskRun}</a>
                </Button>
              </FinancialTerminalSurface>
            ) : null}

            {result ? (
              <FinancialTerminalSurface className="border-emerald-500/40 bg-emerald-500/10 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">
                    <CheckCircle2 className="h-3 w-3" />
                    {labels.refreshSuccess}
                  </Badge>
                  <Badge variant="outline">
                    {formatLabel(labels.insertedCount, { count: numberValue(result.inserted) })}
                  </Badge>
                  <Badge variant="outline">
                    {formatLabel(labels.updatedCount, { count: numberValue(result.updated) })}
                  </Badge>
                  <Badge variant="outline">
                    {formatLabel(labels.skippedCount, { count: numberValue(result.skipped) })}
                  </Badge>
                </div>
                <div className="mt-3 text-xs text-muted-foreground">
                  <div className="font-semibold text-foreground">{labels.diagnosticsTitle}</div>
                  {diagnostics.length > 0 ? (
                    <ul className="mt-1 list-disc space-y-1 pl-4">
                      {diagnostics.map((diagnostic, index) => (
                        <li key={`${diagnostic.code ?? diagnostic.source ?? "diagnostic"}-${index}`}>
                          {diagnostic.code ? `${diagnostic.code}: ` : null}
                          {diagnostic.message ?? diagnostic.status ?? labels.unavailableShort}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1">{labels.diagnosticsEmpty}</p>
                  )}
                </div>
              </FinancialTerminalSurface>
            ) : null}
          </div>
        </details>
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}
