export type StoredNewsItem = {
  symbol?: string;
  title: string;
  url?: string | null;
  source?: string | null;
  published_at?: string | null;
  summary?: string | null;
  sentiment?: string | null;
  confidence?: number | null;
};

export type InstrumentNewsPayload = {
  symbol: string;
  source?: string | null;
  summary?: {
    latest_sentiment?: string | null;
    article_count?: number | null;
  } | null;
  items: StoredNewsItem[];
};

export type NewsRefreshStatus =
  | "database_hit"
  | "refreshed"
  | "no_data"
  | "provider_error"
  | "unsupported";

export type NewsDiagnostic = {
  provider?: string;
  status?: string;
  severity?: string;
  code?: string;
};

export type NewsRefreshPayload = {
  symbol: string;
  market: string;
  status: NewsRefreshStatus;
  news: InstrumentNewsPayload;
  diagnostics: NewsDiagnostic[];
};

export type LatestStoredNewsPayload = {
  source: string;
  status: "ok" | "no_data";
  count: number;
  limit: number;
  items: StoredNewsItem[];
};

const NEWS_REFRESH_STATUSES = new Set<NewsRefreshStatus>([
  "database_hit",
  "refreshed",
  "no_data",
  "provider_error",
  "unsupported",
]);

const SENSITIVE_URL_PARAMETER_PARTS = new Set([
  "auth",
  "authentication",
  "authorization",
  "bearer",
  "cookie",
  "credential",
  "credentials",
  "key",
  "password",
  "secret",
  "session",
  "sig",
  "signature",
  "token",
]);

const SENSITIVE_URL_PARAMETER_ALIASES = new Set([
  "accesstoken",
  "apikey",
  "authkey",
  "authtoken",
  "clientsecret",
  "sessionid",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isOptionalString(value: unknown): value is string | null | undefined {
  return value === undefined || value === null || typeof value === "string";
}

function isOptionalFiniteNumber(
  value: unknown,
): value is number | null | undefined {
  return value === undefined || value === null ||
    (typeof value === "number" && Number.isFinite(value));
}

function isCredentialUrlParameter(name: string): boolean {
  const separated = name.replace(/([a-z0-9])([A-Z])/g, "$1_$2");
  const parts = separated
    .split(/[^A-Za-z0-9]+/)
    .filter(Boolean)
    .map((part) => part.toLowerCase());
  return (
    SENSITIVE_URL_PARAMETER_ALIASES.has(parts.join("")) ||
    parts.some((part) => SENSITIVE_URL_PARAMETER_PARTS.has(part))
  );
}

function isOptionalPublicHttpUrl(value: unknown): value is string | null | undefined {
  if (value === undefined || value === null) {
    return true;
  }
  if (typeof value !== "string") {
    return false;
  }

  try {
    const url = new URL(value);
    if (
      (url.protocol !== "http:" && url.protocol !== "https:") ||
      url.username !== "" ||
      url.password !== ""
    ) {
      return false;
    }

    if ([...url.searchParams.keys()].some(isCredentialUrlParameter)) {
      return false;
    }
    const fragmentParameters = new URLSearchParams(url.hash.slice(1));
    return ![...fragmentParameters.keys()].some(isCredentialUrlParameter);
  } catch {
    return false;
  }
}

export function isStoredNewsItem(value: unknown): value is StoredNewsItem {
  if (
    !isRecord(value) ||
    typeof value.title !== "string" ||
    value.title.trim().length === 0
  ) {
    return false;
  }

  if (
    typeof value.confidence === "number" &&
    (value.confidence < 0 || value.confidence > 1)
  ) {
    return false;
  }
  if (
    (value.sentiment === "positive" || value.sentiment === "negative") &&
    typeof value.confidence !== "number"
  ) {
    return false;
  }

  return (
    isOptionalString(value.symbol) &&
    isOptionalPublicHttpUrl(value.url) &&
    isOptionalString(value.source) &&
    isOptionalString(value.published_at) &&
    isOptionalString(value.summary) &&
    isOptionalString(value.sentiment) &&
    isOptionalFiniteNumber(value.confidence)
  );
}

export function isInstrumentNewsPayload(
  value: unknown,
  expectedSymbol?: string,
): value is InstrumentNewsPayload {
  if (
    !isRecord(value) ||
    typeof value.symbol !== "string" ||
    !isOptionalString(value.source) ||
    !Array.isArray(value.items) ||
    !value.items.every(isStoredNewsItem)
  ) {
    return false;
  }

  if (
    expectedSymbol !== undefined &&
    value.symbol.trim().toUpperCase() !== expectedSymbol.trim().toUpperCase()
  ) {
    return false;
  }

  if (value.summary === undefined || value.summary === null) {
    return true;
  }
  if (!isRecord(value.summary)) {
    return false;
  }

  const summaryIsValid = (
    isOptionalString(value.summary.latest_sentiment) &&
    isOptionalFiniteNumber(value.summary.article_count)
  );
  if (!summaryIsValid) {
    return false;
  }
  const articleCount = value.summary.article_count;
  return (
    articleCount === undefined ||
    articleCount === null ||
    (typeof articleCount === "number" &&
      Number.isInteger(articleCount) &&
      articleCount >= 0 &&
      articleCount === value.items.length)
  );
}

function isNewsDiagnostic(value: unknown): value is NewsDiagnostic {
  return (
    isRecord(value) &&
    isOptionalString(value.provider) &&
    isOptionalString(value.status) &&
    isOptionalString(value.severity) &&
    isOptionalString(value.code)
  );
}

export function isNewsRefreshPayload(
  value: unknown,
  expectedSymbol?: string,
  expectedMarket?: string,
): value is NewsRefreshPayload {
  if (
    !isRecord(value) ||
    typeof value.symbol !== "string" ||
    typeof value.market !== "string" ||
    typeof value.status !== "string" ||
    !NEWS_REFRESH_STATUSES.has(value.status as NewsRefreshStatus) ||
    !isInstrumentNewsPayload(value.news, value.symbol) ||
    !Array.isArray(value.diagnostics) ||
    !value.diagnostics.every(isNewsDiagnostic)
  ) {
    return false;
  }

  if (
    (expectedSymbol !== undefined &&
      value.symbol.trim().toUpperCase() !== expectedSymbol.trim().toUpperCase()) ||
    (expectedMarket !== undefined &&
      value.market.trim().toUpperCase() !== expectedMarket.trim().toUpperCase())
  ) {
    return false;
  }

  const hasStoredNews = value.news.items.length > 0;
  return value.status === "database_hit" || value.status === "refreshed"
    ? hasStoredNews
    : !hasStoredNews;
}

export function isLatestStoredNewsPayload(
  value: unknown,
): value is LatestStoredNewsPayload {
  if (
    !isRecord(value) ||
    typeof value.source !== "string" ||
    (value.status !== "ok" && value.status !== "no_data") ||
    typeof value.count !== "number" ||
    !Number.isInteger(value.count) ||
    value.count < 0 ||
    typeof value.limit !== "number" ||
    !Number.isInteger(value.limit) ||
    value.limit <= 0 ||
    !Array.isArray(value.items) ||
    !value.items.every(isStoredNewsItem)
  ) {
    return false;
  }

  return (
    value.count === value.items.length &&
    value.count <= value.limit &&
    (value.status === "ok" ? value.count > 0 : value.count === 0)
  );
}
