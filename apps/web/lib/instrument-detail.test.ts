import { afterEach, expect, it, vi } from "vitest";

const { backendFetchMock } = vi.hoisted(() => ({
  backendFetchMock: vi.fn(),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: backendFetchMock,
}));

import {
  fetchInstrumentDetailContext,
  fetchInstrumentDetailPayload,
} from "./instrument-detail";

afterEach(() => {
  backendFetchMock.mockReset();
});
function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function mockInstrumentDetailBackend({
  barItems = [
    {
      timestamp: "2026-07-15",
      open: 4000,
      high: 4020,
      low: 3980,
      close: 4010,
      volume: 1000,
    },
  ],
  barStatus,
}: {
  barItems?: Array<Record<string, number | string>>;
  barStatus?: string;
} = {}) {
  backendFetchMock.mockImplementation((path: string) => {
    if (path.includes("/bars?")) {
      return Promise.resolve(
        jsonResponse({
          status: barStatus ?? (barItems.length > 0 ? "ok" : "no_data"),
          source: "akshare",
          provider: "akshare",
          effective_provider: "akshare",
          provenance_known: true,
          provenance_corrected: false,
          diagnostics: [],
          items: barItems,
        }),
      );
    }
    if (path.includes("/latest")) {
      return Promise.resolve(
        jsonResponse({
          status: "ok",
          item: { timestamp: "2026-07-15", close: 4010 },
        }),
      );
    }
    return Promise.resolve(jsonResponse({}));
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

it("keeps provider-specific market indexes out of CN stock fallback", async () => {
  mockInstrumentDetailBackend();

  const result = await fetchInstrumentDetailPayload({
    symbol: "cn_csi_300",
    providerName: "akshare",
    market: "CN",
  });

  expect(result.status).toBe("loaded");
  const requestedPaths = backendFetchMock.mock.calls.map(([path]) =>
    String(path),
  );
  expect(requestedPaths).toContainEqual(
    expect.stringMatching(
      /^\/market-data\/000300\/bars\?.*&provider=akshare$/,
    ),
  );
  expect(
    requestedPaths.filter((path) => path.startsWith("/market-data/000300/")),
  ).not.toEqual(expect.arrayContaining([expect.stringContaining("market=CN")]));
});

it("derives latest provenance from nonempty bars without another provider request", async () => {
  mockInstrumentDetailBackend();

  const result = await fetchInstrumentDetailPayload({
    symbol: "600519",
    providerName: "yfinance",
    market: "CN",
  });

  expect(result.status).toBe("loaded");
  if (result.status !== "loaded") {
    throw new Error("expected loaded instrument detail");
  }
  expect(result.payload.latest).toMatchObject({
    status: "ok",
    source: "akshare",
    provider: "akshare",
    effective_provider: "akshare",
    provenance_known: true,
    provenance_corrected: false,
    diagnostics: [],
    item: { timestamp: "2026-07-15", close: 4010 },
  });
  expect(
    backendFetchMock.mock.calls.some(([path]) =>
      String(path).includes("/market-data/600519/latest"),
    ),
  ).toBe(false);
});

it("derives empty latest provenance without repeating the provider chain", async () => {
  mockInstrumentDetailBackend({ barItems: [] });

  const result = await fetchInstrumentDetailPayload({
    symbol: "600519",
    providerName: "yfinance",
    market: "CN",
  });

  expect(result.status).toBe("loaded");
  if (result.status !== "loaded") {
    throw new Error("expected loaded instrument detail");
  }
  expect(result.payload.latest).toMatchObject({
    status: "no_data",
    source: "akshare",
    item: null,
  });
  expect(
    backendFetchMock.mock.calls.filter(([path]) =>
      String(path).includes("/market-data/600519/latest"),
    ),
  ).toHaveLength(0);
});

it("keeps degraded provenance when latest is derived from bars", async () => {
  mockInstrumentDetailBackend({ barStatus: "degraded" });

  const result = await fetchInstrumentDetailPayload({
    symbol: "600519",
    providerName: "yfinance",
    market: "CN",
  });

  expect(result.status).toBe("loaded");
  if (result.status !== "loaded") {
    throw new Error("expected loaded instrument detail");
  }
  expect(result.payload.bars.status).toBe("degraded");
  expect(result.payload.latest.status).toBe("degraded");
});
