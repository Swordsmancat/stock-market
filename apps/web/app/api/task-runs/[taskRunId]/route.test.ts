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

it("forwards task-run detail requests to the backend without caching", async () => {
  const responsePayload = {
    source: "database",
    item: {
      id: "task-run-123",
      task_name: "reports.refresh_daily_stock_analysis",
      status: "succeeded",
    },
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(responsePayload), {
      status: 200,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await GET(new Request("http://localhost/api/task-runs/task-run-123"), {
    params: Promise.resolve({ taskRunId: "task-run-123" }),
  });

  expect(fetchMock).toHaveBeenCalledWith("https://backend.example/task-runs/task-run-123", {
    cache: "no-store",
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual(responsePayload);
});

it("propagates backend task-run detail failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Task run not found" }), {
      status: 404,
      headers: {
        "content-type": "application/problem+json",
      },
    }),
  );

  const response = await GET(new Request("http://localhost/api/task-runs/missing"), {
    params: Promise.resolve({ taskRunId: "missing" }),
  });

  expect(response.status).toBe(404);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "Task run not found" });
});
