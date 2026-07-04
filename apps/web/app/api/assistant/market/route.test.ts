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

it("proxies market assistant requests to the backend", async () => {
  const requestBody = {
    scope: "instrument",
    symbol: "AAPL",
    question: "请总结近期走势。",
    locale: "zh",
    timeframe: "1d",
    start: "2026-01-01",
    end: "2026-01-20",
    provider: "mock",
  };
  const backendPayload = {
    status: "degraded",
    answer_markdown: "### 概览\n基于可用数据整理。",
    symbol: "AAPL",
  };
  backendFetchMock.mockResolvedValue(
    new Response(JSON.stringify(backendPayload), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/assistant/market", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(requestBody),
    }),
  );

  expect(backendFetchMock).toHaveBeenCalledWith("/assistant/market", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody),
    cache: "no-store",
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual(backendPayload);
});

it("preserves backend validation status and response body", async () => {
  backendFetchMock.mockResolvedValue(
    new Response(JSON.stringify({ detail: "Question is required." }), {
      status: 400,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/assistant/market", {
      method: "POST",
      body: JSON.stringify({ symbol: "AAPL", question: "" }),
    }),
  );

  expect(response.status).toBe(400);
  await expect(response.json()).resolves.toEqual({ detail: "Question is required." });
});
