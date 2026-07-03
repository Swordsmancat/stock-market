import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { chartMockState, themeMockState } = vi.hoisted(() => ({
  chartMockState: {
    addSeriesCalls: [] as Array<{ seriesType: unknown; options: Record<string, unknown>; setDataMock: ReturnType<typeof vi.fn> }>,
    applyOptionsMock: vi.fn(),
    fitContentMock: vi.fn(),
    removeMock: vi.fn(),
    setVisibleRangeMock: vi.fn(),
    priceScaleApplyOptionsMock: vi.fn(),
    createChartMock: vi.fn(),
  },
  themeMockState: {
    resolvedTheme: "light",
  },
}));

vi.mock("next-themes", () => ({
  useTheme: () => ({ resolvedTheme: themeMockState.resolvedTheme }),
}));

vi.mock("lightweight-charts", () => {
  const CandlestickSeries = { kind: "candlestick" };
  const HistogramSeries = { kind: "histogram" };
  const LineSeries = { kind: "line" };

  return {
    CandlestickSeries,
    HistogramSeries,
    LineSeries,
    createChart: chartMockState.createChartMock.mockImplementation((_container: HTMLElement, options: object) => {
      const chartApi = {
        addSeries: vi.fn((seriesType: unknown, seriesOptions: Record<string, unknown>) => {
          const setDataMock = vi.fn();
          chartMockState.addSeriesCalls.push({
            seriesType,
            options: seriesOptions,
            setDataMock,
          });
          return { setData: setDataMock };
        }),
        applyOptions: chartMockState.applyOptionsMock,
        priceScale: vi.fn(() => ({ applyOptions: chartMockState.priceScaleApplyOptionsMock })),
        timeScale: vi.fn(() => ({
          fitContent: chartMockState.fitContentMock,
          setVisibleRange: chartMockState.setVisibleRangeMock,
        })),
        remove: chartMockState.removeMock,
      };

      return chartApi;
    }),
  };
});

import { AdvancedCandlestickChart } from "./advanced-candlestick-chart";

function createBars(count: number) {
  const startDate = new Date("2026-01-01T00:00:00.000Z");

  return Array.from({ length: count }, (_unusedValue, barIndex) => {
    const timestamp = new Date(startDate.getTime() + barIndex * 24 * 60 * 60 * 1000).toISOString();
    const close = barIndex + 1;

    return {
      timestamp,
      open: close - 0.5,
      high: close + 1,
      low: close - 1,
      close,
      volume: 1_000 + barIndex,
    };
  });
}

afterEach(() => {
  cleanup();
  themeMockState.resolvedTheme = "light";
  chartMockState.addSeriesCalls = [];
  chartMockState.applyOptionsMock.mockClear();
  chartMockState.fitContentMock.mockClear();
  chartMockState.removeMock.mockClear();
  chartMockState.setVisibleRangeMock.mockClear();
  chartMockState.priceScaleApplyOptionsMock.mockClear();
  chartMockState.createChartMock.mockClear();
});

describe("AdvancedCandlestickChart", () => {
  it("adds MA60 and YTD controls while keeping the v5 addSeries API", async () => {
    const bars = createBars(65);

    render(<AdvancedCandlestickChart data={bars} symbol="AAPL" />);

    expect(screen.getByRole("button", { name: "YTD" })).toBeInTheDocument();

    await waitFor(() => {
      expect(chartMockState.addSeriesCalls.length).toBeGreaterThanOrEqual(6);
    });

    const movingAverageTitles = chartMockState.addSeriesCalls
      .map((call) => call.options.title)
      .filter(Boolean);

    expect(movingAverageTitles).toEqual(expect.arrayContaining(["MA5", "MA10", "MA20", "MA60"]));

    const ma60SeriesCall = chartMockState.addSeriesCalls.find((call) => call.options.title === "MA60");
    expect(ma60SeriesCall).toBeDefined();
    const ma60Data = ma60SeriesCall?.setDataMock.mock.calls[0][0] as Array<{ value: number }>;
    expect(ma60Data).toHaveLength(6);
    expect(ma60Data[0].value).toBe(30.5);

    fireEvent.click(screen.getByRole("button", { name: "YTD" }));

    const latestBarDate = new Date(bars.at(-1)!.timestamp);
    const expectedStartOfYear = new Date(latestBarDate.getFullYear(), 0, 1).getTime() / 1000;
    const expectedLatestTime = latestBarDate.getTime() / 1000;

    expect(chartMockState.setVisibleRangeMock).toHaveBeenCalledWith({
      from: expectedStartOfYear,
      to: expectedLatestTime,
    });
  });

  it("uses the dark chart theme when the resolved theme is dark", async () => {
    themeMockState.resolvedTheme = "dark";

    render(<AdvancedCandlestickChart data={createBars(65)} symbol="AAPL" />);

    await waitFor(() => {
      expect(chartMockState.createChartMock).toHaveBeenCalled();
    });

    const chartOptions = chartMockState.createChartMock.mock.calls[0][1] as {
      layout: { background: { color: string }; textColor: string };
      grid: { vertLines: { color: string }; horzLines: { color: string } };
      rightPriceScale: { borderColor: string };
      timeScale: { borderColor: string };
    };

    expect(chartOptions.layout.background.color).toBe("#18181b");
    expect(chartOptions.layout.textColor).toBe("#e4e4e7");
    expect(chartOptions.grid.vertLines.color).toBe("#27272a");
    expect(chartOptions.rightPriceScale.borderColor).toBe("#3f3f46");
    expect(chartOptions.timeScale.borderColor).toBe("#3f3f46");
  });
});
