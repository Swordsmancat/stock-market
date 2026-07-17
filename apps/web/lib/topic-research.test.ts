import { expect, it } from "vitest";

import { decodeTopicResearchPayload } from "./topic-research";

const emptySection = { status: "empty", total: 0, returned: 0, latest_date: null, items: [] };

it("decodes a database-only topic payload", () => {
  const decoded = decodeTopicResearchPayload({
    status: "ready", source: "database", taxonomy_version: "focused-topic-v1",
    topic: "consumption", topics: ["agriculture", "consumption", "real_estate", "nonferrous"], window: "90d",
    period: { start: "2026-04-20", end: "2026-07-18" }, evidence_count: 1, latest_evidence_date: "2026-07-16",
    sections: {
      news: { status: "ready", total: 1, returned: 1, latest_date: "2026-07-16", items: [{
        id: "n1", symbol: "600519", title: "Consumer recovery", url: "https://example.com/n1", source: "eastmoney",
        published_at: "2026-07-16T08:00:00+00:00", summary: "Retail demand", matched_on: { field: "title", keyword: "consumer" },
      }] },
      industry_rankings: emptySection,
      companies: emptySection,
    },
  });

  expect(decoded?.topic).toBe("consumption");
  expect(decoded?.sections.news.items[0].matchedOn.keyword).toBe("consumer");
});

it("rejects non-database and malformed ready sections", () => {
  expect(decodeTopicResearchPayload({ source: "provider" })).toBeNull();
  expect(decodeTopicResearchPayload({
    status: "ready", source: "database", taxonomy_version: "v1", topic: "consumption", topics: [], window: "90d",
    period: { start: "2026-01-01", end: "2026-07-18" }, evidence_count: 1,
    sections: { news: { ...emptySection, status: "ready" }, industry_rankings: emptySection, companies: emptySection },
  })).toBeNull();
});
