"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { FinancialTerminalCard, FinancialTerminalCardContent, FinancialTerminalCardHeader } from "@/components/financial-terminal-section";

export type IndustryRankingPayload = { status: string; dates: string[]; limit: number; items: { date: string; rank: number; code: string; name: string; change_percent: string }[] };
export type IndustryRankingLabels = { title: string; description: string; refresh: string; refreshing: string; empty: string; rank: string; failed: string };

export function IndustryRankingHistoryPanel({ payload, labels }: { payload: IndustryRankingPayload; labels: IndustryRankingLabels }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const byDate = new Map(payload.dates.map((date) => [date, payload.items.filter((item) => item.date === date)]));
  async function refresh() {
    setPending(true); setMessage("");
    try {
      const response = await fetch("/api/sectors/industry-rankings/refresh?days=12", { method: "POST" });
      if (!response.ok) throw new Error();
      router.refresh();
    } catch { setMessage(labels.failed); } finally { setPending(false); }
  }
  return <FinancialTerminalCard>
    <FinancialTerminalCardHeader>
      <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-base font-semibold">{labels.title}</h2><p className="text-sm text-muted-foreground">{labels.description}</p></div><Button size="sm" onClick={refresh} disabled={pending}>{pending ? labels.refreshing : labels.refresh}</Button></div>
      {message ? <p className="text-sm text-destructive">{message}</p> : null}
    </FinancialTerminalCardHeader>
    <FinancialTerminalCardContent>
      {!payload.dates.length ? <p className="py-8 text-center text-sm text-muted-foreground">{labels.empty}</p> : <div className="overflow-x-auto"><table className="min-w-max text-sm"><thead><tr><th className="sticky left-0 bg-card px-3 py-2 text-left">{labels.rank}</th>{payload.dates.map((date) => <th key={date} className="min-w-36 px-3 py-2 text-left">{date.slice(5)}</th>)}</tr></thead><tbody>{Array.from({length: payload.limit}, (_, index) => index + 1).map((rank) => <tr key={rank} className="border-t"><td className="sticky left-0 bg-card px-3 py-2 font-medium">{rank}</td>{payload.dates.map((date) => { const item = byDate.get(date)?.find((candidate) => candidate.rank === rank); const value = Number(item?.change_percent); return <td key={date} className="px-3 py-2"><div>{item?.name ?? "—"}</div>{item ? <div className={value >= 0 ? "text-red-500" : "text-emerald-600"}>{value >= 0 ? "+" : ""}{item.change_percent}%</div> : null}</td>; })}</tr>)}</tbody></table></div>}
    </FinancialTerminalCardContent>
  </FinancialTerminalCard>;
}
