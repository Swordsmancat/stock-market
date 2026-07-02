import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({
  getBackendApiUrlMock: vi.fn(() => "https://backend.example"),
}));

vi.mock("@/lib/backend-api", () => ({
  getBackendApiUrl: getBackendApiUrlMock,
}));

import { POST } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
  getBackendApiUrlMock.mockReturnValue("https://backend.example");
});

it("forwards retry requests to the backend task-run retry endpoint", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "retry_started" }), {
      status: 202,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await POST(new Request("http://localhost/api/task-runs/task-123/retry"), {
    params: Promise.resolve({ taskRunId: "task-123" }),
  });

  expect(fetchMock).toHaveBeenCalledWith("https://backend.example/task-runs/task-123/retry", {
    method: "POST",
    cache: "no-store",
  });
  expect(response.status).toBe(202);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual({ status: "retry_started" });
});

it("propagates backend retry failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Task run not found" }), {
      status: 404,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await POST(new Request("http://localhost/api/task-runs/missing/retry"), {
    params: Promise.resolve({ taskRunId: "missing" }),
  });

  expect(response.status).toBe(404);
  await expect(response.json()).resolves.toEqual({ detail: "Task run not found" });
});
