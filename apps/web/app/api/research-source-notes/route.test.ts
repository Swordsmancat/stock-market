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

it("proxies notebook list requests with no-store cache policy", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [], summary: { total: 0 } }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await GET(new Request("http://localhost/api/research-source-notes?limit=10&citable_only=true"));

  expect(fetchMock).toHaveBeenCalledWith("http://api.test/research-source-notes?limit=10&citable_only=true", {
    method: "GET",
    cache: "no-store",
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual({ items: [], summary: { total: 0 } });
});

it("proxies notebook create requests without changing the JSON payload", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ id: "note-1", title: "Reviewed note" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  const body = JSON.stringify({ title: "Reviewed note" });

  const response = await POST(
    new Request("http://localhost/api/research-source-notes", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith("http://api.test/research-source-notes", {
    method: "POST",
    body,
    cache: "no-store",
    headers: { "content-type": "application/json" },
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual({ id: "note-1", title: "Reviewed note" });
});
