import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { refreshMock } = vi.hoisted(() => ({ refreshMock: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: refreshMock }) }));

import {
  MacroEconomicDashboard,
  type MacroDashboardPayload,
  type MacroEconomicDashboardLabels,
} from "./macro-economic-dashboard";

const labels: MacroEconomicDashboardLabels = {
  title: "宏观经济看板",
  description: "已存储宏观趋势",
  available: "已有数据",
  missing: "缺少数据",
  stale: "数据偏旧",
  latest: "最新观测",
  groupLabels: { rates: "利率与资金面", fundamentals: "经济基本面" },
  indicatorLabels: {
    cn_lpr_1y: "贷款市场报价利率（LPR）1年期",
    cn_cpi_yoy: "居民消费价格（CPI）同比",
    cn_ppi_yoy: "工业生产者出厂价格（PPI）同比",
  },
  fresh: "近期数据",
  staleState: "数据偏旧",
  noData: "暂无已存储观测",
  asOf: "截至 {date}",
  source: "来源：{source}",
  changeUp: "较前值上升 {value}",
  changeDown: "较前值下降 {value}",
  changeFlat: "与前值持平",
  trendSummary: "{name} 的 {count} 条已存储观测趋势",
  refresh: "刷新公开宏观数据",
  refreshing: "正在刷新宏观数据…",
  refreshSuccess: "已存储 {count} 条通过校验的宏观观测。",
  refreshDegraded: "已存储 {count} 条观测，部分数据系列暂不可用。",
  refreshFailed: "宏观刷新失败，已有观测已保留。",
  unavailable: "暂无",
};

const payload: MacroDashboardPayload = {
  status: "ok",
  generated_at: "2026-07-17T01:00:00Z",
  latest_as_of: "2026-07-16",
  summary: { total: 3, available: 2, missing: 1, stale: 0 },
  groups: [
    {
      id: "rates",
      items: [
        {
          code: "cn_lpr_1y",
          name: "China LPR 1Y",
          region: "CN",
          category: "rates",
          unit: "percent",
          status: "ok",
          freshness: "fresh",
          value: 3,
          as_of: "2026-06-22",
          source: "AkShare macro_china_lpr",
          previous_value: 3.1,
          change: -0.1,
          direction: "down",
          history: [
            { as_of: "2026-05-20", value: 3.1 },
            { as_of: "2026-06-22", value: 3 },
          ],
          no_data_reason: null,
        },
      ],
    },
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
        {
          code: "cn_ppi_yoy",
          name: "China PPI YoY",
          region: "CN",
          category: "inflation",
          unit: "percent",
          status: "no_data",
          freshness: "no_data",
          value: null,
          as_of: null,
          source: null,
          previous_value: null,
          change: null,
          direction: null,
          history: [],
          no_data_reason: "no_stored_observation",
        },
      ],
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  refreshMock.mockClear();
});

it("renders localized grouped macro cards, trends, dates, sources, and truthful gaps", () => {
  render(<MacroEconomicDashboard payload={payload} locale="zh-CN" labels={labels} />);

  const dashboard = screen.getByTestId("macro-economic-dashboard");
  expect(within(dashboard).getByText("利率与资金面")).toBeInTheDocument();
  expect(within(dashboard).getByText("经济基本面")).toBeInTheDocument();
  expect(within(dashboard).getByText("贷款市场报价利率（LPR）1年期")).toBeInTheDocument();
  expect(within(dashboard).getByText("3%")).toBeInTheDocument();
  expect(within(dashboard).getByText("较前值下降 0.1")).toBeInTheDocument();
  expect(within(dashboard).getByRole("img", { name: /LPR.*2 条已存储观测趋势/ })).toBeInTheDocument();
  expect(within(dashboard).getByText("来源：AkShare macro_china_lpr")).toBeInTheDocument();
  expect(within(dashboard).getAllByText("暂无已存储观测").length).toBeGreaterThan(0);
  expect(dashboard).not.toHaveTextContent("cn_lpr_1y");
  expect(dashboard).not.toHaveTextContent("no_stored_observation");
});

it("runs one explicit refresh, reports degraded success, and refreshes server data", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "degraded", observations: 18 }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  render(<MacroEconomicDashboard payload={payload} locale="zh-CN" labels={labels} />);

  fireEvent.click(screen.getByRole("button", { name: "刷新公开宏观数据" }));

  await waitFor(() => expect(refreshMock).toHaveBeenCalledTimes(1));
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/macro-dashboard/refresh",
    expect.objectContaining({ method: "POST" }),
  );
  expect(screen.getByText("已存储 18 条观测，部分数据系列暂不可用。")).toBeInTheDocument();
});

it("preserves the visible dashboard and shows a localized refresh error", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network"));
  render(<MacroEconomicDashboard payload={payload} locale="zh-CN" labels={labels} />);

  fireEvent.click(screen.getByRole("button", { name: "刷新公开宏观数据" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("已有观测已保留");
  expect(screen.getByText("居民消费价格（CPI）同比")).toBeInTheDocument();
});
