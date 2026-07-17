"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { FinancialTerminalCard, FinancialTerminalCardContent, FinancialTerminalCardHeader } from "@/components/financial-terminal-section";
import { Button } from "@/components/ui/button";

export type IndustryRankingItem = {
  date: string;
  rank: number;
  code: string;
  name: string;
  change_percent: string;
};
export type IndustryRankingPayload = {
  status: string;
  dates: string[];
  limit: number;
  items: IndustryRankingItem[];
};
export type IndustryRankingLabels = {
  title: string;
  description: string;
  refresh: string;
  refreshing: string;
  empty: string;
  rank: string;
  failed: string;
  ladderView: string;
  listView: string;
  type: string;
  industry: string;
  level: string;
  firstLevel: string;
  sort: string;
  gainDesc: string;
  gainAsc: string;
  count: string;
  topCount: string;
  days: string;
  tradingDays: string;
  sector: string;
  change: string;
  code: string;
};

type ViewMode = "ladder" | "list";
type SortMode = "desc" | "asc";

const selectClass = "h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function movementClass(value: number): string {
  if (value > 0) return "text-red-500";
  if (value < 0) return "text-emerald-600";
  return "text-muted-foreground";
}

function formatChange(raw: string): string {
  const value = Number(raw);
  if (!Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : ""}${raw}%`;
}

function rankBadge(rank: number) {
  const tone = rank === 1 ? "bg-red-500 text-white" : rank === 2 ? "bg-orange-500 text-white" : rank === 3 ? "bg-amber-400 text-amber-950" : "text-muted-foreground";
  return <span className={`inline-flex h-6 min-w-6 items-center justify-center rounded px-1.5 text-xs font-semibold ${tone}`}>{rank}</span>;
}

export function IndustryRankingHistoryPanel({ payload, labels }: { payload: IndustryRankingPayload; labels: IndustryRankingLabels }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [view, setView] = useState<ViewMode>("ladder");
  const [sort, setSort] = useState<SortMode>("desc");
  const [count, setCount] = useState(Math.min(payload.limit, 20));
  const [dayCount, setDayCount] = useState(12);

  const dates = payload.dates.slice(0, dayCount);
  const byDate = useMemo(() => {
    const result = new Map<string, IndustryRankingItem[]>();
    for (const date of payload.dates) {
      const items = payload.items
        .filter((item) => item.date === date)
        .sort((left, right) => {
          const delta = Number(right.change_percent) - Number(left.change_percent);
          return (sort === "desc" ? delta : -delta) || left.code.localeCompare(right.code);
        })
        .slice(0, count);
      result.set(date, items);
    }
    return result;
  }, [count, payload.dates, payload.items, sort]);

  async function refresh() {
    setPending(true);
    setMessage("");
    try {
      const response = await fetch(`/api/sectors/industry-rankings/refresh?days=${dayCount}`, { method: "POST" });
      if (!response.ok) throw new Error();
      router.refresh();
    } catch {
      setMessage(labels.failed);
    } finally {
      setPending(false);
    }
  }

  return (
    <FinancialTerminalCard data-testid="industry-ranking-history">
      <FinancialTerminalCardHeader className="gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">{labels.title}</h2>
            <p className="text-xs text-muted-foreground">{labels.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant={view === "ladder" ? "default" : "outline"} onClick={() => setView("ladder")}>{labels.ladderView}</Button>
            <Button size="sm" variant={view === "list" ? "default" : "outline"} onClick={() => setView("list")}>{labels.listView}</Button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 border-t border-border/70 pt-3 text-xs">
          <label className="flex items-center gap-1.5">{labels.type}<select className={selectClass} aria-label={labels.type} disabled><option>{labels.industry}</option></select></label>
          <label className="flex items-center gap-1.5">{labels.level}<select className={selectClass} aria-label={labels.level} disabled><option>{labels.firstLevel}</option></select></label>
          <label className="flex items-center gap-1.5">{labels.sort}<select className={selectClass} aria-label={labels.sort} value={sort} onChange={(event) => setSort(event.target.value as SortMode)}><option value="desc">{labels.gainDesc}</option><option value="asc">{labels.gainAsc}</option></select></label>
          <label className="flex items-center gap-1.5">{labels.count}<select className={selectClass} aria-label={labels.count} value={count} onChange={(event) => setCount(Number(event.target.value))}><option value={10}>{labels.topCount.replace("{count}", "10")}</option><option value={20}>{labels.topCount.replace("{count}", "20")}</option></select></label>
          <label className="flex items-center gap-1.5">{labels.days}<select className={selectClass} aria-label={labels.days} value={dayCount} onChange={(event) => setDayCount(Number(event.target.value))}>{[5, 10, 12, 20].map((days) => <option key={days} value={days}>{labels.tradingDays.replace("{count}", String(days))}</option>)}</select></label>
          <Button size="sm" variant="secondary" onClick={refresh} disabled={pending}>{pending ? labels.refreshing : labels.refresh}</Button>
          <span className="text-muted-foreground">{labels.tradingDays.replace("{count}", String(dates.length))}</span>
        </div>
        {message ? <p className="text-sm text-destructive">{message}</p> : null}
      </FinancialTerminalCardHeader>
      <FinancialTerminalCardContent className="p-0">
        {!dates.length ? <p className="px-4 py-12 text-center text-sm text-muted-foreground">{labels.empty}</p> : view === "ladder" ? (
          <div className="max-h-[46rem] overflow-auto" tabIndex={0} aria-label={labels.title}>
            <table className="min-w-max border-collapse text-xs">
              <thead className="sticky top-0 z-20 bg-muted/95"><tr><th className="sticky left-0 z-30 min-w-14 border border-border/70 bg-muted px-2 py-2 text-center">{labels.rank}</th>{dates.map((date) => <th key={date} className="min-w-36 border border-border/70 px-3 py-2 text-center">{date.slice(5)}</th>)}</tr></thead>
              <tbody>{Array.from({ length: count }, (_, index) => index).map((rowIndex) => <tr key={rowIndex}><td className="sticky left-0 z-10 border border-border/70 bg-card px-2 py-1 text-center">{rankBadge(rowIndex + 1)}</td>{dates.map((date) => { const item = byDate.get(date)?.[rowIndex]; const value = Number(item?.change_percent); return <td key={date} className="border border-border/70 px-3 py-1.5 text-center"><div className="max-w-32 truncate font-medium" title={item?.name}>{item?.name ?? "—"}</div>{item ? <div className={movementClass(value)}>{formatChange(item.change_percent)}</div> : null}</td>; })}</tr>)}</tbody>
            </table>
          </div>
        ) : (
          <div className="max-h-[46rem] overflow-auto"><table className="w-full text-sm"><thead className="sticky top-0 bg-muted/95"><tr><th className="px-3 py-2 text-left">{labels.rank}</th><th className="px-3 py-2 text-left">{labels.sector}</th><th className="px-3 py-2 text-left">{labels.code}</th><th className="px-3 py-2 text-right">{labels.change}</th></tr></thead><tbody>{(byDate.get(dates[0]) ?? []).map((item, index) => <tr key={item.code} className="border-t border-border/70"><td className="px-3 py-2">{rankBadge(index + 1)}</td><td className="px-3 py-2 font-medium">{item.name}</td><td className="px-3 py-2 text-muted-foreground">{item.code}</td><td className={`px-3 py-2 text-right font-medium ${movementClass(Number(item.change_percent))}`}>{formatChange(item.change_percent)}</td></tr>)}</tbody></table></div>
        )}
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}
