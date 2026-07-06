import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import ReportsPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders latest report, history, and citations", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/reports?limit=10&offset=0")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            total: 2,
            limit: 50,
            offset: 0,
            items: [
              {
                id: "report-1",
                symbol: "AAPL",
                report_type: "stock_daily",
                as_of: "2026-01-20",
                content_markdown: "# AAPL daily report\n\nPersisted report: MA 119.00",
                source_summary: {
                  source: "database",
                  price_source: "bars_1d",
                  provider: "yfinance",
                  effective_provider: "yfinance",
                  task_run_id: "task-run-12345678",
                },
              },
              {
                id: "report-2",
                symbol: "AAPL",
                report_type: "stock_daily",
                as_of: "2026-01-19",
                content_markdown: "# AAPL daily report\n\nPrevious report",
              },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await ReportsPage());

  expect(screen.getAllByText("Reports Center")[0]).toBeInTheDocument();
  expect(screen.getByText("2 reports found")).toBeInTheDocument();
  expect(screen.getByText("Showing 1-2 of 2")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "AAPL" })[0]).toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getAllByText("AAPL daily report").length).toBeGreaterThan(0);
  expect(screen.getByText("source: database")).toBeInTheDocument();
  expect(screen.getByText("price_source: bars_1d")).toBeInTheDocument();
  expect(screen.getByText("provider: yfinance")).toBeInTheDocument();
  expect(screen.queryByText(/Persisted report: MA 119.00/)).not.toBeInTheDocument();
  expect(screen.getAllByTitle("View Full Report")[0]).toHaveAttribute("href", "/reports/report-1");
});
