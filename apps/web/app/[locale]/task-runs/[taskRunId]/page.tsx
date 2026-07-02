import { getTranslations } from "next-intl/server";
import { Link } from "@/src/i18n/routing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TaskRunRetryButton } from "@/components/task-run-actions";
import { backendFetch } from "@/lib/backend-api";

type TranslationValues = Record<string, string | number>;

type TaskRunsTranslator = (key: string, values?: TranslationValues) => string;

type QualityStatus = "OK" | "WARN" | "FAIL" | "UNKNOWN";

type RenderableQualityIssue = {
  symbol: string | null;
  code: string | null;
  message: string;
  count: number | null;
  details: string | null;
};

type InstrumentQualityDiagnostics = {
  symbol: string | null;
  status: QualityStatus;
  checkedBars: number | null;
  missingDates: string[];
  invalidOhlc: string[];
  volumeWarnings: string[];
  qualityError: string | null;
  rawInstrumentFallback: string | null;
};

type QualityDiagnostics = {
  status: QualityStatus;
  instrumentCount: number | null;
  instruments: InstrumentQualityDiagnostics[];
  errors: RenderableQualityIssue[];
  warnings: RenderableQualityIssue[];
  qualityError: string | null;
};

type TaskRunDetail = {
  id: string;
  task_name: string;
  status: string;
  started_at: string;
  duration_ms: number | null;
  celery_task_id: string | null;
  input_json: Record<string, unknown>;
  result_json: Record<string, unknown> | null;
  error_message: string | null;
};

type TaskRunDetailPayload = {
  item?: TaskRunDetail;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeQualityStatus(value: unknown): QualityStatus {
  if (typeof value !== "string") {
    return "UNKNOWN";
  }

  const normalizedValue = value.toUpperCase();
  if (normalizedValue === "OK" || normalizedValue === "WARN" || normalizedValue === "FAIL") {
    return normalizedValue;
  }

  return "UNKNOWN";
}

function renderUnknownValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean" || value === null) {
    return String(value);
  }

  try {
    const serializedValue = JSON.stringify(value, null, 2);
    return serializedValue ?? String(value);
  } catch {
    return String(value);
  }
}

function normalizeOptionalDisplayText(value: unknown): string | null {
  if (value === undefined || value === null) {
    return null;
  }

  const renderedValue = renderUnknownValue(value).trim();
  return renderedValue.length > 0 ? renderedValue : null;
}

function normalizeUnknownArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((item) => renderUnknownValue(item));
}

function normalizeQualityIssue(value: unknown): RenderableQualityIssue {
  if (!isRecord(value)) {
    return {
      symbol: null,
      code: null,
      message: renderUnknownValue(value),
      count: null,
      details: null,
    };
  }

  const fallbackMessage = renderUnknownValue(value);
  const message = normalizeOptionalDisplayText(value.message) ?? fallbackMessage;

  return {
    symbol: normalizeOptionalDisplayText(value.symbol),
    code: normalizeOptionalDisplayText(value.code),
    message,
    count: normalizeFiniteNumber(value.count),
    details: normalizeOptionalDisplayText(value.details),
  };
}

function normalizeQualityIssueArray(value: unknown): RenderableQualityIssue[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((item) => normalizeQualityIssue(item));
}

function normalizeInstrumentDiagnostics(value: unknown): InstrumentQualityDiagnostics {
  if (!isRecord(value)) {
    return {
      symbol: null,
      status: "UNKNOWN",
      checkedBars: null,
      missingDates: [],
      invalidOhlc: [],
      volumeWarnings: [],
      qualityError: null,
      rawInstrumentFallback: renderUnknownValue(value),
    };
  }

  return {
    symbol: normalizeOptionalDisplayText(value.symbol),
    status: normalizeQualityStatus(value.status),
    checkedBars: normalizeFiniteNumber(value.checked_bars),
    missingDates: normalizeUnknownArray(value.missing_dates),
    invalidOhlc: normalizeUnknownArray(value.invalid_ohlc),
    volumeWarnings: normalizeUnknownArray(value.volume_warnings),
    qualityError: normalizeOptionalDisplayText(value.quality_error),
    rawInstrumentFallback: null,
  };
}

function extractQualityDiagnostics(resultJson: Record<string, unknown> | null): QualityDiagnostics | null {
  const rawDiagnostics = resultJson?.quality_diagnostics;
  if (!isRecord(rawDiagnostics)) {
    return null;
  }

  const qualityError = normalizeOptionalDisplayText(rawDiagnostics.quality_error);
  const errors = normalizeQualityIssueArray(rawDiagnostics.errors);

  if (qualityError !== null) {
    errors.unshift({
      symbol: null,
      code: null,
      message: qualityError,
      count: null,
      details: null,
    });
  }

  return {
    status: normalizeQualityStatus(rawDiagnostics.status),
    instrumentCount: normalizeFiniteNumber(rawDiagnostics.instrument_count),
    instruments: Array.isArray(rawDiagnostics.instruments)
      ? rawDiagnostics.instruments.map((instrument) => normalizeInstrumentDiagnostics(instrument))
      : [],
    errors,
    warnings: normalizeQualityIssueArray(rawDiagnostics.warnings),
    qualityError,
  };
}

function extractTaskResultInstrumentCount(resultJson: Record<string, unknown> | null): number | null {
  return normalizeFiniteNumber(resultJson?.instrument_count);
}

function getQualityStatusBadgeVariant(status: QualityStatus): "default" | "secondary" | "destructive" | "outline" {
  if (status === "FAIL") {
    return "destructive";
  }

  if (status === "WARN") {
    return "secondary";
  }

  if (status === "UNKNOWN") {
    return "outline";
  }

  return "default";
}

function getQualityStatusText(status: QualityStatus, t: TaskRunsTranslator): string {
  return status === "UNKNOWN" ? t("qualityStatusUnknown") : status;
}

function getQualitySummaryText(status: QualityStatus, t: TaskRunsTranslator): string {
  if (status === "OK") {
    return t("qualitySummaryOk");
  }

  if (status === "WARN") {
    return t("qualitySummaryWarn");
  }

  if (status === "FAIL") {
    return t("qualitySummaryFail");
  }

  return t("qualitySummaryUnknown");
}

async function fetchTaskRun(taskRunId: string): Promise<TaskRunDetail | null> {
  const response = await backendFetch(`/task-runs/${taskRunId}`, { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  const payload = (await response.json()) as TaskRunDetail | TaskRunDetailPayload;
  return "item" in payload && payload.item ? payload.item : (payload as TaskRunDetail);
}

type GeneratedReportLink = {
  id: string;
  label: string;
  symbol: string | null;
};

function extractGeneratedReportLink(value: unknown): GeneratedReportLink | null {
  if (!isRecord(value)) {
    return null;
  }

  const reportId = value.id;
  if (typeof reportId !== "string" || reportId.length === 0) {
    return null;
  }

  const symbol = normalizeOptionalDisplayText(value.symbol);
  const label = symbol !== null ? `${symbol} · ${reportId}` : reportId;

  return {
    id: reportId,
    label,
    symbol,
  };
}

function appendGeneratedReportLink(
  links: GeneratedReportLink[],
  seenReportIds: Set<string>,
  value: unknown,
): void {
  const reportLink = extractGeneratedReportLink(value);
  if (reportLink === null || seenReportIds.has(reportLink.id)) {
    return;
  }

  seenReportIds.add(reportLink.id);
  links.push(reportLink);
}

function extractGeneratedReportLinks(taskRun: TaskRunDetail): GeneratedReportLink[] {
  const links: GeneratedReportLink[] = [];
  const seenReportIds = new Set<string>();
  const resultJson = taskRun.result_json;

  appendGeneratedReportLink(links, seenReportIds, resultJson?.report);

  const resultItems = resultJson?.items;
  if (Array.isArray(resultItems)) {
    for (const resultItem of resultItems) {
      if (isRecord(resultItem)) {
        appendGeneratedReportLink(links, seenReportIds, resultItem.report);
      }
    }
  }

  return links;
}

function QualityIssueList({
  title,
  emptyText,
  issues,
  t,
}: {
  title: string;
  emptyText: string;
  issues: RenderableQualityIssue[];
  t: TaskRunsTranslator;
}) {
  return (
    <div className="rounded-md border p-3">
      <h4 className="mb-2 text-sm font-medium">{title}</h4>
      {issues.length > 0 ? (
        <ul className="space-y-2">
          {issues.map((issue, index) => (
            <li key={`${title}-${index}`} className="rounded-md bg-muted/40 p-2 text-sm">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                {issue.symbol ? <Badge variant="outline">{issue.symbol}</Badge> : null}
                {issue.code ? <Badge variant="secondary">{issue.code}</Badge> : null}
                {issue.count !== null ? (
                  <span className="text-xs text-muted-foreground">{t("qualityIssueCount", { count: issue.count })}</span>
                ) : null}
              </div>
              <p className="whitespace-pre-wrap break-words text-muted-foreground">{issue.message}</p>
              {issue.details ? (
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-md border bg-background p-2 text-xs">
                  {issue.details}
                </pre>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">{emptyText}</p>
      )}
    </div>
  );
}

function QualityDetailList({ title, values, t }: { title: string; values: string[]; t: TaskRunsTranslator }) {
  return (
    <div>
      <h5 className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h5>
      {values.length > 0 ? (
        <ul className="space-y-1">
          {values.map((value, index) => (
            <li key={`${title}-${index}`}>
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-md border bg-background p-2 text-xs">{value}</pre>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">{t("qualityNone")}</p>
      )}
    </div>
  );
}

function InstrumentDiagnosticsCard({
  instrument,
  t,
}: {
  instrument: InstrumentQualityDiagnostics;
  t: TaskRunsTranslator;
}) {
  return (
    <div className="rounded-md border p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h4 className="text-sm font-medium">{instrument.symbol ?? t("qualityUnknownSymbol")}</h4>
          <p className="text-xs text-muted-foreground">{t("qualitySymbol")}</p>
        </div>
        <Badge variant={getQualityStatusBadgeVariant(instrument.status)}>
          {getQualityStatusText(instrument.status, t)}
        </Badge>
      </div>

      <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-muted-foreground">{t("qualityCheckedBars")}</dt>
          <dd className="font-medium">{instrument.checkedBars ?? t("qualityUnavailable")}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{t("qualityMissingDates")}</dt>
          <dd className="font-medium">{instrument.missingDates.length}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{t("qualityInvalidOhlc")}</dt>
          <dd className="font-medium">{instrument.invalidOhlc.length}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{t("qualityVolumeWarnings")}</dt>
          <dd className="font-medium">{instrument.volumeWarnings.length}</dd>
        </div>
      </dl>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <QualityDetailList title={t("qualityMissingDates")} values={instrument.missingDates} t={t} />
        <QualityDetailList title={t("qualityInvalidOhlc")} values={instrument.invalidOhlc} t={t} />
        <QualityDetailList title={t("qualityVolumeWarnings")} values={instrument.volumeWarnings} t={t} />
      </div>

      {instrument.qualityError ? (
        <div className="mt-3">
          <h5 className="mb-1 text-xs font-medium uppercase tracking-wide text-destructive">{t("qualityError")}</h5>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
            {instrument.qualityError}
          </pre>
        </div>
      ) : null}

      {instrument.rawInstrumentFallback ? (
        <div className="mt-3">
          <h5 className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {t("qualityIssueDetails")}
          </h5>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-md border bg-background p-2 text-xs">
            {instrument.rawInstrumentFallback}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

function buildRenderableQualityIssues(
  diagnostics: QualityDiagnostics,
  t: TaskRunsTranslator,
): { errors: RenderableQualityIssue[]; warnings: RenderableQualityIssue[] } {
  const errors = [...diagnostics.errors];
  const warnings = [...diagnostics.warnings];

  for (const instrument of diagnostics.instruments) {
    if (instrument.qualityError !== null) {
      errors.push({
        symbol: instrument.symbol,
        code: "QUALITY_ERROR",
        message: instrument.qualityError,
        count: null,
        details: null,
      });
    }

    if (instrument.invalidOhlc.length > 0) {
      errors.push({
        symbol: instrument.symbol,
        code: "INVALID_OHLC",
        message: t("qualityInstrumentInvalidOhlcSummary", { count: instrument.invalidOhlc.length }),
        count: instrument.invalidOhlc.length,
        details: instrument.invalidOhlc.join("\n"),
      });
    }

    if (instrument.missingDates.length > 0) {
      warnings.push({
        symbol: instrument.symbol,
        code: "MISSING_DATES",
        message: t("qualityInstrumentMissingDatesSummary", { count: instrument.missingDates.length }),
        count: instrument.missingDates.length,
        details: instrument.missingDates.join("\n"),
      });
    }

    if (instrument.volumeWarnings.length > 0) {
      warnings.push({
        symbol: instrument.symbol,
        code: "VOLUME_WARNING",
        message: t("qualityInstrumentVolumeWarningsSummary", { count: instrument.volumeWarnings.length }),
        count: instrument.volumeWarnings.length,
        details: instrument.volumeWarnings.join("\n"),
      });
    }
  }

  return { errors, warnings };
}

function QualityDiagnosticsSection({
  diagnostics,
  resultInstrumentCount,
  t,
}: {
  diagnostics: QualityDiagnostics | null;
  resultInstrumentCount: number | null;
  t: TaskRunsTranslator;
}) {
  const displayIssues = diagnostics
    ? buildRenderableQualityIssues(diagnostics, t)
    : { errors: [] satisfies RenderableQualityIssue[], warnings: [] satisfies RenderableQualityIssue[] };

  return (
    <div className="rounded-lg border p-4" data-testid="quality-diagnostics-section">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-medium">{t("qualityDiagnostics")}</h3>
          <p className="text-sm text-muted-foreground">{t("qualityDiagnosticsDesc")}</p>
        </div>
        {diagnostics ? (
          <Badge variant={getQualityStatusBadgeVariant(diagnostics.status)}>
            {getQualityStatusText(diagnostics.status, t)}
          </Badge>
        ) : null}
      </div>

      {diagnostics ? (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">{getQualitySummaryText(diagnostics.status, t)}</p>

          <dl className="grid gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-md bg-muted/40 p-3">
              <dt className="text-muted-foreground">{t("qualityStatus")}</dt>
              <dd className="font-medium">{getQualityStatusText(diagnostics.status, t)}</dd>
            </div>
            <div className="rounded-md bg-muted/40 p-3">
              <dt className="text-muted-foreground">{t("qualityInstrumentsChecked")}</dt>
              <dd className="font-medium">{diagnostics.instrumentCount ?? t("qualityUnavailable")}</dd>
            </div>
            <div className="rounded-md bg-muted/40 p-3">
              <dt className="text-muted-foreground">{t("qualityTaskResultInstruments")}</dt>
              <dd className="font-medium">{resultInstrumentCount ?? t("qualityUnavailable")}</dd>
            </div>
          </dl>

          <div className="grid gap-3 lg:grid-cols-2">
            <QualityIssueList
              title={t("qualityErrors")}
              emptyText={t("qualityNoErrors")}
              issues={displayIssues.errors}
              t={t}
            />
            <QualityIssueList
              title={t("qualityWarnings")}
              emptyText={t("qualityNoWarnings")}
              issues={displayIssues.warnings}
              t={t}
            />
          </div>

          <div>
            <h4 className="mb-2 text-sm font-medium">{t("qualityInstrumentDetails")}</h4>
            {diagnostics.instruments.length > 0 ? (
              <div className="space-y-3">
                {diagnostics.instruments.map((instrument, index) => (
                  <InstrumentDiagnosticsCard
                    key={`${instrument.symbol ?? "instrument"}-${index}`}
                    instrument={instrument}
                    t={t}
                  />
                ))}
              </div>
            ) : (
              <p className="rounded-md border p-3 text-sm text-muted-foreground">{t("qualityNoInstrumentDetails")}</p>
            )}
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">{t("qualityDiagnosticsMissing")}</p>
      )}
    </div>
  );
}

export default async function TaskRunDetailPage({
  params,
}: {
  params: Promise<{ taskRunId: string; locale: string }>;
}) {
  const { taskRunId } = await params;
  const taskRun = await fetchTaskRun(taskRunId);
  const t = (await getTranslations("TaskRuns")) as TaskRunsTranslator;

  if (taskRun === null) {
    return (
      <div className="space-y-6">
        <Button variant="outline" asChild>
          <Link href="/task-runs">{t("backToList")}</Link>
        </Button>
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">{t("notFound")}</CardContent>
        </Card>
      </div>
    );
  }

  const generatedReportLinks = extractGeneratedReportLinks(taskRun);
  const qualityDiagnostics = extractQualityDiagnostics(taskRun.result_json);
  const resultInstrumentCount = extractTaskResultInstrumentCount(taskRun.result_json);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("detailTitle")}</h1>
          <p className="font-mono text-sm text-muted-foreground">{taskRun.id}</p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/task-runs">{t("backToList")}</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>{taskRun.task_name}</CardTitle>
            <Badge
              variant={
                taskRun.status === "succeeded"
                  ? "default"
                  : taskRun.status === "failed"
                    ? "destructive"
                    : "secondary"
              }
            >
              {taskRun.status}
            </Badge>
          </div>
          <CardDescription>
            {t("startedAt")}: {new Date(taskRun.started_at).toLocaleString()}
            {taskRun.duration_ms != null ? ` · ${taskRun.duration_ms} ms` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {taskRun.celery_task_id ? (
            <div>
              <h3 className="mb-1 text-sm font-medium">{t("celeryTaskId")}</h3>
              <p className="font-mono text-sm text-muted-foreground">{taskRun.celery_task_id}</p>
            </div>
          ) : null}
          <div>
            <h3 className="mb-1 text-sm font-medium">{t("input")}</h3>
            <pre className="overflow-x-auto rounded-md border bg-muted/50 p-3 text-xs">
              {JSON.stringify(taskRun.input_json, null, 2)}
            </pre>
          </div>
          <QualityDiagnosticsSection
            diagnostics={qualityDiagnostics}
            resultInstrumentCount={resultInstrumentCount}
            t={t}
          />
          <div>
            <h3 className="mb-1 text-sm font-medium">{t("result")}</h3>
            <pre className="overflow-x-auto rounded-md border bg-muted/50 p-3 text-xs">
              {taskRun.result_json ? JSON.stringify(taskRun.result_json, null, 2) : "—"}
            </pre>
          </div>
          {generatedReportLinks.length > 0 ? (
            <div>
              <h3 className="mb-1 text-sm font-medium">{t("generatedReport")}</h3>
              <div className="flex flex-wrap gap-2">
                {generatedReportLinks.map((reportLink) => (
                  <Button key={reportLink.id} variant="link" className="h-auto p-0" asChild>
                    <Link href={`/reports/${reportLink.id}` as any}>{reportLink.label}</Link>
                  </Button>
                ))}
              </div>
            </div>
          ) : null}
          {taskRun.error_message ? (
            <div>
              <h3 className="mb-1 text-sm font-medium text-destructive">{t("error")}</h3>
              <pre className="overflow-x-auto rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
                {taskRun.error_message}
              </pre>
            </div>
          ) : null}
          {taskRun.status === "failed" ? (
            <div className="pt-2">
              <TaskRunRetryButton taskRunId={taskRun.id} />
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
