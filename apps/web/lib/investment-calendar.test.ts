import { describe, expect, it } from "vitest";

import {
  buildCalendarCells,
  isInvestmentCalendarPayload,
  parseInvestmentCalendarQuery,
  shiftMonth,
} from "./investment-calendar";

describe("investment calendar query", () => {
  it("bounds malformed query values and keeps Shanghai dates", () => {
    expect(
      parseInvestmentCalendarQuery(
        { month: "2026-13", date: "bad", kind: "other", importance: "8" },
        new Date("2026-07-16T16:30:00Z"),
      ),
    ).toEqual({
      month: "2026-07",
      start: "2026-07-01",
      end: "2026-07-31",
      date: "2026-07-17",
      kind: "economic",
      importance: 0,
    });
  });

  it("uses the first day for a valid non-current month", () => {
    expect(
      parseInvestmentCalendarQuery(
        { month: "2026-02", kind: "company", importance: "3" },
        new Date("2026-07-16T00:00:00Z"),
      ),
    ).toMatchObject({
      start: "2026-02-01",
      end: "2026-02-28",
      date: "2026-02-01",
      kind: "company",
      importance: 3,
    });
  });
});

it("builds a stable six-week Monday-first grid", () => {
  const cells = buildCalendarCells("2026-07");
  expect(cells).toHaveLength(42);
  expect(cells[0]).toEqual({ date: "2026-06-29", day: 29, inMonth: false });
  expect(cells[2]).toEqual({ date: "2026-07-01", day: 1, inMonth: true });
  expect(cells[41].date).toBe("2026-08-09");
  expect(shiftMonth("2026-01", -1)).toBe("2025-12");
});

it("rejects payloads without normalized day items", () => {
  expect(isInvestmentCalendarPayload({ status: "ok", days: [] })).toBe(false);
  expect(
    isInvestmentCalendarPayload({
      status: "ok",
      start: "2026-07-01",
      end: "2026-07-31",
      kind: "economic",
      count: 0,
      truncated: false,
      days: [],
    }),
  ).toBe(true);
});
