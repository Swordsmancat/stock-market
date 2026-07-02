import { afterEach, expect, it, vi } from "vitest";

const { backendFetchMock, redirectMock, revalidatePathMock } = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
  redirectMock: vi.fn((targetPath: string) => {
    throw new Error(`NEXT_REDIRECT:${targetPath}`);
  }),
  revalidatePathMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
}));

vi.mock("next/cache", () => ({
  revalidatePath: revalidatePathMock,
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: backendFetchMock,
}));

vi.mock("@/lib/platform-settings-store", () => ({
  getPlatformSettings: () =>
    Promise.resolve({
      market_data_provider: "mock",
      llm_provider: "mock",
      llm_api_key: "",
      llm_api_base: "https://api.openai.com/v1",
    }),
  savePlatformSettings: vi.fn(),
}));

import {
  generateDailyReportAction,
  refreshAnalysisAction,
  triggerIngestionAction,
  updateWatchlistAlertsAction,
} from "./actions";

afterEach(() => {
  vi.clearAllMocks();
});

function buildWatchlistAlertFormData(overrides: Record<string, string> = {}) {
  const formData = new FormData();
  const defaults = {
    locale: "en",
    symbol: "AAPL",
    market: "US",
    name: "Apple Inc.",
    price_above: "",
    rsi_below: "",
  };
  for (const [key, value] of Object.entries({ ...defaults, ...overrides })) {
    formData.set(key, value);
  }
  return formData;
}

function buildMarketDataFormData(overrides: Record<string, string> = {}) {
  const formData = new FormData();
  const defaults = {
    locale: "en",
    symbol: "AAPL",
    market: "US",
    start: "2026-01-01",
    end: "2026-01-31",
    ma_window: "3",
    provider: "mock",
    return_to: "",
  };
  for (const [key, value] of Object.entries({ ...defaults, ...overrides })) {
    formData.set(key, value);
  }
  return formData;
}

it("redirects ingestion success with the created task run id", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "dispatched",
        task_run: {
          id: "task-ingest-123",
          status: "queued",
          result_json: { market: "US", bar_count: 0 },
        },
      }),
      { status: 200 },
    ),
  );

  await expect(triggerIngestionAction(buildMarketDataFormData())).rejects.toThrow(
    "NEXT_REDIRECT:/en?ingest=ok&bars=0&market=US&task_run_id=task-ingest-123",
  );
});

it("redirects analysis success with the created task run id", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "dispatched",
        task_run: {
          id: "task-analysis-123",
          status: "queued",
        },
      }),
      { status: 200 },
    ),
  );

  await expect(refreshAnalysisAction(buildMarketDataFormData())).rejects.toThrow(
    "NEXT_REDIRECT:/en?analysis=ok&symbol=AAPL&task_run_id=task-analysis-123",
  );
});

it("redirects generated report success with report and task run links", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        id: "report-123",
        task_run_id: "task-report-123",
        status: "stored",
      }),
      { status: 200 },
    ),
  );

  await expect(
    generateDailyReportAction(buildMarketDataFormData({ return_to: "/en/instruments/AAPL" })),
  ).rejects.toThrow(
    "NEXT_REDIRECT:/en/instruments/AAPL?report=ok&report_id=report-123&task_run_id=task-report-123",
  );
  expect(revalidatePathMock).toHaveBeenCalledWith("/en/instruments/AAPL");
});

it("redirects generated report failures with actionable backend detail", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        detail: {
          no_data_reason: "No daily bars were available for the requested symbol/date range.",
        },
      }),
      { status: 422 },
    ),
  );

  await expect(
    generateDailyReportAction(buildMarketDataFormData({ return_to: "/en/instruments/AAPL" })),
  ).rejects.toThrow(
    "NEXT_REDIRECT:/en/instruments/AAPL?report=error&msg=No+daily+bars+were+available+for+the+requested+symbol%2Fdate+range.",
  );
});

it("submits an empty alert_rules object when existing watchlist rules are cleared", async () => {
  backendFetchMock.mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));

  await expect(updateWatchlistAlertsAction(buildWatchlistAlertFormData())).rejects.toThrow(
    "NEXT_REDIRECT:/en/watchlist?op=alerts_updated",
  );

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/watchlist/items",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        symbol: "AAPL",
        market: "US",
        name: "Apple Inc.",
        alert_rules: {},
      }),
    }),
  );
  expect(revalidatePathMock).toHaveBeenCalledWith("/en/watchlist");
});

it("redirects with an error reason when alert rule saving fails", async () => {
  backendFetchMock.mockResolvedValue(new Response("", { status: 500 }));

  await expect(
    updateWatchlistAlertsAction(
      buildWatchlistAlertFormData({
        price_above: "150",
        rsi_below: "30",
      }),
    ),
  ).rejects.toThrow("NEXT_REDIRECT:/en/watchlist?op=error&reason=http_500");

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/watchlist/items",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        symbol: "AAPL",
        market: "US",
        name: "Apple Inc.",
        alert_rules: {
          price_above: 150,
          rsi_below: 30,
        },
      }),
    }),
  );
});
