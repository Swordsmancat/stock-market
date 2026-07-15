import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it, vi } from "vitest";
import zhMessages from "../messages/zh.json";
import type { MarketAssistantResponse } from "@/lib/market-assistant";

const { askMarketAssistantMock } = vi.hoisted(() => ({
  askMarketAssistantMock: vi.fn(),
}));

vi.mock("@/lib/market-assistant", () => ({
  askMarketAssistant: askMarketAssistantMock,
}));

import { MarketAssistantCard } from "./market-assistant-card";

afterEach(() => {
  cleanup();
  askMarketAssistantMock.mockReset();
});

function renderChineseMarketAssistantCard(
  researchSnapshotId?: string | null,
  market?: string | null,
) {
  render(
    <NextIntlClientProvider locale="zh" messages={zhMessages}>
      <MarketAssistantCard
        symbol="AAPL"
        locale="zh"
        provider="mock"
        market={market}
        start="2026-01-01"
        end="2026-01-20"
        researchSnapshotId={researchSnapshotId}
      />
    </NextIntlClientProvider>,
  );
}

it("forwards the exact instrument market with assistant questions", async () => {
  askMarketAssistantMock.mockResolvedValue(buildAssistantResponse());
  renderChineseMarketAssistantCard(null, "CN");

  fireEvent.click(screen.getByRole("button", { name: zhMessages.MarketAssistant.submit }));

  await waitFor(() => {
    expect(askMarketAssistantMock).toHaveBeenCalledWith({
      scope: "instrument",
      symbol: "AAPL",
      question: zhMessages.MarketAssistant.defaultQuestion.replace("{symbol}", "AAPL"),
      locale: "zh",
      timeframe: "1d",
      start: "2026-01-01",
      end: "2026-01-20",
      market: "CN",
      provider: "mock",
    });
  });
});

function buildAssistantResponse(overrides: Partial<MarketAssistantResponse> = {}): MarketAssistantResponse {
  return {
    status: "degraded",
    answer_markdown: "### 概览\n基于可用数据整理。",
    symbol: "AAPL",
    as_of: "2026-01-20",
    model: {
      provider: "deterministic",
      name: "market-assistant-deterministic-fallback",
      used_llm: false,
      fallback_reason: "OpenAI-compatible LLM provider is not configured.",
    },
    context: {
      scope: "instrument",
      timeframe: "1d",
      start: "2026-01-01",
      end: "2026-01-20",
      latest_close: 102,
      period_change_pct: 0.99,
      bar_count: 2,
      source: "mock",
      provider: "mock",
      requested_provider: "mock",
      effective_provider: "mock",
    },
    citations: [
      {
        id: "bars_1d:AAPL:2026-01-20",
        label: "Daily bars for AAPL as of 2026-01-20",
        source: "bars_1d",
        url: null,
        source_type: "bars",
        as_of: "2026-01-20",
        provider: "mock",
        excerpt: "Daily bars from 2026-01-01 to 2026-01-20.",
      },
    ],
    diagnostics: [
      {
        source: "news",
        status: "no_data",
        severity: "info",
        code: "SOURCE_NO_DATA",
        message: "No stored news sentiment is available for this symbol.",
      },
    ],
    safety: {
      not_investment_advice: true,
      no_fabricated_market_data: true,
      disclaimer: "以下内容仅用于信息整理和投资者教育，不构成投资建议、收益承诺或买卖指令。",
    },
    ...overrides,
  };
}

it("renders the market assistant empty state and quick prompts", () => {
  renderChineseMarketAssistantCard();

  expect(screen.getByText("AI 市场助手")).toBeInTheDocument();
  expect(screen.getByText("走势总结")).toBeInTheDocument();
  expect(screen.getByText("风险提示")).toBeInTheDocument();
  expect(screen.getByText("数据缺口")).toBeInTheDocument();
  expect(screen.getByLabelText("你的问题")).toHaveValue("请总结 AAPL 近期走势、主要风险和还缺哪些数据。");
  expect(screen.getByText("输入问题后，助手会返回可追溯的分析、引用、诊断和安全声明。")).toBeInTheDocument();
});

it("submits a contextual assistant question and renders traceable output", async () => {
  askMarketAssistantMock.mockResolvedValue(buildAssistantResponse());
  renderChineseMarketAssistantCard();

  fireEvent.change(screen.getByLabelText("你的问题"), {
    target: { value: "请总结近期走势。" },
  });
  fireEvent.click(screen.getByRole("button", { name: "询问助手" }));

  await waitFor(() => {
    expect(askMarketAssistantMock).toHaveBeenCalledWith({
      scope: "instrument",
      symbol: "AAPL",
      question: "请总结近期走势。",
      locale: "zh",
      timeframe: "1d",
      start: "2026-01-01",
      end: "2026-01-20",
      provider: "mock",
    });
  });
  expect(await screen.findByText("降级")).toBeInTheDocument();
  expect(screen.getByText(/基于可用数据整理。/)).toBeInTheDocument();
  expect(screen.getByText("Daily bars for AAPL as of 2026-01-20")).toBeInTheDocument();
  expect(screen.getByText(/type=bars/)).toBeInTheDocument();
  expect(
    screen.getByText(zhMessages.MarketAssistant.diagnosticSourceNoData, {
      exact: false,
    }),
  ).toBeInTheDocument();
  expect(screen.getByText(/不构成投资建议/)).toBeInTheDocument();
});

it("keeps the hidden shortlist snapshot on quick-prompt requests", async () => {
  askMarketAssistantMock.mockResolvedValue(buildAssistantResponse());
  renderChineseMarketAssistantCard("12345678-1234-1234-1234-123456789abc");

  expect(screen.getByText("每日候选快照 12345678...")).toHaveAttribute(
    "data-research-snapshot-id",
    "12345678-1234-1234-1234-123456789abc",
  );
  fireEvent.click(screen.getByRole("button", { name: "数据缺口" }));
  fireEvent.click(screen.getByRole("button", { name: "询问助手" }));

  await waitFor(() => {
    expect(askMarketAssistantMock).toHaveBeenCalledWith({
      scope: "instrument",
      symbol: "AAPL",
      question: "请说明分析 AAPL 时当前还缺少哪些关键数据。",
      locale: "zh",
      timeframe: "1d",
      start: "2026-01-01",
      end: "2026-01-20",
      provider: "mock",
      researchSnapshotId: "12345678-1234-1234-1234-123456789abc",
    });
  });
});

it("localizes shortlist citations and diagnostics without rendering raw snapshot prose", async () => {
  const rawLabel = "Committed daily research shortlist for AAPL on 2026-01-20";
  const rawExcerpt = "Committed research shortlist snapshot evidence: raw JSON.";
  const rawDiagnostic = "The requested research snapshot does not contain the exact symbol.";
  const baseResponse = buildAssistantResponse();
  askMarketAssistantMock.mockResolvedValue({
    ...baseResponse,
    context: {
      ...baseResponse.context,
      research_snapshot: {
        status: "symbol_mismatch",
        applied: false,
        decision_date: "2026-01-20",
      },
    },
    citations: [
      {
        id: "research_shortlist:run:candidate",
        label: rawLabel,
        source: "research_shortlist",
        source_type: "research_shortlist",
        as_of: "2026-01-20",
        excerpt: rawExcerpt,
      },
    ],
    diagnostics: [
      {
        source: "research_shortlist",
        status: "symbol_mismatch",
        severity: "warning",
        code: "RESEARCH_SNAPSHOT_SYMBOL_MISMATCH",
        message: rawDiagnostic,
      },
    ],
  });
  renderChineseMarketAssistantCard("12345678-1234-1234-1234-123456789abc");

  fireEvent.click(screen.getByRole("button", { name: zhMessages.MarketAssistant.submit }));

  const expectedLabel = zhMessages.MarketAssistant.snapshotCitationLabel
    .replace("{symbol}", "AAPL")
    .replace("{date}", "2026-01-20");
  expect(await screen.findByText(expectedLabel)).toBeInTheDocument();
  expect(
    screen.getByText(
      zhMessages.MarketAssistant.diagnosticResearchSnapshotSymbolMismatch,
      { exact: false },
    ),
  ).toBeInTheDocument();
  expect(screen.queryByText(rawLabel)).not.toBeInTheDocument();
  expect(screen.queryByText(rawExcerpt)).not.toBeInTheDocument();
  expect(screen.queryByText(rawDiagnostic)).not.toBeInTheDocument();
});

it("localizes daily-bar provenance diagnostics without rendering backend messages", async () => {
  const diagnostics = [
    {
      source: "database",
      status: "degraded",
      severity: "warning",
      code: "MIXED_DAILY_BAR_PROVENANCE",
      message: "raw mixed provenance backend message",
    },
    {
      source: "database",
      status: "degraded",
      severity: "warning",
      code: "UNKNOWN_DAILY_BAR_PROVENANCE",
      message: "raw unknown provenance backend message",
    },
    {
      source: "bars_1d",
      status: "unavailable",
      severity: "error",
      code: "SOURCE_UNAVAILABLE",
      message: "raw unavailable backend message",
    },
    {
      source: "bars_1d",
      status: "no_data",
      severity: "info",
      code: "SOURCE_NO_DATA",
      message: "raw no-data backend message",
    },
  ];
  askMarketAssistantMock.mockResolvedValue({
    ...buildAssistantResponse(),
    diagnostics,
  });
  renderChineseMarketAssistantCard();

  fireEvent.click(screen.getByRole("button", { name: zhMessages.MarketAssistant.submit }));

  for (const expected of [
    "日线数据来自多个来源或复权批次，仅使用最新的连续可信批次。",
    "已存储日线缺少完整的来源或复权信息。",
    "所需数据源暂时不可用。",
    "该数据源没有可用的已验证数据。",
  ]) {
    expect(await screen.findByText(expected, { exact: false })).toBeInTheDocument();
  }
  for (const diagnostic of diagnostics) {
    expect(screen.queryByText(diagnostic.message)).not.toBeInTheDocument();
  }
});

it("renders citation links and compact research metadata", async () => {
  askMarketAssistantMock.mockResolvedValue(
    buildAssistantResponse({
      citations: [
        {
          id: "news:AAPL:2026-01-20:abc123",
          label: "Apple expands services revenue",
          source: "news",
          url: "https://example.com/aapl-services",
          source_type: "news",
          as_of: "2026-01-20T12:00:00+00:00",
          provider: "mock_news",
          excerpt: "Apple expands services revenue in the quarter.",
        },
      ],
      diagnostics: [
        {
          source: "citations",
          status: "invalid",
          severity: "warning",
          code: "CITATION_UNKNOWN_ID",
          message: "The LLM response referenced an unknown citation.",
        },
      ],
    }),
  );
  renderChineseMarketAssistantCard();

  fireEvent.click(screen.getByRole("button", { name: "询问助手" }));

  const citationLink = await screen.findByRole("link", { name: "Apple expands services revenue" });
  expect(citationLink).toHaveAttribute("href", "https://example.com/aapl-services");
  expect(screen.getByText(/type=news/)).toBeInTheDocument();
  expect(screen.getByText(/provider=mock_news/)).toBeInTheDocument();
  expect(screen.getByText(/Apple expands services revenue in the quarter/)).toBeInTheDocument();
  expect(screen.getByText(/citations \[warning\/CITATION_UNKNOWN_ID\]/)).toBeInTheDocument();
});

it("updates the question from a quick prompt and renders request errors", async () => {
  askMarketAssistantMock.mockRejectedValue(new Error("Backend unavailable"));
  renderChineseMarketAssistantCard();

  fireEvent.click(screen.getByRole("button", { name: "风险提示" }));
  expect(screen.getByLabelText("你的问题")).toHaveValue("请列出 AAPL 当前需要关注的风险点，不要给出买卖建议。");

  fireEvent.click(screen.getByRole("button", { name: "询问助手" }));

  expect(await screen.findByText("AI 助手请求失败：Backend unavailable")).toBeInTheDocument();
});
