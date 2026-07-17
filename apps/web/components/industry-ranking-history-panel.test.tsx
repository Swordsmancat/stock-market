import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { IndustryRankingHistoryPanel } from "./industry-ranking-history-panel";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const labels = { title: "行业涨幅历史榜", description: "已入库", refresh: "刷新排名", refreshing: "正在刷新", empty: "暂无", rank: "排名", failed: "刷新失败" };

it("renders stored dates and rankings", () => {
  render(<IndustryRankingHistoryPanel labels={labels} payload={{ status: "ok", dates: ["2026-07-17"], limit: 1, items: [{ date: "2026-07-17", rank: 1, code: "BK1", name: "银行", change_percent: "1.24" }] }} />);
  expect(screen.getByText("银行")).toBeInTheDocument();
  expect(screen.getByText("+1.24%")).toBeInTheDocument();
});

it("refreshes explicitly and preserves a truthful failure message", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  render(<IndustryRankingHistoryPanel labels={labels} payload={{ status: "ok", dates: [], limit: 20, items: [] }} />);
  fireEvent.click(screen.getByRole("button", { name: "刷新排名" }));
  await waitFor(() => expect(screen.getByText("刷新失败")).toBeInTheDocument());
});
