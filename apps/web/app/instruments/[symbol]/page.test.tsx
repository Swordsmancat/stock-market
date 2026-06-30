import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

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
            items: [{ close: 102 }],
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
            indicators: { ma: 119, rsi: 100 },
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

  render(await InstrumentDetailPage({ params: Promise.resolve({ symbol: "AAPL" }) }));

  expect(screen.getByText("AAPL 个股详情")).toBeInTheDocument();
  expect(screen.getByText("US - AAPL - Apple Inc.")).toBeInTheDocument();
  expect(screen.getByText("最新收盘价：102，来源：database")).toBeInTheDocument();
  expect(screen.getByText("MA：119，RSI：100，来源：database")).toBeInTheDocument();
  expect(
    screen.getByText(
      "PE 28.40，营收增速 8.00%，净利率 24.00%，资产负债率 31.00%，来源：mock_fundamentals",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText("新闻：Apple reports strong growth in services revenue，情绪：positive，置信度：0.6"),
  ).toBeInTheDocument();
  expect(
    screen.getByText((content) =>
      content.includes("# AAPL AI 个股报告") && content.includes("综合摘要"),
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("bars_1d:AAPL:2026-01-20")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "news_articles:AAPL:https://example.com/aapl-services-growth" }))
    .toHaveAttribute("href", "https://example.com/aapl-services-growth");
});
