import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import { SidebarNavigation } from "./sidebar-navigation";

it("includes market research in the desktop sidebar", () => {
  render(<SidebarNavigation />);

  const navigation = screen.getByRole("navigation");
  const links = within(navigation).getAllByRole("link");

  expect(links.map((link) => link.getAttribute("href"))).toEqual([
    "/",
    "/ai-research",
    "/instruments",
    "/market-research",
    "/watchlist",
    "/settings",
  ]);
  expect(within(navigation).getByRole("link", { name: "Market Research" })).toHaveAttribute(
    "href",
    "/market-research",
  );
  expect(within(navigation).getByRole("link", { name: "Dashboard" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});
