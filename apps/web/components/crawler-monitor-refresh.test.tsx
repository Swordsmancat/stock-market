import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { CrawlerMonitorRefresh } from "./crawler-monitor-refresh";

afterEach(() => {
  vi.restoreAllMocks();
});

it("offers manual refresh and schedules a 30-second read refresh", () => {
  const intervalSpy = vi.spyOn(window, "setInterval");

  render(<CrawlerMonitorRefresh label="Refresh crawler status" />);

  const button = screen.getByRole("button", { name: "Refresh crawler status" });
  expect(button.querySelector("svg")).toBeInTheDocument();
  expect(intervalSpy).toHaveBeenCalledWith(expect.any(Function), 30_000);
  fireEvent.click(button);
});
