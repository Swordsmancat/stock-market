import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({ getBackendApiUrlMock: vi.fn(() => "http://api.test") }));
vi.mock("@/lib/backend-api", () => ({ getBackendApiUrl: getBackendApiUrlMock }));

import { GET } from "./route";

afterEach(() => vi.restoreAllMocks());

it("proxies no-store A-share evidence coverage", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ status: "ok" })));
  const response = await GET();
  expect(fetchMock).toHaveBeenCalledWith(new URL("http://api.test/stock-selection/evidence-coverage?market=CN&provider=akshare"), { cache: "no-store" });
  expect(response.headers.get("cache-control")).toBe("no-store");
});
