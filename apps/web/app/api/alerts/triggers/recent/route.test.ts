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

it("forwards recent alert trigger queries to the backend without caching", async () => {
  const responsePayload = {
    source: "database",
    items: [{ id: "trigger-1", symbol: "AAPL", condition: "price_above" }],
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
    new Request("http://localhost/api/alerts/triggers/recent?limit=5&symbol=AAPL"),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "https://backend.example/alerts/triggers/recent?limit=5&symbol=AAPL",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual(responsePayload);
});

it("propagates recent alert trigger failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Alert trigger query failed" }), {
      status: 502,
      headers: {
        "content-type": "application/problem+json",
      },
    }),
  );

  const response = await GET(new Request("http://localhost/api/alerts/triggers/recent?limit=5"));

  expect(response.status).toBe(502);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "Alert trigger query failed" });
});
