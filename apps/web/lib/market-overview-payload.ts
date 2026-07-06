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
  diagnostics?: Array<Record<string, unknown>>;
};
