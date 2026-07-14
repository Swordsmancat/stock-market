import { afterEach, expect, it, vi } from "vitest";

const {
  backendFetchMock,
  getPlatformSettingsMock,
  redirectMock,
  revalidatePathMock,
  savePlatformSettingsMock,
} = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
  getPlatformSettingsMock: vi.fn<
    () => Promise<Record<string, unknown>>
  >(() =>
    Promise.resolve({
      market_data_provider: "mock",
      llm_provider: "mock",
      llm_api_key: "",
      llm_api_base: "https://api.openai.com/v1",
      llm_model: "gpt-4o-mini",
      llm_api_key_configured: false,
      favorite_home_index_codes: ["us_sp_500", "cn_csi_300"],
      home_index_display_fields: ["latest_close", "percent_change"],
      favorite_macro_indicator_codes: ["buffett_indicator_us"],
    }),
  ),
  redirectMock: vi.fn((targetPath: string) => {
    throw new Error(`NEXT_REDIRECT:${targetPath}`);
  }),
  revalidatePathMock: vi.fn(),
  savePlatformSettingsMock: vi.fn(),
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
  getPlatformSettings: getPlatformSettingsMock,
  savePlatformSettings: savePlatformSettingsMock,
}));

import {
  generateDailyReportAction,
  refreshAnalysisAction,
  savePlatformSettingsAction,
  triggerIngestionAction,
  updateWatchlistAlertsAction,
} from "./actions";

afterEach(() => {
  vi.clearAllMocks();
});

function buildSettingsFormData(
  overrides: Record<string, string | string[]> = {},
) {
  const formData = new FormData();
  const defaults: Record<string, string | string[]> = {
    locale: "en",
    market_data_provider: "yfinance",
    llm_api_preset: "disabled",
    llm_api_key: "",
    llm_api_base: "https://api.openai.com/v1",
    llm_model: "gpt-4o-mini",
    tushare_token: "",
    tushare_http_url: "",
    color_scheme: "china",
    favorite_home_index_codes: "cn_csi_300\nus_sp_500\ncn_csi_300",
    home_index_display_fields: ["latest_close", "provider"],
    favorite_macro_indicator_codes: "buffett_indicator_us\nus_10y_yield",
    news_search_provider_order: "anspire\nserpapi_baidu\nmock",
    news_search_enabled_providers: ["anspire", "serpapi_baidu"],
    news_search_key_anspire: "anspire-key",
    news_search_key_serpapi_baidu: "serpapi-key",
    news_search_max_results: "12",
    news_search_timeout_seconds: "6",
  };
  for (const [key, value] of Object.entries({ ...defaults, ...overrides })) {
    if (Array.isArray(value)) {
      for (const item of value) {
        formData.append(key, item);
      }
    } else {
      formData.set(key, value);
    }
  }
  return formData;
}

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

  await expect(
    triggerIngestionAction(buildMarketDataFormData()),
  ).rejects.toThrow(
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

  await expect(
    refreshAnalysisAction(buildMarketDataFormData()),
  ).rejects.toThrow(
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
    generateDailyReportAction(
      buildMarketDataFormData({ return_to: "/en/instruments/AAPL" }),
    ),
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
          no_data_reason:
            "No daily bars were available for the requested symbol/date range.",
        },
      }),
      { status: 422 },
    ),
  );

  await expect(
    generateDailyReportAction(
      buildMarketDataFormData({ return_to: "/en/instruments/AAPL" }),
    ),
  ).rejects.toThrow(
    "NEXT_REDIRECT:/en/instruments/AAPL?report=error&msg=No+daily+bars+were+available+for+the+requested+symbol%2Fdate+range.",
  );
});

it("saves homepage index preferences through platform settings", async () => {
  savePlatformSettingsMock.mockResolvedValue({});

  await expect(
    savePlatformSettingsAction(buildSettingsFormData()),
  ).rejects.toThrow("NEXT_REDIRECT:/en/settings?saved=ok");

  expect(savePlatformSettingsMock).toHaveBeenCalledWith(
    expect.objectContaining({
      market_data_provider: "yfinance",
      llm_provider: "mock",
      color_scheme: "china",
      favorite_home_index_codes: "cn_csi_300\nus_sp_500\ncn_csi_300",
      home_index_display_fields: ["latest_close", "provider"],
      favorite_macro_indicator_codes: "buffett_indicator_us\nus_10y_yield",
      news_search_provider_order: "anspire\nserpapi_baidu\nmock",
      news_search_enabled_providers: ["anspire", "serpapi_baidu"],
      news_search_provider_keys: {
        anspire: "anspire-key",
        serpapi_baidu: "serpapi-key",
      },
      news_search_max_results: "12",
      news_search_timeout_seconds: "6",
    }),
  );
  expect(revalidatePathMock).toHaveBeenCalledWith("/en/settings");
});

it("resolves the DeepSeek preset and forwards the configured model", async () => {
  savePlatformSettingsMock.mockResolvedValue({});

  await expect(
    savePlatformSettingsAction(
      buildSettingsFormData({
        llm_api_preset: "deepseek",
        llm_api_key: "deepseek-key",
      }),
    ),
  ).rejects.toThrow("NEXT_REDIRECT:/en/settings?saved=ok");

  expect(savePlatformSettingsMock).toHaveBeenCalledWith(
    expect.objectContaining({
      llm_provider: "openai",
      llm_api_key: "deepseek-key",
      llm_api_base: "https://api.deepseek.com/v1",
      llm_model: "deepseek-chat",
    }),
  );
});

it("ignores stale advanced fields when disabling the LLM API", async () => {
  savePlatformSettingsMock.mockResolvedValue({});

  await expect(
    savePlatformSettingsAction(
      buildSettingsFormData({
        llm_api_preset: "disabled",
        llm_api_base: "not-a-url",
        llm_model: " ",
      }),
    ),
  ).rejects.toThrow("NEXT_REDIRECT:/en/settings?saved=ok");

  expect(savePlatformSettingsMock).toHaveBeenCalledWith(
    expect.objectContaining({
      llm_provider: "mock",
    }),
  );
  const savedUpdate = savePlatformSettingsMock.mock.calls[0]?.[0];
  expect(savedUpdate).not.toHaveProperty("llm_api_base");
  expect(savedUpdate).not.toHaveProperty("llm_model");
});

it("preserves an existing key when an external preset submits a blank key", async () => {
  getPlatformSettingsMock.mockResolvedValueOnce({
    llm_api_key_configured: true,
    llm_api_base: "https://api.deepseek.com/v1",
  });
  savePlatformSettingsMock.mockResolvedValue({});

  await expect(
    savePlatformSettingsAction(
      buildSettingsFormData({
        llm_api_preset: "deepseek",
        llm_api_key: "",
      }),
    ),
  ).rejects.toThrow("NEXT_REDIRECT:/en/settings?saved=ok");

  expect(savePlatformSettingsMock).toHaveBeenCalledWith(
    expect.objectContaining({
      llm_provider: "openai",
      llm_api_key: "",
      llm_model: "deepseek-chat",
    }),
  );
});

it("requires a new key when switching to a different LLM API service", async () => {
  getPlatformSettingsMock.mockResolvedValueOnce({
    llm_api_key_configured: true,
    llm_api_base: "https://api.deepseek.com/v1",
  });

  await expect(
    savePlatformSettingsAction(
      buildSettingsFormData({
        llm_api_preset: "openai",
        llm_api_key: "",
      }),
    ),
  ).rejects.toThrow(
    "NEXT_REDIRECT:/en/settings?saved=error&llm_error=missing_key&llm_preset=openai",
  );

  expect(savePlatformSettingsMock).not.toHaveBeenCalled();
});

it("requires a key for the first external LLM API setup", async () => {
  await expect(
    savePlatformSettingsAction(
      buildSettingsFormData({
        llm_api_preset: "openai",
        llm_api_key: "",
      }),
    ),
  ).rejects.toThrow(
    "NEXT_REDIRECT:/en/settings?saved=error&llm_error=missing_key&llm_preset=openai",
  );

  expect(savePlatformSettingsMock).not.toHaveBeenCalled();
});

it("requires a new key after an invalid stored API base is disabled", async () => {
  getPlatformSettingsMock.mockResolvedValueOnce({
    llm_provider: "mock",
    llm_api_key_configured: false,
    llm_api_base: "https://api.openai.com/v1",
  });

  await expect(
    savePlatformSettingsAction(
      buildSettingsFormData({
        llm_api_preset: "openai",
        llm_api_key: "",
      }),
    ),
  ).rejects.toThrow(
    "NEXT_REDIRECT:/en/settings?saved=error&llm_error=missing_key&llm_preset=openai",
  );

  expect(savePlatformSettingsMock).not.toHaveBeenCalled();
});

it("rejects invalid custom LLM API settings with stable error codes", async () => {
  await expect(
    savePlatformSettingsAction(
      buildSettingsFormData({
        llm_api_preset: "custom",
        llm_api_base: "not-a-url",
        llm_model: "custom-model",
        llm_api_key: "custom-key",
      }),
    ),
  ).rejects.toThrow(
    "NEXT_REDIRECT:/en/settings?saved=error&llm_error=invalid_base&llm_preset=custom",
  );
  await expect(
    savePlatformSettingsAction(
      buildSettingsFormData({
        llm_api_preset: "custom",
        llm_api_base: "https://llm.example.test/v1",
        llm_model: " ",
        llm_api_key: "custom-key",
      }),
    ),
  ).rejects.toThrow(
    "NEXT_REDIRECT:/en/settings?saved=error&llm_error=missing_model&llm_preset=custom",
  );

  expect(savePlatformSettingsMock).not.toHaveBeenCalled();
});

it("forwards trimmed custom OpenAI-compatible settings", async () => {
  savePlatformSettingsMock.mockResolvedValue({});

  await expect(
    savePlatformSettingsAction(
      buildSettingsFormData({
        llm_api_preset: "custom",
        llm_api_base: " https://llm.example.test/v1/ ",
        llm_model: " custom-model ",
        llm_api_key: "custom-key",
      }),
    ),
  ).rejects.toThrow("NEXT_REDIRECT:/en/settings?saved=ok");

  expect(savePlatformSettingsMock).toHaveBeenCalledWith(
    expect.objectContaining({
      llm_provider: "openai",
      llm_api_base: "https://llm.example.test/v1",
      llm_model: "custom-model",
    }),
  );
});

it("submits an empty alert_rules object when existing watchlist rules are cleared", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
  );

  await expect(
    updateWatchlistAlertsAction(buildWatchlistAlertFormData()),
  ).rejects.toThrow("NEXT_REDIRECT:/en/watchlist?op=alerts_updated");

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
