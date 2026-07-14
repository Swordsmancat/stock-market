import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { getPlatformSettingsMock } = vi.hoisted(() => ({
  getPlatformSettingsMock: vi.fn(),
}));

vi.mock("@/app/[locale]/actions", () => ({
  savePlatformSettingsAction: vi.fn(),
}));

vi.mock("@/lib/platform-settings-store", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/platform-settings-store")
  >("@/lib/platform-settings-store");
  return {
    ...actual,
    getPlatformSettings: getPlatformSettingsMock,
  };
});

import SettingsPage from "./page";

afterEach(() => {
  cleanup();
  getPlatformSettingsMock.mockReset();
});

function buildSettings(overrides: Record<string, unknown> = {}) {
  return {
    market_data_provider: "yfinance",
    llm_provider: "mock",
    llm_api_key: "",
    llm_api_base: "https://api.openai.com/v1",
    llm_model: "gpt-4o-mini",
    akshare_enabled: false,
    tushare_token: "",
    tushare_http_url: "",
    color_scheme: "china",
    favorite_home_index_codes: ["cn_csi_300", "us_sp_500"],
    home_index_display_fields: ["latest_close", "provider"],
    favorite_macro_indicator_codes: ["buffett_indicator_us"],
    news_search_provider_order: ["anspire", "serpapi_baidu", "mock"],
    news_search_enabled_providers: ["anspire"],
    news_search_provider_keys: {},
    news_search_max_results: 10,
    news_search_timeout_seconds: 8,
    llm_api_key_configured: false,
    tushare_token_configured: false,
    news_search_provider_keys_configured: { anspire: true },
    market_data_provider_capabilities: [
      {
        provider: "yfinance",
        active: true,
        configured: true,
        category: "historical_daily",
        supports_daily_bars: true,
        supports_realtime_quotes: false,
        readiness_note: "Historical daily bars are available.",
      },
    ],
    news_search_provider_capabilities: [
      {
        provider: "anspire",
        display_name: "Anspire AI Search",
        enabled: true,
        configured: true,
        credential_required: true,
        credential_configured: true,
        credential_field: "api_key",
        priority: 1,
        supported_markets: ["A-share", "US", "HK"],
        supported_regions: ["CN", "US", "HK"],
        supported_result_kinds: ["news", "web"],
        default_timeout_seconds: 8,
        default_max_results: 10,
        implementation_status: "implemented",
        readiness_note: "ready",
        citation_caveat: "stored only",
      },
      {
        provider: "serpapi_baidu",
        display_name: "SerpAPI Baidu",
        enabled: false,
        configured: false,
        credential_required: true,
        credential_configured: false,
        credential_field: "api_key",
        priority: 2,
        supported_markets: ["A-share"],
        supported_regions: ["CN"],
        supported_result_kinds: ["news", "web"],
        default_timeout_seconds: 8,
        default_max_results: 10,
        implementation_status: "implemented",
        readiness_note: "ready",
        citation_caveat: "stored only",
      },
    ],
    ...overrides,
  };
}

it("renders homepage core index preferences in settings", async () => {
  getPlatformSettingsMock.mockResolvedValue(buildSettings());

  render(
    await SettingsPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getAllByText("Homepage Core Indices").length).toBeGreaterThan(
    0,
  );
  expect(screen.getByLabelText("Index codes")).toHaveValue(
    "cn_csi_300\nus_sp_500",
  );
  expect(screen.getByLabelText("Latest close")).toBeChecked();
  expect(screen.getByLabelText("Provider/source")).toBeChecked();
  expect(screen.getByLabelText("Percent change")).not.toBeChecked();
  expect(
    screen.getByText(/Default: us_sp_500, us_nasdaq_composite/),
  ).toBeInTheDocument();
  expect(screen.getAllByText("News Search Sources").length).toBeGreaterThan(0);
  expect(screen.getByLabelText("Anspire API Key")).toHaveAttribute(
    "placeholder",
    "Key already saved — leave blank to keep unchanged",
  );
  expect(screen.getByLabelText("Provider priority")).toHaveValue(
    "anspire\nserpapi_baidu\nmock",
  );
  expect(screen.getByLabelText("Max results")).toHaveValue(10);
  expect(
    screen.getByText(
      "Enter an API key when enabling DeepSeek, OpenAI, or a custom endpoint.",
    ),
  ).toBeInTheDocument();
});

it("renders the DeepSeek preset without exposing the stored API key", async () => {
  getPlatformSettingsMock.mockResolvedValue(
    buildSettings({
      llm_provider: "openai",
      llm_api_key: "secret-that-must-not-render",
      llm_api_base: "https://api.deepseek.com/v1",
      llm_model: "deepseek-chat",
      llm_api_key_configured: true,
    }),
  );

  render(
    await SettingsPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByLabelText("API preset")).toHaveValue("deepseek");
  expect(screen.getByLabelText("API Key")).toHaveValue("");
  expect(
    screen.getByText(/A key is saved on the server/),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Custom endpoint and model").closest("details"),
  ).not.toHaveAttribute("open");

  const llmPresetSelect = screen.getByLabelText("API preset");
  const marketDataSelect = document.querySelector(
    'select[name="market_data_provider"]',
  );
  expect(marketDataSelect).not.toBeNull();
  expect(
    llmPresetSelect.compareDocumentPosition(marketDataSelect as Element) &
      Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
});

it("opens custom fields and localizes stable LLM configuration errors", async () => {
  getPlatformSettingsMock.mockResolvedValue(buildSettings());

  render(
    await SettingsPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({
        saved: "error",
        llm_error: "invalid_base",
        llm_preset: "custom",
      }),
    }),
  );

  expect(screen.getByLabelText("API preset")).toHaveValue("custom");
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Enter a valid HTTP or HTTPS API Base URL",
  );
  expect(screen.getByLabelText("API Base URL")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  expect(screen.getByLabelText("API Base URL")).toHaveAttribute(
    "aria-describedby",
    "llm_api_base_help llm_api_base_error",
  );
  expect(screen.getByLabelText("API Base URL")).toHaveAttribute(
    "type",
    "text",
  );
  expect(
    screen.getByText("Custom endpoint and model").closest("details"),
  ).toHaveAttribute("open");
});
