import { afterEach, expect, it, vi } from "vitest";
import { POST } from "./route";

afterEach(() => vi.restoreAllMocks());

it("proxies exact disclosure ingestion without accepting a caller URL", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
  );
  const response = await POST(
    new Request("http://localhost/api/official-disclosures/id/ingest-document", { method: "POST" }),
    { params: Promise.resolve({ disclosureId: "11111111-2222-3333-4444-555555555555" }) },
  );
  expect(response.status).toBe(200);
  const [upstreamUrl, init] = fetchMock.mock.calls[0];
  expect(String(upstreamUrl)).toBe(
    "http://127.0.0.1:8000/official-disclosures/11111111-2222-3333-4444-555555555555/ingest-document",
  );
  expect(init).toEqual({ method: "POST", cache: "no-store" });
});
