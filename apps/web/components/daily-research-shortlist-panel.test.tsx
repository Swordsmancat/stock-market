import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it, vi } from "vitest";

import enMessages from "../messages/en.json";
import zhMessages from "../messages/zh.json";
import type { DailyResearchShortlistPayload } from "@/lib/daily-research-shortlist";

import { DailyResearchShortlistPanel } from "./daily-research-shortlist-panel";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const loadedPayload: DailyResearchShortlistPayload = {
  status: "ok",
  research_signal_only: true,
  run: {
    id: "run-2026-07-10",
    decision_date: "2026-07-10",
    generated_at: "2026-07-10T08:30:00Z",
    market: "CN",
    profile_id: "balanced_research",
    scoring_model: "daily_research_score_v1",
    shortlist_limit: 10,
    locale: "en",
    counts: {
      candidate_count: 5200,
      evaluated_count: 5001,
      matched_count: 18,
      returned_count: 2,
    },
    coverage: {
      status: "ok",
      ready: true,
      evidence: {
        daily_bars: { coverage_ratio: 0.962, threshold: 0.95, passes_threshold: true },
      },
    },
    diagnostics: [{ code: "STALE_BAR_EXCLUDED", count: 3 }],
    model: { used_llm: false, name: "deterministic-stock-discovery-v1" },
    explanation_markdown: "The fixed cohort is ranked only by stored evidence.",
    safety: { disclaimer: "Research only. No investment advice or automated trading." },
  },
  items: [
    {
      id: "candidate-1",
      symbol: "600519",
      name: "Kweichow Moutai",
      market: "CN",
      rank: 1,
      total_score: 0.8732,
      minimum_rule_buffer: 0.61,
      supporting_factors: [
        { code: "min_net_margin", buffer: 0.92, message: "English backend factor label." },
        { code: "price_above_ma", buffer: 0.81 },
      ],
      opposing_factors: [{ code: "max_pe_ratio", buffer: 0.61 }],
      data_gaps: [
        {
          code: "TECHNICAL_BEFORE_DECISION_DATE",
          as_of: "2026-07-09",
          decision_date: "2026-07-10",
          message: "English backend technical gap.",
        },
        {
          code: "NEWS_NOT_EVALUATED_BY_PROFILE",
          message: "English backend news gap.",
        },
        { code: "NEWS_WINDOW_PARTIAL", message: "Recent news coverage is partial." },
      ],
      invalidation_conditions: [
        {
          rule: "require_price_above_ma",
          operator: "<=",
          threshold: 1680,
          message: "English backend invalidation message.",
        },
      ],
      entry_observation: { trade_date: "2026-07-10", close: 1688.5 },
      evidence_citations: [
        { id: "bars_1d:600519:2026-07-10" },
        { id: "fundamentals:600519:2026-07-10" },
      ],
    },
    {
      id: "candidate-2",
      symbol: "000001",
      name: "Ping An Bank",
      market: "CN",
      rank: 2,
      total_score: 0.7411,
      minimum_rule_buffer: 0.7,
      supporting_factors: [{ code: "max_pe_ratio", buffer: 0.9 }],
      opposing_factors: [],
      data_gaps: [
        {
          code: "TECHNICAL_AS_OF_UNAVAILABLE",
          message: "English backend missing technical metadata.",
        },
        {
          code: "FUNDAMENTALS_UNAVAILABLE",
          message: "English backend fundamentals gap.",
        },
        {
          code: "FUNDAMENTALS_BEFORE_DECISION_DATE",
          as_of: "2026-06-30",
          decision_date: "2026-07-10",
          message: "English backend stale fundamentals gap.",
        },
      ],
      invalidation_conditions: [
        {
          rule: "max_pe_ratio",
          operator: ">",
          threshold: 35,
          message: "English backend PE invalidation message.",
        },
      ],
      entry_observation: { trade_date: "2026-07-10", close: 11.82 },
      evidence_citations: [{ id: "bars_1d:000001:2026-07-10" }],
    },
  ],
  safety: { not_investment_advice: true, no_automated_trading: true },
};

function renderPanel(
  initialPayload: DailyResearchShortlistPayload | null,
  initialLoadFailed = false,
  locale = "en",
) {
  render(
    <NextIntlClientProvider
      locale={locale}
      messages={locale === "zh" ? zhMessages : enMessages}
    >
      <DailyResearchShortlistPanel
        locale={locale}
        initialPayload={initialPayload}
        initialLoadFailed={initialLoadFailed}
      />
    </NextIntlClientProvider>,
  );
}

it("renders the persisted ranked cohort, evidence limits, and both research handoffs", () => {
  const handoff = vi.fn();
  window.addEventListener("stock-discovery:select-symbol", handoff);
  Element.prototype.scrollIntoView = vi.fn();

  renderPanel(loadedPayload);

  expect(screen.getByRole("heading", { name: "Daily A-share research shortlist" })).toBeInTheDocument();
  expect(screen.getByText("2026-07-10")).toBeInTheDocument();
  expect(screen.getByText("Jul 10, 2026, 4:30 PM")).toBeInTheDocument();
  expect(screen.getAllByText("Published").length).toBeGreaterThan(0);
  expect(screen.getByText("5,001")).toBeInTheDocument();
  expect(screen.getByText("0.8732")).toBeInTheDocument();
  expect(screen.getByText("Net margin above minimum (92%)")).toBeInTheDocument();
  expect(screen.getByText("PE below maximum (61%)")).toBeInTheDocument();
  expect(
    screen.getByText("Technical indicators are dated 2026-07-09, before the decision date 2026-07-10."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("News and sentiment were not active eligibility rules for this profile."),
  ).toBeInTheDocument();
  expect(screen.getByText("Technical-indicator as-of metadata is unavailable.")).toBeInTheDocument();
  expect(screen.getByText("A fundamentals snapshot was not evaluated for this candidate.")).toBeInTheDocument();
  expect(
    screen.getByText("Fundamentals are dated 2026-06-30, before the decision date 2026-07-10."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("An unrecognized evidence gap was reported (NEWS_WINDOW_PARTIAL)."),
  ).toBeInTheDocument();
  expect(screen.queryByText("Recent news coverage is partial.")).not.toBeInTheDocument();
  expect(
    screen.getByText("Price above moving average is invalidated when the observed value is <= 1680."),
  ).toBeInTheDocument();
  expect(screen.getByText("2 stored evidence references")).toBeInTheDocument();
  expect(
    screen.getByText(/Research support only\. The shortlist does not provide buy, sell, hold/),
  ).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Open deep analysis" })[0]).toHaveAttribute(
    "href",
    "/instruments/600519?research_snapshot_id=run-2026-07-10",
  );

  fireEvent.click(screen.getAllByRole("button", { name: "Use in research desk" })[0]);
  expect(handoff).toHaveBeenCalledOnce();
  window.removeEventListener("stock-discovery:select-symbol", handoff);
});

it("localizes supported scoring rules on the Chinese comparison surface", () => {
  renderPanel(
    {
      ...loadedPayload,
      run: loadedPayload.run ? { ...loadedPayload.run, locale: "zh" } : null,
    },
    false,
    "zh",
  );

  expect(screen.getByRole("heading", { name: "每日 A 股研究候选清单" })).toBeInTheDocument();
  expect(screen.getByText("净利率高于下限 (92%)")).toBeInTheDocument();
  expect(screen.getByText("市盈率低于上限 (61%)")).toBeInTheDocument();
  expect(
    screen.getByText("技术指标截至 2026-07-09，早于决策日期 2026-07-10。"),
  ).toBeInTheDocument();
  expect(screen.getByText("当前筛选预设未启用新闻与情绪资格条件。")).toBeInTheDocument();
  expect(screen.getByText("技术指标缺少截至日期元数据。")).toBeInTheDocument();
  expect(screen.getByText("该候选未评估基本面快照。")).toBeInTheDocument();
  expect(
    screen.getByText("基本面截至 2026-06-30，早于决策日期 2026-07-10。"),
  ).toBeInTheDocument();
  expect(
    screen.getByText("当观测值 <= 1680 时，“价格位于移动均线上方”研究条件失效。"),
  ).toBeInTheDocument();
  expect(screen.queryByText(/English backend/)).not.toBeInTheDocument();
});

it("hides opposite-locale persisted prose and unknown backend messages", () => {
  const chineseRaw = {
    explanation: "不应直接显示的中文持久化解释。",
    disclaimer: "不应直接显示的中文免责声明。",
    diagnostic: "不应直接显示的中文未知诊断。",
    gap: "不应直接显示的中文未知缺口。",
    invalidation: "不应直接显示的中文未知失效条件。",
  };
  renderPanel(
    contaminatedPayload("zh", chineseRaw),
    false,
    "en",
  );

  expect(
    screen.getByText(
      "This immutable cohort's explanation was first published in Chinese. Structured factors, gaps, and invalidation conditions remain available in the current language.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("An unrecognized publication diagnostic was reported (UNKNOWN_DIAGNOSTIC).")).toBeInTheDocument();
  expect(screen.getByText("An unrecognized evidence gap was reported (UNKNOWN_GAP).")).toBeInTheDocument();
  expect(screen.getByText("An unrecognized invalidation condition was reported (UNKNOWN_RULE).")).toBeInTheDocument();
  for (const rawText of Object.values(chineseRaw)) {
    expect(screen.queryByText(rawText)).not.toBeInTheDocument();
  }

  cleanup();

  const englishRaw = {
    explanation: "English persisted explanation must not render directly.",
    disclaimer: "English backend disclaimer must not render directly.",
    diagnostic: "English unknown diagnostic must not render directly.",
    gap: "English unknown gap must not render directly.",
    invalidation: "English unknown invalidation must not render directly.",
  };
  renderPanel(
    contaminatedPayload("en", englishRaw),
    false,
    "zh",
  );

  expect(
    screen.getByText(
      "这个不可变候选集的解释最初以英文发布；当前语言仍可查看结构化因素、缺口与失效条件。",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("报告了未识别的发布诊断（UNKNOWN_DIAGNOSTIC）。")).toBeInTheDocument();
  expect(screen.getByText("报告了未识别的证据缺口（UNKNOWN_GAP）。")).toBeInTheDocument();
  expect(screen.getByText("报告了未识别的失效条件（UNKNOWN_RULE）。")).toBeInTheDocument();
  for (const rawText of Object.values(englishRaw)) {
    expect(screen.queryByText(rawText)).not.toBeInTheDocument();
  }
});

it("shows a distinct empty state and publishes through the generation proxy", async () => {
  let resolveResponse: ((response: Response) => void) | undefined;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
    () => new Promise<Response>((resolve) => {
      resolveResponse = resolve;
    }),
  );
  renderPanel({
    status: "no_data",
    research_signal_only: true,
    run: null,
    items: [],
  });

  expect(screen.getByText("No published shortlist yet")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Generate today's shortlist" }));
  expect(screen.getByRole("button", { name: "Generating daily shortlist..." })).toBeDisabled();

  resolveResponse?.(
    new Response(JSON.stringify(loadedPayload), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  expect(await screen.findByText("Kweichow Moutai")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith("/api/research-shortlists/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      profile_id: "balanced_research",
      market: "CN",
      asset_type: "stock",
      shortlist_limit: 10,
      locale: "en",
      use_llm: true,
      overrides: {},
    }),
  });
});

it("keeps load failures visible and reports readiness conflicts", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({
      detail: {
        code: "EVIDENCE_COVERAGE_NOT_READY",
        message: "English readiness message must not render directly.",
      },
    }), {
      status: 409,
      headers: { "content-type": "application/json" },
    }),
  );
  renderPanel(null, true);

  expect(screen.getByText("Latest shortlist could not be loaded")).toBeInTheDocument();
  expect(screen.queryByText("No published shortlist yet")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Generate today's shortlist" }));

  await waitFor(() => {
    expect(screen.getAllByRole("alert")[0]).toHaveTextContent(
      "Evidence coverage has not reached the publication thresholds.",
    );
  });
  expect(
    screen.queryByText("English readiness message must not render directly."),
  ).not.toBeInTheDocument();
});

function contaminatedPayload(
  runLocale: "en" | "zh",
  raw: {
    explanation: string;
    disclaimer: string;
    diagnostic: string;
    gap: string;
    invalidation: string;
  },
): DailyResearchShortlistPayload {
  const firstItem = loadedPayload.items[0];
  return {
    ...loadedPayload,
    run: loadedPayload.run
      ? {
          ...loadedPayload.run,
          locale: runLocale,
          explanation_markdown: raw.explanation,
          diagnostics: [{ code: "UNKNOWN_DIAGNOSTIC", message: raw.diagnostic }],
          safety: { disclaimer: raw.disclaimer },
        }
      : null,
    items: [
      {
        ...firstItem,
        data_gaps: [{ code: "UNKNOWN_GAP", message: raw.gap }],
        invalidation_conditions: [
          { code: "UNKNOWN_RULE", message: raw.invalidation },
        ],
      },
    ],
    safety: { disclaimer: raw.disclaimer },
  };
}
