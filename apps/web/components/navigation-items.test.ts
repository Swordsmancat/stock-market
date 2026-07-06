import { expect, it } from "vitest";

import { NAVIGATION_ITEMS } from "./navigation-items";

it("keeps the shared navigation configuration complete and stable", () => {
  const navigationHrefs = NAVIGATION_ITEMS.map((item) => item.href);
  const navigationTitleKeys = NAVIGATION_ITEMS.map((item) => item.titleKey);

  expect(navigationHrefs).toEqual([
    "/",
    "/instruments",
    "/evidence",
    "/watchlist",
    "/portfolios",
    "/reports",
    "/alerts",
    "/task-runs",
    "/settings",
  ]);
  expect(navigationTitleKeys).toContain("evidence");
  expect(navigationTitleKeys).toContain("taskRuns");
  expect(new Set(navigationHrefs).size).toBe(navigationHrefs.length);
});
