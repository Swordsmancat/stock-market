export const DAILY_RESEARCH_SHORTLIST_PUBLISHED_EVENT =
  "daily-research-shortlist:published";

export type DailyResearchCitation = {
  id: string;
  label?: string | null;
  source?: string | null;
  source_type?: string | null;
  symbol?: string | null;
  as_of?: string | null;
  provider?: string | null;
};

export type DailyResearchDiagnostic = {
  code?: string | null;
  message?: string | null;
  source?: string | null;
  dimension?: string | null;
  status?: string | null;
  severity?: string | null;
  count?: number | null;
  [key: string]: unknown;
};

export type DailyResearchSafety = {
  disclaimer?: string | null;
  research_signal_only?: boolean;
  not_investment_advice?: boolean;
  no_automated_trading?: boolean;
  no_buy_sell_hold?: boolean;
  no_target_price?: boolean;
  no_position_sizing?: boolean;
  ai_cannot_change_membership_or_ranking?: boolean;
  [key: string]: unknown;
};

export type DailyResearchFactor = {
  code?: string | null;
  rule_code?: string | null;
  field?: string | null;
  dimension?: string | null;
  actual?: unknown;
  threshold?: unknown;
  buffer?: number | null;
  contribution?: number | null;
  weighted_contribution?: number | null;
  normalization?: string | null;
  normalization_id?: string | null;
  label?: string | null;
  message?: string | null;
  [key: string]: unknown;
};

export type DailyResearchGap =
  | string
  | {
      code?: string | null;
      message?: string | null;
      field?: string | null;
      source?: string | null;
      [key: string]: unknown;
    };

export type DailyResearchInvalidation =
  | string
  | {
      code?: string | null;
      message?: string | null;
      field?: string | null;
      operator?: string | null;
      threshold?: unknown;
      [key: string]: unknown;
    };

export type DailyResearchEntryObservation = {
  trade_date?: string | null;
  close?: number | null;
  provider?: string | null;
  source?: string | null;
  adjustment?: string | null;
  source_priority?: number | null;
  ingested_at?: string | null;
  [key: string]: unknown;
};

export type DailyResearchShortlistItem = {
  id: string;
  run_id?: string;
  instrument_id?: string;
  symbol: string;
  name?: string | null;
  market?: string | null;
  asset_type?: string | null;
  rank: number;
  total_score: number;
  score?: number | null;
  minimum_rule_buffer?: number | null;
  factor_scores?: DailyResearchFactor[] | Record<string, unknown> | null;
  supporting_factors?: DailyResearchFactor[];
  opposing_factors?: DailyResearchFactor[];
  data_gaps?: DailyResearchGap[];
  invalidation_conditions?: DailyResearchInvalidation[];
  entry_observation?: DailyResearchEntryObservation | null;
  entry?: DailyResearchEntryObservation | null;
  evidence?: Record<string, unknown> | null;
  matched_rules?: Array<Record<string, unknown>>;
  evidence_citations?: Array<string | DailyResearchCitation>;
  citations?: string[];
  allowed_citation_ids?: string[];
  evidence_count?: number;
  safety?: DailyResearchSafety | null;
  research_signal_only?: boolean;
};

export type DailyResearchCoverage = {
  status?: string | null;
  ready?: boolean;
  candidate_count?: number | null;
  evaluated_count?: number | null;
  matched_count?: number | null;
  returned_count?: number | null;
  evidence?: Record<
    string,
    {
      coverage_ratio?: number | null;
      threshold?: number | null;
      passes_threshold?: boolean;
      missing_count?: number | null;
      [key: string]: unknown;
    }
  >;
  [key: string]: unknown;
};

export type DailyResearchCounts = {
  candidate_count?: number | null;
  evaluated_count?: number | null;
  matched_count?: number | null;
  returned_count?: number | null;
  eligible_count?: number | null;
  decision_date_aligned_count?: number | null;
};

export type DailyResearchShortlistRun = {
  id: string;
  decision_date: string;
  generated_at: string;
  market: string;
  asset_type?: string | null;
  profile_id: string;
  scoring_model: string;
  shortlist_limit: number;
  status?: string | null;
  generation_key?: string | null;
  profile?: { id?: string | null } | null;
  rule_set?: string | null;
  locale?: string | null;
  default_criteria?: Record<string, unknown>;
  effective_criteria?: Record<string, unknown>;
  overrides?: Record<string, unknown>;
  candidate_scope?: Record<string, unknown>;
  counts?: DailyResearchCounts | null;
  coverage?: DailyResearchCoverage | null;
  diagnostics?: DailyResearchDiagnostic[];
  dimension_weights?: Record<string, number>;
  model?: {
    used_llm?: boolean;
    name?: string | null;
    provider?: string | null;
    fallback_reason?: string | null;
    [key: string]: unknown;
  } | null;
  explanation_markdown?: string | null;
  citations?: DailyResearchCitation[];
  safety?: DailyResearchSafety | null;
  research_signal_only?: boolean;
  [key: string]: unknown;
};

export type DailyResearchShortlistPayload = {
  status: string;
  research_signal_only: boolean;
  run: DailyResearchShortlistRun | null;
  items: DailyResearchShortlistItem[];
  safety?: DailyResearchSafety | null;
};

export type GenerateDailyResearchShortlistRequest = {
  profile_id: string;
  market: string;
  asset_type: string;
  shortlist_limit: number;
  locale: "en" | "zh";
  use_llm: boolean;
  overrides: Record<string, unknown>;
};
