import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/backend-api", () => ({ getBackendApiUrl: () => "https://backend.example" }));

import { GET } from "./route";

afterEach(() => vi.restoreAllMocks());

it("forwards the GET-only topic query without caching", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "empty", source: "database" })),
  );
  const response = await GET(new Request("http://localhost/api/topic-research?topic=nonferrous&window=180d"));

  expect(fetchMock).toHaveBeenCalledWith(
    "https://backend.example/topic-research?topic=nonferrous&window=180d",
    { cache: "no-store" },
  );
  expect(response.status).toBe(200);
});
