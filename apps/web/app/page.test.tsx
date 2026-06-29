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
            content_markdown: "# AAPL AI 个股报告",
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
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await HomePage());

  expect(screen.getByText("股票分析平台")).toBeInTheDocument();
  expect(screen.getByText("US - AAPL - Apple Inc.")).toBeInTheDocument();
  expect(screen.getByText("AAPL 最新收盘价：102，来源：database")).toBeInTheDocument();
  expect(screen.getByText("MA：119，RSI：100，来源：database")).toBeInTheDocument();
  expect(screen.getByText("# AAPL AI 个股报告")).toBeInTheDocument();
  expect(screen.getByText("模拟组合市值：1020，来源：database")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "触发行情采集" }));

  expect(await screen.findByText("采集完成：US，2 条行情写入数据库")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/ingestion/mock-snapshot?market=US&start=2026-01-01&end=2026-01-02",
    { method: "POST" },
  );
  expect(fetchMock).toHaveBeenCalledTimes(6);
});
