import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

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
    llm_api_key_configured: false,
    tushare_token_configured: false,
    market_data_provider_capabilities: [],
  }),
}));

import EvidenceCenterPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function createMarketOverviewPayload() {
  const indicators = [
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
      components: {},
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
      components: {
        source_series_id: "DGS10",
        source_url: "https://fred.stlouisfed.org/series/DGS10",
        methodology: "Reviewed FRED daily observation.",
      },
      no_data_reason: null,
    },
  ];

  return {
    generated_at: "2026-01-02T00:00:00+00:00",
    provider: "yfinance",
    macro_indicators: { items: indicators },
    valuation_indicators: { items: indicators },
    dashboard_brief: {
      status: "degraded",
      generated_at: "2026-01-02T00:00:00+00:00",
      sections: [
        {
          id: "what_changed",
          title: "What changed",
          items: ["US 10Y Treasury Yield: 4.25% as of 2026-01-02."],
        },
        {
          id: "data_gaps",
          title: "Data gaps",
          items: ["Buffett Indicator - CN still needs a reviewed observation."],
        },
      ],
      citations: [
        {
          id: "market_indicator:us_10y_yield:2026-01-02",
          label: "US 10Y Treasury Yield",
          source: "market_indicators",
        },
      ],
      diagnostics: [
        {
          source: "market_indicators",
          status: "no_data",
          severity: "info",
          code: "MACRO_INDICATOR_NO_DATA",
          message: "Some macro indicators do not have audited observations yet.",
        },
      ],
      safety: {
        not_investment_advice: true,
        no_buy_sell_hold: true,
        no_fabricated_macro_data: true,
      },
      narrative: {
        answer_markdown:
          "### Summary\nUS 10Y remains the cited macro datapoint [market_indicator:us_10y_yield:2026-01-02].",
        model: {
          provider: "deterministic",
          name: "dashboard-brief-deterministic-fallback",
          used_llm: false,
          fallback_reason: "OpenAI-compatible LLM provider is not configured.",
        },
        context: {
          source_mix: {
            macro_citations: 1,
            report_citations: 0,
            news_citations: 0,
            information_source_gaps: 2,
          },
        },
      },
    },
    information_sources: {
      status: "degraded",
      summary: {
        total: 3,
        configured: 1,
        needs_action: 2,
        future: 0,
      },
      items: [
        {
          id: "fred_us_rates",
          label: "FRED US rates",
          category: "macro",
          authority: "Federal Reserve Bank of St. Louis FRED",
          status: "needs_adapter",
          freshness_policy: "Daily official Treasury series.",
          ai_usage: "Can support rates context after audited observations are imported.",
          next_action: "Add an official-source adapter or reviewed seed import.",
          evidence_count: 0,
          latest_as_of: null,
          coverage: ["DGS10", "us_10y_yield"],
          collection_note: "Collect DGS10 observations from FRED before seeding rates data.",
          citation_policy: "FRED links are collection guidance only.",
          collection_links: [
            {
              label: "FRED DGS10",
              url: "https://fred.stlouisfed.org/series/DGS10",
              source_type: "official_series",
            },
          ],
          seed_template: {
            label: "FRED rates seed template",
            description: "Prepare reviewed daily Treasury observations before importing rates context.",
            target_indicator_codes: ["us_10y_yield"],
            required_fields: ["code", "as_of", "value", "source", "components"],
            json_template: {
              observations: [
                {
                  code: "us_10y_yield",
                  as_of: "YYYY-MM-DD",
                  value: "<reviewed decimal>",
                  source: "Audited seed: FRED DGS10",
                  components: {
                    source_series_id: "DGS10",
                    methodology: "<operator review note>",
                  },
                },
              ],
            },
            csv_header: ["code", "as_of", "value", "source", "components_json"],
            csv_example_rows: [
              'us_10y_yield,YYYY-MM-DD,<reviewed decimal>,Audited seed: FRED DGS10,"{""source_series_id"": ""DGS10"", ""methodology"": ""<operator review note>""}"',
            ],
            review_checklist: [
              {
                id: "replace_placeholders",
                label: "Replace every placeholder date and value before import.",
                required: true,
                why: "The template is not an observation until reviewed values are supplied.",
              },
            ],
            warnings: ["Do not treat source links or template rows as AI citations."],
            import_command: "python scripts/import_market_indicator_seeds.py path/to/macro-seeds.json",
            citation_boundary:
              "This template is not evidence; imported observations become citeable only after validation.",
          },
        },
        {
          id: "buffett_manual_valuation_components",
          label: "Buffett Indicator manual valuation components",
          category: "valuation",
          authority: "Operator-reviewed public market capitalization and GDP sources",
          status: "needs_manual_seed",
          freshness_policy: "Manual valuation seed.",
          ai_usage: "Can support valuation context after local observations exist.",
          next_action: "Seed Buffett Indicator observations with source notes.",
          evidence_count: 0,
          latest_as_of: null,
          coverage: ["buffett_indicator_cn"],
          collection_note: "Collect market-cap and GDP components from reviewed public sources.",
          citation_policy: "Ratios are citeable only after stored locally.",
          collection_links: [],
          seed_template: null,
        },
        {
          id: "generated_reports",
          label: "Generated reports",
          category: "reports",
          authority: "Local GeneratedReport store",
          status: "configured",
          freshness_policy: "Use latest report as-of date.",
          ai_usage: "Can be cited today when stored reports exist.",
          next_action: "Generate or refresh stored reports.",
          evidence_count: 1,
          latest_as_of: "2026-01-02",
          coverage: ["GeneratedReport.as_of"],
          collection_note: "Generate platform reports.",
          citation_policy: "Stored reports can be cited.",
          collection_links: [],
          seed_template: null,
        },
      ],
      groups: [
        {
          category: "macro",
          label: "Macro sources",
          items: [],
        },
      ],
      diagnostics: [],
    },
    research_follow_up_queue: {
      status: "ok",
      generated_at: "2026-01-02T00:00:00+00:00",
      summary: {
        total: 3,
        returned: 3,
        source_review: 0,
        seed_prep: 1,
        ai_summary_question: 1,
        source_gap: 1,
        research_note: 0,
        citable: 1,
        collection_only: 0,
        guidance_only: 2,
      },
      items: [
        {
          id: "source_note_ai_follow_up:note-1",
          kind: "ai_summary_question",
          priority: "high",
          title: "AAPL valuation source note",
          prompt: "Summarize whether this note is ready for a future Buffett Indicator AI summary.",
          next_action: "Use this as a future AI-summary question after checking citation readiness.",
          citation_policy: "citable",
          citation_id: "research_source_note:note-1",
          note_id: "note-1",
          note_title: "AAPL valuation source note",
          source_name: "Manual notebook",
          source_type: "valuation_component",
          source_id: "buffett_manual_valuation_components",
          source_label: "Buffett Indicator manual valuation components",
          source_category: "valuation",
          source_status: "needs_manual_seed",
          target_indicator_codes: ["buffett_indicator_cn"],
          component_role: "market_cap",
          completeness_status: "complete",
          retrieved_at: "2026-01-02T00:00:00+00:00",
        },
        {
          id: "source_seed_prep:buffett_manual_valuation_components",
          kind: "seed_prep",
          priority: "high",
          title: "Buffett Indicator manual valuation components",
          prompt: "Collect market-cap and GDP components from reviewed public sources.",
          next_action: "Seed Buffett Indicator observations with source notes.",
          citation_policy: "guidance_only",
          source_id: "buffett_manual_valuation_components",
          source_label: "Buffett Indicator manual valuation components",
          source_category: "valuation",
          source_status: "needs_manual_seed",
          target_indicator_codes: ["buffett_indicator_cn"],
          linked_note_count: 1,
          seed_ready_note_count: 1,
        },
        {
          id: "source_gap:fred_us_rates",
          kind: "source_gap",
          priority: "high",
          title: "FRED US rates",
          prompt: "Collect DGS10 observations from FRED before seeding rates data.",
          next_action: "Add an official-source adapter or reviewed seed import.",
          citation_policy: "guidance_only",
          source_id: "fred_us_rates",
          source_label: "FRED US rates",
          source_category: "macro",
          source_status: "needs_adapter",
          target_indicator_codes: ["us_10y_yield"],
        },
      ],
      safety: {
        not_investment_advice: true,
        citations_require_reviewed_citable_notes: true,
        no_automated_trading: true,
      },
    },
  };
}

function createResearchSourceNotesPayload() {
  return {
    items: [
      {
        id: "note-1",
        title: "AAPL valuation source note",
        source_name: "Manual notebook",
        source_type: "valuation_component",
        source_url: "https://example.com/aapl-valuation-source",
        symbols: ["AAPL"],
        tags: ["valuation"],
        ai_follow_up: "Summarize whether this note is ready for a future Buffett Indicator AI summary.",
        excerpt: "Reviewed source excerpt for AAPL valuation.",
        note: "Use this source for Buffett Indicator comparison.",
        review_status: "reviewed",
        is_citable: true,
        citation_id: "research_source_note:note-1",
        retrieved_at: "2026-01-02T00:00:00+00:00",
        metadata: {
          source_id: "buffett_manual_valuation_components",
          source_label: "Buffett Indicator manual valuation components",
          source_category: "valuation",
          target_indicator_codes: ["buffett_indicator_cn"],
          component_role: "market_cap",
          methodology_note: "Reviewed market-cap component.",
          license_note: "Public source for personal research review.",
          review_checklist: {
            source_identity: true,
            source_url_or_document: true,
            date_metadata: true,
            excerpt: true,
            methodology: true,
            targets: true,
            license_note: true,
          },
          completeness: { score: 7, total: 7, status: "complete" },
        },
      },
    ],
    summary: { total: 1, returned: 1, citable: 1 },
  };
}

function createOfficialMacroSourceStatusPayload() {
  return {
    status: "needs_configuration",
    generated_at: "2026-01-02T00:00:00+00:00",
    citation_policy:
      "Source status, configuration, links, and refresh diagnostics are guidance only.",
    providers: [
      {
        provider: "fred",
        label: "FRED US macro",
        status: "needs_configuration",
        configured: false,
        can_refresh_from_browser: false,
        credential_required: true,
        credential_configured: false,
        credential_label: "FRED_API_KEY",
        base_url: "https://api.stlouisfed.org/fred",
        source_url: "https://fred.stlouisfed.org/",
        source_frequency: "daily_or_monthly",
        freshness_policy:
          "Treasury rates and spreads are daily business-day series; CPI and M2 YoY are monthly/source-release dependent.",
        indicator_codes: ["us_10y_yield", "us_2y_yield", "us_10y_2y_spread", "us_cpi_yoy", "us_m2_yoy"],
        evidence_count: 1,
        latest_as_of: "2026-01-02",
        missing_indicator_codes: ["us_2y_yield", "us_10y_2y_spread", "us_cpi_yoy", "us_m2_yoy"],
        recommended_next_action: "Set FRED_API_KEY, then run a dry-run refresh from Macro Research.",
        citation_policy:
          "Source status, configuration, links, and refresh diagnostics are guidance only.",
        collection_links: [],
      },
      {
        provider: "world_bank",
        label: "World Bank Buffett Indicator",
        status: "degraded",
        configured: true,
        can_refresh_from_browser: true,
        credential_required: false,
        credential_configured: true,
        credential_label: null,
        base_url: "https://api.worldbank.org/v2",
        source_url: "https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS",
        source_frequency: "annual_lagged",
        freshness_policy:
          "World Bank market capitalization as percent of GDP is annual and lagged.",
        indicator_codes: ["buffett_indicator_cn", "buffett_indicator_hk", "buffett_indicator_us"],
        evidence_count: 0,
        latest_as_of: null,
        missing_indicator_codes: ["buffett_indicator_cn", "buffett_indicator_hk", "buffett_indicator_us"],
        recommended_next_action: "Run World Bank dry-run, then write refresh.",
        citation_policy:
          "Source status, configuration, links, and refresh diagnostics are guidance only.",
        collection_links: [],
      },
    ],
  };
}

function createResearchBriefsPayload() {
  return {
    items: [
      {
        id: "brief-1",
        title: "Morning macro evidence",
        brief_type: "evidence_center",
        content_markdown:
          "### Summary\n- US 10Y remains the cited macro datapoint [market_indicator:us_10y_yield:2026-01-02].",
        citations: [
          {
            id: "market_indicator:us_10y_yield:2026-01-02",
            label: "US 10Y Treasury Yield",
            source: "market_indicators",
          },
        ],
        source_summary: { source_gap_count: 2 },
        diagnostics: [],
        model: {
          provider: "deterministic",
          name: "research-brief-deterministic-fallback",
          used_llm: false,
        },
        safety: {
          not_investment_advice: true,
          no_buy_sell_hold: true,
          no_fabricated_macro_data: true,
        },
        created_at: "2026-01-02T00:00:00+00:00",
      },
    ],
    summary: { total: 1, returned: 1 },
  };
}

function createMarketDailyEvidencePayload() {
  return {
    items: [],
    citations: [
      {
        id: "market_daily_event:hot_sector:semiconductor:2026-01-02",
        label: "Hot sector: Semiconductor",
        source: "market_daily_evidence",
        source_type: "market_daily_event",
        as_of: "2026-01-02",
        provider: "akshare",
      },
    ],
    summary: {
      total: 4,
      returned: 1,
      counts_by_event_type: {
        stock_fund_flow: 2,
        hot_sector: 2,
      },
      latest_imported_at: "2026-01-02T08:00:00+00:00",
      latest_trade_date: "2026-01-02",
    },
    safety: {
      persisted_rows_only: true,
      not_investment_advice: true,
      no_automated_trading: true,
    },
  };
}

function createOfficialDisclosureEvidencePayload() {
  return {
    status: "ok",
    symbols: ["000001"],
    summary: {
      eligible_symbol_count: 1,
      metadata_disclosure_count: 1,
      extracted_document_count: 1,
      citable_section_count: 3,
    },
    items: [{
      id: "11111111-2222-3333-4444-555555555555",
      symbol: "000001",
      title: "2025 Annual Report",
      published_at: "2026-03-21T00:00:00+00:00",
      source_url: "https://www.cninfo.com.cn/disclosure/1",
      citation_id: "official_disclosure:11111111-2222-3333-4444-555555555555",
      status: "extracted",
      section_count: 3,
      content_citable: true,
    }],
  };
}

function createMacroDashboardPayload() {
  return {
    status: "ok",
    generated_at: "2026-07-17T01:00:00+00:00",
    latest_as_of: "2026-06-30",
    summary: { total: 23, available: 1, missing: 22, stale: 0 },
    groups: [
      {
        id: "fundamentals",
        items: [
          {
            code: "cn_cpi_yoy",
            name: "China CPI YoY",
            region: "CN",
            category: "inflation",
            unit: "percent",
            status: "ok",
            freshness: "fresh",
            value: 1,
            as_of: "2026-06-30",
            source: "AkShare macro_china_cpi",
            previous_value: 1.2,
            change: -0.2,
            direction: "down",
            history: [
              { as_of: "2026-05-31", value: 1.2 },
              { as_of: "2026-06-30", value: 1 },
            ],
            no_data_reason: null,
          },
        ],
      },
    ],
  };
}

it("renders macro evidence first, keeps advanced source tools reachable, and resolves template labels", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/dashboard/market-overview?provider=yfinance")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketOverviewPayload())));
    }
    if (url.endsWith("/market-indicators/official-sources/status")) {
      return Promise.resolve(new Response(JSON.stringify(createOfficialMacroSourceStatusPayload())));
    }
    if (url.endsWith("/research-source-notes?limit=50")) {
      return Promise.resolve(new Response(JSON.stringify(createResearchSourceNotesPayload())));
    }
    if (url.endsWith("/research-briefs?limit=10")) {
      return Promise.resolve(new Response(JSON.stringify(createResearchBriefsPayload())));
    }
    if (url.endsWith("/market-daily-evidence?limit=12&citable_only=true")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketDailyEvidencePayload())));
    }
    if (url.endsWith("/official-disclosures/evidence-status?limit=50")) {
      return Promise.resolve(new Response(JSON.stringify(createOfficialDisclosureEvidencePayload())));
    }
    if (url.endsWith("/market-indicators/dashboard?history_limit=12")) {
      return Promise.resolve(new Response(JSON.stringify(createMacroDashboardPayload())));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await EvidenceCenterPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByRole("heading", { name: "Macro Research" })).toBeInTheDocument();
  expect(screen.getByText("Macroeconomic dashboard")).toBeInTheDocument();
  expect(screen.getByText("China CPI YoY")).toBeInTheDocument();
  expect(screen.getByText("1%")).toBeInTheDocument();
  expect(screen.getByText("Configured indicators").parentElement).toHaveTextContent("23");
  expect(screen.getByText("AI-citable observations").parentElement).toHaveTextContent("1");
  const outerMaintenance = screen
    .getByText("Evidence maintenance and advanced tools")
    .closest("details");
  expect(outerMaintenance).not.toBeNull();
  expect(outerMaintenance).not.toHaveAttribute("open");
  expect(screen.getByText("Active provider: yfinance")).toBeInTheDocument();
  expect(screen.getAllByText(/US 10Y remains the cited macro datapoint/).length).toBeGreaterThan(0);
  expect(screen.getAllByText("Deterministic fallback").length).toBeGreaterThan(0);
  expect(screen.getByText("Macro evidence: 1")).toBeInTheDocument();
  expect(screen.getByText("Source gaps: 2")).toBeInTheDocument();

  const sourceMaintenanceSummary = screen.getByText("Data sources and maintenance").closest("summary");
  const sourceMaintenanceDetails = sourceMaintenanceSummary?.closest("details");
  expect(sourceMaintenanceDetails).not.toBeNull();
  expect(sourceMaintenanceDetails).not.toHaveAttribute("open");
  fireEvent.click(sourceMaintenanceSummary!);
  expect(sourceMaintenanceDetails).toHaveAttribute("open");

  expect(screen.getByText("Official macro refresh status")).toBeInTheDocument();
  expect(screen.getByText("Manual runbook")).toBeInTheDocument();
  expect(screen.getByText("Browser refresh enabled")).toBeInTheDocument();
  expect(screen.queryByText("No web refresh action")).not.toBeInTheDocument();
  expect(screen.getByText("FRED US macro")).toBeInTheDocument();
  expect(screen.getByText("World Bank Buffett Indicator")).toBeInTheDocument();
  expect(screen.getByText("Needs configuration")).toBeInTheDocument();
  expect(screen.getByText("Browser refresh blocked")).toBeInTheDocument();
  expect(screen.getByText("FRED_API_KEY is missing.")).toBeInTheDocument();
  expect(screen.getByText("Stored observations: 1")).toBeInTheDocument();
  expect(screen.getByText(/Missing: us_2y_yield, us_10y_2y_spread/)).toBeInTheDocument();
  expect(screen.getByText("No secret required.")).toBeInTheDocument();
  expect(screen.getByText("Browser refresh ready")).toBeInTheDocument();
  expect(screen.getByText(/Annual lagged World Bank context/)).toBeInTheDocument();
  expect(screen.getAllByText(/Status rows, links, and diagnostics are guidance only/).length).toBeGreaterThan(0);
  expect(screen.getAllByRole("button", { name: "Run dry-run" })).toHaveLength(2);
  expect(screen.getAllByRole("button", { name: "Write observations" })).toHaveLength(2);
  expect(screen.getAllByText(/Write refresh stores audited local observations/)).toHaveLength(2);
  expect(screen.getByText("1/5 local observations")).toBeInTheDocument();
  expect(screen.getByText("0/3 local observations")).toBeInTheDocument();
  expect(screen.getByText("python scripts/refresh_fred_macro_indicators.py --series all --latest-only")).toBeInTheDocument();
  expect(screen.getByText("python scripts/refresh_world_bank_macro_indicators.py --target all")).toBeInTheDocument();
  expect(screen.getByText("Runbook path: docs/runbooks/official-macro-refresh.md")).toBeInTheDocument();
  expect(screen.getByText(/cn_m2_yoy remain source gaps/)).toBeInTheDocument();
  expect(screen.getByText("MACRO_INDICATOR_NO_DATA: Some macro indicators do not have audited observations yet.")).toBeInTheDocument();
  expect(screen.queryByText("ResearchSourceNotebook.completenessSummary")).not.toBeInTheDocument();
  expect(screen.getAllByText("7/7 checks").length).toBeGreaterThan(0);

  const pageText = document.body.textContent ?? "";
  expect(pageText.indexOf("AI evidence summary")).toBeLessThan(pageText.indexOf("Saved research brief inbox"));
  expect(pageText.indexOf("Saved research brief inbox")).toBeLessThan(pageText.indexOf("Source notebook"));
  expect(pageText.indexOf("Source notebook")).toBeLessThan(pageText.indexOf("Stored market daily evidence"));
  expect(pageText.indexOf("Official disclosure document evidence")).toBeLessThan(
    pageText.indexOf("Official macro refresh status"),
  );
  expect(pageText.indexOf("Official macro refresh status")).toBeLessThan(pageText.indexOf("Macro and valuation evidence"));
  expect(pageText.indexOf("Macro and valuation evidence")).toBeLessThan(
    pageText.indexOf("Source readiness and collection workflow"),
  );
  expect(pageText.indexOf("Source readiness and collection workflow")).toBeLessThan(
    pageText.indexOf("Advanced source review tools"),
  );
  expect(screen.getByText("Data sources and maintenance")).toBeInTheDocument();

  const ratesRow = screen
    .getAllByText("US 10Y Treasury Yield")
    .map((element) => element.closest("tr"))
    .find(Boolean);
  expect(ratesRow).not.toBeNull();
  expect(within(ratesRow as HTMLElement).getByText("4.25%")).toBeInTheDocument();
  expect(within(ratesRow as HTMLElement).getByText("AI-citable")).toBeInTheDocument();
  expect(within(ratesRow as HTMLElement).getByText("Source + method")).toBeInTheDocument();

  const buffettRow = screen
    .getAllByText("Buffett Indicator - CN")
    .map((element) => element.closest("tr"))
    .find(Boolean);
  expect(buffettRow).not.toBeNull();
  expect(within(buffettRow as HTMLElement).getAllByText("N/A").length).toBeGreaterThan(0);
  expect(within(buffettRow as HTMLElement).getByText("Needs manual seed")).toBeInTheDocument();
  expect(screen.queryByText("0.00%")).not.toBeInTheDocument();

  expect(screen.getByText("FRED rates seed template")).toBeInTheDocument();
  expect(screen.getByText("python scripts/import_market_indicator_seeds.py path/to/macro-seeds.json")).toBeInTheDocument();
  expect(screen.getByText("This template is not evidence; imported observations become citeable only after validation.")).toBeInTheDocument();
  expect(screen.getAllByText("Source notebook").length).toBeGreaterThan(0);
  expect(screen.getAllByText("AAPL valuation source note").length).toBeGreaterThan(0);
  expect(screen.getByText("Linked: Buffett Indicator manual valuation components")).toBeInTheDocument();
  expect(screen.getByText("Target: buffett_indicator_cn")).toBeInTheDocument();
  expect(screen.getByText("Linked notebook entries: 1")).toBeInTheDocument();
  expect(screen.getByText("Seed-review ready: 1")).toBeInTheDocument();
  expect(screen.getByText("Citation: research_source_note:note-1")).toBeInTheDocument();

  expect(screen.getByText("Research follow-up queue")).toBeInTheDocument();
  expect(screen.getByText("AI questions")).toBeInTheDocument();
  expect(screen.getAllByText("Seed prep").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Source gaps").length).toBeGreaterThan(0);
  expect(screen.getByText("AI summary question")).toBeInTheDocument();
  expect(screen.getAllByText("Guidance only").length).toBeGreaterThan(0);
  expect(screen.getByText("Citable evidence")).toBeInTheDocument();
  expect(screen.getAllByText(/research_source_note:note-1/).length).toBeGreaterThan(0);
  expect(screen.getByText(/Summarize whether this note is ready/)).toBeInTheDocument();
  expect(screen.getByText(/Queue items are research prompts and evidence-preparation tasks only/)).toBeInTheDocument();
  expect(screen.getByText("Saved research brief inbox")).toBeInTheDocument();
  expect(screen.getByText("Morning macro evidence")).toBeInTheDocument();
  expect(screen.getByText("research-brief-deterministic-fallback", { exact: false })).toBeInTheDocument();
  expect(screen.getByText("Stored market daily evidence")).toBeInTheDocument();
  expect(screen.getByText("Stock fund flow: 2")).toBeInTheDocument();
  expect(screen.getByText("Hot sector: 2")).toBeInTheDocument();
  expect(
    screen.getByText("market_daily_event:hot_sector:semiconductor:2026-01-02"),
  ).toBeInTheDocument();
  expect(screen.getByText("Only persisted rows are citable")).toBeInTheDocument();
  expect(screen.getByText("Official disclosure document evidence")).toBeInTheDocument();
  expect(screen.getAllByText("2025 Annual Report").length).toBeGreaterThan(0);
  expect(screen.getByText("Watchlist-only, sequential CNINFO requests")).toBeInTheDocument();

  const marketMaintenanceDetails = screen
    .getByText("Market evidence refresh and import")
    .closest("details");
  const disclosureMaintenanceDetails = screen
    .getByText("Disclosure ingestion operations")
    .closest("details");
  expect(marketMaintenanceDetails).not.toBeNull();
  expect(marketMaintenanceDetails).not.toHaveAttribute("open");
  expect(marketMaintenanceDetails).not.toContainElement(
    screen.getByText("market_daily_event:hot_sector:semiconductor:2026-01-02"),
  );
  expect(
    within(marketMaintenanceDetails!).getByRole("button", {
      name: "Refresh today's market evidence",
      hidden: true,
    }),
  ).toBeInTheDocument();
  expect(disclosureMaintenanceDetails).not.toBeNull();
  expect(disclosureMaintenanceDetails).not.toHaveAttribute("open");
  expect(disclosureMaintenanceDetails).not.toContainElement(
    screen.getByRole("link", { name: "2025 Annual Report" }),
  );
  expect(
    within(disclosureMaintenanceDetails!).getByRole("button", {
      name: "Ingest watchlist disclosures",
      hidden: true,
    }),
  ).toBeInTheDocument();
  expect(
    within(disclosureMaintenanceDetails!).getByRole("button", {
      name: "Ingest PDF",
      hidden: true,
    }),
  ).toBeInTheDocument();
  expect(sourceMaintenanceDetails).not.toContainElement(
    screen.getByText("Stored market daily evidence"),
  );
  expect(sourceMaintenanceDetails).not.toContainElement(
    screen.getByText("Official disclosure document evidence"),
  );

  const fredLink = screen.getByRole("link", { name: /FRED DGS10/, hidden: true });
  expect(fredLink).toHaveAttribute("href", "https://fred.stlouisfed.org/series/DGS10");
  expect(fredLink).toHaveAttribute("target", "_blank");
  expect(fredLink).toHaveAttribute("rel", "noreferrer");

  expect(screen.getByText("Citation boundary")).toBeInTheDocument();
  expect(screen.getByText("Collection links and seed templates stay collection guidance until reviewed observations are imported.")).toBeInTheDocument();
  expect(screen.getAllByText("Not investment advice").length).toBeGreaterThan(0);
});

it("keeps independently loaded notes and briefs visible when market overview fails", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/research-source-notes?limit=50")) {
      return Promise.resolve(new Response(JSON.stringify(createResearchSourceNotesPayload())));
    }
    if (url.endsWith("/research-briefs?limit=10")) {
      return Promise.resolve(new Response(JSON.stringify(createResearchBriefsPayload())));
    }
    if (url.endsWith("/market-daily-evidence?limit=12&citable_only=true")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketDailyEvidencePayload())));
    }
    if (url.endsWith("/official-disclosures/evidence-status?limit=50")) {
      return Promise.resolve(new Response(JSON.stringify(createOfficialDisclosureEvidencePayload())));
    }
    return Promise.resolve(new Response("", { status: 503 }));
  });

  render(
    await EvidenceCenterPage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByText("Macro Research is unavailable")).toBeInTheDocument();
  expect(screen.getByText("The market overview could not be loaded. Independently available notes, briefs, and stored evidence remain visible below.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Provider settings" })).toHaveAttribute("href", "/settings");
  expect(screen.getByText("Morning macro evidence")).toBeInTheDocument();
  expect(screen.getAllByText("AAPL valuation source note").length).toBeGreaterThan(0);
  expect(
    screen.getByText("market_daily_event:hot_sector:semiconductor:2026-01-02"),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "2025 Annual Report" })).toBeInTheDocument();
});
