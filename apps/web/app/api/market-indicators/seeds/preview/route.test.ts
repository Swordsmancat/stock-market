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

it("forwards seed preview requests to the backend without caching", async () => {
  const requestPayload = {
    content: "{\"observations\":[]}",
    filename: "macro-seeds.json",
  };
  const responsePayload = {
    status: "invalid",
    can_import: false,
    errors: ["seed content contains no observations"],
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
    new Request("http://localhost/api/market-indicators/seeds/preview", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(requestPayload),
    }),
  );

  expect(fetchMock).toHaveBeenCalledWith("https://backend.example/market-indicators/seeds/preview", {
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

it("propagates seed preview upstream failures without rewriting the payload", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "invalid request" }), {
      status: 422,
      headers: {
        "content-type": "application/problem+json",
      },
    }),
  );

  const response = await POST(
    new Request("http://localhost/api/market-indicators/seeds/preview", {
      method: "POST",
      body: JSON.stringify({ content: "" }),
    }),
  );

  expect(response.status).toBe(422);
  expect(response.headers.get("content-type")).toBe("application/problem+json");
  await expect(response.json()).resolves.toEqual({ detail: "invalid request" });
});
