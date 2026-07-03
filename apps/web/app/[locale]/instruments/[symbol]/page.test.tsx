import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/dates", () => ({
  parseInstrumentRange: () => "20d",
  getInstrumentDateRange: () => ({ start: "2026-01-01", end: "2026-01-20" }),
  getDashboardDateRanges: () => ({
    recent: { start: "2026-01-01", end: "2026-01-02" },
    analysis: { start: "2026-01-01", end: "2026-01-20" },
  }),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
  getBackendApiUrl: () => "http://127.0.0.1:8000",
}));

vi.mock("@/lib/platform-settings-store", () => ({
  getPlatformSettings: async () => ({
    market_data_provider: "yfinance",
    llm_provider: "mock",
    llm_api_key: "",
    llm_api_base: "https://api.openai.com/v1",
    akshare_enabled: false,
    tushare_token: "",
    llm_api_key_configured: false,
  }),
}));

vi.mock("@/components/instrument-watchlist-form", () => ({
  InstrumentWatchlistForm: () => <button type="submit">Add to Watchlist</button>,
}));

vi.mock("@/components/instrument-actions", () => ({
  InstrumentQuickActions: () => (
    <div>
      <button type="submit">Add to Watchlist</button>
      <button type="submit">Generate Daily Report</button>
      <button type="submit">Refresh Analysis</button>
    </div>
  ),
}));

import InstrumentDetailPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it("renders instrument detail with market, indicators, fundamentals, news, and report", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-01-22T00:00:00Z"));

  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/instruments")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "AAPL", name: "Apple Inc.", market: "US" }],
          }),
        ),
      );
    }
    if (url.includes("/market-data/AAPL/bars")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "database",
            provider: "yfinance",
            effective_provider: "yfinance",
            status: "ok",
            items: [
              {
                timestamp: "2026-01-19",
                open: 100,
                high: 103,
                low: 99,
                close: 101,
                volume: 1000,
              },
              {
                timestamp: "2026-01-20",
                open: 101,
                high: 104,
                low: 100,
                close: 102,
                volume: 1200,
              },
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/indicators/AAPL")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "database",
            as_of: "2026-01-20T00:00:00+00:00",
            indicators: {
              ma: 119,
              rsi: 100,
              bollinger: { upper: 121, middle: 119, lower: 117 },
              atr: 3,
            },
          }),
        ),
      );
    }
    if (url.endsWith("/fundamentals/AAPL")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "mock_fundamentals",
            item: {
              summary: "PE 28.40，营收增速 8.00%，净利率 24.00%，资产负债率 31.00%",
            },
          }),
        ),
      );
    }
    if (url.endsWith("/news/AAPL")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "database",
            items: [
              {
                title: "Apple reports strong growth in services revenue",
                sentiment: "positive",
                confidence: 0.6,
              },
            ],
          }),
        ),
      );
    }
    if (url.includes("/reports/AAPL/stock")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            content_markdown: "# AAPL AI 个股报告\n\n综合摘要",
            citations: [
              "bars_1d:AAPL:2026-01-20",
              "news_articles:AAPL:https://example.com/aapl-services-growth",
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await InstrumentDetailPage({ params: Promise.resolve({ symbol: "AAPL", locale: "en" }) }));

  expect(screen.getByText("AAPL")).toBeInTheDocument();
  expect(screen.getByText("Apple Inc.")).toBeInTheDocument();
  expect(screen.getByText("US")).toBeInTheDocument();
  expect(screen.getAllByText("$102.00").length).toBeGreaterThan(0);
  expect(screen.getByText("Daily Bar Summary")).toBeInTheDocument();
  expect(screen.getByText("Daily movement")).toBeInTheDocument();
  expect(screen.getByText("Up: +1.00 (+0.99%)")).toBeInTheDocument();
  expect(screen.getByText("Direction is shown with signs and labels, not color alone.")).toBeInTheDocument();
  expect(screen.getByText("Latest volume")).toBeInTheDocument();
  expect(screen.getByText("Source: database")).toBeInTheDocument();
  expect(screen.getByText("Provider: yfinance")).toBeInTheDocument();
  expect(screen.getByText("Fresh")).toBeInTheDocument();
  expect(screen.getByText("2 daily bars")).toBeInTheDocument();
  expect(screen.getByText("Recent OHLCV")).toBeInTheDocument();
  expect(screen.getAllByText("1/20/2026").length).toBeGreaterThan(0);
  expect(screen.getAllByText("102.00").length).toBeGreaterThan(0);
  expect(screen.getAllByText("1,200").length).toBeGreaterThan(0);
  expect(screen.getByText("Price History")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Candles" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "MA(20)" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "BOLL" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "RSI" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Volume" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Technical" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Fundamentals" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "News" })).toBeInTheDocument();
  expect(
    screen.getByText((content) =>
      content.includes("# AAPL AI 个股报告") && content.includes("综合摘要"),
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("bars_1d:AAPL:2026-01-20")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "news_articles:AAPL:https://example.com/aapl-services-growth" }))
    .toHaveAttribute("href", "https://example.com/aapl-services-growth");
});

it("renders actionable empty states when the bars endpoint returns no data", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/instruments")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "AAPL", name: "Apple Inc.", market: "US" }],
          }),
        ),
      );
    }
    if (url.includes("/market-data/AAPL/bars")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "yfinance",
            provider: "yfinance",
            effective_provider: "yfinance",
            status: "no_data",
            no_data_reason: "No daily bars were available for the requested symbol/date range.",
            items: [],
          }),
        ),
      );
    }
    if (url.includes("/reports/AAPL/stock")) {
      return Promise.resolve(new Response(JSON.stringify({ content_markdown: "", citations: [] })));
    }
    if (url.endsWith("/indicators/AAPL")) {
      return Promise.resolve(new Response(JSON.stringify({ source: "unavailable", indicators: {} })));
    }
    if (url.endsWith("/fundamentals/AAPL")) {
      return Promise.resolve(new Response(JSON.stringify({ source: "unavailable", item: null })));
    }
    if (url.endsWith("/news/AAPL")) {
      return Promise.resolve(new Response(JSON.stringify({ source: "unavailable", items: [] })));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await InstrumentDetailPage({ params: Promise.resolve({ symbol: "AAPL", locale: "en" }) }));

  expect(screen.getByText("Daily Bar Summary")).toBeInTheDocument();
  expect(screen.getByText("No data")).toBeInTheDocument();
  expect(screen.getAllByText("No daily bars available.").length).toBeGreaterThan(0);
  expect(
    screen.getAllByText("Run single-symbol daily-bar ingestion or verify the active provider settings.").length,
  ).toBeGreaterThan(0);
});

it("renders actionable error states when daily bars fail to load", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/instruments")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "AAPL", name: "Apple Inc.", market: "US" }],
          }),
        ),
      );
    }
    if (url.includes("/market-data/AAPL/bars")) {
      return Promise.resolve(new Response("", { status: 503 }));
    }
    if (url.includes("/reports/AAPL/stock")) {
      return Promise.resolve(new Response(JSON.stringify({ content_markdown: "", citations: [] })));
    }
    if (url.endsWith("/indicators/AAPL")) {
      return Promise.resolve(new Response(JSON.stringify({ source: "unavailable", indicators: {} })));
    }
    if (url.endsWith("/fundamentals/AAPL")) {
      return Promise.resolve(new Response(JSON.stringify({ source: "unavailable", item: null })));
    }
    if (url.endsWith("/news/AAPL")) {
      return Promise.resolve(new Response(JSON.stringify({ source: "unavailable", items: [] })));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await InstrumentDetailPage({ params: Promise.resolve({ symbol: "AAPL", locale: "en" }) }));

  expect(screen.getAllByText("Could not load daily bars.").length).toBeGreaterThan(0);
  expect(
    screen.getAllByText("Check provider settings or task-run diagnostics, then retry ingestion.").length,
  ).toBeGreaterThan(0);
});
