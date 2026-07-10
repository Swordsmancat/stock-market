import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({
  getBackendApiUrlMock: vi.fn(() => "http://api.test"),
}));

vi.mock("@/lib/backend-api", () => ({ getBackendApiUrl: getBackendApiUrlMock }));

import { GET } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  getBackendApiUrlMock.mockClear();
});

it("proxies universe status query parameters and disables caching", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok", active_instrument_count: 5200 }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await GET(
    new Request("http://localhost/api/stock-selection/universe-status?market=CN&provider=akshare"),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    new URL("http://api.test/stock-selection/universe-status?market=CN&provider=akshare"),
    { cache: "no-store" },
  );
  expect(response.headers.get("cache-control")).toBe("no-store");
});
