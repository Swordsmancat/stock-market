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

it("forwards report generation requests with encoded symbol and query parameters", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ report_id: "report-123", status: "queued" }), {
      status: 202,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/reports/BRK%2FB/daily/generate?force=true&task_run_id=task-123"),
    {
      params: Promise.resolve({ symbol: "BRK/B" }),
    },
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "https://backend.example/reports/BRK%2FB/daily/generate?force=true&task_run_id=task-123",
    {
      method: "POST",
      cache: "no-store",
    },
  );
  expect(response.status).toBe(202);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual({ report_id: "report-123", status: "queued" });
});

it("propagates backend report generation failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Report generation failed" }), {
      status: 503,
      headers: {
        "content-type": "application/problem+json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/reports/600000.SH/daily/generate?provider=tushare"),
    {
      params: Promise.resolve({ symbol: "600000.SH" }),
    },
  );

  expect(response.status).toBe(503);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "Report generation failed" });
});
