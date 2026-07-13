export const RESEARCH_OUTCOME_HORIZONS = [5, 20, 60] as const;

export type ResearchOutcomeHorizon = (typeof RESEARCH_OUTCOME_HORIZONS)[number];
export type ResearchOutcomeStatus = "pending" | "evaluated" | "blocked";
export type ResearchOutcomeBenchmarkStatus =
  | "pending"
  | "evaluated"
  | "blocked"
  | "not_applicable";

export type ResearchOutcomeDiagnostic =
  | string
  | {
      code?: string | null;
      message?: string | null;
      [key: string]: unknown;
    };

export type ResearchOutcomeBenchmark = {
  code: string;
  status: ResearchOutcomeBenchmarkStatus;
  instrument_id?: string | null;
  entry_date?: string | null;
  exit_date?: string | null;
  entry_close?: number | null;
  exit_close?: number | null;
  return_ratio?: number | null;
  excess_return_ratio?: number | null;
  diagnostics?: ResearchOutcomeDiagnostic[];
};

export type ResearchCandidateHorizonOutcome = {
  horizon_sessions: ResearchOutcomeHorizon;
  status: ResearchOutcomeStatus;
  available_forward_bars: number;
  ready_for_evaluation: boolean;
  maturity_date?: string | null;
  exit_close?: number | null;
  minimum_forward_low?: number | null;
  minimum_low_date?: string | null;
  return_ratio?: number | null;
  drawdown_ratio?: number | null;
  benchmark?: ResearchOutcomeBenchmark | null;
  diagnostics?: ResearchOutcomeDiagnostic[];
};

export type ResearchCandidateOutcome = {
  candidate_id: string;
  instrument_id: string;
  symbol: string;
  name?: string | null;
  rank: number;
  entry_trade_date: string;
  horizons: ResearchCandidateHorizonOutcome[];
};

export type ResearchOutcomeSummary = {
  horizon_sessions: ResearchOutcomeHorizon;
  total_count: number;
  evaluated_count: number;
  pending_count: number;
  blocked_count: number;
  return_sample_size: number;
  benchmark_sample_size: number;
  positive_return_ratio?: number | null;
  mean_return_ratio?: number | null;
  median_return_ratio?: number | null;
  mean_drawdown_ratio?: number | null;
  mean_excess_return_ratio?: number | null;
};

export type ResearchOutcomeRun = {
  id: string;
  decision_date: string;
  market: string;
  profile_id: string;
};

export type ResearchShortlistOutcomePayload = {
  status: string;
  as_of: string;
  run: ResearchOutcomeRun;
  items: ResearchCandidateOutcome[];
  summaries: ResearchOutcomeSummary[];
  research_signal_only: boolean;
  safety?: Record<string, unknown> | null;
};

export type ResearchOutcomeHistoryItem = {
  run: ResearchOutcomeRun;
  summaries: ResearchOutcomeSummary[];
};

export type ResearchShortlistOutcomeTrackingPayload = {
  status: string;
  as_of: string;
  market: string;
  profile_id: string;
  latest: ResearchShortlistOutcomePayload | null;
  history: ResearchOutcomeHistoryItem[];
  limit: number;
  offset: number;
  has_more: boolean;
  research_signal_only: boolean;
  safety?: Record<string, unknown> | null;
};

export async function preserveNoStoreResponse(response: Response): Promise<Response> {
  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
