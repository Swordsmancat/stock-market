import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it, vi } from "vitest";
import enMessages from "../../../messages/en.json";
import type { MarketAssistantResponse } from "@/lib/market-assistant";

const { askMarketAssistantMock } = vi.hoisted(() => ({
  askMarketAssistantMock: vi.fn(),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
}));

vi.mock("@/lib/platform-settings-store", () => ({
  getPlatformSettings: async () => ({
    market_data_provider: "yfinance",
    llm_provider: "mock",
    llm_api_key: "",
    llm_api_base: "https://api.openai.com/v1",
    akshare_enabled: false,
    tushare_token: "",
    tushare_http_url: "",
    color_scheme: "china",
    favorite_macro_indicator_codes: ["buffett_indicator_us", "us_10y_yield"],
    llm_api_key_configured: false,
    tushare_token_configured: false,
    market_data_provider_capabilities: [],
  }),
}));

vi.mock("@/lib/market-assistant", () => ({
  askMarketAssistant: askMarketAssistantMock,
}));

import AiResearchPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  askMarketAssistantMock.mockReset();
});

function createAssistantResponse(overrides: Partial<MarketAssistantResponse> = {}): MarketAssistantResponse {
  return {
    status: "degraded",
    answer_markdown: "Research-only answer with cited local evidence.",
    symbol: "AAPL",
    as_of: "2026-01-02",
    model: {
      provider: "deterministic",
      name: "market-assistant-deterministic-fallback",
      used_llm: false,
      fallback_reason: "OpenAI-compatible LLM provider is not configured.",
    },
    context: {
      scope: "instrument",
      timeframe: "1d",
      start: "2026-01-01",
      end: "2026-01-02",
      latest_close: 102,
      period_change_pct: 1.2,
      bar_count: 2,
      source: "database",
      provider: "yfinance",
      requested_provider: "yfinance",
      effective_provider: "yfinance",
    },
    citations: [
      {
        id: "bars_1d:AAPL:2026-01-02",
        label: "Daily bars for AAPL as of 2026-01-02",
        source: "bars_1d",
        source_type: "bars",
        as_of: "2026-01-02",
        provider: "yfinance",
      },
    ],
    diagnostics: [
      {
        source: "fundamentals",
        status: "no_data",
        severity: "info",
        code: "SOURCE_NO_DATA",
        message: "No stored fundamentals are available.",
      },
    ],
    safety: {
      not_investment_advice: true,
      no_fabricated_market_data: true,
      disclaimer: "Research only. Not investment advice.",
    },
    ...overrides,
  };
}

function createMarketOverviewPayload() {
  const macroIndicators = [
    {
      code: "buffett_indicator_us",
      name: "Buffett Indicator - US",
      region: "US",
      category: "valuation",
      status: "ok",
      value: 188.5,
      unit: "percent",
      as_of: "2026-01-02",
      source: "Audited seed: World Bank market cap and GDP",
      no_data_reason: null,
    },
    {
      code: "buffett_indicator_cn",
      name: "Buffett Indicator - CN",
      region: "CN",
      category: "valuation",
      status: "no_data",
      value: null,
      unit: "percent",
      as_of: null,
      source: null,
      no_data_reason: "No audited observation has been seeded for this indicator yet.",
    },
    {
      code: "us_10y_yield",
      name: "US 10Y Treasury Yield",
      region: "US",
      category: "rates",
      status: "ok",
      value: 4.25,
      unit: "percent",
      as_of: "2026-01-02",
      source: "Audited seed: FRED DGS10",
      no_data_reason: null,
    },
  ];

  return {
    generated_at: "2026-01-02T00:00:00+00:00",
    provider: "yfinance",
    followed: {
      items: [
        {
          symbol: "AAPL",
          name: "Apple Inc.",
          market: "US",
          freshness: "fresh",
          status: "ok",
          latest: { timestamp: "2026-01-02", close: 102 },
        },
        {
          symbol: "0700",
          name: "Tencent Holdings",
          market: "HK",
          freshness: "stale",
          status: "ok",
          latest: { timestamp: "2025-12-30", close: 420 },
        },
      ],
    },
    macro_indicators: { items: macroIndicators },
    valuation_indicators: { items: macroIndicators },
    dashboard_brief: {
      diagnostics: [
        {
          source: "market_indicators",
          status: "no_data",
          severity: "info",
          code: "MACRO_INDICATOR_NO_DATA",
          message: "Some macro indicators do not have audited observations yet.",
        },
      ],
    },
    diagnostics: [],
  };
}

function createOfficialSourceStatusPayload() {
  return {
    status: "degraded",
    citation_policy: "Only stored local macro observations are AI citations.",
    providers: [
      {
        provider: "fred",
        label: "FRED US macro",
        status: "needs_configuration",
        configured: false,
        can_refresh_from_browser: false,
        credential_required: true,
        evidence_count: 1,
        latest_as_of: "2026-01-02",
        source_frequency: "daily_or_monthly",
        indicator_codes: ["us_10y_yield", "us_cpi_yoy"],
        missing_indicator_codes: ["us_cpi_yoy"],
        recommended_next_action: "Set FRED_API_KEY, then run a dry-run refresh from Macro Research.",
        citation_policy: "Readiness guidance only; cite stored observations after import.",
      },
      {
        provider: "world_bank",
        label: "World Bank Buffett Indicator",
        status: "degraded",
        configured: true,
        can_refresh_from_browser: true,
        credential_required: false,
        evidence_count: 0,
        latest_as_of: null,
        source_frequency: "annual_lagged",
        indicator_codes: ["buffett_indicator_us", "buffett_indicator_cn", "buffett_indicator_hk"],
        missing_indicator_codes: ["buffett_indicator_us", "buffett_indicator_cn", "buffett_indicator_hk"],
        recommended_next_action: "Run World Bank dry-run, then write refresh for missing Buffett Indicator regions.",
        citation_policy: "Readiness guidance only; cite stored observations after import.",
      },
    ],
  };
}

async function renderAiResearchPage() {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {await AiResearchPage({ params: Promise.resolve({ locale: "en" }) })}
    </NextIntlClientProvider>,
  );
}

it("renders the AI research desk with watchlist, signal, macro, and source-gap context", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            name: "default",
            source: "database",
            items: [
              {
                symbol: "AAPL",
                name: "Apple Inc.",
                market: "US",
                is_active: true,
                latest_price: 102,
                rsi: 55,
                alert_status: { triggered: false, rules: [] },
              },
              {
                symbol: "0700",
                name: "Tencent Holdings",
                market: "HK",
                is_active: true,
                latest_price: 420,
                rsi: 48,
                alert_status: { triggered: true, rules: [] },
              },
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/dashboard/market-overview?provider=yfinance")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketOverviewPayload())));
    }
    if (url.endsWith("/market-indicators/official-sources/status")) {
      return Promise.resolve(new Response(JSON.stringify(createOfficialSourceStatusPayload())));
    }
    if (url.includes("/recommendations?symbols=AAPL%2C0700&limit=6")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "ok",
            generated_at: "2026-01-02T00:00:00Z",
            diagnostics: [
              {
                source: "recommendations",
                status: "partial",
                severity: "info",
                code: "SIGNAL_SAMPLE_LIMITED",
                message: "Signals are deterministic research inputs only.",
              },
            ],
            items: [
              {
                symbol: "AAPL",
                type: "breakout",
                title: "AAPL crossed above its moving average",
                reason: "Price moved above a recent moving-average reference with improving volume.",
                confidence: 0.82,
                timestamp: "2026-01-02T00:00:00Z",
                data: { close: 102 },
              },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  await renderAiResearchPage();

  expect(screen.getByRole("heading", { name: "AI Research Desk" })).toBeInTheDocument();
  expect(screen.getByText(/Research only: this desk summarizes evidence/)).toBeInTheDocument();
  expect(screen.getByText("Provider: yfinance")).toBeInTheDocument();
  expect(screen.getAllByText("AAPL").length).toBeGreaterThan(0);
  expect(screen.getAllByText("0700").length).toBeGreaterThan(0);
  expect(screen.getAllByText("AAPL crossed above its moving average").length).toBeGreaterThan(0);
  expect(screen.getByText("Breakout research signal")).toBeInTheDocument();
  expect(screen.getByText("Buffett Indicator - US")).toBeInTheDocument();
  expect(screen.getByText("Buffett Indicator - CN")).toBeInTheDocument();
  expect(screen.getByText("Value: 188.5%")).toBeInTheDocument();
  expect(screen.getByText("Official source readiness")).toBeInTheDocument();
  expect(screen.getByText("World Bank Buffett Indicator")).toBeInTheDocument();
  expect(screen.getByText("Next: Run World Bank dry-run, then write refresh for missing Buffett Indicator regions.")).toBeInTheDocument();
  expect(screen.getByText("No audited observation has been seeded for this indicator yet.")).toBeInTheDocument();
  expect(screen.getByText("Signals are deterministic research inputs only.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open watchlist" })).toHaveAttribute("href", "/watchlist");
  expect(screen.getByRole("link", { name: "Open macro research" })).toHaveAttribute("href", "/evidence");
});

it("adds a manual symbol and submits the active symbol through the existing market assistant", async () => {
  askMarketAssistantMock.mockResolvedValue(createAssistantResponse({ symbol: "MSFT" }));
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "AAPL", name: "Apple Inc.", market: "US", is_active: true }],
          }),
        ),
      );
    }
    if (url.endsWith("/dashboard/market-overview?provider=yfinance")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketOverviewPayload())));
    }
    if (url.endsWith("/market-indicators/official-sources/status")) {
      return Promise.resolve(new Response(JSON.stringify(createOfficialSourceStatusPayload())));
    }
    if (url.includes("/recommendations?")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", items: [] })));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  await renderAiResearchPage();

  fireEvent.change(screen.getByLabelText("Manual symbol"), { target: { value: "MSFT" } });
  fireEvent.click(screen.getByRole("button", { name: "Add" }));
  expect(screen.getAllByText("MSFT").length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));

  await waitFor(() => {
    expect(askMarketAssistantMock).toHaveBeenCalledWith({
      scope: "instrument",
      symbol: "MSFT",
      question: expect.stringContaining("Build a research-only summary for MSFT"),
      locale: "en",
      timeframe: "1d",
      start: null,
      end: null,
      provider: "yfinance",
    });
  });
  expect(askMarketAssistantMock.mock.calls[0][0].question).toContain("FRED US macro");
  expect(await screen.findByText("Research-only answer with cited local evidence.")).toBeInTheDocument();
  expect(screen.getByText("Daily bars for AAPL as of 2026-01-02")).toBeInTheDocument();
  expect(screen.getByText("Research only. Not investment advice.")).toBeInTheDocument();
});

it("keeps the AI research desk usable when official source status is unavailable", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "AAPL", name: "Apple Inc.", market: "US", is_active: true }],
          }),
        ),
      );
    }
    if (url.endsWith("/dashboard/market-overview?provider=yfinance")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketOverviewPayload())));
    }
    if (url.endsWith("/market-indicators/official-sources/status")) {
      return Promise.resolve(new Response("unavailable", { status: 503 }));
    }
    if (url.includes("/recommendations?")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", items: [] })));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  await renderAiResearchPage();

  expect(screen.getByRole("heading", { name: "AI Research Desk" })).toBeInTheDocument();
  expect(screen.getByText("Official source readiness could not be loaded.")).toBeInTheDocument();
});
