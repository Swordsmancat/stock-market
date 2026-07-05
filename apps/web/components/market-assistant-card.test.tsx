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

function renderChineseMarketAssistantCard() {
  render(
    <NextIntlClientProvider locale="zh" messages={zhMessages}>
      <MarketAssistantCard
        symbol="AAPL"
        locale="zh"
        provider="mock"
        start="2026-01-01"
        end="2026-01-20"
      />
    </NextIntlClientProvider>,
  );
}

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
  expect(screen.getByText(/news \[info\/SOURCE_NO_DATA\]: No stored news sentiment/)).toBeInTheDocument();
  expect(screen.getByText(/不构成投资建议/)).toBeInTheDocument();
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
