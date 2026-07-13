import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it, vi } from "vitest";

import enMessages from "../messages/en.json";
import zhMessages from "../messages/zh.json";
import type { DailyResearchShortlistPayload } from "@/lib/daily-research-shortlist";
import type { ResearchShortlistOutcomeTrackingPayload } from "@/lib/research-shortlist-outcomes";

import { DailyResearchShortlistPanel } from "./daily-research-shortlist-panel";
import { ResearchShortlistOutcomePanel } from "./research-shortlist-outcome-panel";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const loadedTrackingPayload: ResearchShortlistOutcomeTrackingPayload = {
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
      id: "run-2026-07-10",
      decision_date: "2026-07-10",
      market: "CN",
      profile_id: "balanced_research",
    },
    summaries: [
      {
        horizon_sessions: 5,
        total_count: 3,
        evaluated_count: 1,
        pending_count: 1,
        blocked_count: 1,
        return_sample_size: 1,
        benchmark_sample_size: 0,
        positive_return_ratio: 1,
        mean_return_ratio: 0.125,
        median_return_ratio: 0.125,
        mean_drawdown_ratio: -0.04,
        mean_excess_return_ratio: null,
      },
      {
        horizon_sessions: 20,
        total_count: 3,
        evaluated_count: 0,
        pending_count: 3,
        blocked_count: 0,
        return_sample_size: 0,
        benchmark_sample_size: 0,
        positive_return_ratio: null,
        mean_return_ratio: null,
        median_return_ratio: null,
        mean_drawdown_ratio: null,
        mean_excess_return_ratio: null,
      },
      {
        horizon_sessions: 60,
        total_count: 3,
        evaluated_count: 0,
        pending_count: 3,
        blocked_count: 0,
        return_sample_size: 0,
        benchmark_sample_size: 0,
        positive_return_ratio: null,
        mean_return_ratio: null,
        median_return_ratio: null,
        mean_drawdown_ratio: null,
        mean_excess_return_ratio: null,
      },
    ],
    items: [
      {
        candidate_id: "candidate-evaluated",
        instrument_id: "instrument-600519",
        symbol: "600519",
        name: "Kweichow Moutai",
        rank: 1,
        entry_trade_date: "2026-07-10",
        horizons: [
          {
            horizon_sessions: 5,
            status: "evaluated",
            available_forward_bars: 5,
            ready_for_evaluation: false,
            maturity_date: "2026-07-17",
            exit_close: 1899.56,
            minimum_forward_low: 1620.96,
            minimum_low_date: "2026-07-13",
            return_ratio: 0.125,
            drawdown_ratio: -0.04,
            benchmark: {
              code: "cn_csi_300",
              status: "pending",
              return_ratio: null,
              excess_return_ratio: null,
              diagnostics: [
                {
                  code: "BENCHMARK_INSTRUMENT_MISSING",
                  message: "Chinese or English backend prose must not render.",
                },
              ],
            },
            diagnostics: [{ code: "QFQ_PROXY_BASIS", message: "Backend methodology prose." }],
          },
          pendingHorizon(20, 8),
          pendingHorizon(60, 8),
        ],
      },
      {
        candidate_id: "candidate-ready",
        instrument_id: "instrument-000001",
        symbol: "000001",
        name: "Ping An Bank",
        rank: 2,
        entry_trade_date: "2026-07-10",
        horizons: [
          { ...pendingHorizon(5, 5), ready_for_evaluation: true },
          pendingHorizon(20, 8),
          pendingHorizon(60, 8),
        ],
      },
      {
        candidate_id: "candidate-blocked",
        instrument_id: "instrument-300750",
        symbol: "300750",
        name: "CATL",
        rank: 3,
        entry_trade_date: "2026-07-10",
        horizons: [
          {
            horizon_sessions: 5,
            status: "blocked",
            available_forward_bars: 5,
            ready_for_evaluation: false,
            return_ratio: null,
            drawdown_ratio: null,
            benchmark: null,
            diagnostics: [
              "INSTRUMENT_INACTIVE",
              {
                code: "ENTRY_BAR_REVISED",
                message: "Backend blocked prose must not render.",
              },
            ],
          },
          pendingHorizon(20, 8),
          pendingHorizon(60, 8),
        ],
      },
    ],
  },
  history: [
    {
      run: {
        id: "run-2026-07-09",
        decision_date: "2026-07-09",
        market: "CN",
        profile_id: "balanced_research",
      },
      summaries: [
        {
          horizon_sessions: 5,
          total_count: 2,
          evaluated_count: 2,
          pending_count: 0,
          blocked_count: 0,
          return_sample_size: 2,
          benchmark_sample_size: 1,
          positive_return_ratio: 0.5,
          mean_return_ratio: 0.03,
          median_return_ratio: 0.03,
          mean_drawdown_ratio: -0.02,
          mean_excess_return_ratio: 0.01,
        },
      ],
    },
  ],
  limit: 10,
  offset: 0,
  has_more: false,
};

const loadedDailyPayload: DailyResearchShortlistPayload = {
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
    explanation_markdown: "Frozen research cohort.",
  },
  items: [
    {
      id: "candidate-old",
      symbol: "600519",
      name: "Kweichow Moutai",
      rank: 1,
      total_score: 0.81,
    },
  ],
};

function pendingHorizon(horizon: 5 | 20 | 60, available: number) {
  return {
    horizon_sessions: horizon,
    status: "pending" as const,
    available_forward_bars: available,
    ready_for_evaluation: false,
    maturity_date: null,
    exit_close: null,
    minimum_forward_low: null,
    minimum_low_date: null,
    return_ratio: null,
    drawdown_ratio: null,
    benchmark: null,
    diagnostics: [],
  };
}

function renderPanel(
  payload: ResearchShortlistOutcomeTrackingPayload | null = loadedTrackingPayload,
  initialLoadFailed = false,
  locale = "en",
) {
  render(
    <NextIntlClientProvider locale={locale} messages={locale === "zh" ? zhMessages : enMessages}>
      <ResearchShortlistOutcomePanel
        locale={locale}
        initialPayload={payload}
        initialLoadFailed={initialLoadFailed}
      />
    </NextIntlClientProvider>,
  );
}

it("renders cohort summaries, candidate horizon states, benchmark gaps, history, and safety", () => {
  renderPanel();

  expect(screen.getByRole("heading", { name: "Published cohort outcomes" })).toBeInTheDocument();
  const summary = screen.getByRole("region", { name: "Cohort horizon summary" });
  expect(within(summary).getByText("Mean return +12.5%")).toBeInTheDocument();
  expect(within(summary).getByText("Positive returns 100.0%")).toBeInTheDocument();
  expect(within(summary).getByText("Samples 1 / benchmark 0")).toBeInTheDocument();
  expect(screen.getByText("2026-07-20")).toBeInTheDocument();

  const matrix = screen.getByRole("region", { name: "Candidate outcome matrix" });
  expect(matrix).toHaveClass("overflow-auto");
  expect(matrix).toHaveAttribute("tabindex", "0");
  expect(within(matrix).getByText("Return +12.5%")).toBeInTheDocument();
  expect(within(matrix).getByText("Drawdown -4.0%")).toBeInTheDocument();
  expect(within(matrix).getByText("CSI 300 comparison unavailable")).toBeInTheDocument();
  expect(within(matrix).getByText("5/5 sessions")).toBeInTheDocument();
  expect(within(matrix).getByText("Ready to evaluate")).toBeInTheDocument();
  expect(within(matrix).getByText("Instrument is inactive but remains in the cohort")).toBeInTheDocument();
  expect(within(matrix).getByText("Frozen entry bar was revised")).toBeInTheDocument();

  const history = screen.getByRole("region", { name: "Recent cohort outcomes" });
  expect(history).toHaveClass("overflow-auto");
  expect(history).toHaveAttribute("tabindex", "0");
  expect(within(history).getByText("2026-07-09")).toBeInTheDocument();
  expect(within(history).getByText("2/2 samples")).toBeInTheDocument();
  expect(screen.getByText(/does not provide buy, sell, hold/)).toBeInTheDocument();
  expect(screen.queryByText(/Backend/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Chinese or English/)).not.toBeInTheDocument();
});

it("evaluates the current run and replaces the cohort detail with the frozen response", async () => {
  const evaluated = structuredClone(loadedTrackingPayload.latest!);
  evaluated.items[1].horizons[0] = {
    horizon_sessions: 5,
    status: "evaluated",
    available_forward_bars: 5,
    ready_for_evaluation: false,
    maturity_date: "2026-07-17",
    exit_close: 12.41,
    minimum_forward_low: 11.55,
    minimum_low_date: "2026-07-13",
    return_ratio: 0.05,
    drawdown_ratio: -0.023,
    benchmark: {
      code: "cn_csi_300",
      status: "evaluated",
      instrument_id: "csi-300-index",
      entry_date: "2026-07-10",
      exit_date: "2026-07-17",
      entry_close: 4010,
      exit_close: 4130.3,
      return_ratio: 0.03,
      excess_return_ratio: 0.02,
      diagnostics: [],
    },
    diagnostics: [],
  };
  let resolveResponse: ((response: Response) => void) | undefined;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
    () => new Promise<Response>((resolve) => {
      resolveResponse = resolve;
    }),
  );
  renderPanel();

  fireEvent.click(screen.getByRole("button", { name: "Update outcomes" }));
  expect(screen.getByRole("button", { name: "Updating outcomes..." })).toBeDisabled();

  resolveResponse?.(
    new Response(JSON.stringify(evaluated), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  expect(await screen.findByText("vs CSI 300 +2.0%")).toBeInTheDocument();
  expect(screen.queryByText("Ready to evaluate")).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/research-shortlists/run-2026-07-10/outcomes/evaluate",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    },
  );
});

it("keeps the loaded cohort visible when an update fails without leaking upstream prose", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({
      detail: { message: "Backend evaluation failure must not render." },
    }), {
      status: 503,
      headers: { "content-type": "application/problem+json" },
    }),
  );
  renderPanel();

  fireEvent.click(screen.getByRole("button", { name: "Update outcomes" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Outcome update failed.");
  expect(screen.getByText("Kweichow Moutai")).toBeInTheDocument();
  expect(screen.queryByText(/Backend evaluation failure/)).not.toBeInTheDocument();
});

it("distinguishes no published cohort from an isolated tracking load failure", () => {
  renderPanel({
    status: "no_data",
    as_of: "2026-07-20",
    market: "CN",
    profile_id: "balanced_research",
    research_signal_only: true,
    latest: null,
    history: [],
    limit: 10,
    offset: 0,
    has_more: false,
  });

  expect(screen.getByText("No cohort outcomes yet")).toBeInTheDocument();
  expect(screen.queryByText("Cohort outcomes could not be loaded")).not.toBeInTheDocument();

  cleanup();
  renderPanel(null, true);

  expect(screen.getByText("Cohort outcomes could not be loaded")).toBeInTheDocument();
  expect(screen.queryByText("No cohort outcomes yet")).not.toBeInTheDocument();
});

it("localizes structured string diagnostics and never renders object message prose", () => {
  const unknown = structuredClone(loadedTrackingPayload);
  unknown.latest!.items[2].horizons[0].diagnostics = [
    {
      code: "NEW_BACKEND_CODE",
      message: "English backend detail must not render on the Chinese page.",
    },
  ];
  renderPanel(unknown, false, "zh");

  expect(screen.getByRole("heading", { name: "已发布候选集结果" })).toBeInTheDocument();
  expect(screen.getByText("结果证据异常（NEW_BACKEND_CODE）")).toBeInTheDocument();
  expect(screen.queryByText(/English backend detail/)).not.toBeInTheDocument();
});

it("does not interpolate an unstructured string diagnostic into localized copy", () => {
  const malformed = structuredClone(loadedTrackingPayload);
  malformed.latest!.items[2].horizons[0].diagnostics = [
    "Backend English failure detail must not render.",
  ];
  renderPanel(malformed, false, "zh");

  expect(screen.queryByText(/Backend English failure detail/)).not.toBeInTheDocument();
  expect(screen.getByText(/结果证据异常/)).toBeInTheDocument();
});

it("hides the previous cohort outcomes as soon as the shortlist sibling publishes a new run", async () => {
  const nextDaily = structuredClone(loadedDailyPayload);
  nextDaily.run!.id = "run-2026-07-11";
  nextDaily.run!.decision_date = "2026-07-11";
  nextDaily.items[0].id = "candidate-new";
  nextDaily.items[0].symbol = "000001";
  nextDaily.items[0].name = "New cohort candidate";
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(nextDaily), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <DailyResearchShortlistPanel locale="en" initialPayload={loadedDailyPayload} />
      <ResearchShortlistOutcomePanel
        locale="en"
        initialPayload={loadedTrackingPayload}
      />
    </NextIntlClientProvider>,
  );

  expect(screen.getAllByText("Kweichow Moutai").length).toBeGreaterThan(1);
  fireEvent.click(screen.getByRole("button", { name: "Refresh today's snapshot" }));

  expect(
    await screen.findByText("A new shortlist was published. Refreshing its outcomes..."),
  ).toBeInTheDocument();
  expect(screen.getByText("New cohort candidate")).toBeInTheDocument();
  expect(screen.queryAllByText("Kweichow Moutai")).toHaveLength(0);
});
