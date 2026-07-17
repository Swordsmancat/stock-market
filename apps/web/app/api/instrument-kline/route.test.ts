import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/backend-api", () => ({
  getBackendApiUrl: () => "https://backend.example",
}));

import { GET } from "./route";

afterEach(() => vi.restoreAllMocks());

it("forwards only the GET query to the stored K-line projection", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "empty", source: "database" })),
  );

  const response = await GET(new Request("http://localhost/api/instrument-kline?q=300&asset_type=etf&limit=10"));

  expect(fetchMock).toHaveBeenCalledWith(
    "https://backend.example/instrument-kline?q=300&asset_type=etf&limit=10",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
});
