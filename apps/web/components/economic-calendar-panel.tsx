"use client";

import * as React from "react";
import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

import { FinancialTerminalCard, FinancialTerminalCardContent, FinancialTerminalCardHeader } from "@/components/financial-terminal-section";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";

export type EconomicCalendarItem = {
  id: string; country: string; name: string; reference_period: string | null;
  importance: number; scheduled_at: string; previous: string | null;
  forecast: string | null; actual: string | null; unit: string | null;
};
export type EconomicCalendarPayload = { status: string; start: string; end: string; count: number; countries: string[]; items: EconomicCalendarItem[] };
export type EconomicCalendarLabels = {
  title: string; description: string; refresh: string; refreshing: string; refreshSuccess: string; refreshFailed: string;
  allCountries: string; allImportance: string; importance: string; time: string; country: string; event: string;
  previous: string; forecast: string; actual: string; empty: string; unavailable: string;
};

export function EconomicCalendarPanel({ payload, locale, labels }: { payload: EconomicCalendarPayload; locale: string; labels: EconomicCalendarLabels }) {
  const router = useRouter();
  const [country, setCountry] = React.useState("");
  const [importance, setImportance] = React.useState(0);
  const [pending, setPending] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const rows = payload.items.filter((item) => (!country || item.country === country) && item.importance >= importance);
  async function refresh() {
    setPending(true); setMessage(null);
    try {
      const response = await fetch("/api/economic-calendar/refresh", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ start: payload.start, end: payload.end, dry_run: false }) });
      const result = await response.json() as { fetched?: number };
      if (!response.ok) throw new Error();
      setMessage(labels.refreshSuccess.replace("{count}", String(result.fetched ?? 0)));
      router.refresh();
    } catch { setMessage(labels.refreshFailed); }
    finally { setPending(false); }
  }
  const format = (value: string | null, unit: string | null) => value == null ? labels.unavailable : `${value}${unit ?? ""}`;
  return <FinancialTerminalCard data-testid="economic-calendar-panel">
    <FinancialTerminalCardHeader>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"><div><CardTitle>{labels.title}</CardTitle><CardDescription>{labels.description}</CardDescription></div>
        <Button size="sm" type="button" onClick={() => void refresh()} disabled={pending}><RefreshCw className={pending ? "h-4 w-4 animate-spin" : "h-4 w-4"}/>{pending ? labels.refreshing : labels.refresh}</Button></div>
      <div className="flex flex-wrap gap-2">
        <select aria-label={labels.country} className="rounded-md border bg-background px-3 py-2 text-sm" value={country} onChange={(event) => setCountry(event.target.value)}><option value="">{labels.allCountries}</option>{payload.countries.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select aria-label={labels.importance} className="rounded-md border bg-background px-3 py-2 text-sm" value={importance} onChange={(event) => setImportance(Number(event.target.value))}><option value={0}>{labels.allImportance}</option>{[1,2,3,4,5].map((item) => <option key={item} value={item}>{labels.importance} ≥ {item}</option>)}</select>
        {message ? <span role="status" className="self-center text-sm text-muted-foreground">{message}</span> : null}
      </div>
    </FinancialTerminalCardHeader>
    <FinancialTerminalCardContent>
      {rows.length === 0 ? <div className="py-10 text-center text-sm text-muted-foreground">{labels.empty}</div> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-sm"><thead><tr className="border-b text-left text-xs text-muted-foreground"><th className="p-2">{labels.time}</th><th className="p-2">{labels.country}</th><th className="p-2">{labels.importance}</th><th className="p-2">{labels.event}</th><th className="p-2">{labels.previous}</th><th className="p-2">{labels.forecast}</th><th className="p-2">{labels.actual}</th></tr></thead><tbody>{rows.map((item) => <tr key={item.id} className="border-b border-border/60"><td className="whitespace-nowrap p-2 font-mono">{new Intl.DateTimeFormat(locale, { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Shanghai" }).format(new Date(item.scheduled_at))}</td><td className="p-2">{item.country}</td><td className="p-2 text-amber-500">{"★".repeat(item.importance)}</td><td className="p-2"><div className="font-medium">{item.name}</div>{item.reference_period ? <div className="text-xs text-muted-foreground">{item.reference_period}</div> : null}</td><td className="p-2 font-mono">{format(item.previous,item.unit)}</td><td className="p-2 font-mono">{format(item.forecast,item.unit)}</td><td className="p-2 font-mono font-semibold">{format(item.actual,item.unit)}</td></tr>)}</tbody></table></div>}
    </FinancialTerminalCardContent>
  </FinancialTerminalCard>;
}
