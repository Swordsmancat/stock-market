import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { fetchInstrumentDetailPayloadMock } = vi.hoisted(() => ({
  fetchInstrumentDetailPayloadMock: vi.fn(),
}));

vi.mock("@/components/advanced-candlestick-chart", () => ({
  AdvancedCandlestickChart: ({ symbol }: { symbol: string }) => (
    <div data-testid="advanced-candlestick-chart">Advanced chart for {symbol}</div>
  ),
}));

vi.mock("@/lib/instrument-detail", () => ({
  fetchInstrumentDetailPayload: fetchInstrumentDetailPayloadMock,
  normalizeInstrumentDetailProvider: (providerName: string | null | undefined) =>
    providerName?.trim().toLowerCase() || "yfinance",
}));

import InstrumentDetailPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  fetchInstrumentDetailPayloadMock.mockReset();
});

function mockInstrumentDetailResponse(
  items: Array<{ timestamp: string; open: number; high: number; low: number; close: number; volume: number }>,
  latestClose?: number,
) {
  fetchInstrumentDetailPayloadMock.mockResolvedValue({
    status: "loaded",
    payload: {
      symbol: "AAPL",
      request_symbol: "AAPL",
      latest: latestClose === undefined
        ? { status: "unavailable", item: null }
        : { status: "ok", item: { timestamp: "2026-01-20", close: latestClose } },
      bars: { items },
      range: { timeframe: "1d", start: "2026-01-01", end: "2026-01-20" },
    },
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

it("renders latest price even when the detail endpoint has no bars", async () => {
  mockInstrumentDetailResponse([], 105);

  render(await InstrumentDetailPage({ params: Promise.resolve({ symbol: "AAPL", locale: "en" }) }));

  expect(await screen.findByText("AAPL")).toBeInTheDocument();
  expect(screen.getByText("暂无K线数据")).toBeInTheDocument();
  expect(screen.getByText("105.00")).toBeInTheDocument();
});

it("renders an error state when the detail endpoint fails", async () => {
  fetchInstrumentDetailPayloadMock.mockResolvedValue({
    status: "failed",
    responseStatus: 503,
    body: JSON.stringify({ detail: "Instrument service unavailable" }),
    headers: { "content-type": "application/json" },
  });

  render(await InstrumentDetailPage({ params: Promise.resolve({ symbol: "AAPL", locale: "en" }) }));

  expect(await screen.findByText("加载失败: Failed to fetch instrument data")).toBeInTheDocument();
});
