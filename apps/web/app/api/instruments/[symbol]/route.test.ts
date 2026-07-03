import { afterEach, expect, it, vi } from "vitest";

const { backendFetchMock } = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: backendFetchMock,
}));

import { GET } from "./route";

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

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toEqual({
    symbol: "AAPL",
    request_symbol: "AAPL",
    latest: { status: "ok", item: { timestamp: "2026-07-03", close: 102 } },
    bars: { source: "database", items: [{ timestamp: "2026-07-03", close: 102 }] },
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

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    symbol: "cn_shanghai_composite",
    request_symbol: "000001.SS",
    bars: { source: "yfinance", items: [{ timestamp: "2026-07-03", close: 3450 }] },
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
