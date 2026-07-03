import { cleanup, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it } from "vitest";
import zhMessages from "../messages/zh.json";
import { MarketDepthCard } from "./market-depth-card";
import type { InstrumentMarketDepthPayload } from "@/lib/instrument-detail";

afterEach(() => {
  cleanup();
});

function renderMarketDepthCard(marketDepth?: InstrumentMarketDepthPayload | null) {
  render(
    <NextIntlClientProvider locale="zh" messages={zhMessages}>
      <MarketDepthCard marketDepth={marketDepth} />
    </NextIntlClientProvider>,
  );
}

function buildMarketDepthPayload(overrides: Partial<InstrumentMarketDepthPayload> = {}): InstrumentMarketDepthPayload {
  return {
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
      reason: "Provider does not expose verified depth.",
      as_of: null,
      depth_levels: 5,
      bids: [],
      asks: [],
    },
    recent_trades: {
      status: "degraded",
      reason: "Recent trades unavailable.",
      as_of: null,
      items: [],
    },
    large_orders: {
      status: "degraded",
      reason: "Large orders unavailable.",
      threshold_amount: 1000000,
      threshold_volume: null,
      currency: null,
      as_of: null,
      items: [],
    },
    fund_flow: {
      status: "degraded",
      reason: "Fund flow unavailable.",
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
    ...overrides,
  };
}

it("renders a degraded market depth state without fabricated rows", () => {
  renderMarketDepthCard(buildMarketDepthPayload());

  expect(screen.getByText("深度数据")).toBeInTheDocument();
  expect(screen.getByText("不可用")).toBeInTheDocument();
  expect(screen.getByText("当前数据源暂不支持深度数据。")).toBeInTheDocument();
  expect(screen.getByText("大单金额阈值：1,000,000")).toBeInTheDocument();
  expect(screen.getAllByText("暂无已验证盘口数据。")).toHaveLength(2);
  expect(screen.getByText("暂无已验证逐笔成交。")).toBeInTheDocument();
  expect(screen.getByText("暂无已验证大单数据。")).toBeInTheDocument();
});

it("renders order book, recent trades, large orders, and fund-flow values when present", () => {
  renderMarketDepthCard(
    buildMarketDepthPayload({
      source: "akshare",
      provider: "akshare",
      requested_provider: "akshare",
      effective_provider: "akshare",
      status: "ok",
      as_of: "2026-07-03T09:31:00Z",
      is_realtime: true,
      order_book: {
        status: "ok",
        reason: null,
        as_of: "2026-07-03T09:31:00Z",
        depth_levels: 2,
        bids: [{ price: 101.23, volume: 1200, amount: 121476, order_count: 8 }],
        asks: [{ price: 101.25, volume: 900, amount: 91125, order_count: 5 }],
      },
      recent_trades: {
        status: "ok",
        reason: null,
        as_of: "2026-07-03T09:31:00Z",
        items: [{ timestamp: "09:31:00", side: "buy", price: 101.24, volume: 500, amount: 50620 }],
      },
      large_orders: {
        status: "ok",
        reason: null,
        threshold_amount: 1000000,
        threshold_volume: null,
        currency: "CNY",
        as_of: "2026-07-03T09:31:00Z",
        items: [{ timestamp: "09:31:05", side: "sell", price: 101.2, volume: 12000, amount: 1214400 }],
      },
      fund_flow: {
        status: "ok",
        reason: null,
        as_of: "2026-07-03T09:31:00Z",
        currency: "CNY",
        net_inflow: 1234567,
        main_net_inflow: 765432,
        retail_net_inflow: -12345,
        source_definition: "provider-defined",
      },
      availability: {
        status: "ok",
        reason: "Depth data available.",
        capabilities: {
          order_book: true,
          recent_trades: true,
          large_orders: true,
          fund_flow: true,
        },
      },
    }),
  );

  expect(screen.getByText("可用")).toBeInTheDocument();
  expect(screen.getByText("实时")).toBeInTheDocument();
  expect(screen.getByText("101.23")).toBeInTheDocument();
  expect(screen.getByText("101.25")).toBeInTheDocument();
  expect(screen.getByText("09:31:00")).toBeInTheDocument();
  expect(screen.getByText("09:31:05")).toBeInTheDocument();
  expect(screen.getByText("1,234,567")).toBeInTheDocument();
  expect(screen.getByText("765,432")).toBeInTheDocument();
  expect(screen.getByText("provider-defined")).toBeInTheDocument();

  const capabilities = screen.getByLabelText("深度数据能力");
  expect(within(capabilities).getByText("五档盘口: 可用")).toBeInTheDocument();
});
