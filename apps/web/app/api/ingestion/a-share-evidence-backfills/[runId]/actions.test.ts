import { afterEach, expect, it, vi } from "vitest";

const { getBackendApiUrlMock } = vi.hoisted(() => ({ getBackendApiUrlMock: vi.fn(() => "http://api.test") }));
vi.mock("@/lib/backend-api", () => ({ getBackendApiUrl: getBackendApiUrlMock }));

import { GET } from "./route";
import { POST as cancel } from "./cancel/route";
import { POST as resume } from "./resume/route";
import { POST as retryFailed } from "./retry-failed/route";

afterEach(() => vi.restoreAllMocks());

it.each([
  ["get", GET, ""],
  ["resume", resume, "/resume"],
  ["retry", retryFailed, "/retry-failed"],
  ["cancel", cancel, "/cancel"],
])("proxies the %s operation with an encoded run id", async (_name, handler, suffix) => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ status: "ok" })));
  await handler(new Request("http://localhost"), { params: Promise.resolve({ runId: "run / 1" }) });
  expect(fetchMock.mock.calls[0][0]).toEqual(new URL(`http://api.test/ingestion/a-share-evidence-backfills/run%20%2F%201${suffix}`));
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ cache: "no-store", ...(suffix ? { method: "POST" } : {}) });
});
