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

  expect(screen.getByText("关注列表")).toBeInTheDocument();
  expect(screen.getByText("默认关注标的")).toBeInTheDocument();
  expect(screen.getByText("列表：default，来源：database")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "CN - 600519 - Kweichow Moutai" }))
    .toHaveAttribute("href", "/instruments/600519");
  expect(screen.getByRole("link", { name: "HK - 0700 - Tencent Holdings" }))
    .toHaveAttribute("href", "/instruments/0700");
  expect(screen.getByRole("link", { name: "US - AAPL - Apple Inc." }))
    .toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getByText("提醒规则：已配置")).toBeInTheDocument();
  expect(screen.getAllByText("提醒规则：未配置，等待后续价格/指标提醒。")).toHaveLength(2);
});
