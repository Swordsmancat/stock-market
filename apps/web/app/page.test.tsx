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

  expect(screen.getByText("股票分析平台")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "US - AAPL - Apple Inc." }))
    .toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getByText("AAPL 最新收盘价：102，来源：database")).toBeInTheDocument();
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
      content.includes("# AAPL AI 个股报告") &&
      content.includes("MA 119.00, RSI 100.00") &&
      content.includes("Apple reports strong growth in services revenue"),
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("报告引用")).toBeInTheDocument();
  expect(screen.getByText("bars_1d:AAPL:2026-01-02")).toBeInTheDocument();
  expect(screen.getByText("fundamental_metrics:AAPL:2026-01-02")).toBeInTheDocument();
  expect(screen.getByText("最新日报日期：2026-01-20")).toBeInTheDocument();
  expect(
    screen.getByText((content) =>
      content.includes("# AAPL 每日报告") && content.includes("持久化日报：MA 119.00"),
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("日报引用")).toBeInTheDocument();
  expect(screen.getByText("technical_indicators:AAPL:2026-01-20T00:00:00+00:00")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "news_articles:AAPL:https://example.com/aapl-services-growth" }))
    .toHaveAttribute("href", "https://example.com/aapl-services-growth");
  expect(screen.getByText("历史日报：2026-01-20")).toBeInTheDocument();
  expect(screen.getByText("历史日报：2026-01-19")).toBeInTheDocument();
  expect(screen.getByText("自动任务状态")).toBeInTheDocument();
  expect(screen.getByText("最近日报调度：succeeded，处理股票数：2，耗时：1280ms")).toBeInTheDocument();
  expect(screen.getByText("模拟组合市值：1020，来源：database")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "触发行情采集" }));

  expect(await screen.findByText("采集完成：US，2 条行情写入数据库")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/ingestion/mock-snapshot?market=US&start=2026-01-01&end=2026-01-02",
    { method: "POST" },
  );
  fireEvent.click(screen.getByRole("button", { name: "刷新股票分析" }));

  expect(await screen.findByText("分析刷新完成：AAPL，报告已生成")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/analysis/refresh?symbol=AAPL&market=US&start=2026-01-01&end=2026-01-20&ma_window=3",
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

  expect(screen.getByText("CN - 600519 - Kweichow Moutai")).toBeInTheDocument();
  expect(screen.getByText("600519 最新收盘价：1666，来源：mock")).toBeInTheDocument();
  expect(screen.getByText("暂无技术指标数据，来源：unavailable")).toBeInTheDocument();
  expect(screen.getByText("暂无新闻舆情数据，来源：unavailable")).toBeInTheDocument();
  expect(screen.getByText("暂无持久化每日报告")).toBeInTheDocument();
  expect(screen.getByText("最近日报调度：unknown，处理股票数：0，耗时：0ms")).toBeInTheDocument();
});
