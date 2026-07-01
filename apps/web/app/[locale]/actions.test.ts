import { afterEach, expect, it, vi } from "vitest";

const { backendFetchMock, redirectMock, revalidatePathMock } = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
  redirectMock: vi.fn((targetPath: string) => {
    throw new Error(`NEXT_REDIRECT:${targetPath}`);
  }),
  revalidatePathMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
}));

vi.mock("next/cache", () => ({
  revalidatePath: revalidatePathMock,
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: backendFetchMock,
}));

vi.mock("@/lib/platform-settings-store", () => ({
  getPlatformSettings: () =>
    Promise.resolve({
      market_data_provider: "mock",
      llm_provider: "mock",
      llm_api_key: "",
      llm_api_base: "https://api.openai.com/v1",
    }),
  savePlatformSettings: vi.fn(),
}));

import { updateWatchlistAlertsAction } from "./actions";

afterEach(() => {
  vi.clearAllMocks();
});

function buildWatchlistAlertFormData(overrides: Record<string, string> = {}) {
  const formData = new FormData();
  const defaults = {
    locale: "en",
    symbol: "AAPL",
    market: "US",
    name: "Apple Inc.",
    price_above: "",
    rsi_below: "",
  };
  for (const [key, value] of Object.entries({ ...defaults, ...overrides })) {
    formData.set(key, value);
  }
  return formData;
}

it("submits an empty alert_rules object when existing watchlist rules are cleared", async () => {
  backendFetchMock.mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));

  await expect(updateWatchlistAlertsAction(buildWatchlistAlertFormData())).rejects.toThrow(
    "NEXT_REDIRECT:/en/watchlist?op=alerts_updated",
  );

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/watchlist/items",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        symbol: "AAPL",
        market: "US",
        name: "Apple Inc.",
        alert_rules: {},
      }),
    }),
  );
  expect(revalidatePathMock).toHaveBeenCalledWith("/en/watchlist");
});

it("redirects with an error reason when alert rule saving fails", async () => {
  backendFetchMock.mockResolvedValue(new Response("", { status: 500 }));

  await expect(
    updateWatchlistAlertsAction(
      buildWatchlistAlertFormData({
        price_above: "150",
        rsi_below: "30",
      }),
    ),
  ).rejects.toThrow("NEXT_REDIRECT:/en/watchlist?op=error&reason=http_500");

  expect(backendFetchMock).toHaveBeenCalledWith(
    "/watchlist/items",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        symbol: "AAPL",
        market: "US",
        name: "Apple Inc.",
        alert_rules: {
          price_above: 150,
          rsi_below: 30,
        },
      }),
    }),
  );
});
