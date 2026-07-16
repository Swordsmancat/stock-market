import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { StoredNewsItem } from "@/lib/news-payload";

const { getPlatformSettingsMock } = vi.hoisted(() => ({
  getPlatformSettingsMock: vi.fn(),
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

const defaultNewsItems: StoredNewsItem[] = [
  { symbol: "NVDA", source: "Reuters", title: "US chip stocks rally as AI demand improves", sentiment: "positive", confidence: 0.82, published_at: "2026-07-16T09:35:00+08:00" },
  { symbol: "AAPL", source: "Company filing", title: "Apple expands AI features for enterprise devices", sentiment: "positive", confidence: 0.68, published_at: "2026-07-16T08:20:00+08:00" },
  { symbol: "US10Y", source: "Market desk", title: "Yield volatility keeps rate-sensitive sectors cautious", sentiment: "negative", confidence: 0.57, published_at: "2026-07-15T22:45:00+08:00" },
];

const defaultHotSectors = [
  {
    sector_id: "semiconductors",
    name: "Semiconductors",
    market: "US",
    rank: 1,
    change_percent: 3.21,
    net_flow_amount: 4_562_000_000,
    leader_symbol: "NVDA",
  },
  {
    sector_id: "ai_compute",
    name: "AI compute",
    market: "US",
    rank: 2,
    change_percent: 2.85,
    net_flow_amount: 3_871_000_000,
    leader_symbol: "MSFT",
  },
  {
    sector_id: "consumer_electronics",
    name: "Consumer electronics",
    market: "US",
    rank: 3,
    change_percent: -1.12,
    net_flow_amount: -920_000_000,
    leader_symbol: "AAPL",
  },
];

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
  vi.unstubAllEnvs();
  getPlatformSettingsMock.mockReset();
});

function createMarketOverviewPayload(symbol = "AAPL", name = "Apple Inc.", market = "US", latestClose = 102) {
  const dailyBars = [
    { timestamp: "2026-07-06", open: latestClose - 3, high: latestClose - 1, low: latestClose - 4, close: latestClose - 2, volume: 1000 },
    { timestamp: "2026-07-07", open: latestClose - 2, high: latestClose, low: latestClose - 3, close: latestClose - 1, volume: 1100 },
    { timestamp: "2026-07-08", open: latestClose - 1, high: latestClose + 1, low: latestClose - 2, close: latestClose, volume: 1200 },
  ];
  const movement = {
    direction: "up",
    absolute_change: 1,
    percent_change: 1 / (latestClose - 1),
  };
  const indexRows = [
    ["us_sp_500", "S&P 500", "US"],
    ["us_nasdaq_composite", "Nasdaq Composite", "US"],
    ["us_dow_jones", "Dow Jones Industrial Average", "US"],
    ["cn_shanghai_composite", "Shanghai Composite", "CN"],
    ["cn_shenzhen_component", "Shenzhen Component", "CN"],
    ["cn_csi_300", "CSI 300", "CN"],
    ["cn_chinext", "ChiNext", "CN"],
    ["cn_csi_500", "CSI 500", "CN"],
  ];
  const macroIndicators = [
    ["buffett_indicator_us", "Buffett Indicator - US", "US", "valuation", "no_data", null],
    ["buffett_indicator_cn", "Buffett Indicator - CN", "CN", "valuation", "no_data", null],
    ["buffett_indicator_hk", "Buffett Indicator - HK", "HK", "valuation", "no_data", null],
    ["us_10y_yield", "US 10Y Treasury Yield", "US", "rates", "ok", 4.25],
    ["us_10y_2y_spread", "US 10Y-2Y Yield Spread", "US", "rates", "no_data", null],
    ["us_cpi_yoy", "US CPI YoY", "US", "inflation", "no_data", null],
    ["us_m2_yoy", "US M2 Money Supply YoY", "US", "liquidity", "no_data", null],
    ["cn_m2_yoy", "China M2 Money Supply YoY", "CN", "liquidity", "no_data", null],
  ].map(([code, indicatorName, region, category, status, value]) => ({
    code,
    name: indicatorName,
    region,
    category,
    status,
    value,
    unit: "percent",
    as_of: status === "ok" ? "2026-07-08" : null,
    source: status === "ok" ? "Audited seed: FRED DGS10" : null,
    components: {},
    no_data_reason: status === "ok" ? null : "No audited observation has been seeded for this indicator yet.",
  }));

  return {
    generated_at: "2026-07-08T00:00:00+00:00",
    provider: "yfinance",
    range: { timeframe: "1d", start: "2026-07-06", end: "2026-07-08" },
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
          latest: { timestamp: "2026-07-08", close: latestClose, movement },
          bars: dailyBars,
          source: "database",
          provider: "yfinance",
          effective_provider: "yfinance",
          detail_path: `/instruments/${symbol}`,
        },
      ],
    },
    indices: {
      items: indexRows.map(([code, indexName, region], index) => ({
        code,
        name: indexName,
        name_zh: indexName,
        region,
        market: region,
        currency: region === "US" ? "USD" : "CNY",
        provider_symbol: code,
        status: "ok",
        freshness: "fresh",
        latest: { timestamp: "2026-07-08", close: 3000 + index, movement },
        bars: dailyBars.map((bar, barIndex) => ({ ...bar, close: 3000 + index + barIndex })),
        source: "database",
        provider: "yfinance",
        requested_provider: "yfinance",
        effective_provider: "yfinance",
      })),
    },
    valuation_indicators: { items: macroIndicators },
    macro_indicators: { items: macroIndicators },
    diagnostics: [],
  };
}

function createOfficialMacroSourceStatusPayload() {
  return {
    status: "needs_configuration",
    generated_at: "2026-07-08T00:00:00+00:00",
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
        indicator_codes: ["us_10y_yield", "us_10y_2y_spread"],
        evidence_count: 1,
        latest_as_of: "2026-07-08",
        missing_indicator_codes: ["us_10y_2y_spread"],
      },
    ],
  };
}

function mockHomepageFetch({
  symbol = "AAPL",
  instrumentName = "Apple Inc.",
  market = "US",
  latestClose = 102,
  marketOverviewPayload = createMarketOverviewPayload(symbol, instrumentName, market, latestClose),
  newsItems = defaultNewsItems,
  newsResponseStatus = 200,
  newsPayload,
  sectors = defaultHotSectors,
  latestBarStatus = 200,
}: {
  symbol?: string;
  instrumentName?: string;
  market?: string;
  latestClose?: number;
  marketOverviewPayload?: ReturnType<typeof createMarketOverviewPayload>;
  newsItems?: typeof defaultNewsItems;
  newsResponseStatus?: number;
  newsPayload?: unknown;
  sectors?: typeof defaultHotSectors;
  latestBarStatus?: number;
} = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/instruments")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [{ symbol, name: instrumentName, market }],
          }),
        ),
      );
    }
    if (url.includes(`/market-data/${symbol}/latest`)) {
      if (latestBarStatus !== 200) {
        return Promise.resolve(new Response("", { status: latestBarStatus }));
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol,
            source: "database",
            status: "ok",
            item: { timestamp: "2026-07-08", close: latestClose },
          }),
        ),
      );
    }
    if (url.endsWith("/watchlist")) {
      return Promise.resolve(new Response(JSON.stringify({ items: [] })));
    }
    if (url.includes("/news/latest?limit=6")) {
      if (newsResponseStatus !== 200) {
        return Promise.resolve(
          new Response(JSON.stringify({ detail: "news unavailable" }), {
            status: newsResponseStatus,
            headers: { "content-type": "application/json" },
          }),
        );
      }
      return Promise.resolve(
        new Response(
          JSON.stringify(
            newsPayload ?? {
              source: "database",
              status: newsItems.length > 0 ? "ok" : "no_data",
              count: newsItems.length,
              limit: 6,
              items: newsItems,
            },
          ),
        ),
      );
    }
    if (url.includes("/sectors/hot")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "ok",
            data_mode: "live",
            count: sectors.length,
            items: sectors,
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

async function renderHomepage(locale = "en") {
  render(
    await HomePage({
      params: Promise.resolve({ locale }),
      searchParams: Promise.resolve({}),
    }),
  );
}

it("renders the strict terminal-style homepage cockpit", async () => {
  mockHomepageFetch();

  await renderHomepage();

  expect(screen.getByRole("heading", { name: "A-share market" })).toBeInTheDocument();
  expect(screen.getByText("Selected indices")).toBeInTheDocument();
  expect(screen.getAllByText("A-share market").length).toBeGreaterThan(1);
  expect(screen.getByText("Macro indicators")).toBeInTheDocument();
  expect(screen.getByText("Hot sectors")).toBeInTheDocument();
  expect(screen.getByText("Latest news sentiment")).toBeInTheDocument();
  expect(screen.getAllByText("Market overview").length).toBeGreaterThan(1);
  expect(screen.getByText("Fund flow")).toBeInTheDocument();
  expect(screen.getByText("AI market sentiment")).toBeInTheDocument();
  expect(screen.queryByText("News source status")).not.toBeInTheDocument();
  expect(screen.getAllByText("Semiconductors").length).toBeGreaterThan(1);
  expect(screen.getAllByText("AI compute").length).toBeGreaterThan(1);
  expect(screen.getByText("US chip stocks rally as AI demand improves")).toBeInTheDocument();
  expect(screen.getByText("Apple expands AI features for enterprise devices")).toBeInTheDocument();
  expect(screen.getByText("Yield volatility keeps rate-sensitive sectors cautious")).toBeInTheDocument();
  expect(screen.getByText(/NVDA · Reuters/)).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Market overview" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Fund flow" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "AI market sentiment" })).toBeInTheDocument();
  expect(screen.getByText("Research-only status. No trading instruction, target price, position sizing, or execution guidance.")).toBeInTheDocument();
  expect(screen.queryByText("Anspire AI Search")).not.toBeInTheDocument();
  expect(screen.queryByText("SerpAPI Baidu")).not.toBeInTheDocument();

  const moreLinks = screen.getAllByRole("link", { name: "More" });
  expect(moreLinks).toHaveLength(7);
  expect(moreLinks.map((link) => link.getAttribute("href"))).toEqual(
    expect.arrayContaining([
      "/instruments",
      "/evidence",
      "/ai-research",
    ]),
  );
  expect(
    moreLinks.some((link) => link.getAttribute("href") === "/instruments/AAPL"),
  ).toBe(false);
  expect(screen.getByRole("link", { name: "Add custom indicator" })).toHaveAttribute(
    "href",
    "/settings#favorite_macro_indicator_codes",
  );
  expect(screen.queryByText("Overview of your portfolio, market data, and automated analysis.")).not.toBeInTheDocument();
  expect(screen.queryByText("AI research brief")).not.toBeInTheDocument();
  expect(screen.queryByText("Narrative synthesis")).not.toBeInTheDocument();
  expect(screen.queryByText("Information source readiness")).not.toBeInTheDocument();
  expect(screen.queryByText("Research candidates")).not.toBeInTheDocument();
  expect(screen.queryByText("Followed K-line charts")).not.toBeInTheDocument();
  expect(screen.queryByText("Daily Report (AAPL)")).not.toBeInTheDocument();
  expect(screen.queryByText("Technical Indicators")).not.toBeInTheDocument();
  expect(screen.queryByText("Fundamentals")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Ingest daily bars" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Refresh Analysis" })).not.toBeInTheDocument();
});

it("shows the stored publication date and time using the active locale", async () => {
  const publishedAt = "2026-07-15T16:30:00Z";
  vi.stubEnv("TZ", "UTC");
  mockHomepageFetch({
    newsItems: [
      {
        ...defaultNewsItems[0],
        published_at: publishedAt,
      },
    ],
  });

  await renderHomepage("zh");

  const newsRegion = screen.getByRole("region", {
    name: "Latest news sentiment",
  });
  const expectedPublicationTime = new Intl.DateTimeFormat("zh", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Shanghai",
  }).format(new Date(publishedAt));
  const timeElement = within(newsRegion).getByText(expectedPublicationTime);
  expect(timeElement.tagName).toBe("TIME");
  expect(timeElement.nextElementSibling).toHaveTextContent(/NVDA.*Reuters/);
});

it.each([undefined, null, "not-a-date"])(
  "uses the existing unavailable label for a missing or invalid stored publication time: %s",
  async (publishedAt) => {
    mockHomepageFetch({
      newsItems: [
        {
          ...defaultNewsItems[0],
          published_at: publishedAt,
        },
      ],
    });

    await renderHomepage();

    const newsRegion = screen.getByRole("region", {
      name: "Latest news sentiment",
    });
    expect(within(newsRegion).getByText("N/A")).toBeInTheDocument();
  },
);

it.each([
  { credentialConfigured: true, expectedReadiness: "100" },
  { credentialConfigured: false, expectedReadiness: "0" },
])(
  "keeps provider capabilities in aggregate readiness without rendering provider details: $expectedReadiness",
  async ({ credentialConfigured, expectedReadiness }) => {
    const platformSettings = buildPlatformSettings();
    getPlatformSettingsMock.mockResolvedValue({
      ...platformSettings,
      news_search_provider_capabilities:
        platformSettings.news_search_provider_capabilities.map((provider) => ({
          ...provider,
          enabled: true,
          credential_configured: credentialConfigured,
        })),
    });
    mockHomepageFetch();

    await renderHomepage();

    expect(
      screen.getByText("Provider readiness").parentElement,
    ).toHaveTextContent(expectedReadiness);
    expect(screen.queryByText("Anspire AI Search")).not.toBeInTheDocument();
    expect(screen.queryByText("SerpAPI Baidu")).not.toBeInTheDocument();
  },
);

it("loads bounded cross-symbol stored news without provider-search fan-out", async () => {
  const fetchMock = mockHomepageFetch();

  await renderHomepage();

  const requestedUrls = fetchMock.mock.calls.map(([input]) => String(input));
  expect(
    requestedUrls.some((url) => url.endsWith("/news/latest?limit=6")),
  ).toBe(true);
  expect(
    requestedUrls.some((url) => url.endsWith("/news/AAPL")),
  ).toBe(false);
  expect(
    requestedUrls.some((url) => url.includes("/news/search")),
  ).toBe(false);
  expect(
    fetchMock.mock.calls.some(([, init]) => init?.method === "POST"),
  ).toBe(false);
});

it("distinguishes a failed latest-news read from a genuine empty result", async () => {
  mockHomepageFetch({ newsItems: [], newsResponseStatus: 503 });

  await renderHomepage();

  expect(
    screen.getByText("Latest stored news could not be loaded."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("No news sentiment available."),
  ).not.toBeInTheDocument();
});

it("treats a malformed successful latest-news payload as a failed load", async () => {
  mockHomepageFetch({
    newsPayload: {
      source: "database",
      status: "ok",
      count: 1,
      limit: 6,
      items: "invalid",
    },
  });

  await renderHomepage();

  expect(
    screen.getByText("Latest stored news could not be loaded."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("No news sentiment available."),
  ).not.toBeInTheDocument();
});

it("keeps every loaded fund-flow row in a focusable scroll region", async () => {
  mockHomepageFetch({
    sectors: [
      ...defaultHotSectors,
      {
        sector_id: "energy",
        name: "Energy",
        market: "US",
        rank: 4,
        change_percent: 1.72,
        net_flow_amount: 680_000_000,
        leader_symbol: "XOM",
      },
      {
        sector_id: "industrials",
        name: "Industrials",
        market: "US",
        rank: 5,
        change_percent: 1.14,
        net_flow_amount: 510_000_000,
        leader_symbol: "CAT",
      },
    ],
  });

  await renderHomepage();

  const fundFlowRegion = screen.getByRole("region", { name: "Fund flow" });
  expect(fundFlowRegion).toHaveAttribute("tabindex", "0");
  expect(fundFlowRegion).toHaveClass("overflow-y-auto");
  expect(within(fundFlowRegion).getByText("Industrials")).toBeInTheDocument();
});

it("keeps every bounded news row in a named focusable scroll region", async () => {
  mockHomepageFetch({
    newsItems: [
      ...defaultNewsItems,
      { symbol: "MSFT", source: "Reuters", title: "Fourth bounded news row", sentiment: "neutral", confidence: 0.5, published_at: "2026-07-16T07:40:00+08:00" },
      { symbol: "GOOG", source: "Filing", title: "Fifth bounded news row", sentiment: "positive", confidence: 0.6, published_at: "2026-07-15T19:15:00+08:00" },
      { symbol: "META", source: "Exchange", title: "Sixth bounded news row", sentiment: "negative", confidence: 0.4, published_at: "2026-07-15T18:05:00+08:00" },
    ],
  });

  await renderHomepage();

  const newsRegion = screen.getByRole("region", {
    name: "Latest news sentiment",
  });
  expect(newsRegion).toHaveAttribute("aria-labelledby", "terminal-latest-news-heading");
  expect(newsRegion).toHaveAttribute("tabindex", "0");
  expect(newsRegion).toHaveClass("overflow-y-auto", "focus-visible:ring-2");
  expect(within(newsRegion).getByText("Sixth bounded news row")).toBeInTheDocument();
});

it("uses configured homepage index order and display fields in the market band", async () => {
  getPlatformSettingsMock.mockResolvedValueOnce(
    buildPlatformSettings({
      favorite_home_index_codes: ["cn_csi_300", "us_sp_500", "us_nasdaq_composite"],
      home_index_display_fields: ["latest_close", "provider"],
    }),
  );
  mockHomepageFetch();

  await renderHomepage();

  const firstCsi300 = screen.getAllByText("CSI 300")[0];
  const firstSp500 = screen.getAllByText("S&P 500")[0];
  const firstNasdaq = screen.getAllByText("Nasdaq Composite")[0];
  expect(firstCsi300.compareDocumentPosition(firstSp500) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(firstSp500.compareDocumentPosition(firstNasdaq) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

  const selectedLane = screen.getByText("Selected indices").parentElement?.parentElement;
  const selectedLaneText = selectedLane?.textContent ?? "";
  expect(selectedLaneText.indexOf("CSI 300")).toBeLessThan(selectedLaneText.indexOf("S&P 500"));
  expect(selectedLaneText.indexOf("S&P 500")).toBeLessThan(selectedLaneText.indexOf("Nasdaq Composite"));
  expect(selectedLaneText).toContain("yfinance");
  expect(selectedLaneText).not.toContain("CN");
});

it("shows an explicit unavailable card for configured homepage indices missing from the payload", async () => {
  getPlatformSettingsMock.mockResolvedValueOnce(
    buildPlatformSettings({
      favorite_home_index_codes: ["missing_index"],
    }),
  );
  mockHomepageFetch();

  await renderHomepage();

  expect(screen.getAllByText("missing_index").length).toBeGreaterThan(0);
  expect(
    screen.getAllByText("missing_index is configured for the homepage, but it is not present in the current market overview payload.").length,
  ).toBeGreaterThan(0);
  expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
});

it("keeps the terminal dashboard useful when optional market signals have no data", async () => {
  mockHomepageFetch({
    symbol: "600519",
    instrumentName: "Kweichow Moutai",
    market: "CN",
    latestClose: 1666,
    newsItems: [],
    sectors: [],
    latestBarStatus: 404,
    marketOverviewPayload: createMarketOverviewPayload("600519", "Kweichow Moutai", "CN", 1666),
  });

  await renderHomepage();

  expect(screen.getByRole("heading", { name: "A-share market" })).toBeInTheDocument();
  expect(screen.getByText("Macro indicators")).toBeInTheDocument();
  expect(screen.getByText("Hot sectors")).toBeInTheDocument();
  expect(screen.getByText("Latest news sentiment")).toBeInTheDocument();
  expect(screen.getAllByText("Market overview").length).toBeGreaterThan(1);
  expect(screen.getByText("Fund flow")).toBeInTheDocument();
  expect(screen.getByText("AI market sentiment")).toBeInTheDocument();
  expect(screen.getByText("No live hot-sector data available.")).toBeInTheDocument();
  expect(screen.getByText("No news sentiment available.")).toBeInTheDocument();
  expect(screen.getByText("No fund-flow data available.")).toBeInTheDocument();
  expect(screen.queryByText("News source status")).not.toBeInTheDocument();
  expect(screen.queryByText("Anspire AI Search")).not.toBeInTheDocument();
  expect(screen.queryByText("SerpAPI Baidu")).not.toBeInTheDocument();
  expect(screen.queryByText("AI research brief")).not.toBeInTheDocument();
  expect(screen.queryByText("Narrative synthesis")).not.toBeInTheDocument();
  expect(screen.queryByText("Followed K-line charts")).not.toBeInTheDocument();
  expect(screen.queryByText("No technical indicators available.")).not.toBeInTheDocument();
});
