import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
  getBackendApiUrl: () => "http://127.0.0.1:8000",
}));

import AlertsPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders recent alert triggers with linked instruments", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/alerts/triggers/recent?limit=50")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [
              {
                symbol: "AAPL",
                market: "US",
                rule_key: "price_above",
                threshold: 150,
                triggered_at: "2026-01-20T13:45:00+00:00",
              },
              {
                symbol: "0700",
                market: "HK",
                rule_key: "rsi_below",
                threshold: 30,
                triggered_at: "2026-01-20T14:00:00+00:00",
              },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await AlertsPage());

  expect(screen.getByRole("heading", { name: "Alerts" })).toBeInTheDocument();
  expect(screen.getByText("Recent watchlist alert triggers and rule history.")).toBeInTheDocument();
  expect(screen.getByText("Trigger History")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "AAPL" })).toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getByRole("link", { name: "0700" })).toHaveAttribute("href", "/instruments/0700");
  expect(screen.getByText("US")).toBeInTheDocument();
  expect(screen.getByText("HK")).toBeInTheDocument();
  expect(screen.getByText("price above")).toBeInTheDocument();
  expect(screen.getByText("rsi below")).toBeInTheDocument();
  expect(screen.getByText("150")).toBeInTheDocument();
  expect(screen.getByText("30")).toBeInTheDocument();
});

it("renders an empty state when alert triggers are unavailable", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/alerts/triggers/recent?limit=50")) {
      return Promise.resolve(new Response("", { status: 503 }));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await AlertsPage());

  expect(screen.getByText("No recent alert triggers.")).toBeInTheDocument();
  expect(screen.getByText("Configure alert rules on the watchlist to start tracking triggers.")).toBeInTheDocument();
});
