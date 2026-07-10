import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({
  getBackendApiUrlMock: vi.fn(() => "http://api.test"),
}));

vi.mock("@/lib/backend-api", () => ({
  getBackendApiUrl: getBackendApiUrlMock,
}));

import { GET, POST } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  getBackendApiUrlMock.mockClear();
});

it("proxies stored market daily evidence list queries", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [], summary: { total: 0 } }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await GET(
    new Request("http://localhost/api/market-daily-evidence?limit=12&citable_only=true"),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "http://api.test/market-daily-evidence?limit=12&citable_only=true",
    { method: "GET", cache: "no-store" },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual({ items: [], summary: { total: 0 } });
});

it("proxies today's market daily evidence import without changing the body", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok", inserted: 5, updated: 0, skipped: 0 }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  const body = JSON.stringify({ market: "CN", limit: 20 });

  const response = await POST(
    new Request("http://localhost/api/market-daily-evidence", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith("http://api.test/market-daily-evidence/import", {
    method: "POST",
    body,
    cache: "no-store",
    headers: { "content-type": "application/json" },
  });
  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toMatchObject({ status: "ok", inserted: 5 });
});
