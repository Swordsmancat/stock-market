import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import { SidebarNavigation } from "./sidebar-navigation";

it("includes research, movers, calendar, storage, and crawler monitoring in the desktop sidebar", () => {
  render(<SidebarNavigation />);

  const navigation = screen.getByRole("navigation");
  const links = within(navigation).getAllByRole("link");

  expect(links.map((link) => link.getAttribute("href"))).toEqual([
    "/",
    "/ai-research",
    "/instruments",
    "/market-research",
    "/topic-research",
    "/market-movers",
    "/investment-calendar",
    "/storage",
    "/crawler-monitor",
    "/watchlist",
    "/settings",
  ]);
  expect(within(navigation).getByRole("link", { name: "Market Research" })).toHaveAttribute(
    "href",
    "/market-research",
  );
  expect(within(navigation).getByRole("link", { name: "Topic Research" })).toHaveAttribute(
    "href",
    "/topic-research",
  );
  expect(within(navigation).getByRole("link", { name: "Market Movers" })).toHaveAttribute(
    "href",
    "/market-movers",
  );
  expect(within(navigation).getByRole("link", { name: "Data Storage" })).toHaveAttribute(
    "href",
    "/storage",
  );
  expect(within(navigation).getByRole("link", { name: "Investment Calendar" })).toHaveAttribute(
    "href",
    "/investment-calendar",
  );
  expect(within(navigation).getByRole("link", { name: "Crawler Monitor" })).toHaveAttribute(
    "href",
    "/crawler-monitor",
  );
  expect(within(navigation).getByRole("link", { name: "Dashboard" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});
