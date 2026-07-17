import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import MarketMoversPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const payload = {
  status: "ok",
  market: "CN",
  direction: "gainers",
  exchange: "all",
  limit: 20,
  trade_date: "2026-07-17",
  previous_trade_date: "2026-07-16",
  provider: "akshare",
  adjustment: "qfq",
  comparable_count: 2,
  eligible_count: 1,
  omitted_count: 0,
  items: [
    {
      rank: 1,
      symbol: "600001",
      name: "Alpha Bank",
      exchange: "SSE",
      close: 12,
      previous_close: 10,
      change: 2,
      change_percent: 20,
      volume: 1000,
      amount: 10000,
      provider: "akshare",
      source: "eastmoney",
      adjustment: "qfq",
    },
  ],
};

it("renders stored movers, filters, provenance, and exact instrument links", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(payload)),
  );

  render(
    await MarketMoversPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByRole("heading", { name: "Market Movers" })).toBeInTheDocument();
  expect(screen.getByText("2026-07-17")).toBeInTheDocument();
  expect(screen.getByText("akshare")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Alpha Bank/ })).toHaveAttribute(
    "href",
    "/instruments/600001?market=CN",
  );
  expect(within(screen.getByRole("group", { name: "Direction" })).getByRole("link", { name: "Gainers" })).toHaveAttribute("aria-current", "page");
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/market-movers?market=CN&direction=gainers&exchange=all&limit=20",
    expect.objectContaining({ cache: "no-store" }),
  );
  expect(fetchMock.mock.calls.every(([, init]) => (init as RequestInit | undefined)?.method !== "POST")).toBe(true);
});

it("uses URL filters and keeps backend failure distinct from empty data", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response("", { status: 503 }),
  );

  render(
    await MarketMoversPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({ direction: "losers", exchange: "BSE", limit: "50" }),
    }),
  );

  expect(screen.getByText("Market movers are unavailable")).toBeInTheDocument();
  expect(fetchMock.mock.calls[0][0]).toContain("direction=losers&exchange=BSE&limit=50");
  expect(within(screen.getByRole("group", { name: "Direction" })).getByRole("link", { name: "Losers" })).toHaveAttribute("aria-current", "page");
});

it("renders an explicit empty stored-data state", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ ...payload, status: "no_data", items: [] })),
  );

  render(
    await MarketMoversPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByText("No comparable stored movers")).toBeInTheDocument();
});
