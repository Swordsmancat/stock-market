"use client";

import { AlertTriangle, ArrowDown, ArrowRight, ArrowUp, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";

export type MacroDashboardHistoryPoint = {
  as_of: string;
  value: number;
};

export type MacroDashboardItem = {
  code: string;
  name: string;
  region: string;
  category: string;
  unit: string;
  status: "ok" | "no_data";
  freshness: "fresh" | "stale" | "no_data";
  value: number | null;
  as_of: string | null;
  source: string | null;
  previous_value: number | null;
  change: number | null;
  direction: "up" | "down" | "flat" | null;
  history: MacroDashboardHistoryPoint[];
  no_data_reason: string | null;
};

export type MacroDashboardPayload = {
  status: "ok" | "no_data";
  generated_at: string;
  latest_as_of: string | null;
  summary: {
    total: number;
    available: number;
    missing: number;
    stale: number;
  };
  groups: Array<{ id: string; items: MacroDashboardItem[] }>;
};

export type MacroEconomicDashboardLabels = {
  title: string;
  description: string;
  available: string;
  missing: string;
  stale: string;
  latest: string;
  groupLabels: Record<string, string>;
  indicatorLabels: Record<string, string>;
  fresh: string;
  staleState: string;
  noData: string;
  asOf: string;
  source: string;
  changeUp: string;
  changeDown: string;
  changeFlat: string;
  trendSummary: string;
  refresh: string;
  refreshing: string;
  refreshSuccess: string;
  refreshDegraded: string;
  refreshFailed: string;
  unavailable: string;
};

type MacroEconomicDashboardProps = {
  payload: MacroDashboardPayload;
  locale: string;
  labels: MacroEconomicDashboardLabels;
};

function fill(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template,
  );
}

function formatNumber(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(value);
}

function formatValue(item: MacroDashboardItem, locale: string, unavailable: string): string {
  if (item.value === null || !Number.isFinite(item.value)) return unavailable;
  const value = formatNumber(item.value, locale);
  return item.unit === "percent" ? `${value}%` : value;
}

function formatDate(value: string | null, locale: string, unavailable: string): string {
  if (!value) return unavailable;
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return unavailable;
  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "UTC",
  }).format(parsed);
}

function buildSparklinePath(values: number[], width = 180, height = 44): string | null {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - 4 - ((value - min) / span) * (height - 8);
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function MacroSparkline({
  item,
  name,
  labels,
}: {
  item: MacroDashboardItem;
  name: string;
  labels: MacroEconomicDashboardLabels;
}) {
  const path = buildSparklinePath(item.history.map((point) => point.value));
  if (!path) return <div className="h-11 border-b border-dashed border-border/70" />;
  const directionClass =
    item.direction === "down" ? "stroke-emerald-500" : "stroke-rose-500";
  return (
    <svg
      role="img"
      aria-label={fill(labels.trendSummary, { name, count: item.history.length })}
      viewBox="0 0 180 44"
      className="h-11 w-full"
      preserveAspectRatio="none"
    >
      <path d="M0,40 L180,40" className="stroke-border" strokeDasharray="3 6" />
      <path d={path} className={directionClass} fill="none" strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function DirectionSummary({
  item,
  locale,
  labels,
}: {
  item: MacroDashboardItem;
  locale: string;
  labels: MacroEconomicDashboardLabels;
}) {
  if (item.change === null || item.direction === null) return null;
  const change = formatNumber(Math.abs(item.change), locale);
  if (item.direction === "up") {
    return (
      <span className="inline-flex items-center gap-1 text-rose-500">
        <ArrowUp className="h-3 w-3" aria-hidden="true" />
        {fill(labels.changeUp, { value: change })}
      </span>
    );
  }
  if (item.direction === "down") {
    return (
      <span className="inline-flex items-center gap-1 text-emerald-500">
        <ArrowDown className="h-3 w-3" aria-hidden="true" />
        {fill(labels.changeDown, { value: change })}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-muted-foreground">
      <ArrowRight className="h-3 w-3" aria-hidden="true" />
      {labels.changeFlat}
    </span>
  );
}

export function MacroEconomicDashboard({
  payload,
  locale,
  labels,
}: MacroEconomicDashboardProps) {
  const router = useRouter();
  const [pending, setPending] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [failed, setFailed] = React.useState(false);

  async function refresh() {
    setPending(true);
    setMessage(null);
    setFailed(false);
    try {
      const response = await fetch("/api/macro-dashboard/refresh", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ family: "all", history_limit: 24, dry_run: false }),
      });
      const result = (await response.json()) as { status?: string; observations?: number };
      if (!response.ok) throw new Error("refresh_failed");
      const template = result.status === "degraded" ? labels.refreshDegraded : labels.refreshSuccess;
      setMessage(fill(template, { count: result.observations ?? 0 }));
      router.refresh();
    } catch {
      setFailed(true);
      setMessage(labels.refreshFailed);
    } finally {
      setPending(false);
    }
  }

  return (
    <FinancialTerminalCard data-testid="macro-economic-dashboard">
      <FinancialTerminalCardHeader>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle className="text-xl">{labels.title}</CardTitle>
            <CardDescription>{labels.description}</CardDescription>
          </div>
          <Button type="button" size="sm" onClick={() => void refresh()} disabled={pending}>
            <RefreshCw className={pending ? "h-4 w-4 animate-spin" : "h-4 w-4"} aria-hidden="true" />
            {pending ? labels.refreshing : labels.refresh}
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            [labels.available, payload.summary.available],
            [labels.missing, payload.summary.missing],
            [labels.stale, payload.summary.stale],
            [labels.latest, formatDate(payload.latest_as_of, locale, labels.unavailable)],
          ].map(([label, value]) => (
            <FinancialTerminalSurface key={String(label)} className="p-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
              <div className="mt-1 font-mono text-lg font-semibold tabular-nums">{value}</div>
            </FinancialTerminalSurface>
          ))}
        </div>
        {message ? (
          <div
            role={failed ? "alert" : "status"}
            className={failed ? "flex items-center gap-2 text-sm text-destructive" : "text-sm text-emerald-600 dark:text-emerald-400"}
          >
            {failed ? <AlertTriangle className="h-4 w-4" aria-hidden="true" /> : null}
            {message}
          </div>
        ) : null}
      </FinancialTerminalCardHeader>
      <FinancialTerminalCardContent className="space-y-6">
        {payload.groups.map((group) => (
          <section key={group.id} aria-labelledby={`macro-group-${group.id}`} className="space-y-3">
            <h2 id={`macro-group-${group.id}`} className="border-l-2 border-primary pl-2 text-sm font-semibold uppercase tracking-wide">
              {labels.groupLabels[group.id] ?? group.id}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
              {group.items.map((item) => {
                const name = labels.indicatorLabels[item.code] ?? item.name ?? item.code;
                return (
                  <FinancialTerminalSurface key={item.code} className="min-w-0 p-3">
                    <div className="flex min-h-10 items-start justify-between gap-2">
                      <h3 className="min-w-0 text-sm font-medium leading-5">{name}</h3>
                      <Badge variant={item.freshness === "fresh" ? "secondary" : "outline"} className="shrink-0 text-[10px]">
                        {item.freshness === "fresh"
                          ? labels.fresh
                          : item.freshness === "stale"
                            ? labels.staleState
                            : labels.noData}
                      </Badge>
                    </div>
                    {item.status === "ok" ? (
                      <>
                        <div className="mt-2 font-mono text-2xl font-semibold tabular-nums">
                          {formatValue(item, locale, labels.unavailable)}
                        </div>
                        <div className="mt-1 min-h-5 text-xs">
                          <DirectionSummary item={item} locale={locale} labels={labels} />
                        </div>
                        <div className="mt-2"><MacroSparkline item={item} name={name} labels={labels} /></div>
                        <div className="mt-2 space-y-1 text-[11px] text-muted-foreground">
                          <div>{fill(labels.asOf, { date: formatDate(item.as_of, locale, labels.unavailable) })}</div>
                          <div className="truncate" title={item.source ?? undefined}>
                            {fill(labels.source, { source: item.source ?? labels.unavailable })}
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="flex h-28 items-center justify-center text-center text-sm text-muted-foreground">
                        {labels.noData}
                      </div>
                    )}
                  </FinancialTerminalSurface>
                );
              })}
            </div>
          </section>
        ))}
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}
