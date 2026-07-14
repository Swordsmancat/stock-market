import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import { MobileNavigation } from "./mobile-navigation";

it("renders five fixed labeled destinations without a horizontal scroller", () => {
  render(<MobileNavigation />);

  const navigation = screen.getByRole("navigation");
  const list = within(navigation).getByRole("list");
  const links = within(navigation).getAllByRole("link");

  expect(list).toHaveClass("grid", "grid-cols-5");
  expect(list).not.toHaveClass("overflow-x-auto");
  expect(links.map((link) => link.getAttribute("href"))).toEqual([
    "/",
    "/ai-research",
    "/instruments",
    "/watchlist",
    "/settings",
  ]);
  expect(links.map((link) => link.textContent)).toEqual([
    "Dashboard",
    "AI Research",
    "Instruments",
    "Watchlist",
    "Settings",
  ]);
  expect(links.every((link) => link.querySelector("svg"))).toBe(true);
  expect(links[0]).toHaveAttribute("aria-current", "page");
});
