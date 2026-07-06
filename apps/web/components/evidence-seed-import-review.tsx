"use client";

import * as React from "react";
import { CheckCircle2, FileUp, RefreshCw, ShieldCheck, Upload } from "lucide-react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Link } from "@/src/i18n/routing";

type SeedFormat = "auto" | "json" | "csv";

type SeedPreviewRow = {
  row_label: string;
  status: "valid" | "invalid" | string;
  intent: "insert" | "update" | "invalid" | string;
  code?: string | null;
  name?: string | null;
  category?: string | null;
  region?: string | null;
  unit?: string | null;
  as_of?: string | null;
  value?: string | null;
  source?: string | null;
  metadata?: {
    source_present?: boolean;
    method_present?: boolean;
  };
  errors?: string[];
};

type SeedPreviewPayload = {
  status: "valid" | "invalid" | string;
  can_import: boolean;
  format?: string | null;
  filename?: string | null;
  summary?: {
    rows?: number;
    valid_rows?: number;
    invalid_rows?: number;
    inserts?: number;
    updates?: number;
    affected_codes?: string[];
    latest_as_of?: string | null;
  };
  rows?: SeedPreviewRow[];
  errors?: string[];
};

type SeedImportPayload = {
  status?: string;
  observations?: number;
  codes?: string[];
  latest_as_of?: string | null;
  summary?: {
    inserts?: number;
    updates?: number;
  };
};

export type EvidenceSeedImportReviewLabels = {
  title: string;
  description: string;
  fileLabel: string;
  fileButton: string;
  selectedFile: string;
  pasteLabel: string;
  pastePlaceholder: string;
  formatLabel: string;
  formatAuto: string;
  formatJson: string;
  formatCsv: string;
  previewAction: string;
  previewing: string;
  importAction: string;
  importing: string;
  clearAction: string;
  contentRequired: string;
  fileReadFailed: string;
  previewFailed: string;
  importFailed: string;
  importSuccess: string;
  invalidNoImport: string;
  overwriteWarning: string;
  overwriteCheckbox: string;
  citationBoundary: string;
  summaryRows: string;
  summaryValid: string;
  summaryInvalid: string;
  summaryInserts: string;
  summaryUpdates: string;
  rowColumn: string;
  stateColumn: string;
  intentColumn: string;
  indicatorColumn: string;
  asOfColumn: string;
  valueColumn: string;
  sourceColumn: string;
  metadataColumn: string;
  errorsColumn: string;
  stateValid: string;
  stateInvalid: string;
  intentInsert: string;
  intentUpdate: string;
  intentInvalid: string;
  metadataComplete: string;
  metadataMissing: string;
  noRows: string;
  returnToEvidence: string;
  unavailableShort: string;
};

type EvidenceSeedImportReviewProps = {
  labels: EvidenceSeedImportReviewLabels;
};

function readPayload(payload: Record<string, unknown>): Record<string, unknown> {
  const detail = payload.detail;
  return detail && typeof detail === "object" ? (detail as Record<string, unknown>) : payload;
}

async function readJsonSafe(response: Response): Promise<Record<string, unknown>> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function getNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function summaryValue(preview: SeedPreviewPayload | null, key: keyof NonNullable<SeedPreviewPayload["summary"]>) {
  return preview?.summary?.[key] ?? 0;
}

function badgeVariant(status: string): "secondary" | "outline" | "destructive" {
  if (status === "valid" || status === "insert") {
    return "secondary";
  }
  if (status === "invalid") {
    return "destructive";
  }
  return "outline";
}

function labelForIntent(intent: string, labels: EvidenceSeedImportReviewLabels): string {
  if (intent === "insert") {
    return labels.intentInsert;
  }
  if (intent === "update") {
    return labels.intentUpdate;
  }
  if (intent === "invalid") {
    return labels.intentInvalid;
  }
  return intent;
}

export function EvidenceSeedImportReview({ labels }: EvidenceSeedImportReviewProps) {
  const [content, setContent] = React.useState("");
  const [filename, setFilename] = React.useState<string | null>(null);
  const [format, setFormat] = React.useState<SeedFormat>("auto");
  const [preview, setPreview] = React.useState<SeedPreviewPayload | null>(null);
  const [importResult, setImportResult] = React.useState<SeedImportPayload | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [isPreviewing, setIsPreviewing] = React.useState(false);
  const [isImporting, setIsImporting] = React.useState(false);
  const [overwriteAcknowledged, setOverwriteAcknowledged] = React.useState(false);
  const router = useRouter();
  const rows = preview?.rows ?? [];
  const updates = getNumber(preview?.summary?.updates);
  const requiresOverwriteAcknowledgement = updates > 0;
  const canImport =
    Boolean(preview?.can_import) &&
    !isImporting &&
    (!requiresOverwriteAcknowledgement || overwriteAcknowledged);

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (!file) {
      return;
    }

    try {
      const fileText = await file.text();
      setContent(fileText);
      setFilename(file.name);
      setPreview(null);
      setImportResult(null);
      setMessage(null);
    } catch {
      setMessage(labels.fileReadFailed);
    }
  }

  async function handlePreview() {
    if (!content.trim()) {
      setMessage(labels.contentRequired);
      setPreview(null);
      return;
    }

    setIsPreviewing(true);
    setMessage(null);
    setImportResult(null);
    setOverwriteAcknowledged(false);
    try {
      const response = await fetch("/api/market-indicators/seeds/preview", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          content,
          format,
          filename,
        }),
      });
      const payload = readPayload(await readJsonSafe(response)) as SeedPreviewPayload;
      setPreview(payload);
      if (!response.ok) {
        setMessage(labels.previewFailed);
      } else if (!payload.can_import) {
        setMessage(labels.invalidNoImport);
      }
    } catch {
      setMessage(labels.previewFailed);
    } finally {
      setIsPreviewing(false);
    }
  }

  async function handleImport() {
    if (!canImport) {
      return;
    }

    setIsImporting(true);
    setMessage(null);
    try {
      const response = await fetch("/api/market-indicators/seeds/import", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          content,
          format,
          filename,
          overwrite_acknowledged: overwriteAcknowledged,
        }),
      });
      const payload = readPayload(await readJsonSafe(response));
      if (response.status === 409) {
        setPreview(payload as SeedPreviewPayload);
        setMessage(labels.overwriteWarning);
        return;
      }
      if (!response.ok) {
        setPreview(payload as SeedPreviewPayload);
        setMessage(labels.importFailed);
        return;
      }

      setImportResult(payload as SeedImportPayload);
      setMessage(null);
      router.refresh();
    } catch {
      setMessage(labels.importFailed);
    } finally {
      setIsImporting(false);
    }
  }

  function handleClear() {
    setContent("");
    setFilename(null);
    setPreview(null);
    setImportResult(null);
    setMessage(null);
    setOverwriteAcknowledged(false);
    setFormat("auto");
  }

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">
            <ShieldCheck className="h-3 w-3" />
            {labels.title}
          </Badge>
          {filename ? <Badge variant="outline">{labels.selectedFile.replace("{name}", filename)}</Badge> : null}
        </div>
        <CardTitle className="flex items-center gap-2 text-xl">
          <FileUp className="h-5 w-5" />
          {labels.title}
        </CardTitle>
        <CardDescription>{labels.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,0.6fr)_minmax(0,1.4fr)]">
          <div className="space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="seed-file">
                {labels.fileLabel}
              </label>
              <Input
                id="seed-file"
                type="file"
                accept=".json,.csv,application/json,text/csv"
                onChange={handleFileChange}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="seed-format">
                {labels.formatLabel}
              </label>
              <select
                id="seed-format"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={format}
                onChange={(event) => setFormat(event.target.value as SeedFormat)}
              >
                <option value="auto">{labels.formatAuto}</option>
                <option value="json">{labels.formatJson}</option>
                <option value="csv">{labels.formatCsv}</option>
              </select>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={handlePreview} disabled={isPreviewing || isImporting}>
                <RefreshCw className={isPreviewing ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
                {isPreviewing ? labels.previewing : labels.previewAction}
              </Button>
              <Button type="button" variant="outline" onClick={handleClear} disabled={isPreviewing || isImporting}>
                {labels.clearAction}
              </Button>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="seed-content">
              {labels.pasteLabel}
            </label>
            <textarea
              id="seed-content"
              className="min-h-56 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              placeholder={labels.pastePlaceholder}
              value={content}
              onChange={(event) => {
                setContent(event.target.value);
                setPreview(null);
                setImportResult(null);
              }}
            />
          </div>
        </div>

        {message ? <div className="border bg-muted/30 p-3 text-sm text-muted-foreground">{message}</div> : null}

        {preview ? (
          <div className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-5">
              <div className="border p-2 text-sm">
                {labels.summaryRows}: {summaryValue(preview, "rows")}
              </div>
              <div className="border p-2 text-sm">
                {labels.summaryValid}: {summaryValue(preview, "valid_rows")}
              </div>
              <div className="border p-2 text-sm">
                {labels.summaryInvalid}: {summaryValue(preview, "invalid_rows")}
              </div>
              <div className="border p-2 text-sm">
                {labels.summaryInserts}: {summaryValue(preview, "inserts")}
              </div>
              <div className="border p-2 text-sm">
                {labels.summaryUpdates}: {summaryValue(preview, "updates")}
              </div>
            </div>

            {requiresOverwriteAcknowledgement ? (
              <label className="flex items-start gap-2 border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={overwriteAcknowledged}
                  onChange={(event) => setOverwriteAcknowledged(event.target.checked)}
                />
                <span>{labels.overwriteCheckbox}</span>
              </label>
            ) : null}

            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{labels.rowColumn}</TableHead>
                    <TableHead>{labels.stateColumn}</TableHead>
                    <TableHead>{labels.intentColumn}</TableHead>
                    <TableHead>{labels.indicatorColumn}</TableHead>
                    <TableHead>{labels.asOfColumn}</TableHead>
                    <TableHead>{labels.valueColumn}</TableHead>
                    <TableHead>{labels.sourceColumn}</TableHead>
                    <TableHead>{labels.metadataColumn}</TableHead>
                    <TableHead>{labels.errorsColumn}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-sm text-muted-foreground">
                        {labels.noRows}
                      </TableCell>
                    </TableRow>
                  ) : (
                    rows.map((row) => {
                      const metadataComplete = Boolean(
                        row.metadata?.source_present && row.metadata?.method_present,
                      );
                      return (
                        <TableRow key={row.row_label}>
                          <TableCell className="font-mono text-xs">{row.row_label}</TableCell>
                          <TableCell>
                            <Badge variant={badgeVariant(row.status)}>
                              {row.status === "valid" ? labels.stateValid : labels.stateInvalid}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={badgeVariant(row.intent)}>{labelForIntent(row.intent, labels)}</Badge>
                          </TableCell>
                          <TableCell className="min-w-56">
                            <div className="font-medium">{row.name ?? row.code ?? labels.unavailableShort}</div>
                            <div className="font-mono text-xs text-muted-foreground">
                              {row.code ?? labels.unavailableShort}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {[row.region, row.category].filter(Boolean).join(" / ") || labels.unavailableShort}
                            </div>
                          </TableCell>
                          <TableCell>{row.as_of ?? labels.unavailableShort}</TableCell>
                          <TableCell className="font-mono">{row.value ?? labels.unavailableShort}</TableCell>
                          <TableCell className="max-w-64 text-sm text-muted-foreground">
                            {row.source ?? labels.unavailableShort}
                          </TableCell>
                          <TableCell>
                            <Badge variant={metadataComplete ? "secondary" : "outline"}>
                              {metadataComplete ? labels.metadataComplete : labels.metadataMissing}
                            </Badge>
                          </TableCell>
                          <TableCell className="max-w-80 text-xs text-muted-foreground">
                            {(row.errors ?? []).length > 0 ? row.errors?.join("; ") : labels.unavailableShort}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>

            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <p className="text-sm text-muted-foreground">{labels.citationBoundary}</p>
              <Button type="button" onClick={handleImport} disabled={!canImport}>
                <Upload className={isImporting ? "h-4 w-4 animate-pulse" : "h-4 w-4"} />
                {isImporting ? labels.importing : labels.importAction}
              </Button>
            </div>
          </div>
        ) : null}

        {importResult?.status === "imported" ? (
          <div className="flex flex-col gap-3 border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              <span>
                {labels.importSuccess} {labels.summaryRows}: {importResult.observations ?? 0}
              </span>
            </div>
            <Link href="/evidence" className="font-medium text-primary hover:underline">
              {labels.returnToEvidence}
            </Link>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
