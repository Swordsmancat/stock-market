import { describe, expect, it } from "vitest";

import { decodeMarketMoversPayload } from "./market-movers";

describe("decodeMarketMoversPayload", () => {
  it("normalizes numeric strings and drops malformed rows", () => {
    const payload = decodeMarketMoversPayload({
      status: "ok",
      market: "CN",
      direction: "gainers",
      exchange: "SSE",
      limit: 10,
      trade_date: "2026-07-17",
      previous_trade_date: "2026-07-16",
      provider: "akshare",
      adjustment: "qfq",
      comparable_count: 2,
      eligible_count: 1,
      omitted_count: 1,
      items: [
        {
          rank: 1,
          symbol: "600001",
          name: "Alpha",
          exchange: "SSE",
          close: "12",
          previous_close: "10",
          change: "2",
          change_percent: "20",
          volume: "1000",
          amount: null,
          provider: "akshare",
          source: "eastmoney",
          adjustment: "qfq",
        },
        { symbol: "missing-numbers" },
      ],
    });

    expect(payload?.items).toHaveLength(1);
    expect(payload?.items[0]).toMatchObject({ symbol: "600001", changePercent: 20 });
    expect(payload?.tradeDate).toBe("2026-07-17");
  });

  it("rejects unknown top-level statuses", () => {
    expect(decodeMarketMoversPayload({ status: "provider_live", items: [] })).toBeNull();
  });
});
