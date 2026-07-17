import { expect, it } from "vitest";

import { NAVIGATION_ITEMS } from "./navigation-items";

it("keeps one ordered navigation source with desktop-only research utility routes", () => {
  const navigationHrefs = NAVIGATION_ITEMS.map((item) => item.href);
  const navigationTitleKeys = NAVIGATION_ITEMS.map((item) => item.titleKey);

  expect(navigationHrefs).toEqual([
    "/",
    "/ai-research",
    "/instruments",
    "/market-research",
    "/topic-research",
    "/market-movers",
    "/storage",
    "/watchlist",
    "/settings",
  ]);
  expect(navigationTitleKeys).toEqual([
    "dashboard",
    "aiResearch",
    "instruments",
    "marketResearch",
    "topicResearch",
    "marketMovers",
    "storage",
    "watchlist",
    "settings",
  ]);
  expect(NAVIGATION_ITEMS.find((item) => item.href === "/market-research")?.mobile).toBe(false);
  expect(NAVIGATION_ITEMS.find((item) => item.href === "/topic-research")?.mobile).toBe(false);
  expect(NAVIGATION_ITEMS.find((item) => item.href === "/market-movers")?.mobile).toBe(false);
  expect(NAVIGATION_ITEMS.find((item) => item.href === "/storage")?.mobile).toBe(false);
  expect(new Set(navigationHrefs).size).toBe(navigationHrefs.length);
});
