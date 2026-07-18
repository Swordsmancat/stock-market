import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/components/advanced-candlestick-chart", () => ({
  AdvancedCandlestickChart: ({ data, symbol }: { data: unknown[]; symbol: string }) => <div data-testid="kline-chart">{symbol}:{data.length}</div>,
}));

import InstrumentKlinePage from "./page";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const readyPayload = {
  status: "ready", source: "database", total: 1, limit: 20, offset: 0, has_more: false,
  query: {}, data_mode: "stored", research_signal_only: true, safety: { no_provider_request: true }, diagnostics: [],
  catalog: [{
    id: "CN-510300", symbol: "510300", name: "CSI 300 ETF", market: "CN", exchange: "SSE",
    asset_type: "etf", currency: "CNY", stored_bar_count: 2, has_series: true,
    latest_bar: { timestamp: "2026-07-17", close: 4.2, provider: "akshare", source: "eastmoney", adjustment: "qfq" },
  }],
  selected: { id: "CN-510300", symbol: "510300", name: "CSI 300 ETF", market: "CN", exchange: "SSE", asset_type: "etf", currency: "CNY" },
  series: {
    provider: "akshare", adjustment: "qfq", anchor_date: "2026-07-17", period_start: "2026-04-15",
    first_date: "2026-07-16", last_date: "2026-07-17", bar_count: 2, sources: [{ source: "eastmoney", bar_count: 2 }],
    items: [
      { timestamp: "2026-07-16", open: 4, high: 4.1, low: 3.9, close: 4.05, volume: 100 },
      { timestamp: "2026-07-17", open: 4.1, high: 4.3, low: 4, close: 4.2, volume: 120 },
    ],
  },
};

it("renders a selected stored ETF series with one GET-only request", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(readyPayload)));
  render(await InstrumentKlinePage({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({ symbol: "510300", market: "CN" }) }));

  expect(screen.getByRole("heading", { name: "K-line Workspace" })).toBeInTheDocument();
  expect(screen.getAllByText("ETF").length).toBeGreaterThan(0);
  expect(screen.getByTestId("kline-chart")).toHaveTextContent("CN:510300:2");
  expect(screen.getByRole("link", { name: /Open details/ })).toHaveAttribute("href", "/instruments/510300?market=CN");
  expect(within(screen.getByRole("group", { name: "Period" })).getByRole("link", { name: "1 year" })).toHaveAttribute("href", "/instruments/kline?symbol=510300&market=CN&period=1y");
  expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/instrument-kline?period=3m&limit=20&offset=0&symbol=510300&market=CN", expect.objectContaining({ cache: "no-store" }));
  expect(fetchMock.mock.calls.every(([, init]) => (init as RequestInit | undefined)?.method !== "POST")).toBe(true);
});

it.each([
  ["empty", "Choose an instrument"],
  ["not_found", "Instrument not found"],
  ["no_data", "No stored K-line data"],
] as const)("renders the %s state distinctly", async (status, title) => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ...readyPayload, status, selected: status === "no_data" ? readyPayload.selected : null, series: null })));
  render(await InstrumentKlinePage({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve(status === "empty" ? {} : { symbol: "510300", market: "CN" }) }));
  expect(screen.getByText(title)).toBeInTheDocument();
});

it("distinguishes an uncollected asset catalog from a search miss or selection prompt", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
    ...readyPayload,
    status: "empty",
    total: 0,
    query: { asset_type: "etf" },
    catalog: [],
    selected: null,
    series: null,
  })));

  render(await InstrumentKlinePage({
    params: Promise.resolve({ locale: "en" }),
    searchParams: Promise.resolve({ asset_type: "etf" }),
  }));

  expect(screen.getAllByText("No stored ETF instruments").length).toBeGreaterThan(0);
  expect(screen.getByRole("link", { name: "Data storage" })).toHaveAttribute("href", "/storage");
  expect(screen.getByRole("link", { name: "Crawler monitor" })).toHaveAttribute("href", "/crawler-monitor");
  expect(screen.queryByText("Try another symbol, name, or asset type.")).not.toBeInTheDocument();
  expect(screen.queryByText("Choose an instrument")).not.toBeInTheDocument();
});
