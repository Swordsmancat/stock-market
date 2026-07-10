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

it("proxies the failure-safe A-share universe TaskRun mutation", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "dispatched", task_run: { id: "universe-1" } }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  const response = await POST();

  expect(fetchMock).toHaveBeenCalledWith(new URL("http://api.test/ingestion/instrument-universe"), {
    method: "POST",
    cache: "no-store",
  });
  expect(response.status).toBe(200);
});
