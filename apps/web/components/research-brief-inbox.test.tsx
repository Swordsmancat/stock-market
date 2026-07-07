import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { routerRefreshMock } = vi.hoisted(() => ({
  routerRefreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: routerRefreshMock,
  }),
}));

import {
  ResearchBriefInbox,
  type ResearchBriefInboxLabels,
  type ResearchBriefPayload,
} from "./research-brief-inbox";

const labels: ResearchBriefInboxLabels = {
  title: "Saved research brief inbox",
  description: "Generate and keep reusable AI summaries.",
  generateAction: "Generate saved brief",
  generating: "Generating...",
  generateSuccess: "Research brief saved.",
  generateFailed: "Could not generate the research brief.",
  loadFailedTitle: "Research brief inbox is unavailable",
  loadFailedDescription: "Could not load saved research briefs.",
  emptyTitle: "No saved research briefs yet.",
  emptyDescription: "Generate a brief after review.",
  createdAt: "Created: {date}",
  modelGenerated: "AI generated",
  modelFallback: "Deterministic fallback",
  modelName: "Model: {name}",
  citationsCount: "Citations",
  sourceGapsCount: "Source gaps",
  diagnosticsCount: "Diagnostics",
  contentTitle: "Saved brief",
  safetyTitle: "Safety boundary",
  safetyNotAdvice: "Not investment advice",
  safetyNoTrading: "No trading instruction",
  safetyNoFabricatedData: "No fabricated macro data",
  unavailableShort: "N/A",
};

const initialBriefs: ResearchBriefPayload[] = [
  {
    id: "brief-1",
    title: "Morning macro evidence",
    brief_type: "evidence_center",
    content_markdown: "### Summary\n- Buffett evidence is ready [research_source_note:note-1].",
    citations: [{ id: "research_source_note:note-1", label: "Buffett note", source: "research_source_notes" }],
    source_summary: { source_gap_count: 2 },
    diagnostics: [],
    model: { name: "research-brief-deterministic-fallback", used_llm: false },
    safety: {
      not_investment_advice: true,
      no_buy_sell_hold: true,
      no_fabricated_macro_data: true,
    },
    created_at: "2026-07-07T01:02:03+00:00",
  },
];

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  routerRefreshMock.mockReset();
});

it("renders saved briefs with model, metrics, content, and safety badges", () => {
  render(
    <ResearchBriefInbox
      labels={labels}
      initialBriefs={initialBriefs}
      provider="mock"
      locale="en-US"
    />,
  );

  expect(screen.getByText("Saved research brief inbox")).toBeInTheDocument();
  expect(screen.getByText("Morning macro evidence")).toBeInTheDocument();
  expect(screen.getByText("Deterministic fallback")).toBeInTheDocument();
  expect(screen.getByText("research_source_note:note-1", { exact: false })).toBeInTheDocument();
  expect(screen.getByText("Not investment advice")).toBeInTheDocument();
});

it("generates a saved brief and prepends it to the inbox", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        id: "brief-2",
        title: "Fresh evidence brief",
        brief_type: "evidence_center",
        content_markdown: "### Summary\n- Fresh macro summary.",
        citations: [],
        source_summary: { source_gap_count: 0 },
        diagnostics: [],
        model: { name: "gpt-4o-mini", used_llm: true },
        safety: { not_investment_advice: true, no_automated_trading: true },
        created_at: "2026-07-07T02:00:00+00:00",
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(
    <ResearchBriefInbox
      labels={labels}
      initialBriefs={[]}
      provider="mock"
      locale="en-US"
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Generate saved brief" }));

  expect(screen.getByRole("button", { name: "Generating..." })).toBeDisabled();
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith("/api/research-briefs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ provider: "mock", locale: "en" }),
    });
  });
  expect(await screen.findByText("Research brief saved.")).toBeInTheDocument();
  expect(screen.getByText("Fresh evidence brief")).toBeInTheDocument();
  expect(screen.getByText("AI generated")).toBeInTheDocument();
  expect(routerRefreshMock).toHaveBeenCalledOnce();
});

it("shows a distinct load failure state", () => {
  render(
    <ResearchBriefInbox
      labels={labels}
      initialBriefs={[]}
      loadFailed
      provider="mock"
      locale="en-US"
    />,
  );

  expect(screen.getByText("Research brief inbox is unavailable")).toBeInTheDocument();
  expect(screen.queryByText("No saved research briefs yet.")).not.toBeInTheDocument();
});
