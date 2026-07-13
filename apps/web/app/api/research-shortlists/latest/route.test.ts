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

it("proxies the latest shortlist query with no-store semantics", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "no_data", run: null, items: [] }), {
      status: 200,
      headers: { "content-type": "application/json; charset=utf-8" },
    }),
  );

  const response = await GET(
    new Request(
      "http://localhost/api/research-shortlists/latest?market=CN&profile_id=balanced_research",
    ),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    new URL(
      "http://api.test/research-shortlists/latest?market=CN&profile_id=balanced_research",
    ),
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json; charset=utf-8");
  expect(response.headers.get("cache-control")).toBe("no-store");
});

it("preserves an upstream failure status and body", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "backend unavailable" }), {
      status: 503,
      headers: { "content-type": "application/problem+json" },
    }),
  );

  const response = await GET(new Request("http://localhost/api/research-shortlists/latest"));

  expect(response.status).toBe(503);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  expect(await response.json()).toEqual({ detail: "backend unavailable" });
});
