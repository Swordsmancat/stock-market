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
