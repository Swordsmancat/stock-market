import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
  getBackendApiUrl: () => "http://127.0.0.1:8000",
}));

vi.mock("@/components/watchlist-forms", () => ({
  WatchlistAddForm: () => null,
  WatchlistRemoveButton: () => <button title="Remove">Remove</button>,
  WatchlistEditAlertRulesForm: ({ alertRules = {} }: { alertRules?: Record<string, number> }) => (
    <div>
      {alertRules.price_above !== undefined ? (
        <input readOnly value={String(alertRules.price_above)} />
      ) : null}
      {alertRules.rsi_below !== undefined ? (
        <input readOnly value={String(alertRules.rsi_below)} />
      ) : null}
    </div>
  ),
}));

import WatchlistPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders watchlist instruments with alert status from enriched API payload", async () => {
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
                latest_price: 1666,
                rsi: null,
                alert_status: { triggered: false, rules: [] },
              },
              {
                symbol: "0700",
                name: "Tencent Holdings",
                market: "HK",
                is_active: true,
                alert_rules: { price_above: 400, rsi_below: 30 },
                latest_price: 420.5,
                rsi: 35.0,
                alert_status: {
                  triggered: true,
                  rules: [
                    {
                      key: "price_above",
                      threshold: 400,
                      value: 420.5,
                      triggered: true,
                    },
                    {
                      key: "rsi_below",
                      threshold: 30,
                      value: 35.0,
                      triggered: false,
                    },
                  ],
                },
              },
              {
                symbol: "AAPL",
                name: "Apple Inc.",
                market: "US",
                is_active: true,
                alert_rules: {},
                latest_price: 102,
                rsi: 55.0,
                alert_status: { triggered: false, rules: [] },
              },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await WatchlistPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getAllByText("Watchlist")[0]).toBeInTheDocument();
  expect(screen.getByText("Track your favorite stocks and their latest performance.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "600519" })).toHaveAttribute("href", "/instruments/600519");
  expect(screen.getByRole("link", { name: "0700" })).toHaveAttribute("href", "/instruments/0700");
  expect(screen.getByRole("link", { name: "AAPL" })).toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getByText("Tencent Holdings")).toBeInTheDocument();
  expect(screen.getByDisplayValue("400")).toBeInTheDocument();
  expect(screen.getByDisplayValue("30")).toBeInTheDocument();
  expect(screen.getByText("Alert")).toBeInTheDocument();
  expect(screen.getByText("$1666.00")).toBeInTheDocument();
  expect(screen.getByText("$420.50")).toBeInTheDocument();
  expect(screen.getByText("$102.00")).toBeInTheDocument();
  expect(screen.getByText("35.0")).toBeInTheDocument();
  expect(screen.getAllByTitle("Remove")).toHaveLength(3);
});
