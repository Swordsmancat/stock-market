export type MarketOverviewIndicatorItem = {
  code: string;
  name: string;
  region?: string | null;
  category?: string | null;
  status: "ok" | "no_data" | string;
  value?: number | null;
  unit?: string | null;
  as_of?: string | null;
  source?: string | null;
  components?: Record<string, unknown>;
  no_data_reason?: string | null;
};

export type DashboardBriefSection = {
  id: string;
  title: string;
  items: string[];
};

export type DashboardBriefNarrative = {
  answer_markdown: string;
  model: {
    provider?: string | null;
    name?: string | null;
    used_llm?: boolean;
    fallback_reason?: string | null;
  };
  context?: {
    source_mix?: {
      macro_citations?: number;
      report_citations?: number;
      news_citations?: number;
      research_source_note_citations?: number;
      market_daily_citations?: number;
      information_source_gaps?: number;
    };
  };
};

export type DashboardBriefPayload = {
  status: "ok" | "degraded" | string;
  generated_at: string;
  sections: DashboardBriefSection[];
  citations?: Array<{
    id: string;
    label: string;
    source: string;
    source_type?: string | null;
    as_of?: string | null;
    provider?: string | null;
    excerpt?: string | null;
  }>;
  diagnostics?: Array<{
    source?: string;
    status?: string;
    severity?: string;
    code?: string;
    message?: string;
  }>;
  safety?: {
    not_investment_advice?: boolean;
    no_buy_sell_hold?: boolean;
    no_fabricated_macro_data?: boolean;
  };
  narrative?: DashboardBriefNarrative;
};

export type InformationSourceItem = {
  id: string;
  label: string;
  category: string;
  authority?: string | null;
  coverage?: string[];
  status: "configured" | "needs_adapter" | "needs_manual_seed" | "no_data" | "future" | string;
  freshness_policy?: string | null;
  ai_usage?: string | null;
  next_action?: string | null;
  evidence_count?: number;
  latest_as_of?: string | null;
  collection_links?: Array<{
    label: string;
    url: string;
    source_type?: string | null;
  }>;
  seed_template?: {
    label: string;
    description?: string | null;
    target_indicator_codes?: string[];
    required_fields?: string[];
    json_template?: Record<string, unknown>;
    csv_header?: string[];
    csv_example_rows?: string[];
    review_checklist?: Array<{
      id: string;
      label: string;
      required?: boolean;
      why?: string | null;
    }>;
    warnings?: string[];
    import_command?: string | null;
    citation_boundary?: string | null;
  } | null;
  collection_note?: string | null;
  citation_policy?: string | null;
};

export type InformationSourceGroup = {
  category: string;
  label: string;
  items: InformationSourceItem[];
};

export type InformationSourcesPayload = {
  status: "ok" | "degraded" | string;
  summary?: {
    total?: number;
    configured?: number;
    needs_action?: number;
    future?: number;
    by_status?: Record<string, number>;
  };
  groups?: InformationSourceGroup[];
  items?: InformationSourceItem[];
  diagnostics?: Array<Record<string, unknown>>;
  source_capabilities?: {
    status?: "ok" | "degraded" | string;
    summary?: Record<string, unknown>;
    groups?: Array<Record<string, unknown>>;
    items?: Array<Record<string, unknown>>;
    diagnostics?: Array<Record<string, unknown>>;
    citation_policy?: string;
    recommended_next_action?: string;
  };
};

export type OfficialMacroSourceStatusProvider = {
  provider: "fred" | "world_bank" | string;
  label: string;
  status: "ok" | "degraded" | "needs_configuration" | "manual_or_future" | string;
  configured: boolean;
  can_refresh_from_browser?: boolean;
  credential_required: boolean;
  credential_configured?: boolean;
  credential_label?: string | null;
  base_url?: string | null;
  source_url?: string | null;
  source_frequency?: string | null;
  freshness_policy?: string | null;
  indicator_codes: string[];
  evidence_count: number;
  latest_as_of?: string | null;
  missing_indicator_codes?: string[];
  recommended_next_action?: string | null;
  citation_policy?: string | null;
  collection_links?: Array<{
    label: string;
    url: string;
  }>;
  browser_refresh_note?: string | null;
};

export type OfficialMacroSourceStatusPayload = {
  status: "ok" | "degraded" | "needs_configuration" | string;
  generated_at: string;
  providers: OfficialMacroSourceStatusProvider[];
  citation_policy?: string | null;
};

export type ResearchFollowUpQueueItem = {
  id: string;
  kind: "source_review" | "seed_prep" | "ai_summary_question" | "source_gap" | "research_note" | string;
  priority?: "high" | "medium" | "low" | string;
  title?: string | null;
  prompt?: string | null;
  next_action?: string | null;
  citation_policy?: "citable" | "collection_only" | "guidance_only" | string;
  citation_id?: string | null;
  note_id?: string | null;
  note_title?: string | null;
  source_name?: string | null;
  source_type?: string | null;
  source_id?: string | null;
  source_label?: string | null;
  source_category?: string | null;
  source_status?: string | null;
  target_indicator_codes?: string[];
  component_role?: string | null;
  completeness_status?: string | null;
  as_of?: string | null;
  retrieved_at?: string | null;
  linked_note_count?: number;
  seed_ready_note_count?: number;
  missing_review_checks?: string[];
};

export type ResearchFollowUpQueuePayload = {
  status: "ok" | "degraded" | string;
  generated_at: string;
  summary?: {
    total?: number;
    returned?: number;
    source_review?: number;
    seed_prep?: number;
    ai_summary_question?: number;
    source_gap?: number;
    research_note?: number;
    citable?: number;
    collection_only?: number;
    guidance_only?: number;
  };
  items?: ResearchFollowUpQueueItem[];
  diagnostics?: Array<Record<string, unknown>>;
  safety?: {
    not_investment_advice?: boolean;
    citations_require_reviewed_citable_notes?: boolean;
    no_automated_trading?: boolean;
  };
};

export type MarketOverviewPayload = {
  generated_at: string;
  provider: string;
  range?: {
    timeframe?: string;
    start?: string;
    end?: string;
  };
  macro_indicators?: {
    items?: MarketOverviewIndicatorItem[];
  };
  valuation_indicators?: {
    items?: MarketOverviewIndicatorItem[];
  };
  dashboard_brief?: DashboardBriefPayload;
  information_sources?: InformationSourcesPayload;
  research_follow_up_queue?: ResearchFollowUpQueuePayload;
  diagnostics?: Array<Record<string, unknown>>;
};
