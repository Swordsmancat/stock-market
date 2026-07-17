import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

import MarketResearchPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const calendarPayload = {
  status: "ok",
  start: "2026-07-01",
  end: "2026-07-31",
  count: 1,
  countries: ["CN"],
  items: [
    {
      id: "calendar-1",
      country: "CN",
      name: "China GDP",
      reference_period: "Q2",
      importance: 5,
      scheduled_at: "2026-07-17T02:00:00+00:00",
      previous: "5.4",
      forecast: "5.1",
      actual: null,
      unit: "%",
    },
  ],
};

const rankingPayload = {
  status: "ok",
  provider: "eastmoney",
  taxonomy: "eastmoney_industry_level_1",
  source_url: "https://quote.eastmoney.com/center/gridlist.html#industry_board_1",
  retrieved_at: "2026-07-17T10:22:00+00:00",
  dates: ["2026-07-17"],
  limit: 20,
  items: [
    {
      date: "2026-07-17",
      rank: 1,
      code: "BK1",
      name: "Banking",
      change_percent: "1.24",
    },
  ],
};

it("owns the calendar and industry ranking reads outside macro research", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/economic-calendar/events?")) {
      return Promise.resolve(new Response(JSON.stringify(calendarPayload)));
    }
    if (url.endsWith("/sectors/industry-rankings?days=20&limit=20")) {
      return Promise.resolve(new Response(JSON.stringify(rankingPayload)));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await MarketResearchPage({
      params: Promise.resolve({ locale: "en" }),
    }),
  );

  expect(screen.getByRole("heading", { name: "Market Research" })).toBeInTheDocument();
  expect(screen.getByText("Economic release calendar")).toBeInTheDocument();
  expect(screen.getByText("Industry gain ranking history")).toBeInTheDocument();
  expect(screen.getByText("China GDP")).toBeInTheDocument();
  expect(screen.getByText("Banking")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Macro Research" })).toHaveAttribute("href", "/evidence");
  expect(screen.getByRole("link", { name: "Topic Research" })).toHaveAttribute("href", "/topic-research");
  expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/economic-calendar/events?"))).toBe(true);
  expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/sectors/industry-rankings?"))).toBe(true);
});

it("keeps both failed states explicit", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 503 }));

  render(
    await MarketResearchPage({
      params: Promise.resolve({ locale: "en" }),
    }),
  );

  expect(screen.getByText("Economic calendar is unavailable")).toBeInTheDocument();
  expect(screen.getByText("Industry rankings could not be loaded")).toBeInTheDocument();
});
