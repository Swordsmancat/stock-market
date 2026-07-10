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

it("proxies corporate-action TaskRun requests without changing the batch input", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "dispatched", task_run: { id: "task-1" } }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  const body = JSON.stringify({ report_period: "2025-12-31", cursor: 0, batch_size: 50 });

  const response = await POST(
    new Request("http://localhost/api/ingestion/corporate-actions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith(new URL("http://api.test/ingestion/corporate-actions"), {
    method: "POST",
    body,
    cache: "no-store",
    headers: { "content-type": "application/json" },
  });
  expect(response.status).toBe(200);
});
