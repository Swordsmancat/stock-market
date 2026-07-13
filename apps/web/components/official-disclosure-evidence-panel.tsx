"use client";

import * as React from "react";
import { AlertTriangle, FileCheck2, RefreshCw, ShieldCheck } from "lucide-react";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export type OfficialDisclosureEvidenceItem = {
  id: string;
  symbol: string;
  title: string;
  category?: string | null;
  published_at?: string | null;
  source_url: string;
  citation_id: string;
  status: string;
  section_count: number;
  content_citable: boolean;
  document?: { page_count?: number | null; sha256?: string; extraction_status?: string } | null;
};

export type OfficialDisclosureEvidencePayload = {
  status: string;
  symbols?: string[];
  summary?: {
    eligible_symbol_count?: number;
    metadata_disclosure_count?: number;
    with_document_count?: number;
    extracted_document_count?: number;
    metadata_only_count?: number;
    non_citable_count?: number;
    citable_section_count?: number;
  };
  monitoring?: {
    enabled?: boolean;
    interval_minutes?: number;
    freshness_sla_hours?: number;
    summary?: {
      fresh_symbol_count?: number;
      stale_symbol_count?: number;
      backoff_symbol_count?: number;
      never_succeeded_symbol_count?: number;
      new_disclosure_count?: number;
    };
    items?: Array<{
      symbol: string;
      freshness: string;
      last_success_at?: string | null;
      next_retry_at?: string | null;
      last_new_disclosure_count?: number;
    }>;
  };
  items?: OfficialDisclosureEvidenceItem[];
};

export type OfficialDisclosureEvidenceLabels = {
  title: string;
  description: string;
  batchAction: string;
  batchPending: string;
  batchQueued: string;
  monitorAction: string;
  monitorPending: string;
  monitoringTitle: string;
  monitoringDescription: string;
  freshSymbols: string;
  staleSymbols: string;
  backoffSymbols: string;
  newDisclosures: string;
  lastSuccess: string;
  openTaskRun: string;
  eligibleSymbols: string;
  metadataRows: string;
  extractedDocuments: string;
  citableSections: string;
  symbol: string;
  disclosure: string;
  publishedAt: string;
  status: string;
  sections: string;
  action: string;
  ingestAction: string;
  ingestPending: string;
  officialSource: string;
  emptyTitle: string;
  emptyDescription: string;
  loadFailedTitle: string;
  loadFailedDescription: string;
  operationFailed: string;
  metadataBoundary: string;
  contentBoundary: string;
  watchlistOnly: string;
  statusLabels: Record<string, string>;
  freshnessLabels: Record<string, string>;
};

type Props = {
  initialPayload: OfficialDisclosureEvidencePayload | null;
  loadFailed: boolean;
  labels: OfficialDisclosureEvidenceLabels;
};

async function readPayload(response: Response): Promise<Record<string, unknown>> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function errorMessage(payload: Record<string, unknown>, fallback: string): string {
  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}

function count(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export function OfficialDisclosureEvidencePanel({ initialPayload, loadFailed, labels }: Props) {
  const [batchPending, setBatchPending] = React.useState(false);
  const [monitorPending, setMonitorPending] = React.useState(false);
  const [pendingDisclosureId, setPendingDisclosureId] = React.useState<string | null>(null);
  const [taskRunId, setTaskRunId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const router = useRouter();
  const summary = initialPayload?.summary;
  const monitoring = initialPayload?.monitoring;
  const monitoringSummary = monitoring?.summary;
  const items = initialPayload?.items ?? [];

  async function enqueueWatchlist(path: string) {
    setError(null);
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ lookback_days: 30, max_documents: 20 }),
      });
      const payload = await readPayload(response);
      if (!response.ok) {
        setError(errorMessage(payload, labels.operationFailed));
        return;
      }
      const taskRun = payload.task_run;
      if (taskRun && typeof taskRun === "object" && !Array.isArray(taskRun)) {
        const id = (taskRun as { id?: unknown }).id;
        setTaskRunId(typeof id === "string" ? id : null);
      }
      router.refresh();
    } catch {
      setError(labels.operationFailed);
    }
  }

  async function ingestBatch() {
    setBatchPending(true);
    try {
      await enqueueWatchlist("/api/official-disclosures/watchlist-ingest");
    } finally {
      setBatchPending(false);
    }
  }

  async function monitorWatchlist() {
    setMonitorPending(true);
    try {
      await enqueueWatchlist("/api/official-disclosures/watchlist-monitor");
    } finally {
      setMonitorPending(false);
    }
  }

  async function ingestOne(disclosureId: string) {
    setPendingDisclosureId(disclosureId);
    setError(null);
    try {
      const response = await fetch(
        `/api/official-disclosures/${encodeURIComponent(disclosureId)}/ingest-document`,
        { method: "POST" },
      );
      const payload = await readPayload(response);
      if (!response.ok) {
        setError(errorMessage(payload, labels.operationFailed));
        return;
      }
      router.refresh();
    } catch {
      setError(labels.operationFailed);
    } finally {
      setPendingDisclosureId(null);
    }
  }

  return (
    <FinancialTerminalCard>
      <FinancialTerminalCardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-xl">
              <FileCheck2 className="h-5 w-5" />
              {labels.title}
            </CardTitle>
            <CardDescription className="mt-1">{labels.description}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={() => void monitorWatchlist()} disabled={monitorPending}>
              <RefreshCw className={monitorPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
              {monitorPending ? labels.monitorPending : labels.monitorAction}
            </Button>
            <Button type="button" onClick={() => void ingestBatch()} disabled={batchPending}>
              <RefreshCw className={batchPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
              {batchPending ? labels.batchPending : labels.batchAction}
            </Button>
          </div>
        </div>
      </FinancialTerminalCardHeader>
      <FinancialTerminalCardContent className="space-y-4">
        {loadFailed && initialPayload === null ? (
          <FinancialTerminalSurface className="border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            <div className="flex gap-2"><AlertTriangle className="h-4 w-4" /><div><strong>{labels.loadFailedTitle}</strong><p>{labels.loadFailedDescription}</p></div></div>
          </FinancialTerminalSurface>
        ) : (
          <>
            <div className="grid gap-2 sm:grid-cols-4">
              {[
                [labels.eligibleSymbols, count(summary?.eligible_symbol_count)],
                [labels.metadataRows, count(summary?.metadata_disclosure_count)],
                [labels.extractedDocuments, count(summary?.extracted_document_count)],
                [labels.citableSections, count(summary?.citable_section_count)],
              ].map(([label, value]) => (
                <FinancialTerminalSurface key={String(label)} className="p-3">
                  <div className="text-xs text-muted-foreground">{label}</div>
                  <div className="mt-1 font-mono text-xl font-semibold">{value}</div>
                </FinancialTerminalSurface>
              ))}
            </div>
            {monitoring ? (
              <FinancialTerminalSurface className="space-y-3 p-3">
                <div>
                  <div className="font-semibold">{labels.monitoringTitle}</div>
                  <p className="text-xs text-muted-foreground">{labels.monitoringDescription}</p>
                </div>
                <div className="grid gap-2 sm:grid-cols-4">
                  {[
                    [labels.freshSymbols, count(monitoringSummary?.fresh_symbol_count)],
                    [labels.staleSymbols, count(monitoringSummary?.stale_symbol_count)],
                    [labels.backoffSymbols, count(monitoringSummary?.backoff_symbol_count)],
                    [labels.newDisclosures, count(monitoringSummary?.new_disclosure_count)],
                  ].map(([label, value]) => (
                    <div key={String(label)} className="border-l border-border/70 pl-3">
                      <div className="text-xs text-muted-foreground">{label}</div>
                      <div className="font-mono text-lg font-semibold">{value}</div>
                    </div>
                  ))}
                </div>
                {(monitoring.items ?? []).length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {(monitoring.items ?? []).map((item) => (
                      <Badge key={item.symbol} variant={item.freshness === "fresh" ? "secondary" : "outline"}>
                        <span className="font-mono">{item.symbol}</span>
                        <span>{labels.freshnessLabels[item.freshness] ?? item.freshness}</span>
                        {item.last_success_at ? <span>{labels.lastSuccess}: {item.last_success_at.slice(0, 16).replace("T", " ")}</span> : null}
                      </Badge>
                    ))}
                  </div>
                ) : null}
              </FinancialTerminalSurface>
            ) : null}
            {items.length === 0 ? (
              <div><div className="font-semibold">{labels.emptyTitle}</div><p className="text-sm text-muted-foreground">{labels.emptyDescription}</p></div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader><TableRow><TableHead>{labels.symbol}</TableHead><TableHead>{labels.disclosure}</TableHead><TableHead>{labels.publishedAt}</TableHead><TableHead>{labels.status}</TableHead><TableHead>{labels.sections}</TableHead><TableHead>{labels.action}</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-mono">{item.symbol}</TableCell>
                        <TableCell className="min-w-[18rem]"><a href={item.source_url} target="_blank" rel="noreferrer" className="font-medium hover:underline">{item.title}</a><div className="mt-1 font-mono text-[10px] text-muted-foreground">{item.citation_id}</div></TableCell>
                        <TableCell>{item.published_at?.slice(0, 10) ?? "—"}</TableCell>
                        <TableCell><Badge variant={item.content_citable ? "secondary" : "outline"}>{labels.statusLabels[item.status] ?? item.status}</Badge></TableCell>
                        <TableCell className="font-mono">{item.section_count}</TableCell>
                        <TableCell><Button size="sm" variant="outline" disabled={pendingDisclosureId === item.id} onClick={() => void ingestOne(item.id)}>{pendingDisclosureId === item.id ? labels.ingestPending : labels.ingestAction}</Button></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </>
        )}
        <div className="flex flex-wrap gap-2 text-xs"><Badge variant="secondary"><ShieldCheck className="h-3 w-3" />{labels.watchlistOnly}</Badge><Badge variant="outline">{labels.metadataBoundary}</Badge><Badge variant="outline">{labels.contentBoundary}</Badge></div>
        {taskRunId ? <FinancialTerminalSurface className="flex items-center justify-between gap-2 border-primary/30 bg-primary/5 p-3 text-sm"><span>{labels.batchQueued}</span><Button size="sm" variant="outline" asChild><a href={`/task-runs/${taskRunId}`}>{labels.openTaskRun}</a></Button></FinancialTerminalSurface> : null}
        {error ? <div className="flex gap-2 border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"><AlertTriangle className="h-4 w-4" />{error}</div> : null}
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}
