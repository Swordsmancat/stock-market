import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
}));

import InstrumentsPage from "./page";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function catalogPayload(overrides: Record<string, unknown> = {}) {
  return {
    status: "empty", source: "database", total: 2, limit: 25, offset: 0, has_more: false,
    selected: null, series: null, diagnostics: [],
    catalog: [
      {
        id: "CN-600519", symbol: "600519", name: "Kweichow Moutai", market: "CN", exchange: "SSE",
        asset_type: "stock", currency: "CNY", stored_bar_count: 400, has_series: true,
        latest_bar: { timestamp: "2026-07-17", close: 1500, provider: "akshare", source: "eastmoney", adjustment: "qfq" },
      },
      {
        id: "CN-510300", symbol: "510300", name: "CSI 300 ETF", market: "CN", exchange: "SSE",
        asset_type: "etf", currency: "CNY", stored_bar_count: 0, has_series: false, latest_bar: null,
      },
    ],
    ...overrides,
  };
}

it("renders the shared stored catalog without provider-capable fan-out", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(catalogPayload())));
  render(await InstrumentsPage({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({}) }));

  expect(screen.getByRole("heading", { name: "Instruments" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "K-line workspace" })).toHaveAttribute("href", "/instruments/kline");
  expect(screen.getByRole("link", { name: "600519" })).toHaveAttribute("href", "/instruments/600519?market=CN");
  expect(screen.getAllByRole("link", { name: "K-line" })[0]).toHaveAttribute("href", "/instruments/kline?asset_type=stock&symbol=600519&market=CN");
  expect(screen.getByText(/1,500\.00/)).toBeInTheDocument();
  expect(screen.getByText("K-line available")).toBeInTheDocument();
  expect(screen.getByText("No K-line")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledWith("/instrument-kline?period=3m&limit=25&offset=0", { cache: "no-store" });
  expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/market-data/"))).toBe(false);
});

it("preserves search and asset type in bounded pagination", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(catalogPayload({ total: 76, offset: 25, has_more: true, catalog: [catalogPayload().catalog[1]] }))));
  render(await InstrumentsPage({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({ q: "300", asset_type: "etf", page: "2" }) }));

  expect(fetchMock).toHaveBeenCalledWith("/instrument-kline?period=3m&limit=25&offset=25&q=300&asset_type=etf", { cache: "no-store" });
  expect(screen.getByRole("link", { name: "Previous" })).toHaveAttribute("href", "/instruments?q=300&asset_type=etf");
  expect(screen.getByRole("link", { name: "Next" })).toHaveAttribute("href", "/instruments?q=300&asset_type=etf&page=3");
});

it("distinguishes an empty filtered catalog", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(catalogPayload({ total: 0, catalog: [] }))));
  render(await InstrumentsPage({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({ q: "missing" }) }));
  expect(screen.getByText("No matching instruments.")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Reset" }).length).toBeGreaterThan(0);
});

it("renders transport failure separately from an empty catalog", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 503 }));
  render(await InstrumentsPage({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({}) }));
  expect(screen.getByText("Could not load instruments.")).toBeInTheDocument();
  expect(screen.queryByText("No instruments yet.")).not.toBeInTheDocument();
});
