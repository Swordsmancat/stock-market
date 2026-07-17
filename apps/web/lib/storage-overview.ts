export type StorageDomainCode =
  | "reference_data"
  | "market_prices"
  | "technical_analysis"
  | "fundamentals"
  | "macro_economy"
  | "market_structure"
  | "news_disclosures"
  | "research_outputs"
  | "personal_operations"
  | "other";

export type StorageTableStat = {
  name: string;
  estimated_rows: number;
  data_bytes: number | null;
  index_bytes: number | null;
  total_bytes: number | null;
};

export type StorageDomainStat = {
  code: StorageDomainCode;
  table_count: number;
  estimated_rows: number;
  data_bytes: number | null;
  index_bytes: number | null;
  total_bytes: number | null;
  tables: StorageTableStat[];
};

export type StorageOverviewPayload = {
  status: "ok";
  engine: string;
  row_count_kind: "estimated" | "exact";
  collected_at: string;
  summary: {
    table_count: number;
    estimated_rows: number;
    data_bytes: number | null;
    index_bytes: number | null;
    total_bytes: number | null;
  };
  domains: StorageDomainStat[];
};

export function isStorageOverviewPayload(value: unknown): value is StorageOverviewPayload {
  if (typeof value !== "object" || value === null) return false;
  const payload = value as Partial<StorageOverviewPayload>;
  return (
    payload.status === "ok" &&
    typeof payload.engine === "string" &&
    (payload.row_count_kind === "estimated" || payload.row_count_kind === "exact") &&
    typeof payload.collected_at === "string" &&
    typeof payload.summary === "object" &&
    payload.summary !== null &&
    typeof payload.summary.table_count === "number" &&
    typeof payload.summary.estimated_rows === "number" &&
    Array.isArray(payload.domains)
  );
}

export function formatStorageCount(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, {
    notation: "compact",
    compactDisplay: "short",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatStorageBytes(value: number | null, locale: string): string | null {
  if (value === null || !Number.isFinite(value) || value < 0) return null;
  if (value === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"] as const;
  const exponent = Math.min(
    Math.floor(Math.log(value) / Math.log(1024)),
    units.length - 1,
  );
  const amount = value / 1024 ** exponent;
  return `${new Intl.NumberFormat(locale, {
    maximumFractionDigits: exponent === 0 ? 0 : 1,
  }).format(amount)} ${units[exponent]}`;
}
