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

it("fetches instrument bars and derives latest using the backend date-range contract", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-03T12:00:00Z"));

  backendFetchMock
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

  const response = await GET(new Request("http://localhost/api/instruments/AAPL?provider=yfinance&market=CN"), {
    params: Promise.resolve({ symbol: "AAPL" }),
  });

  expect(backendFetchMock).toHaveBeenNthCalledWith(
    1,
    "/market-data/AAPL/bars?timeframe=1d&start=2026-01-04&end=2026-07-03&provider=yfinance&market=CN",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    2,
    "/market-data/AAPL/intraday?date=2026-07-03&timeframe=1m&provider=yfinance",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    3,
    "/market-data/AAPL/depth?depth_levels=5&large_order_threshold_amount=1000000&provider=yfinance",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenCalledWith("/indicators/AAPL", { cache: "no-store" });
  expect(backendFetchMock).toHaveBeenCalledWith("/fundamentals/AAPL", { cache: "no-store" });
  expect(backendFetchMock).toHaveBeenCalledWith("/news/AAPL", { cache: "no-store" });
  expect(backendFetchMock).toHaveBeenCalledWith("/reports/AAPL/daily/latest", { cache: "no-store" });
  expect(backendFetchMock).toHaveBeenCalledWith("/reports/AAPL/daily/history?limit=5", { cache: "no-store" });
  expect(
    backendFetchMock.mock.calls.some(([path]) =>
      String(path).includes("/market-data/AAPL/latest"),
    ),
  ).toBe(false);

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toEqual({
    symbol: "AAPL",
    market: "CN",
    request_symbol: "AAPL",
    provider_symbol_mapped: false,
    latest: {
      status: "ok",
      source: "database",
      item: { timestamp: "2026-07-03", close: 102 },
      no_data_reason: null,
    },
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
    indicators: { symbol: "AAPL", source: "database", indicators: {} },
    fundamentals: { symbol: "AAPL", source: null, item: null },
    news: {
      symbol: "AAPL",
      source: null,
      summary: { latest_sentiment: null, article_count: 0 },
      items: [],
    },
    latest_daily_report: {
      symbol: "AAPL",
      report_type: "stock_daily",
      source: "database",
      items: [],
    },
    daily_report_history: {
      symbol: "AAPL",
      source: "database",
      items: [],
    },
    range: { timeframe: "1d", start: "2026-01-04", end: "2026-07-03" },
  });
});

it("preserves real intraday minute payloads from the backend", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-03T12:00:00Z"));

  const intradayPayload = {
    symbol: "AAPL",
    timeframe: "1m",
    date: "2026-07-03",
    source: "provider",
    provider: "yfinance",
    requested_provider: "yfinance",
    effective_provider: "yfinance",
    status: "ok",
    previous_close: 213.55,
    items: [
      {
        timestamp: "2026-07-03T13:30:00+00:00",
        open: 214.1,
        high: 214.3,
        low: 213.9,
        close: 214.2,
        price: 214.2,
        average_price: null,
        volume: 12000,
        amount: null,
      },
    ],
    availability: {
      status: "ok",
      reason: null,
      is_realtime: false,
      is_delayed: true,
      delay_minutes: null,
    },
  };

  backendFetchMock
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ source: "database", items: [{ timestamp: "2026-07-03", close: 214.2 }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(intradayPayload), {
        status: 200,
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
    intraday: intradayPayload,
  });
});

it("preserves real market-depth payloads from the backend", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-03T12:00:00Z"));

  const marketDepthPayload = {
    symbol: "AAPL",
    source: "provider",
    provider: "fake_depth",
    requested_provider: "akshare",
    effective_provider: "akshare",
    status: "ok",
    as_of: "2026-07-03T13:30:00+00:00",
    is_realtime: false,
    is_delayed: true,
    delay_minutes: 15,
    order_book: {
      status: "ok",
      reason: null,
      as_of: "2026-07-03T13:30:00+00:00",
      depth_levels: 1,
      bids: [{ price: 101.2, volume: 1000, amount: 101200, order_count: 5 }],
      asks: [{ price: 101.3, volume: 800, amount: 81040, order_count: 4 }],
    },
    recent_trades: {
      status: "ok",
      reason: null,
      as_of: "2026-07-03T13:30:00+00:00",
      items: [{ timestamp: "2026-07-03T13:31:00+00:00", side: "buy", price: 101.25, volume: 15000, amount: 1518750 }],
    },
    large_orders: {
      status: "ok",
      reason: null,
      threshold_amount: 1000000,
      threshold_volume: null,
      currency: "CNY",
      as_of: "2026-07-03T13:30:00+00:00",
      items: [{ timestamp: "2026-07-03T13:31:00+00:00", side: "buy", price: 101.25, volume: 15000, amount: 1518750 }],
    },
    fund_flow: {
      status: "ok",
      reason: null,
      as_of: "2026-07-03T13:30:00+00:00",
      currency: "CNY",
      net_inflow: 1234567,
      main_net_inflow: 765432,
      retail_net_inflow: -12345,
      source_definition: "provider-defined verified fund-flow",
    },
    availability: {
      status: "ok",
      reason: "Depth snapshot from fixture provider.",
      capabilities: {
        order_book: true,
        recent_trades: true,
        large_orders: true,
        fund_flow: true,
      },
    },
  };

  backendFetchMock
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ source: "database", items: [{ timestamp: "2026-07-03", close: 101.25 }] }), {
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
      new Response(JSON.stringify(marketDepthPayload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

  const response = await GET(new Request("http://localhost/api/instruments/AAPL?provider=akshare"), {
    params: Promise.resolve({ symbol: "AAPL" }),
  });

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    symbol: "AAPL",
    market_depth: marketDepthPayload,
  });
});

it("maps dashboard index codes to provider symbols before requesting market data", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-03T12:00:00Z"));

  backendFetchMock
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

  expect(backendFetchMock).toHaveBeenNthCalledWith(
    1,
    "/market-data/000001.SS/bars?timeframe=1d&start=2026-01-04&end=2026-07-03&provider=yfinance",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    2,
    "/market-data/000001.SS/intraday?date=2026-07-03&timeframe=1m&provider=yfinance",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    3,
    "/market-data/000001.SS/depth?depth_levels=5&large_order_threshold_amount=1000000&provider=yfinance",
    { cache: "no-store" },
  );

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    symbol: "cn_shanghai_composite",
    request_symbol: "000001.SS",
    provider_symbol_mapped: true,
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
