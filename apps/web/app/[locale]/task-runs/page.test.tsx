import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import TaskRunsPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders latest watchlist run and recent task runs", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/task-runs/recent?limit=20")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "database",
            items: [
              {
                id: "task-1",
                task_name: "reports.refresh_daily_watchlist_analysis",
                status: "succeeded",
                started_at: "2026-01-20T21:30:00+00:00",
                duration_ms: 1280,
                input_json: { watchlist: "AAPL:US" },
                result_json: { item_count: 2 },
                error_message: null,
              },
              {
                id: "task-2",
                task_name: "reports.refresh_daily_watchlist_analysis",
                status: "failed",
                started_at: "2026-01-19T21:30:00+00:00",
                duration_ms: 500,
                input_json: { watchlist: "0700:HK" },
                result_json: null,
                error_message: "provider timeout",
              },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await TaskRunsPage());

  expect(screen.getAllByText("Task Runs")[0]).toBeInTheDocument();
  expect(screen.getByText("Monitor background tasks and data ingestion processes.")).toBeInTheDocument();
  expect(screen.getAllByText("reports.refresh_daily_watchlist_analysis")).toHaveLength(2);
  expect(screen.getByText("succeeded")).toBeInTheDocument();
  expect(screen.getByText("failed")).toBeInTheDocument();
  expect(screen.getByText("provider timeout")).toBeInTheDocument();
});
