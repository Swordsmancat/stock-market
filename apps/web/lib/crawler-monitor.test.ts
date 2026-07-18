import { expect, it } from "vitest";

import { formatCrawlerDuration, isCrawlerMonitorPayload } from "./crawler-monitor";

const item = {
  id: "market_cn",
  status: "healthy",
  task_name: "ingestion.ingest_market_data",
  scope: "CN",
  provider: "akshare",
  cadence: "daily",
  latest_task_run_id: "run-1",
  started_at: "2026-07-17T10:00:00+00:00",
  finished_at: "2026-07-17T10:01:00+00:00",
  heartbeat_at: null,
  duration_ms: 60_000,
  progress: null,
  recent_failure_count: 0,
  diagnostic_code: null,
  error_summary: null,
};

it("accepts only the complete curated crawler projection", () => {
  const ids = [
    "market_cn",
    "market_us",
    "market_hk",
    "universe_cn",
    "fund_index_cn",
    "evidence_incremental",
    "fundamental_shard",
    "official_disclosures",
    "eastmoney_calendar",
    "eastmoney_industry",
    "eastmoney_news",
    "eastmoney_fundamentals",
  ];
  const payload = {
    status: "ok",
    generated_at: "2026-07-17T12:00:00+00:00",
    summary: { total: 12, running: 0, healthy: 12, attention: 0, recent_failures: 0 },
    items: ids.map((id) => ({ ...item, id })),
  };

  expect(isCrawlerMonitorPayload(payload)).toBe(true);
  expect(isCrawlerMonitorPayload({ ...payload, items: payload.items.slice(0, 11) })).toBe(false);
  expect(
    isCrawlerMonitorPayload({
      ...payload,
      items: payload.items.map((entry, index) =>
        index === 0 ? { ...entry, status: "succeeded" } : entry,
      ),
    }),
  ).toBe(false);
});

it("formats bounded human-readable durations", () => {
  expect(formatCrawlerDuration(35_000, "en-US")).toBe("35s");
  expect(formatCrawlerDuration(3_600_000 + 120_000, "en-US")).toBe("1h 2m");
  expect(formatCrawlerDuration(3_600_000 + 120_000, "zh-CN")).toBe("1小时 2分钟");
  expect(formatCrawlerDuration(null, "en-US")).toBeNull();
});
