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

it("forwards one exact instrument news refresh without browser credentials", async () => {
  const responsePayload = {
    status: "refreshed",
    news: { symbol: "600519", source: "database", items: [] },
    diagnostics: [],
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(responsePayload), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await POST(
    new Request(
      "http://localhost/api/news/600519/refresh?market=CN&provider=ignored",
      {
        method: "POST",
        headers: {
          authorization: "Bearer browser-secret",
          cookie: "session=browser-secret",
        },
      },
    ),
    { params: Promise.resolve({ symbol: "600519" }) },
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "https://backend.example/news/600519/refresh?market=CN",
    { method: "POST", cache: "no-store" },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json");
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual(responsePayload);
});

it("preserves sanitized upstream refresh failures", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "News refresh failed" }), {
      status: 503,
      headers: { "content-type": "application/problem+json" },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/news/AAPL/refresh?market=US", {
      method: "POST",
    }),
    { params: Promise.resolve({ symbol: "AAPL" }) },
  );

  expect(response.status).toBe(503);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "News refresh failed" });
});

it("returns a generic no-store response when the upstream transport fails", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(
    new Error("socket failed with secret upstream details"),
  );

  const response = await POST(
    new Request("http://localhost/api/news/AAPL/refresh?market=US", {
      method: "POST",
    }),
    { params: Promise.resolve({ symbol: "AAPL" }) },
  );

  expect(response.status).toBe(502);
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual({
    detail: "News refresh is temporarily unavailable",
  });
});
