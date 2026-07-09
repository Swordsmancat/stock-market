import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const { getPlatformSettingsMock } = vi.hoisted(() => ({
  getPlatformSettingsMock: vi.fn(),
}));

vi.mock("@/lib/dates", () => ({
  getDashboardDateRanges: () => ({
    recent: { start: "2026-01-01", end: "2026-01-02" },
    analysis: { start: "2026-01-01", end: "2026-01-20" },
  }),
}));

vi.mock("@/context/market-colors-context", () => ({
  useMarketColorsContext: () => ({
    colorScheme: "china",
    setColorScheme: vi.fn(),
    getMovementColor: (value: number) => value >= 0 ? "text-positive" : "text-negative",
    getMovementBg: (value: number) => value >= 0 ? "bg-positive" : "bg-negative",
    colors: {
      up: "text-positive",
      down: "text-negative",
      upBg: "bg-positive",
      downBg: "bg-negative",
    },
  }),
}));

vi.mock("@/lib/platform-settings-store", async () => {
  const actual = await vi.importActual<typeof import("@/lib/platform-settings-store")>(
    "@/lib/platform-settings-store",
  );
  return {
    ...actual,
    getPlatformSettings: getPlatformSettingsMock,
  };
});

import HomePage from "./page";

function buildPlatformSettings(overrides: Record<string, unknown> = {}) {
  return {
    market_data_provider: "yfinance",
    llm_provider: "mock",
    llm_api_key: "",
    llm_api_base: "https://api.openai.com/v1",
    akshare_enabled: false,
    tushare_token: "",
    tushare_http_url: "",
    color_scheme: "china",
    favorite_home_index_codes: [
      "us_sp_500",
      "us_nasdaq_composite",
      "us_dow_jones",
      "cn_shanghai_composite",
      "cn_shenzhen_component",
      "cn_csi_300",
      "cn_chinext",
      "cn_csi_500",
    ],
    home_index_display_fields: ["latest_close", "percent_change", "freshness", "as_of", "region"],
    favorite_macro_indicator_codes: [
      "buffett_indicator_us",
      "buffett_indicator_cn",
      "buffett_indicator_hk",
      "us_10y_yield",
      "us_10y_2y_spread",
      "us_cpi_yoy",
      "us_m2_yoy",
      "cn_m2_yoy",
    ],
    llm_api_key_configured: false,
    tushare_token_configured: false,
    market_data_provider_capabilities: [],
    news_search_provider_capabilities: [
      {
        provider: "anspire",
        display_name: "Anspire AI Search",
        enabled: true,
        configured: true,
        credential_required: true,
        credential_configured: true,
        credential_field: "api_key",
        priority: 1,
        supported_markets: ["A-share", "US", "HK"],
        supported_regions: ["CN", "US", "HK"],
        supported_result_kinds: ["news", "web", "public_opinion"],
        default_timeout_seconds: 8,
        default_max_results: 10,
        implementation_status: "implemented",
        readiness_note: "Bearer-auth search adapter.",
        citation_caveat: "Search results become citable only after local storage.",
      },
      {
        provider: "serpapi_baidu",
        display_name: "SerpAPI Baidu",
        enabled: true,
        configured: false,
        credential_required: true,
        credential_configured: false,
        credential_field: "api_key",
        priority: 2,
        supported_markets: ["A-share", "HK", "China"],
        supported_regions: ["CN"],
        supported_result_kinds: ["news", "web", "social"],
        default_timeout_seconds: 8,
        default_max_results: 10,
        implementation_status: "implemented",
        readiness_note: "Baidu search adapter.",
        citation_caveat: "Collection candidates until stored locally.",
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  getPlatformSettingsMock.mockResolvedValue(buildPlatformSettings());
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  getPlatformSettingsMock.mockReset();
});

function createMarketOverviewPayload(symbol = "AAPL", name = "Apple Inc.", market = "US", latestClose = 102) {
  const dailyBars = [
    { timestamp: "2026-01-01", open: latestClose - 2, high: latestClose, low: latestClose - 3, close: latestClose - 1, volume: 1000 },
    { timestamp: "2026-01-02", open: latestClose - 1, high: latestClose + 1, low: latestClose - 2, close: latestClose, volume: 1100 },
  ];
  const movement = {
    direction: "up",
    absolute_change: 1,
    percent_change: 1 / (latestClose - 1),
  };
  const indexNames = [
    ["cn_shanghai_composite", "Shanghai Composite", "CN"],
    ["cn_shenzhen_component", "Shenzhen Component", "CN"],
    ["cn_chinext", "ChiNext", "CN"],
    ["cn_csi_300", "CSI 300", "CN"],
    ["cn_csi_500", "CSI 500", "CN"],
    ["hk_hang_seng", "Hang Seng Index", "HK"],
    ["hk_hang_seng_tech", "Hang Seng Tech Index", "HK"],
    ["us_sp_500", "S&P 500", "US"],
    ["us_nasdaq_composite", "Nasdaq Composite", "US"],
    ["us_dow_jones", "Dow Jones Industrial Average", "US"],
  ];

  const macroIndicators = [
    ["buffett_indicator_cn", "Buffett Indicator - CN", "CN", "valuation"],
    ["buffett_indicator_hk", "Buffett Indicator - HK", "HK", "valuation"],
    ["buffett_indicator_us", "Buffett Indicator - US", "US", "valuation"],
    ["us_10y_yield", "US 10Y Treasury Yield", "US", "rates"],
    ["us_2y_yield", "US 2Y Treasury Yield", "US", "rates"],
    ["us_10y_2y_spread", "US 10Y-2Y Yield Spread", "US", "rates"],
    ["us_cpi_yoy", "US CPI YoY", "US", "inflation"],
    ["us_m2_yoy", "US M2 Money Supply YoY", "US", "liquidity"],
    ["cn_m2_yoy", "China M2 Money Supply YoY", "CN", "liquidity"],
  ].map(([code, indicatorName, region, category]) => ({
    code,
    name: indicatorName,
    region,
    category,
    status: code === "us_10y_yield" ? "ok" : "no_data",
    value: code === "us_10y_yield" ? 4.25 : null,
    unit: "percent",
    as_of: code === "us_10y_yield" ? "2026-01-02" : null,
    source: code === "us_10y_yield" ? "Audited seed: FRED DGS10" : null,
    components: code === "us_10y_yield" ? { source_series_id: "DGS10" } : {},
    no_data_reason: code === "us_10y_yield" ? null : "No audited observation has been seeded for this indicator yet.",
  }));

  return {
    generated_at: "2026-01-02T00:00:00+00:00",
    provider: "yfinance",
    range: { timeframe: "1d", start: "2025-10-02", end: "2026-01-02" },
    followed: {
      scope: "watchlist",
      limit: 6,
      items: [
        {
          symbol,
          name,
          market,
          currency: market === "CN" ? "CNY" : "USD",
          status: "ok",
          freshness: "fresh",
          latest: { timestamp: "2026-01-02", close: latestClose, movement },
          bars: dailyBars,
          source: "database",
          provider: "yfinance",
          effective_provider: "yfinance",
          detail_path: `/instruments/${symbol}`,
        },
      ],
    },
    indices: {
      items: indexNames.map(([code, indexName, region], index) => ({
        code,
        name: indexName,
        region,
        market: region,
        currency: region === "US" ? "USD" : region === "HK" ? "HKD" : "CNY",
        provider_symbol: code,
        status: "ok",
        freshness: "fresh",
        latest: { timestamp: "2026-01-02", close: 3000 + index, movement },
        bars: dailyBars,
        source: "database",
        provider: "yfinance",
        effective_provider: "yfinance",
      })),
    },
    valuation_indicators: {
      items: macroIndicators,
    },
    macro_indicators: {
      items: macroIndicators,
    },
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
          id: "why_it_matters",
          title: "Why it matters",
          items: ["Macro indicators are shown with source and as-of metadata."],
        },
        {
          id: "what_to_watch_next",
          title: "What to watch next",
          items: ["Review generated reports and watchlist moves together with macro freshness."],
        },
        {
          id: "data_gaps",
          title: "Data gaps",
          items: ["Buffett Indicator - CN: No audited observation has been seeded for this indicator yet."],
        },
      ],
      citations: [
        {
          id: "market_indicator:us_10y_yield:2026-01-02",
          label: "US 10Y Treasury Yield",
          source: "market_indicators",
        },
        {
          id: "research_source_note:note-1",
          label: "Reviewed macro source note",
          source: "research_source_notes",
          source_type: "research_source_note",
        },
      ],
      diagnostics: [
        {
          source: "market_indicators",
          status: "no_data",
          severity: "info",
          code: "MACRO_INDICATOR_NO_DATA",
          message: "Some macro indicators are configured but do not have audited observations yet.",
        },
      ],
      safety: {
        not_investment_advice: true,
        no_buy_sell_hold: true,
        no_fabricated_macro_data: true,
      },
      narrative: {
        answer_markdown:
          "### Summary\nUS 10Y remains the cited macro datapoint [market_indicator:us_10y_yield:2026-01-02].\n\n### Safety note\nNot investment advice.",
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
            research_source_note_citations: 1,
            information_source_gaps: 3,
          },
        },
      },
    },
    information_sources: {
      status: "degraded",
      summary: {
        total: 4,
        configured: 1,
        needs_action: 2,
        future: 1,
      },
      groups: [
        {
          category: "macro",
          label: "Macro sources",
          items: [
            {
              id: "fred_us_rates",
              label: "FRED US Treasury rates",
              category: "macro",
              authority: "Federal Reserve Bank of St. Louis FRED",
              coverage: ["DGS10", "DGS2", "T10Y2Y"],
              status: "needs_adapter",
              freshness_policy: "Daily official series; update after FRED observation publication.",
              ai_usage: "Can support rates and yield-curve context after observations are imported.",
              next_action: "Add official-source adapter or audited seed import for DGS10/DGS2/T10Y2Y.",
              evidence_count: 0,
              latest_as_of: null,
              collection_note: "Collect DGS10, DGS2, and T10Y2Y observations from official FRED pages before seeding rates data.",
              citation_policy: "Can be cited only after a reviewed observation is stored locally.",
              collection_links: [
                {
                  label: "FRED DGS10",
                  url: "https://fred.stlouisfed.org/series/DGS10",
                  source_type: "official_series",
                },
              ],
              seed_template: {
                label: "FRED rates seed template",
                description: "Prepare reviewed daily Treasury observations before importing rates and yield-curve context.",
                target_indicator_codes: ["us_10y_yield", "us_2y_yield", "us_10y_2y_spread"],
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
                        source_url: "https://fred.stlouisfed.org/series/DGS10",
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
                warnings: [
                  "Replace every placeholder before import; template values are not market data.",
                ],
                import_command: "python scripts/import_market_indicator_seeds.py path/to/macro-seeds.json",
                citation_boundary:
                  "This template is not evidence; imported observations become citeable only after validation stores reviewed source and methodology metadata locally.",
              },
            },
          ],
        },
        {
          category: "documents",
          label: "Hard-to-find documents",
          items: [
            {
              id: "sec_filings",
              label: "SEC filings and announcements",
              category: "documents",
              authority: "SEC EDGAR",
              coverage: ["10-K", "10-Q", "8-K"],
              status: "future",
              freshness_policy: "Use official APIs or user-provided files only; do not scrape restricted content.",
              ai_usage: "Future evidence for company-specific AI summaries with citations.",
              next_action: "Define legal ingestion policy before storing filing text or transcripts.",
              evidence_count: 0,
              latest_as_of: null,
              collection_note: "Use EDGAR or user-provided files only; this panel is collection guidance, not automated scraping.",
              citation_policy: "Do not cite filings until an adapter or manually reviewed local document is available.",
              collection_links: [
                {
                  label: "SEC EDGAR company search",
                  url: "https://www.sec.gov/edgar/search/",
                  source_type: "official_documents",
                },
              ],
            },
          ],
        },
      ],
      items: [],
      diagnostics: [],
    },
    diagnostics: [],
  };
}

function createOfficialMacroSourceStatusPayload() {
  return {
    status: "needs_configuration",
    generated_at: "2026-01-02T00:00:00+00:00",
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
        source_frequency: "daily_or_monthly",
        indicator_codes: ["us_10y_yield", "us_2y_yield", "us_10y_2y_spread", "us_cpi_yoy", "us_m2_yoy"],
        evidence_count: 1,
        latest_as_of: "2026-01-02",
        missing_indicator_codes: ["us_2y_yield", "us_10y_2y_spread", "us_cpi_yoy", "us_m2_yoy"],
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
        source_frequency: "annual_lagged",
        indicator_codes: ["buffett_indicator_us", "buffett_indicator_cn", "buffett_indicator_hk"],
        evidence_count: 0,
        latest_as_of: null,
        missing_indicator_codes: ["buffett_indicator_us", "buffett_indicator_cn", "buffett_indicator_hk"],
      },
    ],
  };
}

function mockCuratedHomepageFetch(marketOverviewPayload = createMarketOverviewPayload()) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/instruments")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "AAPL", name: "Apple Inc.", market: "US" }],
          }),
        ),
      );
    }
    if (url.includes("/market-data/AAPL/latest")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "database",
            status: "ok",
            item: { timestamp: "2026-01-02", close: 102 },
          }),
        ),
      );
    }
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(new Response(JSON.stringify({ items: [] })));
    }
    if (url.endsWith("/alerts/triggers/recent?limit=5")) {
      return Promise.resolve(new Response(JSON.stringify({ items: [] })));
    }
    if (url.endsWith("/task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "succeeded" })));
    }
    if (url.includes("/news/AAPL")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            source: "database",
            items: [{ title: "Apple reports strong growth in services revenue", sentiment: "positive", confidence: 0.6 }],
          }),
        ),
      );
    }
    if (url.includes("/sectors/hot")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "ok",
            data_mode: "live",
            count: 0,
            items: [],
          }),
        ),
      );
    }
    if (url.includes("/dashboard/market-overview")) {
      return Promise.resolve(new Response(JSON.stringify(marketOverviewPayload)));
    }
    if (url.includes("/market-indicators/official-sources/status")) {
      return Promise.resolve(new Response(JSON.stringify(createOfficialMacroSourceStatusPayload())));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });
}

it("renders stock analysis dashboard data from backend APIs", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/settings/platform")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            market_data_provider: "yfinance",
            llm_provider: "mock",
            llm_api_key: "",
            llm_api_base: "https://api.openai.com/v1",
          }),
        ),
      );
    }
    if (url.endsWith("/instruments")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "AAPL", name: "Apple Inc.", market: "US" }],
          }),
        ),
      );
    }
    if (url.includes("/market-data/AAPL/latest")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "database",
            item: { close: 102 },
          }),
        ),
      );
    }
    if (url.includes("/market-data/AAPL/bars")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "database",
            items: [{ close: 102 }],
          }),
        ),
      );
    }
    if (url.includes("/reports/AAPL/stock")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            report_type: "stock_daily",
            content_markdown:
              "# AAPL AI 个股报告\n\nMA 119.00, RSI 100.00\n\nApple reports strong growth in services revenue",
            citations: [
              "bars_1d:AAPL:2026-01-02",
              "fundamental_metrics:AAPL:2026-01-02",
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/reports/AAPL/daily/latest")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            report_type: "stock_daily",
            as_of: "2026-01-20",
            content_markdown:
              "# AAPL 每日报告\n\n持久化日报：MA 119.00，Apple reports strong growth in services revenue",
            citations: [
              "technical_indicators:AAPL:2026-01-20T00:00:00+00:00",
              "news_articles:AAPL:https://example.com/aapl-services-growth",
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/reports/AAPL/daily/history?limit=5")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            items: [
              {
                as_of: "2026-01-20",
                content_markdown: "# AAPL 每日报告\n\n最新持久化日报",
              },
              {
                as_of: "2026-01-19",
                content_markdown: "# AAPL 每日报告\n\n上一交易日日报",
              },
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/portfolios/demo")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: "demo",
            source: "database",
            positions: [{ symbol: "AAPL", market_value: 1020 }],
          }),
        ),
      );
    }
    if (url.endsWith("/indicators/AAPL")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "database",
            as_of: "2026-01-20T00:00:00+00:00",
            indicators: {
              ma: 119,
              rsi: 100,
              bollinger: { upper: 121, middle: 119, lower: 117 },
              atr: 3,
            },
          }),
        ),
      );
    }
    if (url.endsWith("/fundamentals/AAPL")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "mock_fundamentals",
            item: {
              summary: "PE 28.40，营收增速 8.00%，净利率 24.00%，资产负债率 31.00%",
            },
          }),
        ),
      );
    }
    if (url.endsWith("/news/AAPL")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            source: "database",
            summary: { latest_sentiment: "positive", article_count: 1 },
            items: [
              {
                title: "Apple reports strong growth in services revenue",
                sentiment: "positive",
                confidence: 0.6,
              },
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            task_name: "reports.refresh_daily_watchlist_analysis",
            status: "succeeded",
            duration_ms: 1280,
            result_json: { item_count: 2 },
          }),
        ),
      );
    }
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(new Response(JSON.stringify({ items: [] })));
    }
    if (url.endsWith("/alerts/triggers/recent?limit=5")) {
      return Promise.resolve(new Response(JSON.stringify({ items: [] })));
    }
    if (url.includes("/recommendations?")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "ok",
            generated_at: "2026-07-03T10:00:00Z",
            count: 1,
            items: [
              {
                symbol: "AAPL",
                type: "breakout",
                title: "AAPL 突破20日均线",
                reason: "价格重新站上关键均线，短线动能改善。",
                confidence: 0.82,
                timestamp: "2026-07-03T10:00:00Z",
                data: { close: 102 },
              },
            ],
          }),
        ),
      );
    }
    if (url.includes("/sectors/hot")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "degraded",
            data_mode: "mock",
            source: "static_sector_fixture",
            provider: "static_fixture",
            effective_provider: "static_fixture",
            requested_provider: "static_fixture",
            as_of: null,
            is_realtime: false,
            is_delayed: false,
            delay_minutes: null,
            flow_definition: {
              metric: "static_fixture_demo_value",
              window: "unknown",
              currency: "N/A",
              unit: "hundred_million",
              methodology: "Static fixture values for UI demonstration only.",
            },
            message: "Static mock sector data; not live market data.",
            count: 1,
            items: [
              {
                sector_id: "ev_new_energy",
                name: "新能源汽车",
                name_en: "EV & New Energy",
                market: "mixed_global",
                rank: 1,
                change_percent: 5.2,
                fund_flow: "流入",
                fund_flow_amount: 12.5,
                flow_direction: "inflow",
                net_flow_amount: 1_250_000_000,
                net_flow_currency: "USD",
                net_flow_unit: "yuan",
                flow_definition: "Static fixture values for UI demonstration only.",
                leader_symbol: "TSLA",
                leader_name: "特斯拉",
                leader_change_percent: 6.8,
                leader: { symbol: "TSLA", name: "特斯拉", change_percent: 6.8 },
                symbols_count: 4,
                top_constituents: [
                  { symbol: "TSLA", name: "特斯拉", change_percent: 6.8 },
                  { symbol: "NIO", name: "蔚来", change_percent: 4.2 },
                ],
                provider: "static_fixture",
                is_verified: false,
              },
            ],
          }),
        ),
      );
    }
    if (url.includes("/dashboard/market-overview")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketOverviewPayload())));
    }
    if (url.includes("/market-indicators/official-sources/status")) {
      return Promise.resolve(new Response(JSON.stringify(createOfficialMacroSourceStatusPayload())));
    }
    if (url.includes("/api/ingestion/snapshot")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "dispatched",
            task_run: {
              id: "ingest-task-id",
              status: "running",
              task_name: "ingestion.ingest_market_data",
            },
          }),
        ),
      );
    }
    if (url.includes("/api/task-runs/ingest-task-id")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            item: {
              id: "ingest-task-id",
              status: "succeeded",
              task_name: "ingestion.ingest_market_data",
              result_json: { market: "US", bar_count: 2 },
            },
          }),
        ),
      );
    }
    if (url.includes("/api/analysis/refresh")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "dispatched",
            task_run: {
              id: "analysis-task-id",
              status: "running",
              task_name: "reports.refresh_daily_stock_analysis",
            },
          }),
        ),
      );
    }
    if (url.includes("/api/task-runs/analysis-task-id")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            item: {
              id: "analysis-task-id",
              status: "succeeded",
              task_name: "reports.refresh_daily_stock_analysis",
              result_json: { symbol: "AAPL", status: "refreshed" },
            },
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await HomePage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByRole("heading", { name: "Market overview" })).toBeInTheDocument();
  expect(
    screen.getByText("Core market pulse, macro watchpoints, sector rotation, news sentiment, and key operating status."),
  ).toBeInTheDocument();
  expect(screen.getAllByText("Market dashboard").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Core market indices").length).toBeGreaterThan(0);
  expect(screen.getByText("US and A-share benchmark indices stay at the top of the homepage.")).toBeInTheDocument();
  expect(screen.getAllByText("Shanghai Composite").length).toBeGreaterThan(0);
  expect(screen.getAllByText("S&P 500").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Followed macro indicators").length).toBeGreaterThan(0);
  expect(screen.getByText("Your homepage watchlist for Buffett Indicator, rates, inflation, and liquidity context.")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Open macro research" }).length).toBeGreaterThan(0);
  expect(screen.getByRole("link", { name: "Edit favorites" })).toHaveAttribute("href", "/settings");
  expect(screen.getAllByText("Buffett Indicator - US").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Buffett Indicator - CN").length).toBeGreaterThan(0);
  expect(screen.getAllByText("US 10Y Treasury Yield").length).toBeGreaterThan(0);
  expect(screen.getByText("Code: buffett_indicator_us")).toBeInTheDocument();
  expect(screen.getByText("Code: buffett_indicator_cn")).toBeInTheDocument();
  expect(screen.getAllByText(/Source gap: No audited observation has been seeded for this indicator yet/).length).toBeGreaterThan(0);
  expect(screen.getAllByText("Next:").length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Configure FRED_API_KEY/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/World Bank refresh; values are annual and lagged/).length).toBeGreaterThan(0);
  expect(screen.getAllByText("Hot sectors").length).toBeGreaterThan(0);
  expect(screen.getByText("Mock data")).toBeInTheDocument();
  expect(screen.getByText(/This sector data is not complete verified realtime fund-flow data/)).toBeInTheDocument();
  expect(screen.getByText(/Provider: static_fixture/)).toBeInTheDocument();
  expect(screen.getAllByText(/Definition: Static fixture values for UI demonstration only/).length).toBeGreaterThan(0);
  expect(screen.getByText("新能源汽车")).toBeInTheDocument();
  expect(screen.getByText(/Constituents: 特斯拉 \/ 蔚来/)).toBeInTheDocument();
  expect(screen.getAllByText("Latest News").length).toBeGreaterThan(0);
  expect(screen.getByText("Apple reports strong growth in services revenue")).toBeInTheDocument();
  expect(screen.getByText("Important signals")).toBeInTheDocument();
  expect(screen.getByText("News source status")).toBeInTheDocument();
  expect(screen.getByText("Anspire AI Search")).toBeInTheDocument();
  expect(screen.getByText("SerpAPI Baidu")).toBeInTheDocument();
  expect(screen.getByText("Needs key")).toBeInTheDocument();
  expect(screen.getAllByText("Market data health").length).toBeGreaterThan(0);
  expect(screen.getByText("0 triggered rules")).toBeInTheDocument();
  expect(screen.getByText("Latest run: succeeded")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View alert history" })).toHaveAttribute("href", "/alerts");
  expect(screen.getByRole("link", { name: "View task runs" })).toHaveAttribute("href", "/task-runs");
  expect(screen.getByRole("link", { name: "Open instrument" })).toHaveAttribute("href", "/instruments/AAPL");
  expect(screen.getByText(/102\.00/)).toBeInTheDocument();
  expect(screen.queryByText("Market workspace")).not.toBeInTheDocument();
  expect(screen.queryByText("AAPL daily candles")).not.toBeInTheDocument();
  expect(screen.queryByText("Watchlist")).not.toBeInTheDocument();
  expect(screen.queryByText("AI research brief")).not.toBeInTheDocument();
  expect(screen.queryByText("Narrative synthesis")).not.toBeInTheDocument();
  expect(screen.queryByText("Information source readiness")).not.toBeInTheDocument();
  expect(screen.queryByText("Research candidates")).not.toBeInTheDocument();
  expect(screen.queryByText("对比分析")).not.toBeInTheDocument();
  expect(screen.queryByText("Followed K-line charts")).not.toBeInTheDocument();
  expect(screen.queryByText("Daily Report (AAPL)")).not.toBeInTheDocument();
  expect(screen.queryByText("Technical Indicators")).not.toBeInTheDocument();
  expect(screen.queryByText("Fundamentals")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Ingest daily bars" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Refresh Analysis" })).not.toBeInTheDocument();
});

it("uses configured homepage index order for the ticker and core cards", async () => {
  getPlatformSettingsMock.mockResolvedValueOnce(
    buildPlatformSettings({
      favorite_home_index_codes: ["cn_csi_300", "us_sp_500", "us_nasdaq_composite"],
      home_index_display_fields: ["latest_close", "provider"],
    }),
  );
  mockCuratedHomepageFetch();

  render(
    await HomePage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  const firstCsi300 = screen.getAllByText("CSI 300")[0];
  const firstSp500 = screen.getAllByText("S&P 500")[0];
  expect(firstCsi300.compareDocumentPosition(firstSp500) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

  const coreIndexRegion = screen.getByRole("region", { name: "Core market indices" });
  const coreText = coreIndexRegion.textContent ?? "";
  expect(coreText.indexOf("CSI 300")).toBeLessThan(coreText.indexOf("S&P 500"));
  expect(coreText.indexOf("S&P 500")).toBeLessThan(coreText.indexOf("Nasdaq Composite"));
  expect(coreText).toContain("Provider: yfinance");
  expect(coreText).not.toContain("Region: CN");
});

it("shows an explicit unavailable card for configured homepage indices missing from the payload", async () => {
  getPlatformSettingsMock.mockResolvedValueOnce(
    buildPlatformSettings({
      favorite_home_index_codes: ["missing_index"],
    }),
  );
  mockCuratedHomepageFetch();

  render(
    await HomePage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getAllByText("missing_index").length).toBeGreaterThan(0);
  expect(
    screen.getByText("missing_index is configured for the homepage, but it is not present in the current market overview payload."),
  ).toBeInTheDocument();
  expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
});

it("renders the dashboard when optional analysis APIs have no data", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/settings/platform")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            market_data_provider: "yfinance",
            llm_provider: "mock",
            llm_api_key: "",
            llm_api_base: "https://api.openai.com/v1",
          }),
        ),
      );
    }
    if (url.endsWith("/instruments")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol: "600519", name: "Kweichow Moutai", market: "CN" }],
          }),
        ),
      );
    }
    if (url.includes("/market-data/600519/latest")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.includes("/market-data/600519/bars")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "600519",
            source: "mock",
            items: [{ close: 1666 }],
          }),
        ),
      );
    }
    if (url.includes("/reports/600519/stock")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "600519",
            report_type: "stock_daily",
            content_markdown: "# 600519 AI 个股报告",
            citations: [],
          }),
        ),
      );
    }
    if (url.endsWith("/reports/600519/daily/latest")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.endsWith("/reports/600519/daily/history?limit=5")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.endsWith("/portfolios/demo")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: "demo",
            source: "mock",
            positions: [{ symbol: "AAPL", market_value: 1020 }],
          }),
        ),
      );
    }
    if (url.endsWith("/indicators/600519")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.endsWith("/fundamentals/600519")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "600519",
            source: "mock_fundamentals",
            item: {
              summary: "PE 26.80，营收增速 10.00%，净利率 52.00%，资产负债率 18.00%",
            },
          }),
        ),
      );
    }
    if (url.endsWith("/news/600519")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.endsWith("/task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis")) {
      return Promise.resolve(new Response("", { status: 404 }));
    }
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(new Response(JSON.stringify({ items: [] })));
    }
    if (url.endsWith("/alerts/triggers/recent?limit=5")) {
      return Promise.resolve(new Response(JSON.stringify({ items: [] })));
    }
    if (url.includes("/recommendations?")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "ok",
            generated_at: "2026-07-03T10:00:00Z",
            count: 0,
            items: [],
          }),
        ),
      );
    }
    if (url.includes("/sectors/hot")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "ok",
            data_mode: "live",
            count: 0,
            items: [],
          }),
        ),
      );
    }
    if (url.includes("/dashboard/market-overview")) {
      return Promise.resolve(new Response(JSON.stringify(createMarketOverviewPayload("600519", "Kweichow Moutai", "CN", 1666))));
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(
    await HomePage({
      params: Promise.resolve({ locale: "en" }),
      searchParams: Promise.resolve({}),
    }),
  );

  expect(screen.getByRole("heading", { name: "Market overview" })).toBeInTheDocument();
  expect(screen.getAllByText("Market dashboard").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Core market indices").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Shanghai Composite").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Followed macro indicators").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Buffett Indicator - US").length).toBeGreaterThan(0);
  expect(screen.getByText("No live hot-sector data available.")).toBeInTheDocument();
  expect(screen.getAllByText("Latest News").length).toBeGreaterThan(0);
  expect(screen.getAllByText("No news sentiment available.").length).toBeGreaterThan(0);
  expect(screen.getByText("Important signals")).toBeInTheDocument();
  expect(screen.getAllByText("Market data health").length).toBeGreaterThan(0);
  expect(screen.getByText(/1,666\.00/)).toBeInTheDocument();
  expect(screen.getByText("Latest run: unknown")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open instrument" })).toHaveAttribute("href", "/instruments/600519");
  expect(screen.queryByText("AI research brief")).not.toBeInTheDocument();
  expect(screen.queryByText("Narrative synthesis")).not.toBeInTheDocument();
  expect(screen.queryByText("No research candidates yet. Keep monitoring the available data.")).not.toBeInTheDocument();
  expect(screen.queryByText("对比分析")).not.toBeInTheDocument();
  expect(screen.queryByText("Followed K-line charts")).not.toBeInTheDocument();
  expect(screen.queryByText("No technical indicators available.")).not.toBeInTheDocument();
});
