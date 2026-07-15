import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

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
    tushare_token_configured: false,
    market_data_provider_capabilities: [],
  }),
}));

import InstrumentsPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it("renders instruments with latest daily-bar source and freshness", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-01-22T00:00:00Z"));

  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/instruments?limit=25&offset=0") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "database",
            items: [
              {
                symbol: "AAPL",
                name: "Apple Inc.",
                market: "US",
                exchange: "NASDAQ",
                asset_type: "stock",
                currency: "USD",
                source: "database",
              },
              {
                symbol: "MSFT",
                name: "Microsoft Corp.",
                market: "US",
                exchange: "NASDAQ",
                asset_type: "stock",
                currency: "USD",
                source: "database",
              },
            ],
            total: 2,
            limit: 25,
            offset: 0,
            has_more: false,
          }),
        ),
      );
    }
    if (url.includes("/market-data/AAPL/latest")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "database",
            provider: "yfinance",
            effective_provider: "yfinance",
            status: "ok",
            item: {
              timestamp: "2026-01-21T00:00:00+00:00",
              close: 102.15,
            },
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
              { timestamp: "2026-01-19", close: 100 },
              { timestamp: "2026-01-20", close: 101 },
              { timestamp: "2026-01-21", close: 102.15 },
            ],
          }),
        ),
      );
    }
    if (url.includes("/market-data/MSFT/latest")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "MSFT",
            source: "yfinance",
            provider: "yfinance",
            effective_provider: "yfinance",
            status: "no_data",
            no_data_reason: "No daily bars were available for the requested symbol/date range.",
            item: null,
          }),
        ),
      );
    }
    if (url.includes("/market-data/MSFT/bars")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "MSFT",
            source: "database",
            items: [
              { timestamp: "2026-01-19", close: 200 },
              { timestamp: "2026-01-20", close: 198 },
              { timestamp: "2026-01-21", close: 199 },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await InstrumentsPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByRole("heading", { name: "Instruments" })).toBeInTheDocument();
  expect(screen.getByText("Instrument source: database")).toBeInTheDocument();
  expect(screen.getByText("Active provider: yfinance")).toBeInTheDocument();
  expect(screen.getByText("Visible daily-bar health")).toBeInTheDocument();
  expect(screen.getByText("Latest daily-bar health for 2 of 2 instruments using yfinance.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "AAPL" })).toHaveAttribute(
    "href",
    "/instruments/AAPL?market=US",
  );
  expect(screen.getAllByText("Apple Inc.").length).toBeGreaterThan(0);
  expect(screen.getByText("$102.15")).toBeInTheDocument();
  expect(screen.getByText("Source: database")).toBeInTheDocument();
  expect(screen.getAllByText("Provider: yfinance").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Fresh").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Microsoft Corp.").length).toBeGreaterThan(0);
  expect(screen.getByText("No latest daily bar.")).toBeInTheDocument();
  expect(screen.getAllByText("No data").length).toBeGreaterThan(0);
  expect(screen.getAllByRole("link", { name: /Reports/ })[0]).toHaveAttribute("href", "/reports?symbol=AAPL");
  expect(screen.getByText("Comparison analysis")).toBeInTheDocument();
  expect(screen.getByText("Return comparison")).toBeInTheDocument();
  expect(screen.getByText("Pearson correlation")).toBeInTheDocument();
  expect(screen.getByText("Page 1 · showing 2 of 2")).toBeInTheDocument();
});

it("requests a bounded page and preserves filters in pagination links", async () => {
  const fetchedUrls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    fetchedUrls.push(url);
    if (url === "/instruments?q=bank&market=CN&limit=25&offset=25") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "database",
            items: [
              {
                symbol: "600000",
                name: "Shanghai Pudong Development Bank",
                market: "CN",
                exchange: "SSE",
                asset_type: "stock",
                currency: "CNY",
                source: "database",
              },
            ],
            total: 76,
            limit: 25,
            offset: 25,
            has_more: true,
          }),
        ),
      );
    }
    if (url.includes("/market-data/600000/latest")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "600000",
            source: "database",
            provider: "yfinance",
            effective_provider: "yfinance",
            status: "ok",
            item: { timestamp: "2026-01-21", close: 10.5 },
          }),
        ),
      );
    }
    if (url.includes("/market-data/600000/bars")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "600000",
            source: "database",
            items: [{ timestamp: "2026-01-21", close: 10.5 }],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await InstrumentsPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({ q: "bank", market: "CN", page: "2" }),
    }),
  );

  expect(fetchedUrls[0]).toBe(
    "/instruments?q=bank&market=CN&limit=25&offset=25",
  );
  expect(screen.getByText("Page 2 · showing 1 of 76")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Previous" })).toHaveAttribute(
    "href",
    "/instruments?q=bank&market=CN",
  );
  expect(screen.getByRole("link", { name: "Next" })).toHaveAttribute(
    "href",
    "/instruments?q=bank&market=CN&page=3",
  );
});

it("renders an actionable empty state when the instrument list is empty", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/instruments?limit=25&offset=0") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "seed",
            items: [],
            total: 0,
            limit: 25,
            offset: 0,
            has_more: false,
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await InstrumentsPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByText("No instruments yet.")).toBeInTheDocument();
  expect(
    screen.getByText("Configure provider settings or run single-symbol daily-bar ingestion to populate this page."),
  ).toBeInTheDocument();
});

it("distinguishes an empty filtered result from an unavailable instrument catalog", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/instruments?q=missing&market=CN&limit=25&offset=0") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "database",
            items: [],
            total: 0,
            limit: 25,
            offset: 0,
            has_more: false,
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await InstrumentsPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({ q: "missing", market: "CN" }),
    }),
  );

  expect(screen.getByText("No matching instruments.")).toBeInTheDocument();
  expect(
    screen.getByText("Try another symbol or name, or clear the current filters."),
  ).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Reset" })).not.toHaveLength(0);
  expect(screen.queryByText("No instruments yet.")).not.toBeInTheDocument();
});

it("renders an error state when instruments cannot be loaded", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/instruments?limit=25&offset=0") {
      return Promise.resolve(new Response("", { status: 503 }));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await InstrumentsPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByText("Could not load instruments.")).toBeInTheDocument();
  expect(screen.getByText("Check that the API is running, then refresh this page.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Provider settings/ })).toHaveAttribute("href", "/settings");
});
