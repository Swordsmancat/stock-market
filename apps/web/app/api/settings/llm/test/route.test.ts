import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({
  getBackendApiUrlMock: vi.fn(() => "http://api.test"),
}));

vi.mock("@/lib/backend-api", () => ({ getBackendApiUrl: getBackendApiUrlMock }));

import { POST } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  getBackendApiUrlMock.mockClear();
});

it("forwards one manual connection-test request and preserves the sanitized response", async () => {
  const payload = {
    status: "ok",
    code: "connected",
    provider: "openai",
    model: "deepseek-chat",
    latency_ms: 246,
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await POST();

  expect(fetchMock).toHaveBeenCalledOnce();
  expect(fetchMock).toHaveBeenCalledWith(new URL("http://api.test/settings/llm/test"), {
    method: "POST",
    cache: "no-store",
    headers: { "content-type": "application/json" },
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
  await expect(response.json()).resolves.toEqual(payload);
});

it("returns a generic secret-safe failure when the backend cannot be reached", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(
    new Error("https://user:secret@api.example/v1 failed"),
  );

  const response = await POST();
  const payload = await response.json();

  expect(response.status).toBe(502);
  expect(payload).toEqual({
    status: "error",
    code: "provider_unavailable",
    message: "LLM provider is unavailable.",
  });
  expect(JSON.stringify(payload)).not.toContain("secret");
  expect(JSON.stringify(payload)).not.toContain("api.example");
});
