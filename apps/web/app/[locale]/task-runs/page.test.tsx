import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import TaskRunsPage from "./page";

afterEach(() => {
  cleanup();
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
  expect(screen.getByText("2 recent task runs.")).toBeInTheDocument();
  expect(screen.getAllByText("reports.refresh_daily_watchlist_analysis")).toHaveLength(2);
  expect(screen.getAllByText("Succeeded")).toHaveLength(2);
  expect(screen.getAllByText("Failed")).toHaveLength(2);
  expect(screen.getByText("provider timeout")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});

it("renders an error state instead of an empty state when task runs fail to load", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 503 }));

  render(await TaskRunsPage());

  expect(screen.getByText("Could not load task runs.")).toBeInTheDocument();
  expect(screen.getByText("Check that the API is running, then refresh this page.")).toBeInTheDocument();
  expect(screen.queryByText("0 recent task runs.")).not.toBeInTheDocument();
  expect(screen.queryByText("No recent task runs.")).not.toBeInTheDocument();
});

it("renders an empty state when task runs load successfully with no items", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        source: "database",
        items: [],
      }),
    ),
  );

  render(await TaskRunsPage());

  expect(screen.getByText("0 recent task runs.")).toBeInTheDocument();
  expect(screen.getByText("No recent task runs.")).toBeInTheDocument();
  expect(screen.queryByText("Could not load task runs.")).not.toBeInTheDocument();
});
