import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
  getBackendApiUrl: () => "http://127.0.0.1:8000",
}));

import TaskRunDetailPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("unwraps task-run API payloads and links generated reports", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/task-runs/task-run-12345678")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "database",
            item: {
              id: "task-run-12345678",
              task_name: "reports.refresh_daily_stock_analysis",
              status: "succeeded",
              started_at: "2026-01-20T21:30:00+00:00",
              duration_ms: 1280,
              celery_task_id: "celery-task-id",
              input_json: { symbol: "AAPL", market: "US" },
              result_json: {
                symbol: "AAPL",
                status: "refreshed",
                report: { id: "report-1", status: "stored" },
              },
              error_message: null,
            },
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await TaskRunDetailPage({
      params: Promise.resolve({ locale: "en", taskRunId: "task-run-12345678" }),
    }),
  );

  expect(screen.getByText("Task Run Detail")).toBeInTheDocument();
  expect(screen.getByText("reports.refresh_daily_stock_analysis")).toBeInTheDocument();
  expect(screen.getByText("succeeded")).toBeInTheDocument();
  expect(screen.getByText("Generated Report")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "report-1" })).toHaveAttribute("href", "/reports/report-1");
});
