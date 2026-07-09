import { cleanup, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it, vi } from "vitest";
import zhMessages from "../../../../messages/zh.json";

const { fetchInstrumentDetailPayloadMock } = vi.hoisted(() => ({
  fetchInstrumentDetailPayloadMock: vi.fn(),
}));

vi.mock("@/components/advanced-candlestick-chart", () => ({
  AdvancedCandlestickChart: ({ symbol }: { symbol: string }) => (
    <div data-testid="advanced-candlestick-chart">Advanced chart for {symbol}</div>
  ),
}));

vi.mock("@/components/intraday-price-chart", () => ({
  IntradayPriceChart: ({
    status,
    reason,
    points,
    previousClose,
    source,
    provider,
    effectiveProvider,
    availability,
    freshness,
    session,
  }: {
    status?: string;
    reason?: string | null;
    points?: Array<{ timestamp?: string; price?: number; close?: number }>;
    previousClose?: number | null;
    source?: string | null;
    provider?: string | null;
    effectiveProvider?: string | null;
    availability?: { status?: string | null } | null;
    freshness?: { status?: string | null } | null;
    session?: { status?: string | null } | null;
  }) => (
    <div data-testid="intraday-price-chart">
      Intraday chart status {status} {reason} points {points?.length ?? 0} previous {previousClose ?? "none"} source {source ?? "none"} provider {effectiveProvider ?? provider ?? "none"} availability {availability?.status ?? "none"} freshness {freshness?.status ?? "none"} session {session?.status ?? "none"}
    </div>
  ),
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

vi.mock("@/lib/instrument-detail", () => ({
  fetchInstrumentDetailPayload: fetchInstrumentDetailPayloadMock,
  normalizeInstrumentDetailProvider: (providerName: string | null | undefined) =>
    providerName?.trim().toLowerCase() || "yfinance",
}));

import InstrumentDetailPage from "./page";

async function renderChineseInstrumentDetailPage(symbol = "AAPL") {
  const page = await InstrumentDetailPage({ params: Promise.resolve({ symbol, locale: "zh" }) });

  render(
    <NextIntlClientProvider locale="zh" messages={zhMessages}>
      {page}
    </NextIntlClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  fetchInstrumentDetailPayloadMock.mockReset();
});

function mockInstrumentDetailResponse(
  items: Array<{ timestamp: string; open: number; high: number; low: number; close: number; volume: number }>,
  latestClose?: number,
  intradayPayload: Record<string, unknown> | null = null,
  marketDepthPayload: Record<string, unknown> | null = null,
) {
  fetchInstrumentDetailPayloadMock.mockResolvedValue({
    status: "loaded",
    payload: {
      symbol: "AAPL",
      request_symbol: "AAPL",
      latest: latestClose === undefined
        ? {
            status: "unavailable",
            item: null,
            source: "database",
            provider: "yfinance",
            effective_provider: "yfinance",
            no_data_reason: "No latest quote was available for the requested symbol.",
          }
        : {
            status: "ok",
            item: { timestamp: "2026-01-20", close: latestClose },
            source: "database",
            provider: "yfinance",
            effective_provider: "yfinance",
          },
      bars: {
        items,
        status: items.length > 0 ? "ok" : "no_data",
        source: "database",
        provider: "yfinance",
        effective_provider: "yfinance",
        no_data_reason: items.length > 0 ? null : "No daily bars were available for the requested symbol/date range.",
      },
      intraday: intradayPayload ?? {
        symbol: "AAPL",
        timeframe: "1m",
        date: "2026-01-20",
        source: "none",
        status: "degraded",
        previous_close: null,
        items: [],
        availability: {
          status: "degraded",
          reason: "The selected provider does not support verified minute bars in this backend.",
        },
      },
      market_depth: marketDepthPayload ?? {
        symbol: "AAPL",
        source: "none",
        provider: "yfinance",
        requested_provider: "yfinance",
        effective_provider: "yfinance",
        status: "degraded",
        as_of: null,
        is_realtime: false,
        is_delayed: false,
        delay_minutes: null,
        order_book: {
          status: "degraded",
          reason: "The selected provider does not expose verified market depth data in this backend.",
          as_of: null,
          depth_levels: 5,
          bids: [],
          asks: [],
        },
        recent_trades: {
          status: "degraded",
          reason: "Recent trades are not normalized or verified by this backend yet.",
          as_of: null,
          items: [],
        },
        large_orders: {
          status: "degraded",
          reason: "Large order detection requires verified recent trades, which are unavailable.",
          threshold_amount: 1000000,
          threshold_volume: null,
          currency: null,
          as_of: null,
          items: [],
        },
        fund_flow: {
          status: "degraded",
          reason: "Fund-flow data is not normalized or verified by this backend yet.",
          as_of: null,
          currency: null,
          net_inflow: null,
          main_net_inflow: null,
          retail_net_inflow: null,
          source_definition: null,
        },
        availability: {
          status: "degraded",
          reason: "当前数据源暂不支持深度数据。",
          capabilities: {
            order_book: false,
            recent_trades: false,
            large_orders: false,
            fund_flow: false,
          },
        },
      },
      indicators: {
        symbol: "AAPL",
        source: "database",
        as_of: "2026-01-20T00:00:00+00:00",
        indicators: {
          ma: 119,
          rsi: 100,
          bollinger: { upper: 121, middle: 119, lower: 117 },
        },
      },
      fundamentals: {
        symbol: "AAPL",
        source: "mock_fundamentals",
        as_of: "2026-01-20",
        citation: "fundamental_metrics:AAPL:2026-01-20",
        item: {
          currency: "USD",
          pe_ratio: 28.4,
          revenue_growth: 0.08,
          net_margin: 0.24,
          debt_to_assets: 0.31,
          summary: "PE 28.40，营收增速 8.00%，净利率 24.00%，资产负债率 31.00%",
        },
      },
      news: {
        symbol: "AAPL",
        source: "database",
        summary: { latest_sentiment: "positive", article_count: 1 },
        items: [
          {
            title: "Apple reports strong growth in services revenue",
            source: "mock_news",
            published_at: "2026-01-20T00:00:00+00:00",
            summary: "Apple services revenue accelerated.",
            sentiment: "positive",
            confidence: 0.6,
            url: "https://example.com/aapl-services-growth",
          },
        ],
      },
      latest_daily_report: {
        symbol: "AAPL",
        report_type: "stock_daily",
        as_of: "2026-01-20",
        source: "database",
        content_markdown: "# AAPL 每日报告\n\n持久化日报：MA 119.00，Apple reports strong growth in services revenue",
        citations: [
          "technical_indicators:AAPL:2026-01-20T00:00:00+00:00",
          "news_articles:AAPL:https://example.com/aapl-services-growth",
        ],
        task_run_id: "task-report-123456",
      },
      daily_report_history: {
        symbol: "AAPL",
        source: "database",
        items: [
          {
            symbol: "AAPL",
            report_type: "stock_daily",
            as_of: "2026-01-20",
            content_markdown: "# AAPL 每日报告\n\n最新持久化日报",
            citations: [],
          },
        ],
      },
      range: { timeframe: "1d", start: "2026-01-01", end: "2026-01-20" },
    },
  });
}

it("renders the enhanced client-side instrument detail view", async () => {
  mockInstrumentDetailResponse([
    {
      timestamp: "2026-01-19",
      open: 100,
      high: 103,
      low: 99,
      close: 101,
      volume: 1000,
    },
    {
      timestamp: "2026-01-20",
      open: 101,
      high: 104,
      low: 100,
      close: 102,
      volume: 1200,
    },
  ]);

  await renderChineseInstrumentDetailPage();

  expect(await screen.findByRole("heading", { name: "AAPL" })).toBeInTheDocument();
  expect(screen.getByText("标的详情")).toBeInTheDocument();
  expect(screen.getByText("最新价")).toBeInTheDocument();
  expect(screen.getByText("涨跌额")).toBeInTheDocument();
  expect(screen.getByText("涨跌幅")).toBeInTheDocument();
  expect(screen.getAllByText("102.00").length).toBeGreaterThan(0);
  expect(screen.getByText("+1.00")).toBeInTheDocument();
  expect(screen.getByText("+0.99%")).toBeInTheDocument();
  expect(screen.getByText("AI 市场助手")).toBeInTheDocument();
  expect(screen.getAllByText("K线图").length).toBeGreaterThan(0);
  expect(screen.getByText("交互式价格走势图")).toBeInTheDocument();
  expect(screen.getByText("分时图")).toBeInTheDocument();
  expect(screen.getByText("展示可用的分钟价格、均价、昨收参考和成交量。")).toBeInTheDocument();
  expect(screen.getByText("深度数据")).toBeInTheDocument();
  expect(screen.getByText("展示可用的五档买卖盘、逐笔成交、大单追踪和资金流摘要。")).toBeInTheDocument();
  expect(screen.getByText("当前数据源暂不支持深度数据。")).toBeInTheDocument();
  expect(screen.getByText("AI 个股报告")).toBeInTheDocument();
  expect(screen.getAllByText("报告日期：2026/1/20").length).toBeGreaterThan(0);
  expect(screen.getByText("2 条引用")).toBeInTheDocument();
  expect(screen.getByText("近期报告历史")).toBeInTheDocument();
  expect(screen.getByText("技术指标")).toBeInTheDocument();
  expect(screen.getByText("ma")).toBeInTheDocument();
  expect(screen.getByText("119.00")).toBeInTheDocument();
  expect(screen.getByText("基本面摘要")).toBeInTheDocument();
  expect(screen.getByText("市盈率")).toBeInTheDocument();
  expect(screen.getByText("PE 28.40，营收增速 8.00%，净利率 24.00%，资产负债率 31.00%")).toBeInTheDocument();
  expect(screen.getByText("最新新闻舆情")).toBeInTheDocument();
  expect(screen.getByText("Apple reports strong growth in services revenue")).toBeInTheDocument();
  expect(screen.getAllByText("provider: yfinance").length).toBeGreaterThan(0);
  expect(screen.getAllByText("source: database").length).toBeGreaterThan(0);
  expect(screen.getByTestId("intraday-price-chart")).toHaveTextContent("Intraday chart status degraded");
  expect(screen.getByTestId("advanced-candlestick-chart")).toHaveTextContent("Advanced chart for AAPL");
});

it("passes real intraday minute data to the intraday chart", async () => {
  mockInstrumentDetailResponse(
    [
      {
        timestamp: "2026-01-20",
        open: 213,
        high: 215,
        low: 212,
        close: 214.2,
        volume: 1200,
      },
    ],
    214.2,
    {
      symbol: "AAPL",
      timeframe: "1m",
      date: "2026-01-20",
      source: "provider",
      provider: "yfinance",
      requested_provider: "yfinance",
      effective_provider: "yfinance",
      status: "ok",
      previous_close: 213.55,
      items: [
        {
          timestamp: "2026-01-20T13:30:00+00:00",
          open: 214.1,
          high: 214.3,
          low: 213.9,
          close: 214.2,
          price: 214.2,
          average_price: null,
          volume: 12000,
          amount: null,
        },
      ],
      availability: {
        status: "ok",
        reason: null,
        is_realtime: false,
        is_delayed: true,
        delay_minutes: null,
      },
      freshness: {
        status: "fresh",
        reason: null,
        cache_status: "hit",
        data_as_of: "2026-01-20T13:30:00+00:00",
        fetched_at: "2026-01-20T13:31:00+00:00",
      },
      session: {
        status: "closed",
        reason: "Regular session closed.",
      },
    },
  );

  await renderChineseInstrumentDetailPage();

  expect(screen.getByTestId("intraday-price-chart")).toHaveTextContent("Intraday chart status ok");
  expect(screen.getByTestId("intraday-price-chart")).toHaveTextContent("points 1");
  expect(screen.getByTestId("intraday-price-chart")).toHaveTextContent("previous 213.55");
  expect(screen.getByTestId("intraday-price-chart")).toHaveTextContent("source provider");
  expect(screen.getByTestId("intraday-price-chart")).toHaveTextContent("provider yfinance");
  expect(screen.getByTestId("intraday-price-chart")).toHaveTextContent("freshness fresh");
  expect(screen.getByTestId("intraday-price-chart")).toHaveTextContent("session closed");
});

it("renders real market depth rows when the detail payload includes provider-backed depth", async () => {
  mockInstrumentDetailResponse(
    [
      {
        timestamp: "2026-01-20",
        open: 100,
        high: 103,
        low: 99,
        close: 101.25,
        volume: 1000,
      },
    ],
    101.25,
    null,
    {
      symbol: "AAPL",
      source: "provider",
      provider: "fake_depth",
      requested_provider: "akshare",
      effective_provider: "akshare",
      status: "ok",
      as_of: "2026-07-03T13:30:00+00:00",
      is_realtime: false,
      is_delayed: true,
      delay_minutes: 15,
      order_book: {
        status: "ok",
        reason: null,
        as_of: "2026-07-03T13:30:00+00:00",
        depth_levels: 1,
        bids: [{ price: 101.2, volume: 1000, amount: 101200, order_count: 5 }],
        asks: [{ price: 101.3, volume: 800, amount: 81040, order_count: 4 }],
      },
      recent_trades: {
        status: "ok",
        reason: null,
        as_of: "2026-07-03T13:30:00+00:00",
        items: [{ timestamp: "2026-07-03T13:31:00+00:00", side: "buy", price: 101.25, volume: 15000, amount: 1518750 }],
      },
      large_orders: {
        status: "ok",
        reason: null,
        threshold_amount: 1000000,
        threshold_volume: null,
        currency: "CNY",
        as_of: "2026-07-03T13:30:00+00:00",
        items: [{ timestamp: "2026-07-03T13:31:00+00:00", side: "buy", price: 101.25, volume: 15000, amount: 1518750 }],
      },
      fund_flow: {
        status: "ok",
        reason: null,
        as_of: "2026-07-03T13:30:00+00:00",
        currency: "CNY",
        net_inflow: 1234567,
        main_net_inflow: 765432,
        retail_net_inflow: -12345,
        source_definition: "provider-defined verified fund-flow",
      },
      availability: {
        status: "ok",
        reason: "Depth snapshot from fixture provider.",
        capabilities: {
          order_book: true,
          recent_trades: true,
          large_orders: true,
          fund_flow: true,
        },
      },
    },
  );

  await renderChineseInstrumentDetailPage();

  expect(screen.getByText("101.2")).toBeInTheDocument();
  expect(screen.getByText("101.3")).toBeInTheDocument();
  expect(screen.getByText("1,234,567")).toBeInTheDocument();
  expect(screen.getByText("provider-defined verified fund-flow")).toBeInTheDocument();
});

it("renders latest price even when the detail endpoint has no bars", async () => {
  mockInstrumentDetailResponse([], 105);

  await renderChineseInstrumentDetailPage();

  expect(await screen.findByRole("heading", { name: "AAPL" })).toBeInTheDocument();
  expect(screen.getByText("暂无K线数据")).toBeInTheDocument();
  expect(screen.getByTestId("intraday-price-chart")).toHaveTextContent("Intraday chart status degraded");
  expect(screen.getByText("105.00")).toBeInTheDocument();
});

it("renders an error state when the detail endpoint fails", async () => {
  fetchInstrumentDetailPayloadMock.mockResolvedValue({
    status: "failed",
    responseStatus: 503,
    body: JSON.stringify({ detail: "Instrument service unavailable" }),
    headers: { "content-type": "application/json" },
  });

  await renderChineseInstrumentDetailPage();

  expect(await screen.findByText("加载失败：Failed to fetch instrument data")).toBeInTheDocument();
});
