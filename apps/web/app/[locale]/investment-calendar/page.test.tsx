import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import InvestmentCalendarPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const payload = {
  status: "ok",
  start: "2026-07-01",
  end: "2026-07-31",
  kind: "economic",
  count: 2,
  truncated: false,
  days: [
    {
      date: "2026-07-16",
      count: 1,
      max_importance: 3,
      items: [
        {
          id: "one",
          kind: "economic",
          date: "2026-07-16",
          time: "10:00",
          title: "China GDP",
          importance: 3,
          country: "China",
          symbol: null,
          company_name: null,
          category: null,
          reference_period: "Q2",
          previous: "5.0",
          forecast: "5.1",
          actual: "5.2",
          unit: "%",
          provider: "eastmoney",
          source_url: "https://example.test/one",
          retrieved_at: "2026-07-16T09:00:00+08:00",
        },
      ],
    },
    {
      date: "2026-07-17",
      count: 1,
      max_importance: 5,
      items: [
        {
          id: "two",
          kind: "economic",
          date: "2026-07-17",
          time: "20:30",
          title: "US retail sales",
          importance: 5,
          country: "United States",
          symbol: null,
          company_name: null,
          category: null,
          reference_period: "June",
          previous: "0.1",
          forecast: "0.2",
          actual: null,
          unit: "%",
          provider: "eastmoney",
          source_url: "https://example.test/two",
          retrieved_at: "2026-07-17T09:00:00+08:00",
        },
      ],
    },
  ],
};

it("renders a month agenda and switches the selected day without refetching", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(payload)),
  );

  render(
    await InvestmentCalendarPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({
        month: "2026-07",
        date: "2026-07-16",
        kind: "economic",
        importance: "0",
      }),
    }),
  );

  expect(screen.getByRole("heading", { name: "Investment Calendar" })).toBeInTheDocument();
  expect(screen.getByText("China GDP")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/investment-calendar?start=2026-07-01&end=2026-07-31&kind=economic&min_importance=0",
    { cache: "no-store" },
  );

  fireEvent.click(screen.getByRole("button", { name: /Friday, July 17, 2026/ }));

  expect(screen.getByText("US retail sales")).toBeInTheDocument();
  expect(screen.queryByText("China GDP")).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(window.location.search).toContain("date=2026-07-17");

  fireEvent.click(screen.getByRole("button", { name: "Company events" }));
  expect(window.location.search).toContain("date=2026-07-17");
});

it("keeps API failure distinct from an empty month", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 503 }));

  render(
    await InvestmentCalendarPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({ month: "2026-07" }),
    }),
  );

  expect(screen.getByText("Investment calendar is unavailable")).toBeInTheDocument();
  expect(screen.queryByText("No stored events match this month and filter.")).not.toBeInTheDocument();
});
