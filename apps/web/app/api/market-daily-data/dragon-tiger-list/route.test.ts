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

it("proxies normalized Dragon Tiger List query to the backend", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "ok",
        data_mode: "delayed",
        source: "fake_dragon_tiger_list",
        provider: "akshare",
        trade_date: "2026-07-09",
        count: 1,
        items: [{ symbol: "600519", rank: 1 }],
      }),
    ),
  );

  const response = await GET(
    new Request(
      "http://localhost/api/market-daily-data/dragon-tiger-list?market=cn&date=2026-07-09&limit=999&provider=akshare",
    ),
  );

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/market-daily-data/dragon-tiger-list?market=CN&limit=100&date=2026-07-09&provider=akshare",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    status: "ok",
    provider: "akshare",
    trade_date: "2026-07-09",
  });
});

it("defaults invalid Dragon Tiger List params before forwarding", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(JSON.stringify({ status: "degraded", data_mode: "none", count: 0, items: [] })),
  );

  const response = await GET(
    new Request("http://localhost/api/market-daily-data/dragon-tiger-list?limit=abc"),
  );

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/market-daily-data/dragon-tiger-list?market=CN&limit=50",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
});

it("returns a normalized unavailable payload when Dragon Tiger List backend fails", async () => {
  backendFetchMock.mockResolvedValue(new Response("", { status: 503 }));

  const response = await GET(
    new Request("http://localhost/api/market-daily-data/dragon-tiger-list?limit=5"),
  );

  expect(response.status).toBe(502);
  await expect(response.json()).resolves.toEqual({
    status: "unavailable",
    data_mode: "none",
    source: "backend_proxy",
    message: "Failed to fetch Dragon Tiger List data",
    count: 0,
    items: [],
  });
});
