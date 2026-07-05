import { afterEach, expect, it, vi } from "vitest";

const { backendFetchMock } = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: backendFetchMock,
}));

import { GET } from "./route";

afterEach(() => {
  backendFetchMock.mockReset();
});

it("proxies market overview requests with provider and no-store cache policy", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        provider: "mock",
        indices: { items: [] },
        diagnostics: [],
      }),
      { status: 200 },
    ),
  );

  const response = await GET(new Request("http://localhost/api/market-overview?provider=mock"));

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/dashboard/market-overview?provider=mock",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toMatchObject({ provider: "mock" });
});

it("encodes provider names before forwarding to the backend", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(JSON.stringify({ provider: "mock provider", indices: { items: [] } }), { status: 200 }),
  );

  const response = await GET(new Request("http://localhost/api/market-overview?provider=mock provider"));

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/dashboard/market-overview?provider=mock%20provider",
    { cache: "no-store" },
  );
  expect(response.headers.get("cache-control")).toBe("no-store");
});

it("returns no-store errors when the backend fails", async () => {
  backendFetchMock.mockResolvedValue(new Response("", { status: 503 }));

  const response = await GET(new Request("http://localhost/api/market-overview?provider=mock"));

  expect(response.status).toBe(500);
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual({ error: "Failed to fetch market overview" });
});
