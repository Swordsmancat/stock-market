import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MarketTicker } from "./market-ticker";

vi.mock("@/context/market-colors-context", () => ({
  useMarketColorsContext: () => ({
    colorScheme: "china",
    setColorScheme: vi.fn(),
    getMovementColor: (value: number) => value >= 0 ? "text-positive" : "text-negative",
    getMovementBg: (value: number) => value >= 0 ? "bg-positive" : "bg-negative",
    colors: {
      up: "text-positive",
      down: "text-negative",
      upBg: "bg-positive",
      downBg: "bg-negative",
    },
  }),
}));

function getTickerMovementElement(textFragment: string): HTMLElement {
  return screen.getByText((_content, element) => {
    return element?.tagName.toLowerCase() === "span" && Boolean(element.textContent?.includes(textFragment));
  });
}

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
    status: "ok",
    freshness: "fresh",
    source: "database",
    provider: "yfinance",
    effective_provider: "yfinance",
  },
  {
    code: "hk_hang_seng",
    name: "恒生指数",
    close: 18000.5,
    change: -20.1,
    changePercent: -0.0011,
    region: "HK",
    status: "ok",
    freshness: "delayed",
    source: "provider",
    provider: "akshare",
    effective_provider: "akshare",
  },
  {
    code: "us_sp_500",
    name: "S&P 500",
    close: 5100,
    change: 6.5,
    changePercent: 0.0013,
    region: "US",
    status: "ok",
    freshness: "fresh",
    source: "provider",
    provider: "yfinance",
    effective_provider: "yfinance",
  },
  {
    code: "cn_csi_500",
    name: "CSI 500",
    close: null,
    change: null,
    changePercent: null,
    region: "CN",
    status: "no_data",
    freshness: "no_data",
    source: "none",
    provider: "mock",
    effective_provider: "mock",
    no_data_reason: "provider returned no rows",
  },
];

it("renders all ticker items by default", () => {
  render(<MarketTicker items={tickerItems} />);

  expect(screen.getByText("上证指数")).toBeInTheDocument();
  expect(screen.getByText("恒生指数")).toBeInTheDocument();
  expect(screen.getByText("S&P 500")).toBeInTheDocument();
  expect(getTickerMovementElement("+12.34")).toHaveClass("text-positive");
  expect(getTickerMovementElement("-20.10")).toHaveClass("text-negative");
  expect(getTickerMovementElement("(--)")).toHaveClass("text-gray-300");
  expect(screen.getByLabelText(/上证指数.*provider: yfinance/)).toBeInTheDocument();
  expect(screen.getByText(/source: database/)).toBeInTheDocument();
  expect(screen.getByLabelText(/CSI 500.*provider returned no rows/)).toBeInTheDocument();
});

it("filters ticker items by selected market", async () => {
  render(<MarketTicker items={tickerItems} />);

  fireEvent.keyDown(screen.getByRole("combobox"), { key: "ArrowDown" });
  fireEvent.click(await screen.findByText("美股"));

  expect(screen.queryByText("上证指数")).not.toBeInTheDocument();
  expect(screen.queryByText("恒生指数")).not.toBeInTheDocument();
  expect(screen.getByText("S&P 500")).toBeInTheDocument();
});
