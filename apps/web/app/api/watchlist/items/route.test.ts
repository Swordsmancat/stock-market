import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({
  getBackendApiUrlMock: vi.fn(() => "https://backend.example"),
}));

vi.mock("@/lib/backend-api", () => ({
  getBackendApiUrl: getBackendApiUrlMock,
}));

import { DELETE, POST } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  getBackendApiUrlMock.mockReturnValue("https://backend.example");
});

it("forwards watchlist item creation bodies to the backend without caching", async () => {
  const requestPayload = {
    symbol: "AAPL",
    market: "US",
    name: "Apple Inc.",
    alert_rules: { price_above: 250 },
  };
  const responsePayload = {
    source: "database",
    item: { symbol: "AAPL", market: "US", name: "Apple Inc." },
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(responsePayload), {
      status: 201,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/watchlist/items", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(requestPayload),
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith("https://backend.example/watchlist/items", {
    method: "POST",
    body: JSON.stringify(requestPayload),
    cache: "no-store",
    headers: {
      "content-type": "application/json",
    },
  });
  expect(response.status).toBe(201);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual(responsePayload);
});

it("propagates watchlist item creation failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Invalid watchlist item" }), {
      status: 422,
      headers: {
        "content-type": "application/problem+json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/watchlist/items", {
      method: "POST",
      body: JSON.stringify({ symbol: "" }),
    }),
  );

  expect(response.status).toBe(422);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "Invalid watchlist item" });
});

it("forwards watchlist item deletion identity query parameters", async () => {
  const responsePayload = { source: "database", status: "deleted" };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(responsePayload), {
      status: 200,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await DELETE(
    new Request("http://localhost/api/watchlist/items?symbol=0700&market=HK&unused=value"),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "https://backend.example/watchlist/items?symbol=0700&market=HK",
    {
      method: "DELETE",
      cache: "no-store",
    },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual(responsePayload);
});

it("propagates watchlist item deletion failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Watchlist item not found" }), {
      status: 404,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await DELETE(new Request("http://localhost/api/watchlist/items?symbol=AAPL&market=US"));

  expect(response.status).toBe(404);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual({ detail: "Watchlist item not found" });
});
