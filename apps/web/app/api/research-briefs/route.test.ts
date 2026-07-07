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

it("proxies research brief list requests with no-store cache policy", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [], summary: { total: 0 } }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await GET(new Request("http://localhost/api/research-briefs?limit=10"));

  expect(fetchMock).toHaveBeenCalledWith("http://api.test/research-briefs?limit=10", {
    method: "GET",
    cache: "no-store",
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual({ items: [], summary: { total: 0 } });
});

it("proxies research brief generation requests without changing the JSON payload", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ id: "brief-1", title: "Saved brief" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  const body = JSON.stringify({ provider: "mock", locale: "en" });

  const response = await POST(
    new Request("http://localhost/api/research-briefs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith("http://api.test/research-briefs/generate", {
    method: "POST",
    body,
    cache: "no-store",
    headers: { "content-type": "application/json" },
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual({ id: "brief-1", title: "Saved brief" });
});
