import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { refreshMock } = vi.hoisted(() => ({ refreshMock: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: refreshMock }) }));
import { EconomicCalendarPanel, type EconomicCalendarLabels, type EconomicCalendarPayload } from "./economic-calendar-panel";

const labels: EconomicCalendarLabels = { title:"经济数据发布日历", description:"已存储", refresh:"刷新经济日历", refreshing:"正在刷新", refreshSuccess:"已更新 {count} 条", refreshFailed:"刷新失败，已有数据已保留", allCountries:"全部国家", allImportance:"全部重要程度", importance:"重要程度", time:"时间", country:"国家", event:"经济指标", previous:"前值", forecast:"预测值", actual:"公布值", empty:"暂无事件", unavailable:"暂无" };
const payload: EconomicCalendarPayload = { status:"ok", start:"2026-07-01", end:"2026-07-31", count:1, countries:["中国"], items:[{ id:"1", country:"中国", name:"居民消费价格指数", reference_period:"6月", importance:3, scheduled_at:"2026-07-09T01:30:00Z", previous:null, forecast:"1.1", actual:"1.2", unit:"%" }] };

afterEach(() => { cleanup(); vi.restoreAllMocks(); refreshMock.mockClear(); });

it("renders localized stored events and truthful null values", () => {
  render(<EconomicCalendarPanel payload={payload} locale="zh-CN" labels={labels}/>);
  expect(screen.getByText("居民消费价格指数")).toBeInTheDocument();
  expect(screen.getByText("1.2%")).toBeInTheDocument();
  expect(screen.getByText("暂无")).toBeInTheDocument();
});

it("renders an empty state and preserves it on refresh failure", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network"));
  render(<EconomicCalendarPanel payload={{...payload, count:0, countries:[], items:[]}} locale="en-US" labels={{...labels, empty:"No stored releases"}}/>);
  expect(screen.getByText("No stored releases")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name:"刷新经济日历" }));
  await waitFor(() => expect(screen.getByText("刷新失败，已有数据已保留")).toBeInTheDocument());
  expect(refreshMock).not.toHaveBeenCalled();
});

it("refreshes the current stored month explicitly", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ fetched:12 }), { status:200 }));
  render(<EconomicCalendarPanel payload={payload} locale="zh-CN" labels={labels}/>);
  fireEvent.click(screen.getByRole("button", { name:"刷新经济日历" }));
  await waitFor(() => expect(refreshMock).toHaveBeenCalledOnce());
  expect(fetchMock).toHaveBeenCalledWith("/api/economic-calendar/refresh", expect.objectContaining({ method:"POST", body:JSON.stringify({start:"2026-07-01",end:"2026-07-31",dry_run:false}) }));
});
