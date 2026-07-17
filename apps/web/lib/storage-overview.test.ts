import { expect, it } from "vitest";

import {
  formatStorageBytes,
  formatStorageCount,
  isStorageOverviewPayload,
} from "./storage-overview";

it("formats compact counts and binary storage sizes", () => {
  expect(formatStorageCount(81_000, "zh-CN")).toContain("8.1");
  expect(formatStorageBytes(49_650_000, "en-US")).toBe("47.3 MB");
  expect(formatStorageBytes(null, "en-US")).toBeNull();
});

it("rejects malformed storage projections", () => {
  expect(isStorageOverviewPayload({ status: "ok", domains: [] })).toBe(false);
  expect(
    isStorageOverviewPayload({
      status: "ok",
      engine: "PostgreSQL",
      row_count_kind: "estimated",
      collected_at: "2026-07-17T10:00:00Z",
      summary: { table_count: 1, estimated_rows: 2 },
      domains: [],
    }),
  ).toBe(true);
});
