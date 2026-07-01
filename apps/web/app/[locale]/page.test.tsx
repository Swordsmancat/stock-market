import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import HomePage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders stock analysis dashboard data from backend APIs", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
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
    if (url.includes("/reports/AAPL/stock")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            report_type: "stock_daily",
            content_markdown:
              "# AAPL AI 个股报告\n\nMA 119.00, RSI 100.00\n\nApple reports strong growth in services revenue",
            citations: [
              "bars_1d:AAPL:2026-01-02",
              "fundamental_metrics:AAPL:2026-01-02",
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/reports/AAPL/daily/latest")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            report_type: "stock_daily",
            as_of: "2026-01-20",
            content_markdown:
              "# AAPL 每日报告\n\n持久化日报：MA 119.00，Apple reports strong growth in services revenue",
            citations: [
              "technical_indicators:AAPL:2026-01-20T00:00:00+00:00",
              "news_articles:AAPL:https://example.com/aapl-services-growth",
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/reports/AAPL/daily/history?limit=5")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            items: [
              {
                as_of: "2026-01-20",
                content_markdown: "# AAPL 每日报告\n\n最新持久化日报",
              },
              {
                as_of: "2026-01-19",
                content_markdown: "# AAPL 每日报告\n\n上一交易日日报",
              },
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/portfolios/demo")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: "demo",
            source: "database",
            positions: [{ symbol: "AAPL", market_value: 1020 }],
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
            summary: { latest_sentiment: "positive", article_count: 1 },
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
    if (url.endsWith("/task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            task_name: "reports.refresh_daily_watchlist_analysis",
            status: "succeeded",
            duration_ms: 1280,
            result_json: { item_count: 2 },
          }),
        ),
      );
    }
    if (url.includes("/api/ingestion/mock-snapshot")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "ingested",
            market: "US",
            bar_count: 2,
          }),
        ),
      );
    }
    if (url.includes("/api/analysis/refresh")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            status: "refreshed",
            report: { report_type: "stock_daily" },
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await HomePage());

  expect(screen.getByText("Dashboard")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /AAPL Apple Inc./ }))
    .toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getByText("AAPL Latest Price")).toBeInTheDocument();
  expect(screen.getByText("$102.00")).toBeInTheDocument();
  expect(screen.getByText("Technical Indicators")).toBeInTheDocument();
  expect(screen.getByText("Fundamentals")).toBeInTheDocument();
  expect(screen.getByText("Latest News")).toBeInTheDocument();
  expect(
    screen.getByText((content) =>
      content.includes("# AAPL AI 个股报告") &&
      content.includes("MA 119.00, RSI 100.00") &&
      content.includes("Apple reports strong growth in services revenue"),
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("Citations")).toBeInTheDocument();
  expect(screen.getByText("bars_1d:AAPL:2026-01-02")).toBeInTheDocument();
  expect(screen.getByText("fundamental_metrics:AAPL:2026-01-02")).toBeInTheDocument();
  expect(screen.getAllByText("Latest Task Run").length).toBeGreaterThan(0);
  expect(screen.getByText("Portfolio Value")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Trigger Ingestion" }));

  expect(await screen.findByText("✅ US: 2 bars")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/ingestion/mock-snapshot?market=US&start=2026-01-01&end=2026-01-02&provider=mock",
    { method: "POST" },
  );
  fireEvent.click(screen.getByRole("button", { name: "Refresh Analysis" }));

  expect(await screen.findByText("✅ AAPL refreshed")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/analysis/refresh?symbol=AAPL&market=US&start=2026-01-01&end=2026-01-20&ma_window=3&provider=mock",
    { method: "POST" },
  );
  expect(fetchMock).toHaveBeenCalledTimes(12);
});

it("renders the dashboard when optional analysis APIs have no data", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/instruments")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "600519", name: "Kweichow Moutai", market: "CN" }],
          }),
        ),
      );
    }
    if (url.includes("/market-data/600519/bars")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "600519",
            source: "mock",
            items: [{ close: 1666 }],
          }),
        ),
      );
    }
    if (url.includes("/reports/600519/stock")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "600519",
            report_type: "stock_daily",
            content_markdown: "# 600519 AI 个股报告",
            citations: [],
          }),
        ),
      );
    }
    if (url.endsWith("/reports/600519/daily/latest")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.endsWith("/reports/600519/daily/history?limit=5")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.endsWith("/portfolios/demo")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: "demo",
            source: "mock",
            positions: [{ symbol: "AAPL", market_value: 1020 }],
          }),
        ),
      );
    }
    if (url.endsWith("/indicators/600519")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.endsWith("/fundamentals/600519")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "600519",
            source: "mock_fundamentals",
            item: {
              summary: "PE 26.80，营收增速 10.00%，净利率 52.00%，资产负债率 18.00%",
            },
          }),
        ),
      );
    }
    if (url.endsWith("/news/600519")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.endsWith("/task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await HomePage());

  expect(screen.getByText("600519 Latest Price")).toBeInTheDocument();
  expect(screen.getByText("$1666.00")).toBeInTheDocument();
  expect(screen.getByText("No technical indicators available.")).toBeInTheDocument();
  expect(screen.getByText("No news sentiment available.")).toBeInTheDocument();
  expect(screen.getAllByText("Latest Task Run").length).toBeGreaterThan(0);
});
