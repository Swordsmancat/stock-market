import { afterEach, expect, it, vi } from "vitest";

const { backendFetchMock } = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: backendFetchMock,
}));

import { GET } from "./route";

function buildMarketDepthPayload(symbol = "AAPL") {
  return {
    symbol,
    source: "none",
    provider: "yfinance",
    requested_provider: "yfinance",
    effective_provider: "yfinance",
    status: "degraded",
    as_of: null,
    is_realtime: false,
    is_delayed: false,
    delay_minutes: null,
    order_book: {
      status: "degraded",
      reason: "Provider does not support market depth data.",
      as_of: null,
      depth_levels: 5,
      bids: [],
      asks: [],
    },
    recent_trades: {
      status: "degraded",
      reason: "Recent trades are unavailable.",
      as_of: null,
      items: [],
    },
    large_orders: {
      status: "degraded",
      reason: "Large orders are unavailable.",
      threshold_amount: 1000000,
      threshold_volume: null,
      currency: null,
      as_of: null,
      items: [],
    },
    fund_flow: {
      status: "degraded",
      reason: "Fund flow is unavailable.",
      as_of: null,
      currency: null,
      net_inflow: null,
      main_net_inflow: null,
      retail_net_inflow: null,
      source_definition: null,
    },
    availability: {
      status: "degraded",
      reason: "Provider does not support market depth data.",
      capabilities: {
        order_book: false,
        recent_trades: false,
        large_orders: false,
        fund_flow: false,
      },
    },
  };
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  backendFetchMock.mockReset();
});

it("fetches instrument latest and bars using the backend date-range contract", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-03T12:00:00Z"));

  backendFetchMock
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "ok", item: { timestamp: "2026-07-03", close: 102 } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ source: "database", items: [{ timestamp: "2026-07-03", close: 102 }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          symbol: "AAPL",
          timeframe: "1m",
          date: "2026-07-03",
          source: "none",
          status: "degraded",
          previous_close: null,
          items: [],
          availability: { status: "degraded", reason: "Provider does not support intraday data." },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(buildMarketDepthPayload()), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

  const response = await GET(new Request("http://localhost/api/instruments/AAPL?provider=yfinance"), {
    params: Promise.resolve({ symbol: "AAPL" }),
  });

  expect(backendFetchMock).toHaveBeenNthCalledWith(1, "/market-data/AAPL/latest?provider=yfinance", {
    cache: "no-store",
  });
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    2,
    "/market-data/AAPL/bars?timeframe=1d&start=2026-01-04&end=2026-07-03&provider=yfinance",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    3,
    "/market-data/AAPL/intraday?date=2026-07-03&timeframe=1m&provider=yfinance",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    4,
    "/market-data/AAPL/depth?depth_levels=5&large_order_threshold_amount=1000000&provider=yfinance",
    { cache: "no-store" },
  );

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toEqual({
    symbol: "AAPL",
    request_symbol: "AAPL",
    latest: { status: "ok", item: { timestamp: "2026-07-03", close: 102 } },
    bars: { source: "database", items: [{ timestamp: "2026-07-03", close: 102 }] },
    intraday: {
      symbol: "AAPL",
      timeframe: "1m",
      date: "2026-07-03",
      source: "none",
      status: "degraded",
      previous_close: null,
      items: [],
      availability: { status: "degraded", reason: "Provider does not support intraday data." },
    },
    market_depth: buildMarketDepthPayload(),
    range: { timeframe: "1d", start: "2026-01-04", end: "2026-07-03" },
  });
});

it("maps dashboard index codes to provider symbols before requesting market data", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-03T12:00:00Z"));

  backendFetchMock
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "ok", item: { timestamp: "2026-07-03", close: 3450 } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ source: "yfinance", items: [{ timestamp: "2026-07-03", close: 3450 }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "degraded", items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(buildMarketDepthPayload("000001.SS")), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

  const response = await GET(new Request("http://localhost/api/instruments/cn_shanghai_composite"), {
    params: Promise.resolve({ symbol: "cn_shanghai_composite" }),
  });

  expect(backendFetchMock).toHaveBeenNthCalledWith(1, "/market-data/000001.SS/latest?provider=yfinance", {
    cache: "no-store",
  });
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    2,
    "/market-data/000001.SS/bars?timeframe=1d&start=2026-01-04&end=2026-07-03&provider=yfinance",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    3,
    "/market-data/000001.SS/intraday?date=2026-07-03&timeframe=1m&provider=yfinance",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    4,
    "/market-data/000001.SS/depth?depth_levels=5&large_order_threshold_amount=1000000&provider=yfinance",
    { cache: "no-store" },
  );

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    symbol: "cn_shanghai_composite",
    request_symbol: "000001.SS",
    bars: { source: "yfinance", items: [{ timestamp: "2026-07-03", close: 3450 }] },
    intraday: { status: "degraded", items: [] },
    market_depth: { symbol: "000001.SS", status: "degraded" },
  });
});

it("degrades intraday failures without failing the instrument detail response", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-03T12:00:00Z"));

  backendFetchMock
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "ok", item: { timestamp: "2026-07-03", close: 102 } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ source: "database", items: [{ timestamp: "2026-07-03", close: 102 }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "intraday backend unavailable" }), {
        status: 503,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(buildMarketDepthPayload()), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

  const response = await GET(new Request("http://localhost/api/instruments/AAPL?provider=yfinance"), {
    params: Promise.resolve({ symbol: "AAPL" }),
  });

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    symbol: "AAPL",
    latest: { status: "ok", item: { timestamp: "2026-07-03", close: 102 } },
    bars: { source: "database", items: [{ timestamp: "2026-07-03", close: 102 }] },
    intraday: {
      symbol: "AAPL",
      timeframe: "1m",
      date: "2026-07-03",
      status: "degraded",
      items: [],
    },
    market_depth: { symbol: "AAPL", status: "degraded" },
  });
});

it("degrades market depth failures without failing the instrument detail response", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-03T12:00:00Z"));

  backendFetchMock
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "ok", item: { timestamp: "2026-07-03", close: 102 } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ source: "database", items: [{ timestamp: "2026-07-03", close: 102 }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "degraded", items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "market depth backend unavailable" }), {
        status: 503,
        headers: { "content-type": "application/json" },
      }),
    );

  const response = await GET(new Request("http://localhost/api/instruments/AAPL?provider=yfinance"), {
    params: Promise.resolve({ symbol: "AAPL" }),
  });

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    symbol: "AAPL",
    bars: { source: "database", items: [{ timestamp: "2026-07-03", close: 102 }] },
    market_depth: {
      symbol: "AAPL",
      status: "degraded",
      order_book: {
        status: "degraded",
        depth_levels: 5,
        bids: [],
        asks: [],
      },
      large_orders: {
        status: "degraded",
        threshold_amount: 1000000,
        items: [],
      },
    },
  });
});

it("propagates backend bars failures instead of rewriting them as empty data", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-03T12:00:00Z"));

  backendFetchMock
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "ok", item: { timestamp: "2026-07-03", close: 102 } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Missing start/end date range" }), {
        status: 422,
        headers: { "content-type": "application/problem+json" },
      }),
    );

  const response = await GET(new Request("http://localhost/api/instruments/AAPL"), {
    params: Promise.resolve({ symbol: "AAPL" }),
  });

  expect(response.status).toBe(422);
  expect(response.headers.get("content-type")).toContain("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "Missing start/end date range" });
});
