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

it("proxies stock discovery without changing the request body", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "degraded", shortlist: [] }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  const body = JSON.stringify({ profile_id: "balanced_research", market: "CN" });

  const response = await POST(
    new Request("http://localhost/api/stock-selection/discover", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith(new URL("http://api.test/stock-selection/discover"), {
    method: "POST",
    body,
    cache: "no-store",
    headers: { "content-type": "application/json" },
  });
  expect(response.status).toBe(200);
});
