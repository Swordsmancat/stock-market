import { expect, it } from "vitest";

import {
  decodeMarketComparisonPayload,
  toComparisonInstruments,
} from "./market-comparison";

it("decodes stored comparison identity and finite shared bars", () => {
  const payload = decodeMarketComparisonPayload({
    status: "ok",
    market: "CN",
    symbols: ["600001", "600002"],
    period: "3m",
    requested_count: 2,
    anchor_date: "2026-07-17",
    period_start: "2026-04-15",
    shared_date_count: 2,
    comparable_count: 2,
    missing_symbols: [],
    diagnostics: [],
    search_results: [],
    items: [
      {
        id: "CN-600001",
        symbol: "600001",
        name: "Alpha",
        market: "CN",
        exchange: "SSE",
        status: "ok",
        provider: "akshare",
        adjustment: "qfq",
        first_date: "2026-07-16",
        last_date: "2026-07-17",
        bar_count: 2,
        bars: [
          { timestamp: "2026-07-16", close: 10 },
          { timestamp: "2026-07-17", close: 11 },
          { timestamp: "bad", close: "NaN" },
        ],
      },
    ],
  });

  expect(payload?.items[0].bars).toHaveLength(2);
  expect(toComparisonInstruments(payload?.items ?? [])[0]).toMatchObject({
    id: "CN-600001",
    symbol: "600001",
  });
});

it("rejects unknown top-level comparison states", () => {
  expect(decodeMarketComparisonPayload({ status: "partial" })).toBeNull();
});
