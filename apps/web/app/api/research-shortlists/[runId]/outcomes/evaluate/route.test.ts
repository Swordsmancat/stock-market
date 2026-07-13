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

it("proxies outcome evaluation without rewriting its body", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok", run: { id: "run-1" }, items: [] }), {
      status: 200,
      headers: { "content-type": "application/json; charset=utf-8" },
    }),
  );
  const body = JSON.stringify({ as_of: "2026-07-10" });

  const response = await POST(
    new Request("http://localhost/api/research-shortlists/run-1/outcomes/evaluate", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    }),
    { params: Promise.resolve({ runId: "run-1" }) },
  );

  expect(fetchMock).toHaveBeenCalledWith(
    new URL("http://api.test/research-shortlists/run-1/outcomes/evaluate"),
    {
      method: "POST",
      body,
      cache: "no-store",
      headers: { "content-type": "application/json" },
    },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json; charset=utf-8");
  expect(response.headers.get("cache-control")).toBe("no-store");
});

it("preserves an invalid cutoff response", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: { code: "INVALID_AS_OF" } }), {
      status: 400,
      headers: { "content-type": "application/problem+json" },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/research-shortlists/run-1/outcomes/evaluate", {
      method: "POST",
      body: "{}",
    }),
    { params: Promise.resolve({ runId: "run-1" }) },
  );

  expect(response.status).toBe(400);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: { code: "INVALID_AS_OF" } });
});
