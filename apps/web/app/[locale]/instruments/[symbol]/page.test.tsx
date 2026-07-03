import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/components/advanced-candlestick-chart", () => ({
  AdvancedCandlestickChart: ({ symbol }: { symbol: string }) => (
    <div data-testid="advanced-candlestick-chart">Advanced chart for {symbol}</div>
  ),
}));

import InstrumentDetailPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mockInstrumentDetailResponse(items: Array<{ timestamp: string; open: number; high: number; low: number; close: number; volume: number }>) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/api/instruments/AAPL")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            bars: { items },
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });
}

it("renders the enhanced client-side instrument detail view", async () => {
  mockInstrumentDetailResponse([
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
  ]);

  render(await InstrumentDetailPage({ params: Promise.resolve({ symbol: "AAPL", locale: "en" }) }));

  expect(await screen.findByText("AAPL")).toBeInTheDocument();
  expect(screen.getByText("标的详情")).toBeInTheDocument();
  expect(screen.getByText("最新价")).toBeInTheDocument();
  expect(screen.getByText("涨跌额")).toBeInTheDocument();
  expect(screen.getByText("涨跌幅")).toBeInTheDocument();
  expect(screen.getAllByText("102.00").length).toBeGreaterThan(0);
  expect(screen.getByText("+1.00")).toBeInTheDocument();
  expect(screen.getByText("+0.99%")).toBeInTheDocument();
  expect(screen.getByText("K线图")).toBeInTheDocument();
  expect(screen.getByText("交互式价格走势图")).toBeInTheDocument();
  expect(screen.getByTestId("advanced-candlestick-chart")).toHaveTextContent("Advanced chart for AAPL");
});

it("renders an empty K-line state when the detail endpoint has no bars", async () => {
  mockInstrumentDetailResponse([]);

  render(await InstrumentDetailPage({ params: Promise.resolve({ symbol: "AAPL", locale: "en" }) }));

  expect(await screen.findByText("AAPL")).toBeInTheDocument();
  expect(screen.getByText("暂无K线数据")).toBeInTheDocument();
  expect(screen.getAllByText("0.00").length).toBeGreaterThan(0);
});

it("renders an error state when the detail endpoint fails", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/api/instruments/AAPL")) {
      return Promise.resolve(new Response("", { status: 503 }));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await InstrumentDetailPage({ params: Promise.resolve({ symbol: "AAPL", locale: "en" }) }));

  expect(await screen.findByText("加载失败: Failed to fetch instrument data")).toBeInTheDocument();
});
