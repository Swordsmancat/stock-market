import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({
  getBackendApiUrlMock: vi.fn(() => "https://backend.example"),
}));

vi.mock("@/lib/backend-api", () => ({
  getBackendApiUrl: getBackendApiUrlMock,
}));

import { GET } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  getBackendApiUrlMock.mockReturnValue("https://backend.example");
});

it("forwards instrument queries to the backend without caching", async () => {
  const responsePayload = {
    source: "database",
    items: [{ symbol: "AAPL", market: "US", name: "Apple Inc." }],
    total: 1,
    limit: 25,
    offset: 25,
    has_more: false,
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(responsePayload), {
      status: 200,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await GET(
    new Request(
      "http://localhost/api/instruments?market=US&exchange=NASDAQ&q=AAPL&limit=25&offset=25",
    ),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "https://backend.example/instruments?market=US&exchange=NASDAQ&q=AAPL&limit=25&offset=25",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual(responsePayload);
});

it("propagates backend instrument failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Instrument service unavailable" }), {
      status: 503,
      headers: {
        "content-type": "application/problem+json",
      },
    }),
  );

  const response = await GET(new Request("http://localhost/api/instruments?market=US"));

  expect(response.status).toBe(503);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "Instrument service unavailable" });
});
