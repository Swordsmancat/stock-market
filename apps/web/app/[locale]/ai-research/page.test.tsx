import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { Children, isValidElement, type ReactElement, type ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import enMessages from "../../../messages/en.json";
import type { DailyResearchShortlistPayload } from "@/lib/daily-research-shortlist";
import type { MarketAssistantResponse } from "@/lib/market-assistant";
import type { ResearchShortlistOutcomeTrackingPayload } from "@/lib/research-shortlist-outcomes";
import { ResearchShortlistOutcomePanel } from "@/components/research-shortlist-outcome-panel";

const { askMarketAssistantMock } = vi.hoisted(() => ({
  askMarketAssistantMock: vi.fn(),
}));

vi.mock("@/lib/backend-api", () => ({
  backendFetch: (path: string, init?: RequestInit) => globalThis.fetch(path, init),
}));

vi.mock("@/lib/platform-settings-store", () => ({
  getPlatformSettings: async () => ({
    market_data_provider: "yfinance",
    llm_provider: "mock",
    llm_api_key: "",
    llm_api_base: "https://api.openai.com/v1",
    akshare_enabled: false,
    tushare_token: "",
    tushare_http_url: "",
    color_scheme: "china",
    favorite_macro_indicator_codes: ["buffett_indicator_us", "us_10y_yield"],
    llm_api_key_configured: false,
    tushare_token_configured: false,
    market_data_provider_capabilities: [],
  }),
}));

vi.mock("@/lib/market-assistant", () => ({
  askMarketAssistant: askMarketAssistantMock,
}));

import AiResearchPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  askMarketAssistantMock.mockReset();
});

function createAssistantResponse(overrides: Partial<MarketAssistantResponse> = {}): MarketAssistantResponse {
  return {
    status: "degraded",
    answer_markdown: "Research-only answer with cited local evidence.",
    symbol: "AAPL",
    as_of: "2026-01-02",
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
      end: "2026-01-02",
      latest_close: 102,
      period_change_pct: 1.2,
      bar_count: 2,
      source: "database",
      provider: "yfinance",
      requested_provider: "yfinance",
      effective_provider: "yfinance",
    },
    citations: [
      {
        id: "bars_1d:AAPL:2026-01-02",
        label: "Daily bars for AAPL as of 2026-01-02",
        source: "bars_1d",
        source_type: "bars",
        as_of: "2026-01-02",
        provider: "yfinance",
      },
    ],
    diagnostics: [
      {
        source: "fundamentals",
        status: "no_data",
        severity: "info",
        code: "SOURCE_NO_DATA",
        message: "No stored fundamentals are available.",
      },
    ],
    safety: {
      not_investment_advice: true,
      no_fabricated_market_data: true,
      disclaimer: "Research only. Not investment advice.",
    },
    ...overrides,
  };
}

function createMarketOverviewPayload() {
  const macroIndicators = [
    {
      code: "buffett_indicator_us",
      name: "Buffett Indicator - US",
      region: "US",
      category: "valuation",
      status: "ok",
      value: 188.5,
      unit: "percent",
      as_of: "2026-01-02",
      source: "Audited seed: World Bank market cap and GDP",
      no_data_reason: null,
    },
    {
      code: "buffett_indicator_cn",
      name: "Buffett Indicator - CN",
      region: "CN",
      category: "valuation",
      status: "no_data",
      value: null,
      unit: "percent",
      as_of: null,
      source: null,
      no_data_reason: "No audited observation has been seeded for this indicator yet.",
    },
    {
      code: "us_10y_yield",
      name: "US 10Y Treasury Yield",
      region: "US",
      category: "rates",
      status: "ok",
      value: 4.25,
      unit: "percent",
      as_of: "2026-01-02",
      source: "Audited seed: FRED DGS10",
      no_data_reason: null,
    },
  ];

  return {
    generated_at: "2026-01-02T00:00:00+00:00",
    provider: "yfinance",
    followed: {
      items: [
        {
          symbol: "AAPL",
          name: "Apple Inc.",
          market: "US",
          freshness: "fresh",
          status: "ok",
          latest: { timestamp: "2026-01-02", close: 102 },
        },
        {
          symbol: "0700",
          name: "Tencent Holdings",
          market: "HK",
          freshness: "stale",
          status: "ok",
          latest: { timestamp: "2025-12-30", close: 420 },
        },
      ],
    },
    macro_indicators: { items: macroIndicators },
    valuation_indicators: { items: macroIndicators },
    dashboard_brief: {
      diagnostics: [
        {
          source: "market_indicators",
          status: "no_data",
          severity: "info",
          code: "MACRO_INDICATOR_NO_DATA",
          message: "Some macro indicators do not have audited observations yet.",
        },
      ],
    },
    diagnostics: [],
  };
}

function createOfficialSourceStatusPayload() {
  return {
    status: "degraded",
    citation_policy: "Only stored local macro observations are AI citations.",
    providers: [
      {
        provider: "fred",
        label: "FRED US macro",
        status: "needs_configuration",
        configured: false,
        can_refresh_from_browser: false,
        credential_required: true,
        evidence_count: 1,
        latest_as_of: "2026-01-02",
        source_frequency: "daily_or_monthly",
        indicator_codes: ["us_10y_yield", "us_cpi_yoy"],
        missing_indicator_codes: ["us_cpi_yoy"],
        recommended_next_action: "Set FRED_API_KEY, then run a dry-run refresh from Macro Research.",
        citation_policy: "Readiness guidance only; cite stored observations after import.",
      },
      {
        provider: "world_bank",
        label: "World Bank Buffett Indicator",
        status: "degraded",
        configured: true,
        can_refresh_from_browser: true,
        credential_required: false,
        evidence_count: 0,
        latest_as_of: null,
        source_frequency: "annual_lagged",
        indicator_codes: ["buffett_indicator_us", "buffett_indicator_cn", "buffett_indicator_hk"],
        missing_indicator_codes: ["buffett_indicator_us", "buffett_indicator_cn", "buffett_indicator_hk"],
        recommended_next_action: "Run World Bank dry-run, then write refresh for missing Buffett Indicator regions.",
        citation_policy: "Readiness guidance only; cite stored observations after import.",
      },
    ],
  };
}

function createStockFundFlowPayload() {
  return {
    status: "ok",
    data_mode: "delayed",
    source: "fake_stock_fund_flow",
    provider: "akshare",
    requested_provider: "akshare",
    effective_provider: "akshare",
    as_of: "2026-07-09T09:30:00+00:00",
    generated_at: "2026-07-09T09:31:00+00:00",
    market: "CN",
    window: "today",
    availability: { status: "delayed", reason: null },
    provider_capabilities: {
      stock_fund_flow: { status: "delayed" },
      citation: { status: "not_citable" },
    },
    message: "Fake stock fund-flow rows.",
    count: 1,
    items: [
      {
        symbol: "600519",
        name: "Kweichow Moutai",
        rank: 1,
        latest_price: 1688.5,
        change_percent: 1.25,
        net_flow_amount: 123456789,
        main_net_flow_amount: 123456789,
        currency: "CNY",
        flow_window: "today",
      },
    ],
  };
}

function createLimitUpReasonsPayload() {
  return {
    status: "ok",
    data_mode: "delayed",
    source: "fake_limit_up_reasons",
    provider: "akshare",
    requested_provider: "akshare",
    effective_provider: "akshare",
    as_of: "2026-07-09T09:30:00+00:00",
    generated_at: "2026-07-09T09:31:00+00:00",
    market: "CN",
    window: "today",
    trade_date: "2026-07-09",
    availability: { status: "delayed", reason: null, reason_detail: "available" },
    provider_capabilities: {
      limit_up_reasons: { status: "delayed" },
      citation: { status: "not_citable" },
    },
    message: "Fake limit-up reason rows.",
    count: 1,
    items: [
      {
        symbol: "002001",
        name: "Test Limit",
        rank: 1,
        trade_date: "2026-07-09",
        change_percent: 10,
        reason: "AI computing",
        sector: "Software",
        consecutive_limit_up_count: 2,
      },
    ],
  };
}

function createDragonTigerPayload() {
  return {
    status: "ok",
    data_mode: "delayed",
    source: "fake_dragon_tiger_list",
    provider: "akshare",
    requested_provider: "akshare",
    effective_provider: "akshare",
    as_of: "2026-07-09T09:30:00+00:00",
    generated_at: "2026-07-09T09:31:00+00:00",
    market: "CN",
    window: "today",
    trade_date: "2026-07-09",
    availability: { status: "delayed", reason: null, dragon_tiger_list: "available" },
    provider_capabilities: {
      dragon_tiger_list: { status: "delayed" },
      citation: { status: "not_citable" },
    },
    message: "Fake Dragon Tiger List rows.",
    count: 1,
    items: [
      {
        symbol: "600519",
        name: "Kweichow Moutai",
        rank: 1,
        trade_date: "2026-07-09",
        change_percent: 3.2,
        net_buy_amount: 123000000,
        reason: "Daily price deviation reached threshold.",
        department_name: "Test brokerage seat",
        department_rank: 1,
      },
    ],
  };
}

function createBlockTradesPayload() {
  return {
    status: "ok",
    data_mode: "delayed",
    source: "fake_block_trades",
    provider: "akshare",
    requested_provider: "akshare",
    effective_provider: "akshare",
    as_of: "2026-07-09T09:30:00+00:00",
    generated_at: "2026-07-09T09:31:00+00:00",
    market: "CN",
    window: "today",
    trade_date: "2026-07-09",
    availability: { status: "delayed", reason: null, block_trades: "available" },
    provider_capabilities: {
      block_trades: { status: "delayed" },
      citation: { status: "not_citable" },
    },
    message: "Fake block-trade rows.",
    count: 1,
    items: [
      {
        symbol: "000001",
        name: "Ping An Bank",
        rank: 1,
        trade_date: "2026-07-09",
        trade_price: 11.8,
        amount: 11800000,
        buyer: "Buyer seat",
        seller: "Seller seat",
        market: "A股",
      },
    ],
  };
}

function createEvidenceCoveragePayload() {
  const dimension = {
    ready_count: 5000,
    missing_count: 200,
    total_count: 5200,
    coverage_ratio: 0.962,
    threshold: 0.95,
    passes_threshold: true,
    by_exchange: {
      SSE: { ready_count: 2200, total_count: 2300, coverage_ratio: 0.957 },
      SZSE: { ready_count: 2550, total_count: 2650, coverage_ratio: 0.962 },
      BSE: { ready_count: 250, total_count: 250, coverage_ratio: 1 },
    },
  };
  return {
    status: "ok",
    market: "CN",
    provider: "akshare",
    as_of: "2026-07-10",
    universe: { active_count: 5200, exchange_counts: { SSE: 2300, SZSE: 2650, BSE: 250 } },
    evidence: {
      daily_bars: dimension,
      technical_indicators: { ...dimension, threshold: 0.9 },
      fundamentals: { ...dimension, threshold: 0.8 },
    },
    latest_run: null,
  };
}

function createDailyShortlistPayload(): DailyResearchShortlistPayload {
  return {
    status: "ok",
    research_signal_only: true,
    run: {
      id: "daily-run-1",
      decision_date: "2026-07-10",
      generated_at: "2026-07-10T08:30:00Z",
      market: "CN",
      profile_id: "balanced_research",
      scoring_model: "daily_research_score_v1",
      shortlist_limit: 10,
      locale: "zh",
      counts: { candidate_count: 5200, evaluated_count: 5000, matched_count: 12, returned_count: 1 },
      coverage: { status: "ok", ready: true },
      model: { used_llm: false, name: "deterministic-stock-discovery-v1" },
      explanation_markdown: "不应直接显示在英文页面的中文持久化解释。",
      diagnostics: [
        {
          code: "UNKNOWN_PAGE_DIAGNOSTIC",
          message: "不应直接显示在英文页面的中文未知诊断。",
        },
      ],
      safety: { disclaimer: "不应直接显示在英文页面的中文免责声明。" },
    },
    items: [
      {
        id: "candidate-600519",
        symbol: "600519",
        name: "Kweichow Moutai",
        market: "CN",
        rank: 1,
        total_score: 0.8732,
        minimum_rule_buffer: 0.61,
        supporting_factors: [{ code: "min_net_margin", buffer: 0.92 }],
        opposing_factors: [{ code: "max_pe_ratio", buffer: 0.61 }],
        data_gaps: [
          {
            code: "UNKNOWN_PAGE_GAP",
            message: "不应直接显示在英文页面的中文未知缺口。",
          },
        ],
        invalidation_conditions: [
          {
            code: "UNKNOWN_PAGE_RULE",
            message: "不应直接显示在英文页面的中文未知失效条件。",
          },
        ],
        entry_observation: { trade_date: "2026-07-10", close: 1688.5 },
        evidence_citations: ["bars_1d:600519:2026-07-10"],
      },
    ],
  };
}

function createOutcomeTrackingPayload(
  runId = "daily-run-1",
  symbol = "600519",
  name = "Kweichow Moutai",
): ResearchShortlistOutcomeTrackingPayload {
  const summaries = ([5, 20, 60] as const).map((horizon) => ({
    horizon_sessions: horizon,
    total_count: 1,
    evaluated_count: 0,
    pending_count: 1,
    blocked_count: 0,
    return_sample_size: 0,
    benchmark_sample_size: 0,
    positive_return_ratio: null,
    mean_return_ratio: null,
    median_return_ratio: null,
    mean_drawdown_ratio: null,
    mean_excess_return_ratio: null,
  }));
  return {
    status: "ok",
    as_of: "2026-07-20",
    market: "CN",
    profile_id: "balanced_research",
    research_signal_only: true,
    latest: {
      status: "ok",
      as_of: "2026-07-20",
      research_signal_only: true,
      run: {
        id: runId,
        decision_date: "2026-07-10",
        market: "CN",
        profile_id: "balanced_research",
      },
      items: [
        {
          candidate_id: `candidate-${symbol}`,
          instrument_id: `instrument-${symbol}`,
          symbol,
          name,
          rank: 1,
          entry_trade_date: "2026-07-10",
          horizons: ([5, 20, 60] as const).map((horizon) => ({
            horizon_sessions: horizon,
            status: "pending",
            available_forward_bars: 0,
            ready_for_evaluation: false,
            benchmark: null,
            diagnostics: [],
          })),
        },
      ],
      summaries,
    },
    history: [],
    limit: 10,
    offset: 0,
    has_more: false,
  };
}

async function renderAiResearchPage() {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {await AiResearchPage({ params: Promise.resolve({ locale: "en" }) })}
    </NextIntlClientProvider>,
  );
}

function getOutcomePanelElement(page: ReactElement): ReactElement {
  const children = Children.toArray(
    (page.props as { children?: ReactNode }).children,
  );
  const outcome = children.find(
    (child) => isValidElement(child) && child.type === ResearchShortlistOutcomePanel,
  );
  if (!isValidElement(outcome)) {
    throw new Error("Outcome panel element was not found");
  }
  return outcome;
}

it("renders the AI research desk with watchlist, signal, macro, and source-gap context", async () => {
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
                symbol: "AAPL",
                name: "Apple Inc.",
                market: "US",
                is_active: true,
                latest_price: 102,
                rsi: 55,
                alert_status: { triggered: false, rules: [] },
              },
              {
                symbol: "0700",
                name: "Tencent Holdings",
                market: "HK",
                is_active: true,
                latest_price: 420,
                rsi: 48,
                alert_status: { triggered: true, rules: [] },
              },
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/dashboard/market-overview?provider=yfinance")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketOverviewPayload())));
    }
    if (url.endsWith("/market-indicators/official-sources/status")) {
      return Promise.resolve(new Response(JSON.stringify(createOfficialSourceStatusPayload())));
    }
    if (url.endsWith("/market-daily-data/fund-flow/stocks?market=CN&window=today&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createStockFundFlowPayload())));
    }
    if (url.endsWith("/market-daily-data/limit-up-reasons?market=CN&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createLimitUpReasonsPayload())));
    }
    if (url.endsWith("/market-daily-data/dragon-tiger-list?market=CN&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createDragonTigerPayload())));
    }
    if (url.endsWith("/market-daily-data/block-trades?market=CN&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createBlockTradesPayload())));
    }
    if (url.endsWith("/stock-selection/evidence-coverage?market=CN&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createEvidenceCoveragePayload())));
    }
    if (url.endsWith("/research-shortlists/latest?market=CN&profile_id=balanced_research")) {
      return Promise.resolve(new Response(JSON.stringify(createDailyShortlistPayload())));
    }
    if (url.endsWith("/research-shortlists/tracking?market=CN&profile_id=balanced_research&limit=10&offset=0")) {
      return Promise.resolve(new Response(JSON.stringify(createOutcomeTrackingPayload())));
    }
    if (url.includes("/recommendations?symbols=AAPL%2C0700&limit=6")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "ok",
            generated_at: "2026-01-02T00:00:00Z",
            diagnostics: [
              {
                source: "recommendations",
                status: "partial",
                severity: "info",
                code: "SIGNAL_SAMPLE_LIMITED",
                message: "Signals are deterministic research inputs only.",
              },
            ],
            items: [
              {
                symbol: "AAPL",
                type: "breakout",
                title: "AAPL crossed above its moving average",
                reason: "Price moved above a recent moving-average reference with improving volume.",
                confidence: 0.82,
                timestamp: "2026-01-02T00:00:00Z",
                data: { close: 102 },
              },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  const consoleErrorMock = vi.spyOn(console, "error").mockImplementation(() => undefined);

  await renderAiResearchPage();

  expect(
    consoleErrorMock.mock.calls.some((call) =>
      call.map(String).join(" ").includes("Non-unique keys"),
    ),
  ).toBe(false);

  expect(screen.getByRole("heading", { name: "AI Research Desk" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Daily A-share research shortlist" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Published cohort outcomes" })).toBeInTheDocument();
  expect(
    screen.getByText(
      "This immutable cohort's explanation was first published in Chinese. Structured factors, gaps, and invalidation conditions remain available in the current language.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText("An unrecognized publication diagnostic was reported (UNKNOWN_PAGE_DIAGNOSTIC)."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("An unrecognized evidence gap was reported (UNKNOWN_PAGE_GAP)."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("An unrecognized invalidation condition was reported (UNKNOWN_PAGE_RULE)."),
  ).toBeInTheDocument();
  expect(screen.queryByText(/不应直接显示在英文页面/)).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "A-share evidence coverage" })).toBeInTheDocument();
  expect(screen.getByText("Coverage ready")).toBeInTheDocument();
  expect(screen.getByText(/Research only: this desk summarizes evidence/)).toBeInTheDocument();
  expect(screen.getByText("Provider: yfinance")).toBeInTheDocument();
  expect(screen.getAllByText("AAPL").length).toBeGreaterThan(0);
  expect(screen.getAllByText("0700").length).toBeGreaterThan(0);
  expect(screen.getAllByText("AAPL crossed above its moving average").length).toBeGreaterThan(0);
  expect(screen.getByText("Breakout research signal")).toBeInTheDocument();
  expect(screen.getByText("A-share daily data")).toBeInTheDocument();
  expect(screen.getAllByText("Kweichow Moutai").length).toBeGreaterThan(0);
  expect(screen.getByText("Main flow: 123,456,789 CNY")).toBeInTheDocument();
  expect(screen.getByText("Reason: AI computing")).toBeInTheDocument();
  expect(screen.getByText("Dragon Tiger List")).toBeInTheDocument();
  expect(screen.getByText(/Net buy: 123,000,000 CNY/)).toBeInTheDocument();
  expect(screen.getByText("Reason: Daily price deviation reached threshold.")).toBeInTheDocument();
  expect(screen.getByText("Block trades")).toBeInTheDocument();
  expect(screen.getByText("Ping An Bank")).toBeInTheDocument();
  expect(screen.getByText(/Deal amount: 11,800,000 CNY/)).toBeInTheDocument();
  expect(screen.getByText("Buyer: Buyer seat; seller: Seller seat")).toBeInTheDocument();
  expect(screen.getByText(/not stored local evidence or assistant citations/)).toBeInTheDocument();
  expect(screen.getAllByText("Buffett Indicator - United States").length).toBeGreaterThan(0);
  expect(screen.getByText("Buffett Indicator - China")).toBeInTheDocument();
  expect(screen.getByText("Value: 188.5%")).toBeInTheDocument();
  const sourceMaintenance = screen
    .getByText("Source maintenance and diagnostics")
    .closest("details");
  expect(sourceMaintenance).not.toHaveAttribute("open");
  expect(screen.getByText("Official source readiness")).toBeInTheDocument();
  expect(screen.getByText("World Bank Buffett Indicator")).toBeInTheDocument();
  expect(screen.getByText("Next: Run World Bank dry-run, then write refresh for missing Buffett Indicator regions.")).toBeInTheDocument();
  expect(screen.getByText("No audited observation has been seeded for this indicator yet.")).toBeInTheDocument();
  expect(screen.getByText("Signals are deterministic research inputs only.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open watchlist" })).toHaveAttribute("href", "/watchlist");
  expect(screen.getByRole("link", { name: "Open macro research" })).toHaveAttribute("href", "/evidence");

  const shortlistHeading = screen.getByRole("heading", { name: "Daily A-share research shortlist" });
  const outcomeHeading = screen.getByRole("heading", { name: "Published cohort outcomes" });
  const deskHeading = screen.getByRole("heading", { name: "AI Research Desk" });
  const coverageHeading = screen.getByRole("heading", { name: "A-share evidence coverage" });
  const discoveryHeading = screen.getByText("Full A-share discovery");
  expect(shortlistHeading.compareDocumentPosition(discoveryHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(discoveryHeading.compareDocumentPosition(deskHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(deskHeading.compareDocumentPosition(outcomeHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(deskHeading.compareDocumentPosition(coverageHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByText("Evidence coverage and backfill operations")).toBeInTheDocument();
});

it("adds a manual symbol and submits the active symbol through the existing market assistant", async () => {
  askMarketAssistantMock.mockResolvedValue(createAssistantResponse({ symbol: "MSFT" }));
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "AAPL", name: "Apple Inc.", market: "US", is_active: true }],
          }),
        ),
      );
    }
    if (url.endsWith("/dashboard/market-overview?provider=yfinance")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketOverviewPayload())));
    }
    if (url.endsWith("/market-indicators/official-sources/status")) {
      return Promise.resolve(new Response(JSON.stringify(createOfficialSourceStatusPayload())));
    }
    if (url.endsWith("/market-daily-data/fund-flow/stocks?market=CN&window=today&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createStockFundFlowPayload())));
    }
    if (url.endsWith("/market-daily-data/limit-up-reasons?market=CN&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createLimitUpReasonsPayload())));
    }
    if (url.endsWith("/market-daily-data/dragon-tiger-list?market=CN&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createDragonTigerPayload())));
    }
    if (url.endsWith("/market-daily-data/block-trades?market=CN&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createBlockTradesPayload())));
    }
    if (url.includes("/recommendations?")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", items: [] })));
    }
    if (url.endsWith("/research-shortlists/latest?market=CN&profile_id=balanced_research")) {
      return Promise.resolve(
        new Response(JSON.stringify({ status: "no_data", research_signal_only: true, run: null, items: [] })),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  await renderAiResearchPage();

  fireEvent.change(screen.getByLabelText("Manual symbol"), { target: { value: "MSFT" } });
  fireEvent.click(screen.getByRole("button", { name: "Add" }));
  expect(screen.getAllByText("MSFT").length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));

  await waitFor(() => {
    expect(askMarketAssistantMock).toHaveBeenCalledWith({
      scope: "instrument",
      symbol: "MSFT",
      question: expect.stringContaining("Build a research-only summary for MSFT"),
      locale: "en",
      timeframe: "1d",
      start: null,
      end: null,
      provider: "yfinance",
    });
  });
  expect(askMarketAssistantMock.mock.calls[0][0].question).toContain(
    "Buffett Indicator - United States: 188.5%",
  );
  expect(askMarketAssistantMock.mock.calls[0][0].question).not.toContain(
    "FRED US macro",
  );
  expect(askMarketAssistantMock.mock.calls[0][0].question).not.toContain(
    "FRED_API_KEY",
  );
  expect(await screen.findByText("Research-only answer with cited local evidence.")).toBeInTheDocument();
  expect(screen.getByText("Daily bars for AAPL as of 2026-01-02")).toBeInTheDocument();
  expect(screen.getByText("Research only. Not investment advice.")).toBeInTheDocument();
});

it("remounts outcome client state when a refreshed page advances to a new tracking run", async () => {
  let currentRunId = "daily-run-1";
  let currentSymbol = "600519";
  let currentName = "First cohort candidate";
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/research-shortlists/latest?market=CN&profile_id=balanced_research")) {
      const payload = createDailyShortlistPayload();
      payload.run!.id = currentRunId;
      return Promise.resolve(new Response(JSON.stringify(payload)));
    }
    if (url.endsWith("/research-shortlists/tracking?market=CN&profile_id=balanced_research&limit=10&offset=0")) {
      return Promise.resolve(
        new Response(JSON.stringify(
          createOutcomeTrackingPayload(currentRunId, currentSymbol, currentName),
        )),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({ items: [] })));
  });

  const firstPage = await AiResearchPage({ params: Promise.resolve({ locale: "en" }) });
  const firstOutcome = getOutcomePanelElement(firstPage);
  const view = render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {firstOutcome}
    </NextIntlClientProvider>,
  );
  expect(screen.getByText("First cohort candidate")).toBeInTheDocument();

  currentRunId = "daily-run-2";
  currentSymbol = "000001";
  currentName = "Second cohort candidate";
  const secondPage = await AiResearchPage({ params: Promise.resolve({ locale: "en" }) });
  const secondOutcome = getOutcomePanelElement(secondPage);
  view.rerender(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {secondOutcome}
    </NextIntlClientProvider>,
  );

  expect(screen.getByText("Second cohort candidate")).toBeInTheDocument();
  expect(screen.queryByText("First cohort candidate")).not.toBeInTheDocument();
});

it("keeps the AI research desk usable when the latest shortlist and official source status are unavailable", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "AAPL", name: "Apple Inc.", market: "US", is_active: true }],
          }),
        ),
      );
    }
    if (url.endsWith("/dashboard/market-overview?provider=yfinance")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketOverviewPayload())));
    }
    if (url.endsWith("/market-indicators/official-sources/status")) {
      return Promise.resolve(new Response("unavailable", { status: 503 }));
    }
    if (url.endsWith("/market-daily-data/fund-flow/stocks?market=CN&window=today&limit=6&provider=akshare")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "unavailable",
            data_mode: "none",
            source: "none",
            provider: "akshare",
            effective_provider: "akshare",
            message: "Market daily-data provider is unavailable.",
            count: 0,
            items: [],
          }),
        ),
      );
    }
    if (url.endsWith("/market-daily-data/limit-up-reasons?market=CN&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createLimitUpReasonsPayload())));
    }
    if (url.endsWith("/market-daily-data/dragon-tiger-list?market=CN&limit=6&provider=akshare")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "degraded",
            data_mode: "none",
            source: "none",
            provider: "akshare",
            effective_provider: "akshare",
            message: "No Dragon Tiger List rows are available.",
            count: 0,
            items: [],
          }),
        ),
      );
    }
    if (url.endsWith("/market-daily-data/block-trades?market=CN&limit=6&provider=akshare")) {
      return Promise.resolve(new Response(JSON.stringify(createBlockTradesPayload())));
    }
    if (url.includes("/recommendations?")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", items: [] })));
    }
    if (url.endsWith("/research-shortlists/latest?market=CN&profile_id=balanced_research")) {
      return Promise.resolve(new Response("unavailable", { status: 503 }));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  await renderAiResearchPage();

  expect(screen.getByRole("heading", { name: "AI Research Desk" })).toBeInTheDocument();
  expect(screen.getByText("Latest shortlist could not be loaded")).toBeInTheDocument();
  expect(screen.getByText("Cohort outcomes could not be loaded")).toBeInTheDocument();
  expect(screen.getByText("Official source readiness could not be loaded.")).toBeInTheDocument();
  expect(screen.getByText("Market daily-data provider is unavailable.")).toBeInTheDocument();
  expect(screen.getByText("No Dragon Tiger List rows are available.")).toBeInTheDocument();
});
