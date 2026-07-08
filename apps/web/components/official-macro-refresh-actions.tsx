"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, Database, RefreshCw, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type OfficialMacroRefreshResult = {
  status?: string;
  provider?: string;
  dry_run?: boolean;
  observations?: number;
  fetched?: number;
  skipped?: number;
  codes?: string[];
  latest_as_of?: string | null;
  diagnostics?: string[];
  cache?: {
    market_overview_cleared?: number;
  };
};

export type OfficialMacroRefreshActionsLabels = {
  dryRunAction: string;
  dryRunRunning: string;
  writeAction: string;
  writeRunning: string;
  writeStoresObservation: string;
  resultDryRun: string;
  resultWrite: string;
  resultObservations: string;
  resultFetched: string;
  resultSkipped: string;
  resultCodes: string;
  resultLatestAsOf: string;
  resultCacheCleared: string;
  diagnosticsTitle: string;
  diagnosticsEmpty: string;
  failed: string;
  unavailableShort: string;
};

type OfficialMacroRefreshActionsProps = {
  endpoint: string;
  defaultPayload: Record<string, string | number | boolean | null>;
  labels: OfficialMacroRefreshActionsLabels;
};

async function readJsonSafe(response: Response): Promise<Record<string, unknown>> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function readPayload(payload: Record<string, unknown>): Record<string, unknown> {
  const detail = payload.detail;
  return detail && typeof detail === "object" && !Array.isArray(detail)
    ? (detail as Record<string, unknown>)
    : payload;
}

function readErrorMessage(payload: Record<string, unknown>, fallback: string): string {
  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  const source = readPayload(payload);
  const message = source.message;
  if (typeof message === "string" && message.trim()) {
    return message;
  }
  const errors = source.errors;
  if (Array.isArray(errors) && errors.length > 0) {
    return errors.map(String).join("; ");
  }
  return fallback;
}

function formatLabel(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (label, [key, value]) => label.replace(`{${key}}`, String(value)),
    template,
  );
}

function getNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export function OfficialMacroRefreshActions({
  endpoint,
  defaultPayload,
  labels,
}: OfficialMacroRefreshActionsProps) {
  const [pendingAction, setPendingAction] = React.useState<"dry-run" | "write" | null>(null);
  const [result, setResult] = React.useState<OfficialMacroRefreshResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const router = useRouter();
  const isPending = pendingAction !== null;

  async function runRefresh(dryRun: boolean) {
    setPendingAction(dryRun ? "dry-run" : "write");
    setError(null);
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          ...defaultPayload,
          dry_run: dryRun,
        }),
      });
      const payload = await readJsonSafe(response);
      if (!response.ok) {
        setError(readErrorMessage(payload, labels.failed));
        return;
      }

      const refreshResult = readPayload(payload) as OfficialMacroRefreshResult;
      setResult(refreshResult);
      if (!dryRun) {
        router.refresh();
      }
    } catch {
      setError(labels.failed);
    } finally {
      setPendingAction(null);
    }
  }

  const diagnostics = result?.diagnostics ?? [];
  const codes = result?.codes?.join(", ") || labels.unavailableShort;
  const latestAsOf = result?.latest_as_of || labels.unavailableShort;
  const cacheCleared = getNumber(result?.cache?.market_overview_cleared);

  return (
    <div className="mt-4 space-y-3 border bg-muted/10 p-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button
          type="button"
          variant="outline"
          onClick={() => void runRefresh(true)}
          disabled={isPending}
        >
          <RefreshCw className={pendingAction === "dry-run" ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          {pendingAction === "dry-run" ? labels.dryRunRunning : labels.dryRunAction}
        </Button>
        <Button type="button" onClick={() => void runRefresh(false)} disabled={isPending}>
          <Database className={pendingAction === "write" ? "h-4 w-4 animate-pulse" : "h-4 w-4"} />
          {pendingAction === "write" ? labels.writeRunning : labels.writeAction}
        </Button>
      </div>
      <p className="flex items-start gap-2 text-xs text-muted-foreground">
        <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>{labels.writeStoresObservation}</span>
      </p>

      {error ? (
        <div className="flex items-start gap-2 border border-destructive/40 bg-destructive/10 p-2 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {result ? (
        <div className="space-y-3 border border-emerald-200 bg-emerald-50/60 p-3 text-sm dark:border-emerald-900/60 dark:bg-emerald-950/20">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              <CheckCircle2 className="h-3 w-3" />
              {result.dry_run ? labels.resultDryRun : labels.resultWrite}
            </Badge>
            <Badge variant="outline">
              {formatLabel(labels.resultObservations, { count: getNumber(result.observations) })}
            </Badge>
            <Badge variant="outline">
              {formatLabel(labels.resultFetched, { count: getNumber(result.fetched) })}
            </Badge>
            <Badge variant="outline">
              {formatLabel(labels.resultSkipped, { count: getNumber(result.skipped) })}
            </Badge>
          </div>
          <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
            <div>{formatLabel(labels.resultCodes, { codes })}</div>
            <div>{formatLabel(labels.resultLatestAsOf, { date: latestAsOf })}</div>
            <div>{formatLabel(labels.resultCacheCleared, { count: cacheCleared })}</div>
          </div>
          <div className="text-xs text-muted-foreground">
            <div className="font-semibold text-foreground">{labels.diagnosticsTitle}</div>
            {diagnostics.length > 0 ? (
              <ul className="mt-1 list-disc space-y-1 pl-4">
                {diagnostics.map((diagnostic, index) => (
                  <li key={`${diagnostic}-${index}`}>{diagnostic}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-1">{labels.diagnosticsEmpty}</p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
