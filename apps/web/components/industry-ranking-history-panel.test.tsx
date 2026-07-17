import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { IndustryRankingHistoryPanel, type IndustryRankingLabels } from "./industry-ranking-history-panel";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); refresh.mockReset(); });

const labels: IndustryRankingLabels = {
  title: "Industry history", description: "Stored rankings", refresh: "Refresh", refreshing: "Refreshing", empty: "No data", rank: "Rank", failed: "Refresh failed",
  ladderView: "Gain ladder", listView: "Sector list", type: "Type", industry: "Industry", level: "Level", firstLevel: "Level 1", sort: "Sort", gainDesc: "Top gains", gainAsc: "Lowest gains",
  count: "Count", topCount: "Top {count}", days: "Days", tradingDays: "{count} trading days", sector: "Sector", change: "Change", code: "Code",
  source: "Eastmoney Quote Center", updatedAt: "Stored {time}",
};

const payload = {
  status: "ok", source_url: "https://quote.eastmoney.com/center/gridlist.html#industry_board_1", retrieved_at: "2026-07-17T10:22:00+00:00", dates: ["2026-07-17", "2026-07-16"], limit: 20,
  items: [
    { date: "2026-07-17", rank: 1, code: "BK1", name: "Banking", change_percent: "1.24" },
    { date: "2026-07-17", rank: 2, code: "BK2", name: "Insurance", change_percent: "-0.40" },
    { date: "2026-07-16", rank: 1, code: "BK2", name: "Insurance", change_percent: "2.26" },
  ],
};

it("renders a compact ladder with truthful values and rank badges", () => {
  render(<IndustryRankingHistoryPanel locale="en" labels={labels} payload={payload} />);
  expect(screen.getByText("Banking")).toBeInTheDocument();
  expect(screen.getByText("+1.24%")).toBeInTheDocument();
  expect(screen.getByText("-0.40%")).toBeInTheDocument();
  expect(screen.getByLabelText("Type")).toBeDisabled();
  expect(screen.getByRole("link", { name: "Eastmoney Quote Center" })).toHaveAttribute("href", payload.source_url);
  expect(screen.getByText(/Stored 7\/17\/26/)).toBeInTheDocument();
});

it("switches list view and applies ascending sort without another request", () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  render(<IndustryRankingHistoryPanel locale="en" labels={labels} payload={payload} />);
  fireEvent.change(screen.getByLabelText("Sort"), { target: { value: "asc" } });
  fireEvent.click(screen.getByRole("button", { name: "Sector list" }));
  const rows = screen.getAllByRole("row");
  expect(within(rows[1]).getByText("Insurance")).toBeInTheDocument();
  expect(within(rows[2]).getByText("Banking")).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

it("refreshes explicitly with the selected bounded day count", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true });
  vi.stubGlobal("fetch", fetchMock);
  render(<IndustryRankingHistoryPanel locale="en" labels={labels} payload={payload} />);
  fireEvent.change(screen.getByLabelText("Days"), { target: { value: "20" } });
  fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/sectors/industry-rankings/refresh?days=20", { method: "POST" }));
  expect(refresh).toHaveBeenCalledOnce();
});

it("preserves a truthful failure message", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  render(<IndustryRankingHistoryPanel locale="en" labels={labels} payload={{ status: "ok", dates: [], limit: 20, items: [] }} />);
  fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
  await waitFor(() => expect(screen.getByText("Refresh failed")).toBeInTheDocument());
});

it("keeps the source link when the stored timestamp is invalid", () => {
  render(<IndustryRankingHistoryPanel locale="en" labels={labels} payload={{ ...payload, retrieved_at: "invalid" }} />);
  expect(screen.getByRole("link", { name: "Eastmoney Quote Center" })).toBeInTheDocument();
  expect(screen.queryByText(/^Stored \d/)).not.toBeInTheDocument();
});
