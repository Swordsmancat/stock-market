import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import CrawlerMonitorPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const ids = [
  "market_cn",
  "market_us",
  "market_hk",
  "universe_cn",
  "evidence_incremental",
  "fundamental_shard",
  "official_disclosures",
  "eastmoney_calendar",
  "eastmoney_industry",
  "eastmoney_news",
  "eastmoney_fundamentals",
];

const payload = {
  status: "ok",
  generated_at: "2026-07-17T12:00:00+00:00",
  summary: { total: 11, running: 1, healthy: 9, attention: 1, recent_failures: 0 },
  items: ids.map((id, index) => ({
    id,
    status: index === 5 ? "running" : index === 6 ? "overdue" : "healthy",
    task_name: id.includes("market") ? "ingestion.ingest_market_data" : "ingestion.pipeline",
    scope: "CN",
    provider: "akshare",
    cadence: index === 6 ? "hourly" : "daily",
    latest_task_run_id: `run-${index}`,
    started_at: "2026-07-17T10:00:00+00:00",
    finished_at: index === 5 ? null : "2026-07-17T10:05:00+00:00",
    heartbeat_at: index === 5 ? "2026-07-17T11:59:00+00:00" : null,
    duration_ms: 300_000,
    progress: index === 5
      ? { phase: "fundamentals", current: 675, total: 1105, message: "Working", updated_at: "2026-07-17T11:59:00+00:00" }
      : null,
    recent_failure_count: 0,
    diagnostic_code: index === 6 ? "freshness_window_exceeded" : null,
    error_summary: null,
  })),
};

it("renders the compact status strip and stored execution details", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(payload)),
  );

  render(await CrawlerMonitorPage({ params: Promise.resolve({ locale: "en-US" }) }));

  expect(screen.getByRole("heading", { name: "Crawler Monitor" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "System status" })).toBeInTheDocument();
  expect(screen.getAllByText("A-share fundamentals shard").length).toBeGreaterThan(0);
  expect(screen.getAllByText("675/1105").length).toBeGreaterThan(0);
  expect(screen.getAllByRole("link", { name: "View run" }).length).toBeGreaterThan(0);
  expect(screen.getByRole("region", { name: "Execution details" })).toHaveAttribute("tabindex", "0");
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/crawler-monitor",
    expect.objectContaining({ cache: "no-store" }),
  );
});

it("keeps API failure distinct from unrecorded pipelines", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 503 }));

  render(await CrawlerMonitorPage({ params: Promise.resolve({ locale: "en-US" }) }));

  expect(screen.getByText("Crawler status is unavailable")).toBeInTheDocument();
  expect(screen.queryByText("Not recorded")).not.toBeInTheDocument();
});
