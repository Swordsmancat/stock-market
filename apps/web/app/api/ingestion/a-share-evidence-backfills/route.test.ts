import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({ getBackendApiUrlMock: vi.fn(() => "http://api.test") }));
vi.mock("@/lib/backend-api", () => ({ getBackendApiUrl: getBackendApiUrlMock }));

import { POST } from "./route";

afterEach(() => vi.restoreAllMocks());

it("forwards the fixed UI backfill request body without rewriting failures", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "busy" }), { status: 409 }));
  const request = new Request("http://localhost/api/ingestion/a-share-evidence-backfills", { method: "POST", body: JSON.stringify({ run_kind: "canary" }) });
  const response = await POST(request);
  expect(fetchMock).toHaveBeenCalledWith(new URL("http://api.test/ingestion/a-share-evidence-backfills"), expect.objectContaining({ method: "POST", body: JSON.stringify({ run_kind: "canary" }) }));
  expect(response.status).toBe(409);
  await expect(response.json()).resolves.toEqual({ detail: "busy" });
});
