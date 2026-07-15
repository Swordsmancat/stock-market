import { describe, expect, it } from "vitest";

import {
  isInstrumentNewsPayload,
  isLatestStoredNewsPayload,
  isNewsRefreshPayload,
} from "./news-payload";

const storedItem = {
  symbol: "600519",
  title: "Stored market update",
  url: "https://example.com/stored-market-update",
  source: "Example Finance",
};

describe("news payload validation", () => {
  it("accepts coherent stored, refresh, and latest projections", () => {
    const news = {
      symbol: "600519",
      source: "database",
      summary: { latest_sentiment: null, article_count: 1 },
      items: [storedItem],
    };

    expect(isInstrumentNewsPayload(news, "600519")).toBe(true);
    expect(
      isNewsRefreshPayload(
        {
          symbol: "600519",
          market: "CN",
          status: "refreshed",
          diagnostics: [],
          news,
        },
        "600519",
        "CN",
      ),
    ).toBe(true);
    expect(
      isLatestStoredNewsPayload({
        source: "database",
        status: "ok",
        count: 1,
        limit: 6,
        items: [
          {
            ...storedItem,
            url: "https://example.com/stored-market-update?id=42#details",
          },
        ],
      }),
    ).toBe(true);
  });

  it("rejects contradictory counts, statuses, symbols, and empty titles", () => {
    expect(
      isInstrumentNewsPayload(
        {
          symbol: "600519",
          summary: { article_count: 2 },
          items: [storedItem],
        },
        "600519",
      ),
    ).toBe(false);
    expect(
      isNewsRefreshPayload(
        {
          symbol: "600519",
          market: "CN",
          status: "no_data",
          diagnostics: [],
          news: { symbol: "600519", items: [storedItem] },
        },
        "600519",
        "CN",
      ),
    ).toBe(false);
    expect(
      isNewsRefreshPayload(
        {
          symbol: "000001",
          market: "CN",
          status: "refreshed",
          diagnostics: [],
          news: { symbol: "000001", items: [storedItem] },
        },
        "600519",
        "CN",
      ),
    ).toBe(false);
    expect(
      isLatestStoredNewsPayload({
        source: "database",
        status: "ok",
        count: 2,
        limit: 6,
        items: [storedItem],
      }),
    ).toBe(false);
    expect(
      isLatestStoredNewsPayload({
        source: "database",
        status: "ok",
        count: 1,
        limit: 6,
        items: [{ ...storedItem, title: "   " }],
      }),
    ).toBe(false);
  });

  it("rejects wrong-market refreshes, credential URLs, and incoherent sentiment", () => {
    const news = {
      symbol: "600519",
      source: "database",
      summary: { latest_sentiment: "neutral", article_count: 1 },
      items: [storedItem],
    };
    expect(
      isNewsRefreshPayload(
        {
          symbol: "600519",
          market: "HK",
          status: "refreshed",
          diagnostics: [],
          news,
        },
        "600519",
        "CN",
      ),
    ).toBe(false);
    expect(
      isLatestStoredNewsPayload({
        source: "database",
        status: "ok",
        count: 1,
        limit: 6,
        items: [{ ...storedItem, url: "https://example.com/a?api_key=secret" }],
      }),
    ).toBe(false);
    expect(
      isLatestStoredNewsPayload({
        source: "database",
        status: "ok",
        count: 1,
        limit: 6,
        items: [{ ...storedItem, url: "https://example.com/a#access_token=secret" }],
      }),
    ).toBe(false);
    expect(
      isLatestStoredNewsPayload({
        source: "database",
        status: "ok",
        count: 1,
        limit: 6,
        items: [{ ...storedItem, sentiment: "positive" }],
      }),
    ).toBe(false);
    expect(
      isLatestStoredNewsPayload({
        source: "database",
        status: "ok",
        count: 1,
        limit: 6,
        items: [{ ...storedItem, sentiment: "negative", confidence: 1.1 }],
      }),
    ).toBe(false);
  });
});
