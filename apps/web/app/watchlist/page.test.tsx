import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import WatchlistPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders watchlist instruments with detail links", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/instruments")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [
              { symbol: "600519", name: "Kweichow Moutai", market: "CN" },
              { symbol: "0700", name: "Tencent Holdings", market: "HK" },
              { symbol: "AAPL", name: "Apple Inc.", market: "US" },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await WatchlistPage());

  expect(screen.getByText("关注列表")).toBeInTheDocument();
  expect(screen.getByText("默认关注标的")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "CN - 600519 - Kweichow Moutai" }))
    .toHaveAttribute("href", "/instruments/600519");
  expect(screen.getByRole("link", { name: "HK - 0700 - Tencent Holdings" }))
    .toHaveAttribute("href", "/instruments/0700");
  expect(screen.getByRole("link", { name: "US - AAPL - Apple Inc." }))
    .toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getAllByText("关键变化提醒：等待下一次自动日报刷新后更新。")).toHaveLength(3);
});
