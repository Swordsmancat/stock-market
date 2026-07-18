"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Database,
  ExternalLink,
  Globe2,
  Star,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  buildCalendarCells,
  shanghaiDate,
  shiftMonth,
  type InvestmentCalendarPayload,
  type InvestmentCalendarQuery,
} from "@/lib/investment-calendar";
import { cn } from "@/lib/utils";
import { usePathname, useRouter } from "@/src/i18n/routing";

export type InvestmentCalendarLabels = {
  economic: string;
  company: string;
  previousMonth: string;
  nextMonth: string;
  today: string;
  importance: string;
  allImportance: string;
  importanceAtLeast: string;
  importanceScore: string;
  eventCount: string;
  selectedDayCount: string;
  emptyMonth: string;
  emptyDay: string;
  loadFailedTitle: string;
  loadFailedDescription: string;
  truncated: string;
  previous: string;
  forecast: string;
  actual: string;
  referencePeriod: string;
  category: string;
  source: string;
  retrievedAt: string;
  databaseOnly: string;
  unavailable: string;
  weekdays: string[];
};

type Props = {
  locale: string;
  query: InvestmentCalendarQuery;
  payload: InvestmentCalendarPayload | null;
  labels: InvestmentCalendarLabels;
};

export function InvestmentCalendar({ locale, query, payload, labels }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [selectedDate, setSelectedDate] = useState(query.date);
  const cells = useMemo(() => buildCalendarCells(query.month), [query.month]);
  const days = useMemo(
    () => new Map((payload?.days ?? []).map((day) => [day.date, day])),
    [payload],
  );
  const selectedDay = days.get(selectedDate);
  const today = shanghaiDate();

  useEffect(() => setSelectedDate(query.date), [query.date]);

  function navigate(next: Partial<InvestmentCalendarQuery>) {
    const month = next.month ?? query.month;
    const params = new URLSearchParams({
      month,
      date: next.date ?? selectedDate,
      kind: next.kind ?? query.kind,
      importance: String(next.importance ?? query.importance),
    });
    router.replace(`${pathname}?${params.toString()}` as never);
  }

  function selectDate(date: string) {
    setSelectedDate(date);
    const params = new URLSearchParams({
      month: query.month,
      date,
      kind: query.kind,
      importance: String(query.importance),
    });
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }

  function navigateMonth(offset: number) {
    const month = shiftMonth(query.month, offset);
    navigate({ month, date: `${month}-01` });
  }

  function goToday() {
    navigate({ month: today.slice(0, 7), date: today });
  }

  const monthLabel = formatMonth(query.month, locale);
  const selectedDateLabel = formatDate(selectedDate, locale);

  return (
    <section className="space-y-3" aria-labelledby="investment-calendar-heading">
      <div className="flex flex-col gap-3 border-y border-border/70 bg-card/50 p-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-sm border border-border bg-background p-0.5" role="group">
            <Button
              size="sm"
              variant={query.kind === "economic" ? "secondary" : "ghost"}
              aria-pressed={query.kind === "economic"}
              onClick={() => navigate({ kind: "economic" })}
            >
              <Globe2 /> {labels.economic}
            </Button>
            <Button
              size="sm"
              variant={query.kind === "company" ? "secondary" : "ghost"}
              aria-pressed={query.kind === "company"}
              onClick={() => navigate({ kind: "company", importance: 0 })}
            >
              <Building2 /> {labels.company}
            </Button>
          </div>

          <div className="flex items-center rounded-sm border border-border bg-background">
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8"
              title={labels.previousMonth}
              onClick={() => navigateMonth(-1)}
            >
              <ChevronLeft />
              <span className="sr-only">{labels.previousMonth}</span>
            </Button>
            <div className="min-w-28 px-2 text-center text-sm font-semibold tabular-nums">
              {monthLabel}
            </div>
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8"
              title={labels.nextMonth}
              onClick={() => navigateMonth(1)}
            >
              <ChevronRight />
              <span className="sr-only">{labels.nextMonth}</span>
            </Button>
          </div>
          <Button size="sm" variant="outline" onClick={goToday}>
            <CalendarDays /> {labels.today}
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {query.kind === "economic" ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{labels.importance}</span>
              <Select
                value={String(query.importance)}
                onValueChange={(value) => navigate({ importance: Number(value) })}
              >
                <SelectTrigger className="h-8 w-40 rounded-sm" aria-label={labels.importance}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">{labels.allImportance}</SelectItem>
                  {[1, 2, 3, 4, 5].map((score) => (
                    <SelectItem key={score} value={String(score)}>
                      {labels.importanceAtLeast.replace("{score}", String(score))}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}
          <Badge variant="outline" className="rounded-sm">
            <Database className="mr-1 h-3 w-3" /> {labels.databaseOnly}
          </Badge>
          <span className="font-mono text-xs tabular-nums text-muted-foreground">
            {labels.eventCount.replace("{count}", String(payload?.count ?? 0))}
          </span>
        </div>
      </div>

      {payload?.truncated ? (
        <div className="border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {labels.truncated}
        </div>
      ) : null}

      <div className="grid min-w-0 gap-3 xl:grid-cols-[minmax(0,1.55fr)_minmax(20rem,0.85fr)]">
        <div className="min-w-0 overflow-hidden rounded-md border border-border bg-card">
          <div className="grid grid-cols-7 border-b border-border bg-muted/35">
            {labels.weekdays.map((weekday) => (
              <div key={weekday} className="px-1 py-2 text-center text-xs font-medium text-muted-foreground">
                {weekday}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {cells.map((cell) => {
              const day = days.get(cell.date);
              const isSelected = selectedDate === cell.date;
              const isToday = today === cell.date;
              return (
                <button
                  key={cell.date}
                  type="button"
                  disabled={!cell.inMonth}
                  aria-pressed={isSelected}
                  aria-label={`${formatDate(cell.date, locale)}, ${labels.eventCount.replace("{count}", String(day?.count ?? 0))}`}
                  onClick={() => selectDate(cell.date)}
                  className={cn(
                    "relative min-h-20 min-w-0 border-b border-r border-border/70 p-1.5 text-left outline-none transition-colors focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:min-h-24 sm:p-2",
                    cell.inMonth ? "bg-background hover:bg-accent/60" : "cursor-default bg-muted/20 text-muted-foreground/40",
                    isSelected && "z-[1] bg-primary/10 ring-2 ring-inset ring-primary",
                  )}
                >
                  <span
                    className={cn(
                      "inline-flex h-6 min-w-6 items-center justify-center rounded-full px-1 font-mono text-xs font-semibold tabular-nums",
                      isToday && "bg-primary text-primary-foreground",
                    )}
                  >
                    {cell.day}
                  </span>
                  {cell.inMonth && day ? (
                    <div className="mt-2 space-y-1">
                      <div className="truncate text-[11px] text-muted-foreground sm:text-xs">
                        {labels.eventCount.replace("{count}", String(day.count))}
                      </div>
                      {day.max_importance !== null ? (
                        <div className="flex items-center gap-1 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                          <Star className="h-3 w-3 fill-current" aria-hidden="true" />
                          <span>{labels.importanceScore.replace("{score}", String(day.max_importance))}</span>
                        </div>
                      ) : (
                        <div className="text-[10px] font-medium text-primary">{labels.company}</div>
                      )}
                    </div>
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>

        <aside className="min-w-0 overflow-hidden rounded-md border border-border bg-card" aria-live="polite">
          <div className="border-b border-border bg-muted/35 px-3 py-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="investment-calendar-heading" className="text-sm font-semibold">
                {selectedDateLabel}
              </h2>
              <span className="font-mono text-xs tabular-nums text-muted-foreground">
                {labels.selectedDayCount.replace("{count}", String(selectedDay?.count ?? 0))}
              </span>
            </div>
          </div>

          {!payload ? (
            <CalendarMessage title={labels.loadFailedTitle} description={labels.loadFailedDescription} />
          ) : payload.count === 0 ? (
            <CalendarMessage title={labels.emptyMonth} />
          ) : !selectedDay ? (
            <CalendarMessage title={labels.emptyDay} />
          ) : (
            <ol className="max-h-[42rem] divide-y divide-border/70 overflow-y-auto">
              {selectedDay.items.map((item) => (
                <li key={`${item.kind}:${item.id}`} className="space-y-2 p-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="flex w-12 shrink-0 items-center gap-1 pt-0.5 font-mono text-xs font-semibold tabular-nums text-muted-foreground">
                      <Clock3 className="h-3 w-3" /> {item.time}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        {item.country ? <Badge variant="outline" className="rounded-sm">{item.country}</Badge> : null}
                        {item.symbol ? <Badge variant="outline" className="rounded-sm font-mono">{item.symbol}</Badge> : null}
                        {item.category ? <Badge variant="secondary" className="rounded-sm">{item.category}</Badge> : null}
                      </div>
                      <h3 className="mt-1 break-words text-sm font-medium leading-5">{item.title}</h3>
                      {item.importance !== null ? (
                        <div className="mt-1 flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                          <Star className="h-3 w-3 fill-current" aria-hidden="true" />
                          <span>{labels.importanceScore.replace("{score}", String(item.importance))}</span>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  {item.kind === "economic" ? (
                    <dl className="grid grid-cols-2 gap-x-3 gap-y-1 pl-[3.75rem] text-xs sm:grid-cols-4">
                      <Value label={labels.previous} value={withUnit(item.previous, item.unit, labels.unavailable)} />
                      <Value label={labels.forecast} value={withUnit(item.forecast, item.unit, labels.unavailable)} />
                      <Value label={labels.actual} value={withUnit(item.actual, item.unit, labels.unavailable)} emphasize />
                      <Value label={labels.referencePeriod} value={item.reference_period ?? labels.unavailable} />
                    </dl>
                  ) : null}

                  <div className="flex flex-wrap items-center justify-between gap-2 pl-[3.75rem] text-[11px] text-muted-foreground">
                    <span>
                      {labels.retrievedAt}: {formatRetrieved(item.retrieved_at, locale, labels.unavailable)}
                    </span>
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      {labels.source}: {item.provider} <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </aside>
      </div>
    </section>
  );
}

function CalendarMessage({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center px-6 py-10 text-center">
      <CalendarDays className="mb-3 h-6 w-6 text-muted-foreground" />
      <div className="text-sm font-medium">{title}</div>
      {description ? <p className="mt-1 max-w-sm text-xs leading-5 text-muted-foreground">{description}</p> : null}
    </div>
  );
}

function Value({ label, value, emphasize = false }: { label: string; value: string; emphasize?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={cn("truncate font-mono font-medium tabular-nums", emphasize && "text-primary")}>{value}</dd>
    </div>
  );
}

function withUnit(value: string | null, unit: string | null, unavailable: string): string {
  if (value === null) return unavailable;
  return `${value}${unit ?? ""}`;
}

function formatMonth(month: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { year: "numeric", month: "long", timeZone: "UTC" }).format(
    new Date(`${month}-01T00:00:00Z`),
  );
}

function formatDate(date: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "full", timeZone: "UTC" }).format(
    new Date(`${date}T00:00:00Z`),
  );
}

function formatRetrieved(value: string, locale: string, unavailable: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return unavailable;
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Shanghai",
  }).format(date);
}
