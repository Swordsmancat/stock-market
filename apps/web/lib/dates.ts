function utcToday(): Date {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
}

export function formatDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function addDays(date: Date, days: number): Date {
  const copy = new Date(date);
  copy.setUTCDate(copy.getUTCDate() + days);
  return copy;
}

export function dateRangeEndingToday(days: number): { start: string; end: string } {
  const end = utcToday();
  const start = addDays(end, -(days - 1));
  return { start: formatDate(start), end: formatDate(end) };
}

export function getDashboardDateRanges(): {
  recent: { start: string; end: string };
  analysis: { start: string; end: string };
} {
  return {
    recent: dateRangeEndingToday(2),
    analysis: dateRangeEndingToday(20),
  };
}

export type InstrumentRange = "5d" | "20d" | "1m" | "3m" | "1y";

const INSTRUMENT_RANGE_DAYS: Record<InstrumentRange, number> = {
  "5d": 5,
  "20d": 20,
  "1m": 30,
  "3m": 90,
  "1y": 365,
};

export function parseInstrumentRange(value?: string): InstrumentRange {
  if (value && value in INSTRUMENT_RANGE_DAYS) {
    return value as InstrumentRange;
  }
  return "20d";
}

export function getInstrumentDateRange(range: InstrumentRange): { start: string; end: string } {
  return dateRangeEndingToday(INSTRUMENT_RANGE_DAYS[range]);
}
