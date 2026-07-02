import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
  getBackendApiUrl: () => "http://127.0.0.1:8000",
}));

import TaskRunDetailPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

type MockTaskRunDetail = {
  id: string;
  task_name: string;
  status: string;
  started_at: string;
  duration_ms: number | null;
  celery_task_id: string | null;
  input_json: Record<string, unknown>;
  result_json: Record<string, unknown> | null;
  error_message: string | null;
};

function buildMockTaskRunDetail(overrides: Partial<MockTaskRunDetail> = {}): MockTaskRunDetail {
  return {
    id: "task-run-12345678",
    task_name: "ingestion.ingest_market_data",
    status: "succeeded",
    started_at: "2026-01-20T21:30:00+00:00",
    duration_ms: 1280,
    celery_task_id: "celery-task-id",
    input_json: { market: "US" },
    result_json: { market: "US", status: "ingested" },
    error_message: null,
    ...overrides,
  };
}

function mockTaskRunDetailResponse(taskRunDetail: MockTaskRunDetail): void {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith(`/task-runs/${taskRunDetail.id}`)) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "database",
            item: taskRunDetail,
          }),
        ),
      );
    }

    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });
}

async function renderTaskRunDetailPage(taskRunId = "task-run-12345678") {
  return render(
    await TaskRunDetailPage({
      params: Promise.resolve({ locale: "en", taskRunId }),
    }),
  );
}

it("unwraps task-run API payloads and links generated reports", async () => {
  mockTaskRunDetailResponse(
    buildMockTaskRunDetail({
      task_name: "reports.refresh_daily_stock_analysis",
      input_json: { symbol: "AAPL", market: "US" },
      result_json: {
        symbol: "AAPL",
        status: "refreshed",
        report: { id: "report-1", status: "stored" },
      },
    }),
  );

  await renderTaskRunDetailPage();

  expect(screen.getByText("Task Run Detail")).toBeInTheDocument();
  expect(screen.getByText("reports.refresh_daily_stock_analysis")).toBeInTheDocument();
  expect(screen.getByText("succeeded")).toBeInTheDocument();
  expect(screen.getByText("Quality Diagnostics")).toBeInTheDocument();
  expect(screen.getByText("No quality diagnostics were persisted for this task run.")).toBeInTheDocument();
  expect(screen.getByText("Generated Report")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "report-1" })).toHaveAttribute("href", "/reports/report-1");
});

it("renders OK quality diagnostics and keeps the raw result visible", async () => {
  mockTaskRunDetailResponse(
    buildMockTaskRunDetail({
      result_json: {
        market: "US",
        instrument_count: 1,
        status: "ingested",
        quality_diagnostics: {
          status: "OK",
          instrument_count: 1,
          instruments: [
            {
              symbol: "AAPL",
              status: "OK",
              checked_bars: 2,
              missing_dates: [],
              invalid_ohlc: [],
              volume_warnings: [],
              quality_error: null,
            },
          ],
          errors: [],
          warnings: [],
        },
      },
    }),
  );

  await renderTaskRunDetailPage();

  expect(screen.getByText("Quality checks completed successfully.")).toBeInTheDocument();
  expect(screen.getByText("Instruments checked")).toBeInTheDocument();
  expect(screen.getByText("Task result instruments")).toBeInTheDocument();
  expect(screen.getByText("AAPL")).toBeInTheDocument();
  expect(screen.getByText("Checked bars")).toBeInTheDocument();
  expect(screen.getByText(/"quality_diagnostics"/)).toBeInTheDocument();
});

it("renders warning diagnostics from partial instrument issue arrays", async () => {
  mockTaskRunDetailResponse(
    buildMockTaskRunDetail({
      result_json: {
        market: "US",
        instrument_count: 1,
        status: "ingested",
        quality_diagnostics: {
          status: "WARN",
          instrument_count: 1,
          instruments: [
            {
              symbol: "AAPL",
              status: "WARN",
              checked_bars: 3,
              missing_dates: ["2026-01-19"],
              volume_warnings: [{ date: "2026-01-20", volume: 0 }],
            },
          ],
          warnings: [{ symbol: "AAPL", code: "CUSTOM_WARNING", details: { provider: "mock" } }],
        },
      },
    }),
  );

  await renderTaskRunDetailPage();

  expect(screen.getByText("Quality checks completed with warnings. The task may still have succeeded.")).toBeInTheDocument();
  expect(screen.getByText("CUSTOM_WARNING")).toBeInTheDocument();
  expect(screen.getAllByText("2026-01-19").length).toBeGreaterThan(0);
  expect(screen.getAllByText(/"volume": 0/).length).toBeGreaterThan(0);
  expect(screen.getByText("MISSING_DATES")).toBeInTheDocument();
  expect(screen.getByText("VOLUME_WARNING")).toBeInTheDocument();
});

it("renders FAIL quality diagnostics separately from task execution status", async () => {
  mockTaskRunDetailResponse(
    buildMockTaskRunDetail({
      status: "succeeded",
      result_json: {
        market: "US",
        instrument_count: 1,
        status: "ingested",
        quality_diagnostics: {
          status: "FAIL",
          instrument_count: 1,
          instruments: [
            {
              symbol: "MSFT",
              status: "FAIL",
              checked_bars: 1,
              invalid_ohlc: [{ date: "2026-01-20", open: 10, high: 9 }],
              quality_error: "Invalid OHLC sequence.",
            },
            "unexpected-instrument-diagnostic",
          ],
          errors: [{ code: "NO_INSTRUMENTS", message: "No instruments returned." }],
        },
      },
    }),
  );

  await renderTaskRunDetailPage();

  expect(screen.getByText("succeeded")).toBeInTheDocument();
  expect(screen.getByText("Quality checks found blocking data issues. This is separate from the task execution status.")).toBeInTheDocument();
  expect(screen.getAllByText("NO_INSTRUMENTS").length).toBeGreaterThan(0);
  expect(screen.getAllByText("No instruments returned.").length).toBeGreaterThan(0);
  expect(screen.getAllByText("MSFT").length).toBeGreaterThan(0);
  expect(screen.getByText("INVALID_OHLC")).toBeInTheDocument();
  expect(screen.getAllByText("Invalid OHLC sequence.").length).toBeGreaterThan(0);
  expect(screen.getAllByText("unexpected-instrument-diagnostic").length).toBeGreaterThan(0);
  expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
});

it("keeps the retry action visible for failed task runs", async () => {
  mockTaskRunDetailResponse(
    buildMockTaskRunDetail({
      status: "failed",
      result_json: {
        market: "US",
        status: "ingested",
        quality_diagnostics: {
          status: "OK",
          instrument_count: 1,
          instruments: [],
        },
      },
      error_message: "provider timeout",
    }),
  );

  await renderTaskRunDetailPage();

  expect(screen.getByText("failed")).toBeInTheDocument();
  expect(screen.getByText("provider timeout")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});
