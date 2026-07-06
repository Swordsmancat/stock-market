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

it("forwards seed import requests to the backend without caching", async () => {
  const requestPayload = {
    content: "{\"observations\":[]}",
    filename: "macro-seeds.json",
    overwrite_acknowledged: true,
  };
  const responsePayload = {
    status: "imported",
    observations: 1,
    codes: ["us_10y_yield"],
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
    new Request("http://localhost/api/market-indicators/seeds/import", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(requestPayload),
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith("https://backend.example/market-indicators/seeds/import", {
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

it("propagates overwrite conflicts without rewriting the payload", async () => {
  const conflictPayload = {
    detail: {
      status: "valid",
      summary: { updates: 1 },
    },
  };
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(conflictPayload), {
      status: 409,
      headers: {
        "content-type": "application/json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/market-indicators/seeds/import", {
      method: "POST",
      body: JSON.stringify({ content: "code,as_of,value,source,components_json" }),
    }),
  );

  expect(response.status).toBe(409);
  expect(response.headers.get("content-type")).toBe("application/json");
  await expect(response.json()).resolves.toEqual(conflictPayload);
});
