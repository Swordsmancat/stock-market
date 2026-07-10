import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({
  getBackendApiUrlMock: vi.fn(() => "http://api.test"),
}));

vi.mock("@/lib/backend-api", () => ({ getBackendApiUrl: getBackendApiUrlMock }));

import { GET } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  getBackendApiUrlMock.mockClear();
});

it("proxies transparent stock-selection profiles with no-store caching", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok", items: [] }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await GET();

  expect(fetchMock).toHaveBeenCalledWith(new URL("http://api.test/stock-selection/profiles"), {
    cache: "no-store",
  });
  expect(response.headers.get("cache-control")).toBe("no-store");
});
