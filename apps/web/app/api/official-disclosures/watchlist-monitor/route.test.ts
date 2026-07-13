import { afterEach, expect, it, vi } from "vitest";
import { POST } from "./route";

afterEach(() => vi.restoreAllMocks());

it("proxies incremental watchlist disclosure monitoring", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "dispatched", task_run: { id: "task-2" } }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  const body = JSON.stringify({ lookback_days: 30, max_documents: 20 });
  const response = await POST(new Request("http://localhost/api/official-disclosures/watchlist-monitor", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  }));
  expect(response.status).toBe(200);
  const [upstreamUrl, init] = fetchMock.mock.calls[0];
  expect(String(upstreamUrl)).toBe("http://127.0.0.1:8000/official-disclosures/watchlist/monitor");
  expect(init).toMatchObject({ method: "POST", body });
});
