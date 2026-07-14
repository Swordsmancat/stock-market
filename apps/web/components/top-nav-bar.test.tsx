import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

vi.mock("@/components/global-search", () => ({
  GlobalSearch: () => <button type="button">Global search</button>,
}));
vi.mock("@/components/notification-bell", () => ({
  NotificationBell: () => <button type="button">Notifications</button>,
}));
vi.mock("@/components/language-switcher", () => ({
  LanguageSwitcher: () => <button type="button">Language</button>,
}));
vi.mock("@/components/mode-toggle", () => ({
  ModeToggle: () => <button type="button">Theme</button>,
}));

import { TopNavBar } from "./top-nav-bar";

it("keeps the personal shell controls without rendering a fake account menu", () => {
  render(<TopNavBar />);

  expect(screen.getByRole("link", { name: "StockAI Hub" })).toHaveAttribute("href", "/");
  expect(screen.getByRole("button", { name: "Global search" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Language" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Theme" })).toBeInTheDocument();
  expect(screen.queryByText("User")).not.toBeInTheDocument();
  expect(screen.queryByText("user@example.com")).not.toBeInTheDocument();
  expect(screen.queryByText("Profile")).not.toBeInTheDocument();
  expect(screen.queryByText("Log out")).not.toBeInTheDocument();
});
