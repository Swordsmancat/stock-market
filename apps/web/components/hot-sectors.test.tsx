import { cleanup, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it } from "vitest";
import zhMessages from "../messages/zh.json";
import { HotSectors } from "./hot-sectors";

afterEach(() => {
  cleanup();
});

function renderChineseHotSectors(ui: React.ReactNode) {
  render(
    <NextIntlClientProvider locale="zh" messages={zhMessages}>
      {ui}
    </NextIntlClientProvider>,
  );
}

function buildSector(overrides = {}) {
  return {
    sector_id: "cn_ai",
    name: "人工智能",
    name_en: "Artificial Intelligence",
    market: "CN",
    rank: 1,
    change_percent: 3.25,
    fund_flow: "流入",
    fund_flow_amount: 5.2,
    flow_direction: "inflow",
    net_flow_amount: 520_000_000,
    net_flow_currency: "CNY",
    net_flow_unit: "yuan",
    flow_definition: "Provider-reported sector net inflow.",
    leader_symbol: "300001.SZ",
    leader_name: "测试龙头",
    leader_change_percent: 6.5,
    symbols_count: 1,
    top_constituents: [{ symbol: "300001.SZ", name: "测试龙头", change_percent: 6.5 }],
    breadth: {
      status: "derived_from_constituents",
      advancers: 1,
      decliners: 0,
      unchanged: 0,
      total: 1,
      advance_decline_ratio: null,
    },
    constituent_contribution: {
      status: "derived_from_constituents",
      top_positive: [{ symbol: "300001.SZ", name: "测试龙头", value: 6.5, label: "change_percent" }],
      top_negative: [],
    },
    taxonomy: {
      status: "versioned",
      provider_taxonomy: "fake_live",
      taxonomy_version: "sector-taxonomy-v1",
      normalized_sector_id: "cn_ai",
    },
    history: {
      status: "unavailable",
      reason: "Rotation history snapshots are not stored for this provider yet.",
      snapshot_count: 0,
    },
    as_of: "2026-07-04T09:30:00+00:00",
    provider: "fake_live",
    is_verified: true,
    ...overrides,
  };
}

it("renders live provider-backed sector data with metadata", () => {
  renderChineseHotSectors(
    <HotSectors
      sectors={[buildSector()]}
      status="ok"
      dataMode="live"
      provider="fake_live"
      asOf="2026-07-04T09:30:00+00:00"
      isRealtime
      flowDefinition={{ methodology: "Provider-reported sector net inflow." }}
      message="Verified provider data."
    />,
  );

  expect(screen.getByText(/热点板块/)).toBeInTheDocument();
  expect(screen.getByText("实时数据")).toBeInTheDocument();
  expect(screen.getByText(/数据源：fake_live/)).toBeInTheDocument();
  expect(screen.getByText("人工智能")).toBeInTheDocument();
  expect(screen.getByText("已验证")).toBeInTheDocument();
  expect(screen.getByText(/成分：测试龙头/)).toBeInTheDocument();
  expect(screen.getByText(/广度：1\/0\/0 · 1 · A\/D --/)).toBeInTheDocument();
  expect(screen.getByText(/贡献领先：测试龙头/)).toBeInTheDocument();
  expect(screen.getByText(/分类版本：sector-taxonomy-v1/)).toBeInTheDocument();
  expect(screen.getByText(/轮动历史：暂无可验证快照/)).toBeInTheDocument();
  expect(screen.getByText(/流入 5.2亿/)).toBeInTheDocument();
});

it("renders delayed provider metadata distinctly from live data", () => {
  renderChineseHotSectors(
    <HotSectors
      sectors={[buildSector({ provider: "akshare" })]}
      status="ok"
      dataMode="delayed"
      provider="akshare"
      asOf="2026-07-04T09:30:00+00:00"
      isDelayed
      delayMinutes={15}
      message="Delayed provider data."
    />,
  );

  expect(screen.getByText("延迟数据")).toBeInTheDocument();
  expect(screen.getByText(/延迟 15 分钟/)).toBeInTheDocument();
});

it("renders mock fixture data with a caution message", () => {
  renderChineseHotSectors(
    <HotSectors
      sectors={[buildSector({ is_verified: false, provider: "static_fixture" })]}
      status="degraded"
      dataMode="mock"
      provider="static_fixture"
      message="Static mock sector data; not live market data."
      flowDefinition={{ methodology: "Static fixture values for UI demonstration only." }}
    />,
  );

  expect(screen.getByText("模拟数据")).toBeInTheDocument();
  expect(screen.getByText(/当前板块数据不是完整验证的实时资金流/)).toBeInTheDocument();
  expect(screen.getByText(/Static mock sector data/)).toBeInTheDocument();
});

it("renders unavailable empty state", () => {
  renderChineseHotSectors(
    <HotSectors
      sectors={[]}
      status="unavailable"
      dataMode="none"
      message="Provider unavailable."
    />,
  );

  expect(screen.getByText("不可用")).toBeInTheDocument();
  expect(screen.getByText("Provider unavailable.")).toBeInTheDocument();
  expect(screen.getByText("热点板块暂不可用，请检查 API 服务或数据源。"))
    .toBeInTheDocument();
});

it("does not crash when provider-backed numeric fields are missing", () => {
  renderChineseHotSectors(
    <HotSectors
      sectors={[
        buildSector({
          change_percent: null,
          fund_flow_amount: null,
          net_flow_amount: null,
          leader_change_percent: null,
          flow_direction: "unknown",
        }),
      ]}
      status="ok"
      dataMode="live"
      provider="fake_live"
    />,
  );

  expect(screen.getByText("人工智能")).toBeInTheDocument();
  expect(screen.getAllByText("--").length).toBeGreaterThan(0);
  expect(screen.getByText(/未知 暂无/)).toBeInTheDocument();
});
