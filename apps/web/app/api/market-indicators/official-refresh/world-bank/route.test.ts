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

it("forwards World Bank official refresh requests to the backend without caching", async () => {
  const requestPayload = {
    target: "all",
    latest_only: true,
    dry_run: false,
  };
  const responsePayload = {
    status: "ok",
    provider: "world_bank",
    dry_run: false,
    observations: 3,
    fetched: 6,
    skipped: 0,
    codes: ["buffett_indicator_us", "buffett_indicator_cn", "buffett_indicator_hk"],
    latest_as_of: "2024-12-31",
    diagnostics: [],
    cache: { market_overview_cleared: 4 },
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(responsePayload), {
      status: 200,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/market-indicators/official-refresh/world-bank", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(requestPayload),
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith("https://backend.example/market-indicators/official-refresh/world-bank", {
    method: "POST",
    body: JSON.stringify(requestPayload),
    cache: "no-store",
    headers: {
      "content-type": "application/json",
    },
  });
  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual(responsePayload);
});

it("propagates World Bank official refresh upstream failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Unsupported World Bank macro target 'bad'" }), {
      status: 400,
      headers: {
        "content-type": "application/problem+json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/market-indicators/official-refresh/world-bank", {
      method: "POST",
      body: JSON.stringify({ target: "bad" }),
    }),
  );

  expect(response.status).toBe(400);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "Unsupported World Bank macro target 'bad'" });
});
