import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({
  getBackendApiUrlMock: vi.fn(() => "https://backend.example"),
}));

vi.mock("@/lib/backend-api", () => ({
  getBackendApiUrl: getBackendApiUrlMock,
}));

import { POST } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  getBackendApiUrlMock.mockReturnValue("https://backend.example");
});

it("forwards FRED official refresh requests to the backend without caching", async () => {
  const requestPayload = {
    series: "all",
    latest_only: true,
    dry_run: true,
  };
  const responsePayload = {
    status: "ok",
    provider: "fred",
    dry_run: true,
    observations: 2,
    fetched: 2,
    skipped: 0,
    codes: ["us_10y_yield"],
    latest_as_of: "2026-07-01",
    diagnostics: [],
    cache: { market_overview_cleared: 0 },
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(responsePayload), {
      status: 200,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/market-indicators/official-refresh/fred", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(requestPayload),
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith("https://backend.example/market-indicators/official-refresh/fred", {
    method: "POST",
    body: JSON.stringify(requestPayload),
    cache: "no-store",
    headers: {
      "content-type": "application/json",
    },
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual(responsePayload);
});

it("propagates FRED official refresh upstream failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: { provider: "fred", message: "FRED API key is not configured." } }), {
      status: 503,
      headers: {
        "content-type": "application/problem+json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/market-indicators/official-refresh/fred", {
      method: "POST",
      body: JSON.stringify({ series: "all" }),
    }),
  );

  expect(response.status).toBe(503);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({
    detail: { provider: "fred", message: "FRED API key is not configured." },
  });
});
