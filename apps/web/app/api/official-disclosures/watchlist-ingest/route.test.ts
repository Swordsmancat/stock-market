import { afterEach, expect, it, vi } from "vitest";
import { POST } from "./route";

afterEach(() => vi.restoreAllMocks());

it("proxies watchlist disclosure batch input and upstream status", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "already_running", task_run: { id: "task-1" } }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  const body = JSON.stringify({ lookback_days: 30, max_documents: 20 });
  const response = await POST(new Request("http://localhost/api/official-disclosures/watchlist-ingest", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  }));
  expect(response.status).toBe(200);
  const [upstreamUrl, init] = fetchMock.mock.calls[0];
  expect(String(upstreamUrl)).toBe("http://127.0.0.1:8000/official-disclosures/watchlist/ingest");
  expect(init).toMatchObject({ method: "POST", body });
});
