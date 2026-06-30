import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import TaskRunsPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders latest watchlist run and recent task runs", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            task_name: "reports.refresh_daily_watchlist_analysis",
            status: "succeeded",
            duration_ms: 1280,
            result_json: { item_count: 2 },
          }),
        ),
      );
    }
    if (url.endsWith("/task-runs/recent?limit=10")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "database",
            items: [
              {
                task_name: "reports.refresh_daily_watchlist_analysis",
                status: "succeeded",
                started_at: "2026-01-20T21:30:00+00:00",
                duration_ms: 1280,
                result_json: { item_count: 2 },
              },
              {
                task_name: "reports.refresh_daily_watchlist_analysis",
                status: "failed",
                started_at: "2026-01-19T21:30:00+00:00",
                duration_ms: 500,
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

  expect(screen.getByText("任务监控")).toBeInTheDocument();
  expect(screen.getByText("每日关注列表报告")).toBeInTheDocument();
  expect(screen.getByText("succeeded，处理股票数：2，耗时：1280ms")).toBeInTheDocument();
  expect(
    screen.getByText((content) =>
      content.includes("reports.refresh_daily_watchlist_analysis：failed") &&
      content.includes("失败原因：provider timeout"),
    ),
  ).toBeInTheDocument();
});
