import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import PortfoliosPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders demo portfolio positions and recommendation", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/portfolios/demo")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            name: "Demo Portfolio",
            base_currency: "USD",
            source: "database",
            positions: [
              {
                symbol: "AAPL",
                market: "US",
                quantity: 10,
                avg_cost: 100,
                latest_price: 102,
                market_value: 1020,
              },
            ],
            recommendation: {
              status: "simulated",
              risk_summary: "MVP skeleton only; no live brokerage connection or automatic trading.",
              actions: [
                {
                  symbol: "AAPL",
                  action: "hold",
                  target_weight: 1,
                  reason: "Mock holding remains within the demo portfolio target allocation.",
                },
              ],
            },
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await PortfoliosPage());

  expect(screen.getByText("模拟组合")).toBeInTheDocument();
  expect(screen.getByText("Demo Portfolio")).toBeInTheDocument();
  expect(screen.getByText("基准币种：USD，组合市值：1020，来源：database")).toBeInTheDocument();
  expect(
    screen.getByText((content) =>
      content.includes("US - AAPL") &&
      content.includes("数量：10") &&
      content.includes("市值：1020"),
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      "状态：simulated，风险摘要：MVP skeleton only; no live brokerage connection or automatic trading.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText((content) =>
      content.includes("AAPL：hold") &&
      content.includes("目标权重：1") &&
      content.includes("Mock holding remains within the demo portfolio target allocation."),
    ),
  ).toBeInTheDocument();
});
