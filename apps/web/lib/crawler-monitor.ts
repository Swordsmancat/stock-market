export const CRAWLER_PIPELINE_IDS = [
  "market_cn",
  "market_us",
  "market_hk",
  "universe_cn",
  "fund_index_cn",
  "evidence_incremental",
  "fundamental_shard",
  "official_disclosures",
  "eastmoney_calendar",
  "eastmoney_industry",
  "eastmoney_news",
  "eastmoney_fundamentals",
] as const;

export type CrawlerPipelineId = (typeof CRAWLER_PIPELINE_IDS)[number];
export type CrawlerStatus =
  | "running"
  | "healthy"
  | "overdue"
  | "stalled"
  | "failed"
  | "not_recorded";

export type CrawlerProgress = {
  phase: string | null;
  current: number;
  total: number;
  message: string | null;
  updated_at: string | null;
};

export type CrawlerMonitorItem = {
  id: CrawlerPipelineId;
  status: CrawlerStatus;
  task_name: string;
  scope: string;
  provider: string;
  cadence: string;
  latest_task_run_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  heartbeat_at: string | null;
  duration_ms: number | null;
  progress: CrawlerProgress | null;
  recent_failure_count: number;
  diagnostic_code: string | null;
  error_summary: string | null;
};

export type CrawlerMonitorPayload = {
  status: "ok";
  generated_at: string;
  summary: {
    total: number;
    running: number;
    healthy: number;
    attention: number;
    recent_failures: number;
  };
  items: CrawlerMonitorItem[];
};

const STATUS_VALUES = new Set<CrawlerStatus>([
  "running",
  "healthy",
  "overdue",
  "stalled",
  "failed",
  "not_recorded",
]);
const PIPELINE_IDS = new Set<CrawlerPipelineId>(CRAWLER_PIPELINE_IDS);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNonNegativeNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function isProgress(value: unknown): value is CrawlerProgress {
  if (!isRecord(value)) return false;
  return (
    isNullableString(value.phase) &&
    isNonNegativeNumber(value.current) &&
    isNonNegativeNumber(value.total) &&
    isNullableString(value.message) &&
    isNullableString(value.updated_at)
  );
}

function isItem(value: unknown): value is CrawlerMonitorItem {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === "string" &&
    PIPELINE_IDS.has(value.id as CrawlerPipelineId) &&
    typeof value.status === "string" &&
    STATUS_VALUES.has(value.status as CrawlerStatus) &&
    typeof value.task_name === "string" &&
    typeof value.scope === "string" &&
    typeof value.provider === "string" &&
    typeof value.cadence === "string" &&
    isNullableString(value.latest_task_run_id) &&
    isNullableString(value.started_at) &&
    isNullableString(value.finished_at) &&
    isNullableString(value.heartbeat_at) &&
    (value.duration_ms === null || isNonNegativeNumber(value.duration_ms)) &&
    (value.progress === null || isProgress(value.progress)) &&
    isNonNegativeNumber(value.recent_failure_count) &&
    isNullableString(value.diagnostic_code) &&
    isNullableString(value.error_summary)
  );
}

export function isCrawlerMonitorPayload(value: unknown): value is CrawlerMonitorPayload {
  if (!isRecord(value) || value.status !== "ok" || typeof value.generated_at !== "string") {
    return false;
  }
  if (!isRecord(value.summary) || !Array.isArray(value.items)) return false;
  if (
    !isNonNegativeNumber(value.summary.total) ||
    !isNonNegativeNumber(value.summary.running) ||
    !isNonNegativeNumber(value.summary.healthy) ||
    !isNonNegativeNumber(value.summary.attention) ||
    !isNonNegativeNumber(value.summary.recent_failures) ||
    value.items.length !== CRAWLER_PIPELINE_IDS.length ||
    !value.items.every(isItem)
  ) {
    return false;
  }
  const ids = new Set(value.items.map((item) => item.id));
  return ids.size === CRAWLER_PIPELINE_IDS.length && value.summary.total === value.items.length;
}

export function formatCrawlerDuration(durationMs: number | null, locale: string): string | null {
  if (durationMs === null || !Number.isFinite(durationMs) || durationMs < 0) return null;
  const formatUnit = (value: number, unit: "second" | "minute" | "hour") =>
    new Intl.NumberFormat(locale, { style: "unit", unit, unitDisplay: "narrow" }).format(value);
  const totalSeconds = Math.round(durationMs / 1_000);
  if (totalSeconds < 60) return formatUnit(totalSeconds, "second");
  const totalMinutes = Math.round(totalSeconds / 60);
  if (totalMinutes < 60) return formatUnit(totalMinutes, "minute");
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${formatUnit(hours, "hour")} ${formatUnit(minutes, "minute")}`;
}
