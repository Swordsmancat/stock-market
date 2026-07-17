import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import TopicResearchPage from "./page";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const emptySection = { status: "empty", total: 0, returned: 0, latest_date: null, items: [] };
const payload = {
  status: "ready", source: "database", taxonomy_version: "focused-topic-v1", topic: "consumption",
  topics: ["agriculture", "consumption", "real_estate", "nonferrous"], window: "90d",
  period: { start: "2026-04-20", end: "2026-07-18" }, evidence_count: 4, latest_evidence_date: "2026-07-17",
  safety: { research_only: true, trading_enabled: false },
  sections: {
    news: { status: "ready", total: 1, returned: 1, latest_date: "2026-07-16", items: [{
      id: "n1", symbol: "600519", title: "Consumer recovery", url: "https://example.com/n1", source: "eastmoney",
      published_at: "2026-07-16T16:30:00+00:00", summary: "Retail demand improved.", matched_on: { field: "title", keyword: "consumer" },
    }] },
    industry_rankings: { status: "ready", total: 2, returned: 1, latest_date: "2026-07-17", items: [{
      date: "2026-07-17", rank: 3, code: "BK0001", name: "Food and beverage", change_percent: 1.25,
      provider: "eastmoney", source_url: "https://quote.eastmoney.com", matched_on: { field: "industry_name", keyword: "食品饮料" },
    }] },
    companies: { status: "ready", total: 1, returned: 1, latest_date: "2026-03-31", items: [{
      symbol: "600519", name: "Kweichow Moutai", industry: "Consumer", business_scope: "Spirits", profile: null,
      as_of: "2026-03-31", market: "CN", instrument_name: "Kweichow Moutai", matched_on: { field: "industry", keyword: "consumer" },
    }] },
  },
};

it("renders all stored topic sections with URL-owned GET controls", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(payload)));
  render(await TopicResearchPage({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({ topic: "consumption" }) }));

  expect(screen.getByRole("heading", { name: "Topic Research" })).toBeInTheDocument();
  expect(within(screen.getByRole("group", { name: "Research topic" })).getByRole("link", { name: /Real estate/ })).toHaveAttribute("href", "/topic-research?topic=real_estate");
  expect(within(screen.getByRole("group", { name: "Evidence window" })).getByRole("link", { name: "180 days" })).toHaveAttribute("href", "/topic-research?topic=consumption&window=180d");
  expect(screen.getByRole("link", { name: /Consumer recovery/ })).toHaveAttribute("href", "https://example.com/n1");
  expect(screen.getByText("Food and beverage")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Kweichow Moutai/ })).toHaveAttribute("href", "/instruments/600519?market=CN");
  expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/topic-research?topic=consumption&window=90d", { cache: "no-store" });
  expect(fetchMock.mock.calls.every(([, init]) => (init as RequestInit | undefined)?.method !== "POST")).toBe(true);
});

it("renders independent empty sections without treating them as a failure", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
    ...payload, status: "empty", topic: "real_estate", evidence_count: 0, latest_evidence_date: null,
    sections: { news: emptySection, industry_rankings: emptySection, companies: emptySection },
  })));
  render(await TopicResearchPage({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({ topic: "real_estate" }) }));

  expect(screen.getByText("No stored topic news")).toBeInTheDocument();
  expect(screen.getByText("No matching industry history")).toBeInTheDocument();
  expect(screen.getByText("No related stored companies")).toBeInTheDocument();
  expect(screen.queryByText("Topic research is unavailable")).not.toBeInTheDocument();
});
