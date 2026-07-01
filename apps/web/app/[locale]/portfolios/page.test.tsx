import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
  getBackendApiUrl: () => "http://127.0.0.1:8000",
}));

vi.mock("@/components/portfolio-forms", () => ({
  PortfolioCreateForm: () => null,
  PortfolioAddPositionForm: () => null,
  PortfolioRemovePositionButton: () => <button title="Remove position">Remove</button>,
  PortfolioRenameForm: () => null,
  PortfolioDeleteButton: () => null,
}));

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
            id: "demo",
            name: "Demo Portfolio",
            base_currency: "USD",
            source: "database",
            summary: {
              total_cost: 1000,
              total_market_value: 1020,
              unrealized_pnl: 20,
              unrealized_return_pct: 0.02,
            },
            positions: [
              {
                symbol: "AAPL",
                market: "US",
                quantity: 10,
                avg_cost: 100,
                latest_price: 102,
                market_value: 1020,
                unrealized_pnl: 20,
                unrealized_return_pct: 0.02,
                weight: 1,
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
    if (url.endsWith("/portfolios")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "database",
            items: [{ id: "demo", name: "Demo Portfolio", base_currency: "USD", is_default: true }],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await PortfoliosPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByText("Portfolios")).toBeInTheDocument();
  expect(screen.getAllByText("Demo Portfolio").length).toBeGreaterThan(0);
  expect(screen.getAllByText("$1,020").length).toBeGreaterThan(0);
  expect(screen.getAllByText("$20").length).toBeGreaterThan(0);
  expect(screen.getAllByText("2.00%").length).toBeGreaterThan(0);
  expect(screen.getByRole("link", { name: "AAPL" })).toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getByText("100.00%")).toBeInTheDocument();
});
