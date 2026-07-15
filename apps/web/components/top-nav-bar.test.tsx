import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

vi.mock("@/components/notification-bell", () => ({
  NotificationBell: () => <button type="button">Notifications</button>,
}));
vi.mock("@/components/language-switcher", () => ({
  LanguageSwitcher: () => <button type="button">Language</button>,
}));
vi.mock("@/components/mode-toggle", () => ({
  ModeToggle: () => <button type="button">Theme</button>,
}));
vi.mock("@/app/[locale]/actions", () => ({
  searchInstrumentAction: vi.fn(),
}));

import { TopNavBar } from "./top-nav-bar";

it("keeps independently interactive personal shell controls without a fake account menu", async () => {
  render(await TopNavBar());

  expect(screen.getByRole("link", { name: "StockAI Hub" })).toHaveAttribute("href", "/");
  const searchButton = screen.getByRole("button", { name: /Search stocks/ });
  expect(searchButton).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Language" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Theme" })).toBeInTheDocument();
  expect(screen.queryByText("User")).not.toBeInTheDocument();
  expect(screen.queryByText("user@example.com")).not.toBeInTheDocument();
  expect(screen.queryByText("Profile")).not.toBeInTheDocument();
  expect(screen.queryByText("Log out")).not.toBeInTheDocument();

  fireEvent.click(searchButton);
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("Enter symbol, e.g. AAPL")).toBeInTheDocument();
});
