import { afterEach, expect, it, vi } from "vitest";

const { backendFetchMock } = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: backendFetchMock,
}));

import { fetchInstrumentDetailContext } from "./instrument-detail";

afterEach(() => {
  backendFetchMock.mockReset();
});
function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

it("resolves one exact market identity before reading membership", async () => {
  backendFetchMock
    .mockResolvedValueOnce(
      jsonResponse({
        items: [
          { symbol: "0700", market: "HK", name: "Tencent Holdings" },
        ],
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({ status: "watched", symbol: "0700", market: "HK" }),
    );

  await expect(fetchInstrumentDetailContext("0700", " hk ")).resolves.toEqual({
    identity: {
      symbol: "0700",
      market: "HK",
      name: "Tencent Holdings",
    },
    watchlistMembership: "watched",
  });
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    1,
    "/instruments?q=0700&market=HK&limit=10",
    { cache: "no-store" },
  );
  expect(backendFetchMock).toHaveBeenNthCalledWith(
    2,
    "/watchlist/items?symbol=0700&market=HK",
    { cache: "no-store" },
  );
});

it("does not guess a market when an exact symbol is ambiguous", async () => {
  backendFetchMock.mockResolvedValueOnce(
    jsonResponse({
      items: [
        { symbol: "DUPL", market: "CN", name: "CN listing" },
        { symbol: "DUPL", market: "HK", name: "HK listing" },
      ],
    }),
  );

  await expect(fetchInstrumentDetailContext("DUPL")).resolves.toEqual({
    identity: null,
    watchlistMembership: "unavailable",
  });
  expect(backendFetchMock).toHaveBeenCalledTimes(1);
});

it("keeps an exact identity but disables mutation when membership fails", async () => {
  backendFetchMock
    .mockResolvedValueOnce(
      jsonResponse({
        items: [{ symbol: "AAPL", market: "US", name: "Apple Inc." }],
      }),
    )
    .mockResolvedValueOnce(jsonResponse({ detail: "unavailable" }, 503));

  await expect(fetchInstrumentDetailContext("AAPL", "US")).resolves.toEqual({
    identity: { symbol: "AAPL", market: "US", name: "Apple Inc." },
    watchlistMembership: "unavailable",
  });
});
