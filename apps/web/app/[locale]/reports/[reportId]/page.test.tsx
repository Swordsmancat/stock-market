import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
  getBackendApiUrl: () => "http://127.0.0.1:8000",
}));

import ReportDetailPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders report detail with a task-run lineage link", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/reports/items/report-1")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: "report-1",
            symbol: "AAPL",
            report_type: "stock_daily",
            as_of: "2026-01-20",
            content_markdown: "# AAPL Daily Report\n\nGenerated from task-run lineage.",
            citations: ["technical_indicators:AAPL:2026-01-20T00:00:00+00:00"],
            created_at: "2026-01-20T21:30:00+00:00",
            task_run_id: "task-run-12345678",
            source_summary: {
              source: "database",
              price_source: "bars_1d",
              provider: "yfinance",
              effective_provider: "yfinance",
              task_run_id: "task-run-12345678",
            },
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await ReportDetailPage({
      params: Promise.resolve({ locale: "en", reportId: "report-1" }),
    }),
  );

  expect(screen.getByText("AAPL")).toBeInTheDocument();
  expect(screen.getByText(/Generated from task-run lineage/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Task Run: task-run/ })).toHaveAttribute(
    "href",
    "/task-runs/task-run-12345678",
  );
  expect(screen.getByText("source: database")).toBeInTheDocument();
  expect(screen.getByText("price_source: bars_1d")).toBeInTheDocument();
  expect(screen.getByText("provider: yfinance")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View instrument" })).toHaveAttribute("href", "/instruments/AAPL");
});
