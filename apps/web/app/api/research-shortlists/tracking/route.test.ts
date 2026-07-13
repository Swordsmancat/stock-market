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

it("proxies outcome tracking queries with no-store semantics", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "no_data", latest: null, history: [] }), {
      status: 200,
      headers: { "content-type": "application/json; charset=utf-8" },
    }),
  );

  const response = await GET(
    new Request(
      "http://localhost/api/research-shortlists/tracking?market=CN&profile_id=balanced_research&limit=10&offset=0",
    ),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    new URL(
      "http://api.test/research-shortlists/tracking?market=CN&profile_id=balanced_research&limit=10&offset=0",
    ),
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json; charset=utf-8");
  expect(response.headers.get("cache-control")).toBe("no-store");
});

it("preserves an upstream tracking failure", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "tracking unavailable" }), {
      status: 503,
      headers: { "content-type": "application/problem+json" },
    }),
  );

  const response = await GET(
    new Request("http://localhost/api/research-shortlists/tracking"),
  );

  expect(response.status).toBe(503);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "tracking unavailable" });
});
