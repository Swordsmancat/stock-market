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

it("proxies hot-sector degraded mock payloads from the backend", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "degraded",
        data_mode: "mock",
        source: "static_sector_fixture",
        message: "Static mock sector data; not live market data.",
        count: 1,
        items: [{ name: "新能源汽车" }],
      }),
    ),
  );

  const response = await GET(new Request("http://localhost/api/hot-sectors?limit=1"));

  expect(backendFetchMock).toHaveBeenCalledWith("/sectors/hot?limit=1", { cache: "no-store" });
  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    status: "degraded",
    data_mode: "mock",
    source: "static_sector_fixture",
    count: 1,
  });
});

it("passes normalized limit, provider, sector type, and window query to the backend", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "ok",
        data_mode: "delayed",
        source: "akshare_sector_fund_flow_rank",
        provider: "akshare",
        as_of: "2026-07-04T09:30:00+00:00",
        is_delayed: true,
        delay_minutes: 15,
        count: 0,
        items: [],
      }),
    ),
  );

  const response = await GET(
    new Request(
      "http://localhost/api/hot-sectors?limit=999&provider=akshare&sector_type=concept&window=5d",
    ),
  );

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/sectors/hot?limit=10&provider=akshare&sector_type=concept&window=5d",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({
    status: "ok",
    data_mode: "delayed",
    provider: "akshare",
    delay_minutes: 15,
  });
});

it("defaults invalid limits before forwarding to the backend", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(JSON.stringify({ status: "degraded", data_mode: "mock", count: 0, items: [] })),
  );

  const response = await GET(new Request("http://localhost/api/hot-sectors?limit=abc"));

  expect(backendFetchMock).toHaveBeenCalledWith("/sectors/hot?limit=5", { cache: "no-store" });
  expect(response.status).toBe(200);
});

it("returns a normalized unavailable payload when the backend fails", async () => {
  backendFetchMock.mockResolvedValue(new Response("", { status: 503 }));

  const response = await GET(new Request("http://localhost/api/hot-sectors?limit=5"));

  expect(response.status).toBe(502);
  await expect(response.json()).resolves.toEqual({
    status: "unavailable",
    data_mode: "none",
    source: "backend_proxy",
    message: "Failed to fetch hot sectors",
    count: 0,
    items: [],
  });
});

it("returns a normalized unavailable payload when backend fetch rejects", async () => {
  backendFetchMock.mockRejectedValue(new Error("network down"));

  const response = await GET(new Request("http://localhost/api/hot-sectors?limit=5"));

  expect(response.status).toBe(502);
  await expect(response.json()).resolves.toEqual({
    status: "unavailable",
    data_mode: "none",
    source: "backend_proxy",
    message: "Internal server error",
    count: 0,
    items: [],
  });
});
