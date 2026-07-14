import { expect, it } from "vitest";

import { NAVIGATION_ITEMS } from "./navigation-items";

it("keeps the shared navigation focused on the five personal research destinations", () => {
  const navigationHrefs = NAVIGATION_ITEMS.map((item) => item.href);
  const navigationTitleKeys = NAVIGATION_ITEMS.map((item) => item.titleKey);

  expect(navigationHrefs).toEqual([
    "/",
    "/ai-research",
    "/instruments",
    "/watchlist",
    "/settings",
  ]);
  expect(navigationTitleKeys).toEqual([
    "dashboard",
    "aiResearch",
    "instruments",
    "watchlist",
    "settings",
  ]);
  expect(new Set(navigationHrefs).size).toBe(navigationHrefs.length);
});
