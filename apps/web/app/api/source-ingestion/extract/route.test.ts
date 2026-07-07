import { afterEach, expect, it, vi } from "vitest";

const { backendFetchMock } = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: backendFetchMock,
}));

import { POST } from "./route";

afterEach(() => {
  backendFetchMock.mockReset();
});

it("proxies source ingestion extraction requests to the backend", async () => {
  const requestBody = {
    content: "World Bank market cap and GDP review.",
    source_id: "buffett_manual_valuation_components",
  };
  const backendPayload = {
    status: "fallback",
    summary: "World Bank market cap and GDP review.",
    key_indicators: [],
  };
  backendFetchMock.mockResolvedValue(
    new Response(JSON.stringify(backendPayload), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/source-ingestion/extract", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(requestBody),
    }),
  );

  expect(backendFetchMock).toHaveBeenCalledWith("/source-ingestion/extract", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody),
    cache: "no-store",
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json");
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual(backendPayload);
});

it("preserves backend error status and response body", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(JSON.stringify({ detail: "bad payload" }), {
      status: 422,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/source-ingestion/extract", {
      method: "POST",
      body: JSON.stringify({ content: "" }),
    }),
  );

  expect(response.status).toBe(422);
  await expect(response.json()).resolves.toEqual({ detail: "bad payload" });
});
