import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MarketTicker } from "./market-ticker";

beforeEach(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
});

const tickerItems = [
  {
    code: "cn_shanghai_composite",
    name: "上证指数",
    close: 3100.12,
    change: 12.34,
    changePercent: 0.004,
    region: "CN",
  },
  {
    code: "hk_hang_seng",
    name: "恒生指数",
    close: 18000.5,
    change: -20.1,
    changePercent: -0.0011,
    region: "HK",
  },
  {
    code: "us_sp_500",
    name: "S&P 500",
    close: 5100,
    change: 6.5,
    changePercent: 0.0013,
    region: "US",
  },
];

it("renders all ticker items by default", () => {
  render(<MarketTicker items={tickerItems} />);

  expect(screen.getByText("上证指数")).toBeInTheDocument();
  expect(screen.getByText("恒生指数")).toBeInTheDocument();
  expect(screen.getByText("S&P 500")).toBeInTheDocument();
});

it("filters ticker items by selected market", async () => {
  render(<MarketTicker items={tickerItems} />);

  fireEvent.keyDown(screen.getByRole("combobox"), { key: "ArrowDown" });
  fireEvent.click(await screen.findByText("美股"));

  expect(screen.queryByText("上证指数")).not.toBeInTheDocument();
  expect(screen.queryByText("恒生指数")).not.toBeInTheDocument();
  expect(screen.getByText("S&P 500")).toBeInTheDocument();
});
