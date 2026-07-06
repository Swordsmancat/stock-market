export type DataTrustSeverity =
  | "ok"
  | "fresh"
  | "delayed"
  | "stale"
  | "mock"
  | "degraded"
  | "no_data"
  | "unavailable"
  | "unknown";

export type RawDataTrustInput = {
  status?: string | null;
  freshness?: string | null | { status?: string | null; reason?: string | null; cache_status?: string | null; data_as_of?: string | null; fetched_at?: string | null; cached_at?: string | null };
  data_mode?: string | null;
  dataMode?: string | null;
  source?: string | null;
  provider?: string | null;
  requested_provider?: string | null;
  requestedProvider?: string | null;
  effective_provider?: string | null;
  effectiveProvider?: string | null;
  as_of?: string | null;
  asOf?: string | null;
  generated_at?: string | null;
  generatedAt?: string | null;
  no_data_reason?: string | null;
  noDataReason?: string | null;
  reason?: string | null;
  message?: string | null;
  availability?: {
    status?: string | null;
    reason?: string | null;
    is_realtime?: boolean | null;
    isRealtime?: boolean | null;
    is_delayed?: boolean | null;
    isDelayed?: boolean | null;
    delay_minutes?: number | null;
    delayMinutes?: number | null;
  } | null;
  is_realtime?: boolean | null;
  isRealtime?: boolean | null;
  is_delayed?: boolean | null;
  isDelayed?: boolean | null;
  delay_minutes?: number | null;
  delayMinutes?: number | null;
  session?: { status?: string | null; reason?: string | null } | null;
};

export type DataTrustSignal = {
  severity: DataTrustSeverity;
  label: string;
  description: string;
  source?: string | null;
  provider?: string | null;
  requestedProvider?: string | null;
  effectiveProvider?: string | null;
  asOf?: string | null;
  generatedAt?: string | null;
  reason?: string | null;
  isRealtime?: boolean;
  isDelayed?: boolean;
  delayMinutes?: number | null;
  cacheStatus?: string | null;
  sessionStatus?: string | null;
};

const LABEL_BY_SEVERITY: Record<DataTrustSeverity, string> = {
  ok: "可用",
  fresh: "新鲜",
  delayed: "延迟",
  stale: "陈旧",
  mock: "模拟",
  degraded: "降级",
  no_data: "无数据",
  unavailable: "不可用",
  unknown: "未知",
};

function normalizeStatus(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  return value.trim().toLowerCase();
}

function getFreshnessStatus(rawInput: RawDataTrustInput): string | null {
  if (typeof rawInput.freshness === "string") {
    return normalizeStatus(rawInput.freshness);
  }
  return normalizeStatus(rawInput.freshness?.status);
}

function getReason(rawInput: RawDataTrustInput): string | null {
  if (rawInput.no_data_reason) return rawInput.no_data_reason;
  if (rawInput.noDataReason) return rawInput.noDataReason;
  if (rawInput.availability?.reason) return rawInput.availability.reason;
  if (typeof rawInput.freshness === "object" && rawInput.freshness?.reason) return rawInput.freshness.reason;
  if (rawInput.session?.reason) return rawInput.session.reason;
  if (rawInput.reason) return rawInput.reason;
  if (rawInput.message) return rawInput.message;
  return null;
}

function resolveSeverity(rawInput: RawDataTrustInput): DataTrustSeverity {
  const status = normalizeStatus(rawInput.status);
  const freshness = getFreshnessStatus(rawInput);
  const dataMode = normalizeStatus(rawInput.data_mode ?? rawInput.dataMode);
  const availabilityStatus = normalizeStatus(rawInput.availability?.status);
  const source = normalizeStatus(rawInput.source);
  const isRealtime = rawInput.is_realtime ?? rawInput.isRealtime ?? rawInput.availability?.is_realtime ?? rawInput.availability?.isRealtime;
  const isDelayed = rawInput.is_delayed ?? rawInput.isDelayed ?? rawInput.availability?.is_delayed ?? rawInput.availability?.isDelayed;

  if (dataMode === "mock" || dataMode === "demo" || source?.includes("mock") || source?.includes("fixture")) {
    return "mock";
  }
  if (status === "unavailable" || freshness === "unavailable" || availabilityStatus === "unavailable") {
    return "unavailable";
  }
  if (status === "no_data" || freshness === "no_data" || availabilityStatus === "no_data") {
    return "no_data";
  }
  if (status === "degraded" || availabilityStatus === "degraded") {
    return "degraded";
  }
  if (dataMode === "delayed" || isDelayed) {
    return "delayed";
  }
  if (freshness === "stale") {
    return "stale";
  }
  if (freshness === "fresh") {
    return "fresh";
  }
  if (status === "ok") {
    return isRealtime === true ? "fresh" : "ok";
  }
  return "unknown";
}

function buildDescription(signal: Omit<DataTrustSignal, "description">): string {
  const details: string[] = [LABEL_BY_SEVERITY[signal.severity]];
  if (signal.effectiveProvider || signal.provider) {
    details.push(`provider: ${signal.effectiveProvider ?? signal.provider}`);
  }
  if (signal.source) {
    details.push(`source: ${signal.source}`);
  }
  if (signal.isRealtime === true) {
    details.push("实时标记: true");
  } else if (signal.isDelayed === true) {
    details.push(`延迟${signal.delayMinutes ? ` ${signal.delayMinutes} 分钟` : ""}`);
  } else {
    details.push("未声明实时");
  }
  if (signal.cacheStatus) {
    details.push(`cache: ${signal.cacheStatus}`);
  }
  if (signal.sessionStatus) {
    details.push(`session: ${signal.sessionStatus}`);
  }
  if (signal.reason) {
    details.push(`reason: ${signal.reason}`);
  }
  return details.join(" · ");
}

export function createDataTrustSignal(rawInput: RawDataTrustInput = {}): DataTrustSignal {
  const freshnessObject = typeof rawInput.freshness === "object" ? rawInput.freshness : null;
  const severity = resolveSeverity(rawInput);
  const signalWithoutDescription: Omit<DataTrustSignal, "description"> = {
    severity,
    label: LABEL_BY_SEVERITY[severity],
    source: rawInput.source ?? null,
    provider: rawInput.provider ?? null,
    requestedProvider: rawInput.requested_provider ?? rawInput.requestedProvider ?? null,
    effectiveProvider: rawInput.effective_provider ?? rawInput.effectiveProvider ?? null,
    asOf: rawInput.as_of ?? rawInput.asOf ?? freshnessObject?.data_as_of ?? null,
    generatedAt: rawInput.generated_at ?? rawInput.generatedAt ?? freshnessObject?.fetched_at ?? freshnessObject?.cached_at ?? null,
    reason: getReason(rawInput),
    isRealtime: rawInput.is_realtime ?? rawInput.isRealtime ?? rawInput.availability?.is_realtime ?? rawInput.availability?.isRealtime ?? false,
    isDelayed: rawInput.is_delayed ?? rawInput.isDelayed ?? rawInput.availability?.is_delayed ?? rawInput.availability?.isDelayed ?? false,
    delayMinutes: rawInput.delay_minutes ?? rawInput.delayMinutes ?? rawInput.availability?.delay_minutes ?? rawInput.availability?.delayMinutes ?? null,
    cacheStatus: freshnessObject?.cache_status ?? null,
    sessionStatus: rawInput.session?.status ?? null,
  };

  return {
    ...signalWithoutDescription,
    description: buildDescription(signalWithoutDescription),
  };
}

export function getDataTrustTitle(signal: DataTrustSignal): string {
  return signal.description;
}
