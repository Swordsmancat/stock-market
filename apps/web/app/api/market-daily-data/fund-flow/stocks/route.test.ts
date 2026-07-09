import { afterEach, expect, it, vi } from "vitest";

const { backendFetchMock } = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: backendFetchMock,
}));

import { GET } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  backendFetchMock.mockReset();
});

it("proxies normalized stock fund-flow query to the backend", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "ok",
        data_mode: "delayed",
        source: "fake_stock_fund_flow",
        provider: "akshare",
        count: 1,
        items: [{ symbol: "600519", rank: 1 }],
      }),
    ),
  );

  const response = await GET(
    new Request(
      "http://localhost/api/market-daily-data/fund-flow/stocks?market=cn&window=5d&limit=999&provider=akshare",
    ),
  );

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/market-daily-data/fund-flow/stocks?market=CN&window=5d&limit=100&provider=akshare",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    status: "ok",
    provider: "akshare",
    count: 1,
  });
});

it("defaults invalid stock fund-flow params before forwarding", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(JSON.stringify({ status: "degraded", data_mode: "none", count: 0, items: [] })),
  );

  const response = await GET(
    new Request("http://localhost/api/market-daily-data/fund-flow/stocks?window=bad&limit=abc"),
  );

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/market-daily-data/fund-flow/stocks?market=CN&window=today&limit=20",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
});

it("returns a normalized unavailable payload when stock fund-flow backend fails", async () => {
  backendFetchMock.mockResolvedValue(new Response("", { status: 503 }));

  const response = await GET(
    new Request("http://localhost/api/market-daily-data/fund-flow/stocks?limit=5"),
  );

  expect(response.status).toBe(502);
  await expect(response.json()).resolves.toEqual({
    status: "unavailable",
    data_mode: "none",
    source: "backend_proxy",
    message: "Failed to fetch stock fund-flow data",
    count: 0,
    items: [],
  });
});
