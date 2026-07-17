import { expect, it } from "vitest";

import { decodeInstrumentKlinePayload } from "./instrument-kline";

it("decodes a stored catalog and coherent series", () => {
  const payload = decodeInstrumentKlinePayload({
    status: "ready",
    source: "database",
    catalog: [{
      id: "CN-510300", symbol: "510300", name: "CSI 300 ETF", market: "CN",
      exchange: "SSE", asset_type: "etf", currency: "CNY", stored_bar_count: 2,
      has_series: true,
      latest_bar: { timestamp: "2026-07-17", close: 4.2, provider: "akshare", source: "eastmoney", adjustment: "qfq" },
    }],
    total: 1, limit: 20, offset: 0, has_more: false,
    selected: { id: "CN-510300", symbol: "510300", name: "CSI 300 ETF", market: "CN", exchange: "SSE", asset_type: "etf", currency: "CNY" },
    series: {
      provider: "akshare", adjustment: "qfq", anchor_date: "2026-07-17", period_start: "2026-04-15",
      first_date: "2026-07-16", last_date: "2026-07-17", bar_count: 2,
      sources: [{ source: "eastmoney", bar_count: 2 }],
      items: [
        { timestamp: "2026-07-16", open: 4, high: 4.1, low: 3.9, close: 4.05, volume: 100 },
        { timestamp: "2026-07-17", open: 4.1, high: 4.3, low: 4, close: 4.2, volume: 120 },
      ],
    },
    diagnostics: [],
  });

  expect(payload?.catalog[0].assetType).toBe("etf");
  expect(payload?.series?.items).toHaveLength(2);
  expect(payload?.series?.sources).toEqual([{ source: "eastmoney", barCount: 2 }]);
});

it("rejects provider payloads and invalid identities", () => {
  expect(decodeInstrumentKlinePayload({ status: "empty", source: "provider" })).toBeNull();
  expect(decodeInstrumentKlinePayload({
    status: "empty", source: "database", catalog: [], total: 0, limit: 20,
    offset: 0, has_more: false, selected: { symbol: "000001" }, series: null,
  })).toBeNull();
});
