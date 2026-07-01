import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/dates", () => ({
  parseInstrumentRange: () => "20d",
  getInstrumentDateRange: () => ({ start: "2026-01-01", end: "2026-01-20" }),
}));

import InstrumentDetailPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders instrument detail with market, indicators, fundamentals, news, and report", async () => {
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
  expect(screen.getByText("$102.00")).toBeInTheDocument();
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
