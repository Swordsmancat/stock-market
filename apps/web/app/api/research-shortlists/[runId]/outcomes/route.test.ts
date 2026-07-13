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

it("proxies one cohort outcome detail query without caching", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok", run: { id: "run-1" }, items: [] }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await GET(
    new Request("http://localhost/api/research-shortlists/run-1/outcomes?as_of=2026-07-10"),
    { params: Promise.resolve({ runId: "run-1" }) },
  );

  expect(fetchMock).toHaveBeenCalledWith(
    new URL("http://api.test/research-shortlists/run-1/outcomes?as_of=2026-07-10"),
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
});

it("preserves a missing-run response body and content type", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Shortlist run not found" }), {
      status: 404,
      headers: { "content-type": "application/problem+json" },
    }),
  );

  const response = await GET(
    new Request("http://localhost/api/research-shortlists/missing/outcomes"),
    { params: Promise.resolve({ runId: "missing" }) },
  );

  expect(response.status).toBe(404);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "Shortlist run not found" });
});
