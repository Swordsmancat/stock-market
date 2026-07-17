import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import StockComparisonPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const okPayload = {
  status: "ok",
  market: "CN",
  symbols: ["000001", "600519"],
  period: "3m",
  requested_count: 2,
  anchor_date: "2026-07-17",
  period_start: "2026-04-15",
  shared_date_count: 3,
  comparable_count: 2,
  missing_symbols: [],
  diagnostics: [],
  search_results: [
    {
      id: "CN-000858",
      symbol: "000858",
      name: "Wuliangye",
      market: "CN",
      exchange: "SZSE",
    },
  ],
  items: [
    {
      id: "CN-000001",
      symbol: "000001",
      name: "Ping An Bank",
      market: "CN",
      exchange: "SZSE",
      status: "ok",
      provider: "akshare",
      adjustment: "qfq",
      first_date: "2026-07-15",
      last_date: "2026-07-17",
      bar_count: 3,
      bars: [
        { timestamp: "2026-07-15", close: 10 },
        { timestamp: "2026-07-16", close: 10.5 },
        { timestamp: "2026-07-17", close: 11 },
      ],
    },
    {
      id: "CN-600519",
      symbol: "600519",
      name: "Kweichow Moutai",
      market: "CN",
      exchange: "SSE",
      status: "ok",
      provider: "akshare",
      adjustment: "qfq",
      first_date: "2026-07-15",
      last_date: "2026-07-17",
      bar_count: 3,
      bars: [
        { timestamp: "2026-07-15", close: 1500 },
        { timestamp: "2026-07-16", close: 1510 },
        { timestamp: "2026-07-17", close: 1530 },
      ],
    },
  ],
};

it("renders a URL-owned stored comparison and issues one GET-only request", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(okPayload)),
  );

  render(
    await StockComparisonPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({
        symbols: "000001,600519",
        q: "liquor",
      }),
    }),
  );

  expect(screen.getByRole("heading", { name: "Stock Comparison" })).toBeInTheDocument();
  expect(screen.getByText("Normalized performance comparison")).toBeInTheDocument();
  expect(screen.getByText("Return comparison")).toBeInTheDocument();
  expect(screen.getByText("Pearson correlation")).toBeInTheDocument();
  expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  expect(screen.getByRole("link", { name: "000001" })).toHaveAttribute(
    "href",
    "/instruments/000001?market=CN",
  );
  expect(screen.getByRole("link", { name: "Remove 000001" })).toHaveAttribute(
    "href",
    "/instruments/compare?symbols=600519&q=liquor",
  );
  expect(screen.getByRole("link", { name: /Add/ })).toHaveAttribute(
    "href",
    "/instruments/compare?symbols=000001%2C600519%2C000858&q=liquor",
  );
  expect(
    within(screen.getByRole("group", { name: "Comparison period" })).getByRole("link", {
      name: "1 year",
    }),
  ).toHaveAttribute(
    "href",
    "/instruments/compare?symbols=000001%2C600519&period=1y&q=liquor",
  );
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/market-comparison?market=CN&period=3m&search_limit=8&symbols=000001%2C600519&q=liquor",
    expect.objectContaining({ cache: "no-store" }),
  );
  expect(
    fetchMock.mock.calls.every(
      ([, init]) => (init as RequestInit | undefined)?.method !== "POST",
    ),
  ).toBe(true);
});

it.each([
  ["empty_selection", "Choose stocks to compare", {}],
  ["insufficient_selection", "Add one more stock", { symbols: "000001" }],
  ["no_data", "No shared stored window", { symbols: "000001,600519" }],
] as const)("renders the %s state distinctly", async (status, expectedTitle, searchParams) => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        ...okPayload,
        status,
        symbols: status === "empty_selection" ? [] : okPayload.symbols,
        requested_count:
          status === "empty_selection"
            ? 0
            : status === "insufficient_selection"
              ? 1
              : 2,
        comparable_count: 0,
        shared_date_count: 0,
        items: [],
        search_results: [],
      }),
    ),
  );

  render(
    await StockComparisonPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve(searchParams),
    }),
  );

  expect(screen.getByText(expectedTitle)).toBeInTheDocument();
});

it("keeps transport failure distinct from an empty stored result", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 503 }));

  render(
    await StockComparisonPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({ symbols: "000001,600519" }),
    }),
  );

  expect(screen.getByText("Stock comparison is unavailable")).toBeInTheDocument();
  expect(screen.queryByText("No shared stored window")).not.toBeInTheDocument();
});
