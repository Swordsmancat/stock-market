import { afterEach, expect, it, vi } from "vitest";

import { askMarketAssistant } from "./market-assistant";

afterEach(() => {
  vi.restoreAllMocks();
});
function assistantResponse() {
  return {
    status: "degraded",
    answer_markdown: "Research-only answer.",
    symbol: "600519",
    model: {
      provider: "deterministic",
      name: "market-assistant-deterministic-fallback",
      used_llm: false,
    },
    context: {
      timeframe: "1d",
      start: "2026-01-01",
      end: "2026-01-20",
      bar_count: 2,
    },
    citations: [],
    diagnostics: [],
    safety: {
      not_investment_advice: true,
      no_fabricated_market_data: true,
      disclaimer: "Research only.",
    },
  };
}

it("serializes the optional shortlist identity using the API field name", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(assistantResponse()), { status: 200 }),
  );

  await askMarketAssistant({
    symbol: "600519",
    question: "Summarize the frozen evidence.",
    locale: "en",
    researchSnapshotId: "12345678-1234-1234-1234-123456789abc",
  });

  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [, init] = fetchMock.mock.calls[0];
  expect(JSON.parse(String(init?.body))).toMatchObject({
    symbol: "600519",
    research_snapshot_id: "12345678-1234-1234-1234-123456789abc",
  });
});

it("omits snapshot identity from ordinary assistant requests", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(assistantResponse()), { status: 200 }),
  );

  await askMarketAssistant({
    symbol: "600519",
    question: "Summarize current evidence.",
  });

  const [, init] = fetchMock.mock.calls[0];
  expect(JSON.parse(String(init?.body))).not.toHaveProperty(
    "research_snapshot_id",
  );
});
