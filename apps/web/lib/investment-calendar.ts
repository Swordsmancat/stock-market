export type InvestmentCalendarKind = "economic" | "company";

export type InvestmentCalendarItem = {
  id: string;
  kind: InvestmentCalendarKind;
  date: string;
  time: string;
  title: string;
  importance: number | null;
  country: string | null;
  symbol: string | null;
  company_name: string | null;
  category: string | null;
  reference_period: string | null;
  previous: string | null;
  forecast: string | null;
  actual: string | null;
  unit: string | null;
  provider: string;
  source_url: string;
  retrieved_at: string;
};

export type InvestmentCalendarDay = {
  date: string;
  count: number;
  max_importance: number | null;
  items: InvestmentCalendarItem[];
};

export type InvestmentCalendarPayload = {
  status: "ok";
  start: string;
  end: string;
  kind: InvestmentCalendarKind;
  count: number;
  truncated: boolean;
  days: InvestmentCalendarDay[];
};

export type InvestmentCalendarQuery = {
  month: string;
  start: string;
  end: string;
  date: string;
  kind: InvestmentCalendarKind;
  importance: number;
};

type SearchValue = string | string[] | undefined;

export function parseInvestmentCalendarQuery(
  searchParams: Record<string, SearchValue>,
  now = new Date(),
): InvestmentCalendarQuery {
  const today = shanghaiDate(now);
  const requestedMonth = single(searchParams.month);
  const month = isMonth(requestedMonth) ? requestedMonth : today.slice(0, 7);
  const start = `${month}-01`;
  const end = `${month}-${String(daysInMonth(month)).padStart(2, "0")}`;
  const requestedDate = single(searchParams.date);
  const date = isDate(requestedDate) && requestedDate >= start && requestedDate <= end
    ? requestedDate
    : today >= start && today <= end
      ? today
      : start;
  const kind = single(searchParams.kind) === "company" ? "company" : "economic";
  const requestedImportance = Number(single(searchParams.importance) ?? "0");
  const importance = Number.isInteger(requestedImportance) && requestedImportance >= 0 && requestedImportance <= 5
    ? requestedImportance
    : 0;
  return { month, start, end, date, kind, importance };
}

export function buildCalendarCells(month: string): Array<{
  date: string;
  day: number;
  inMonth: boolean;
}> {
  const [year, monthNumber] = month.split("-").map(Number);
  const first = new Date(Date.UTC(year, monthNumber - 1, 1));
  const mondayOffset = (first.getUTCDay() + 6) % 7;
  const cells: Array<{ date: string; day: number; inMonth: boolean }> = [];
  for (let index = 0; index < 42; index += 1) {
    const current = new Date(Date.UTC(year, monthNumber - 1, 1 - mondayOffset + index));
    const date = current.toISOString().slice(0, 10);
    cells.push({ date, day: current.getUTCDate(), inMonth: date.slice(0, 7) === month });
  }
  return cells;
}

export function shiftMonth(month: string, offset: number): string {
  const [year, monthNumber] = month.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, monthNumber - 1 + offset, 1));
  return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, "0")}`;
}

export function isInvestmentCalendarPayload(value: unknown): value is InvestmentCalendarPayload {
  if (!isRecord(value) || value.status !== "ok" || !Array.isArray(value.days)) return false;
  if (
    typeof value.start !== "string" ||
    typeof value.end !== "string" ||
    (value.kind !== "economic" && value.kind !== "company") ||
    typeof value.count !== "number" ||
    typeof value.truncated !== "boolean"
  ) return false;
  return value.days.every((day) =>
    isRecord(day) &&
    typeof day.date === "string" &&
    typeof day.count === "number" &&
    Array.isArray(day.items) &&
    day.items.every(isCalendarItem),
  );
}

function isCalendarItem(value: unknown): value is InvestmentCalendarItem {
  return isRecord(value) &&
    typeof value.id === "string" &&
    (value.kind === "economic" || value.kind === "company") &&
    typeof value.date === "string" &&
    typeof value.time === "string" &&
    typeof value.title === "string" &&
    (typeof value.importance === "number" || value.importance === null) &&
    typeof value.provider === "string" &&
    typeof value.source_url === "string" &&
    typeof value.retrieved_at === "string";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function single(value: SearchValue): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function isMonth(value: string | undefined): value is string {
  if (!value || !/^\d{4}-\d{2}$/.test(value)) return false;
  const month = Number(value.slice(5));
  return month >= 1 && month <= 12;
}

function isDate(value: string | undefined): value is string {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
}

function daysInMonth(month: string): number {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
}

export function shanghaiDate(now = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}
