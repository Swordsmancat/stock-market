import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({
  getBackendApiUrlMock: vi.fn(() => "http://api.test"),
}));

vi.mock("@/lib/backend-api", () => ({ getBackendApiUrl: getBackendApiUrlMock }));

import { POST } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  getBackendApiUrlMock.mockClear();
});

it("proxies shortlist generation without changing the request body", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok", run: { id: "run-1" }, items: [] }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  const body = JSON.stringify({
    profile_id: "balanced_research",
    market: "CN",
    asset_type: "stock",
    shortlist_limit: 10,
    locale: "en",
    use_llm: true,
    overrides: {},
  });

  const response = await POST(
    new Request("http://localhost/api/research-shortlists/generate", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    new URL("http://api.test/research-shortlists/generate"),
    {
      method: "POST",
      body,
      cache: "no-store",
      headers: { "content-type": "application/json" },
    },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
});

it("preserves a readiness conflict response", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Evidence coverage is not ready." }), {
      status: 409,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/research-shortlists/generate", {
      method: "POST",
      body: "{}",
    }),
  );

  expect(response.status).toBe(409);
  expect(await response.json()).toEqual({ detail: "Evidence coverage is not ready." });
});
