import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import WatchlistPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders watchlist instruments with detail links", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            name: "default",
            source: "database",
            items: [
              {
                symbol: "600519",
                name: "Kweichow Moutai",
                market: "CN",
                is_active: true,
                alert_rules: {},
              },
              {
                symbol: "0700",
                name: "Tencent Holdings",
                market: "HK",
                is_active: true,
                alert_rules: { price_above: 400 },
              },
              {
                symbol: "AAPL",
                name: "Apple Inc.",
                market: "US",
                is_active: true,
                alert_rules: {},
              },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await WatchlistPage());

  expect(screen.getAllByText("Watchlist")[0]).toBeInTheDocument();
  expect(screen.getByText("Track your favorite stocks and their latest performance.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "600519" }))
    .toHaveAttribute("href", "/instruments/600519");
  expect(screen.getByRole("link", { name: "0700" }))
    .toHaveAttribute("href", "/instruments/0700");
  expect(screen.getByRole("link", { name: "AAPL" }))
    .toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getByText("Tencent Holdings")).toBeInTheDocument();
  expect(screen.getAllByTitle("Remove")).toHaveLength(3);
});
