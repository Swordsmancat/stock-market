import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { chartMockState, themeMockState } = vi.hoisted(() => ({
  chartMockState: {
    addSeriesCalls: [] as Array<{
      seriesType: unknown;
      options: Record<string, unknown>;
      setDataMock: ReturnType<typeof vi.fn>;
      createPriceLineMock?: ReturnType<typeof vi.fn>;
    }>,
    applyOptionsMock: vi.fn(),
    createChartMock: vi.fn(),
    fitContentMock: vi.fn(),
    priceScaleApplyOptionsMock: vi.fn(),
    removeMock: vi.fn(),
    subscribeCrosshairMoveMock: vi.fn(),
    unsubscribeCrosshairMoveMock: vi.fn(),
  },
  themeMockState: {
    resolvedTheme: "light",
  },
}));

vi.mock("next-themes", () => ({
  useTheme: () => ({ resolvedTheme: themeMockState.resolvedTheme }),
}));

vi.mock("lightweight-charts", () => {
  const HistogramSeries = { kind: "histogram" };
  const LineSeries = { kind: "line" };

  return {
    HistogramSeries,
    LineSeries,
    createChart: chartMockState.createChartMock.mockImplementation((_container: HTMLElement, options: object) => {
      const chartApi = {
        addSeries: vi.fn((seriesType: unknown, seriesOptions: Record<string, unknown>) => {
          const setDataMock = vi.fn();
          const createPriceLineMock = vi.fn();
          chartMockState.addSeriesCalls.push({
            seriesType,
            options: seriesOptions,
            setDataMock,
            createPriceLineMock,
          });
          return { createPriceLine: createPriceLineMock, setData: setDataMock };
        }),
        applyOptions: chartMockState.applyOptionsMock,
        priceScale: vi.fn(() => ({ applyOptions: chartMockState.priceScaleApplyOptionsMock })),
        remove: chartMockState.removeMock,
        subscribeCrosshairMove: chartMockState.subscribeCrosshairMoveMock,
        timeScale: vi.fn(() => ({ fitContent: chartMockState.fitContentMock })),
        unsubscribeCrosshairMove: chartMockState.unsubscribeCrosshairMoveMock,
      };

      return chartApi;
    }),
  };
});

import { IntradayPriceChart } from "./intraday-price-chart";

function createIntradayPoints() {
  return [
    {
      timestamp: "2026-07-03T09:30:00+08:00",
      close: 100,
      average_price: 100,
      volume: 1_000,
    },
    {
      timestamp: "2026-07-03T09:31:00+08:00",
      close: 101,
      average_price: 100.5,
      volume: 1_200,
    },
  ];
}

function getSeriesTitles() {
  return chartMockState.addSeriesCalls.map((call) => call.options.title).filter(Boolean);
}

afterEach(() => {
  cleanup();
  themeMockState.resolvedTheme = "light";
  chartMockState.addSeriesCalls = [];
  chartMockState.applyOptionsMock.mockClear();
  chartMockState.createChartMock.mockClear();
  chartMockState.fitContentMock.mockClear();
  chartMockState.priceScaleApplyOptionsMock.mockClear();
  chartMockState.removeMock.mockClear();
  chartMockState.subscribeCrosshairMoveMock.mockClear();
  chartMockState.unsubscribeCrosshairMoveMock.mockClear();
});

describe("IntradayPriceChart", () => {
  it("renders a degraded state without creating a chart", () => {
    render(
      <IntradayPriceChart
        points={[]}
        status="degraded"
        reason="The selected provider does not support verified minute bars in this backend."
      />,
    );

    expect(screen.getByText("Intraday data is unavailable for this provider.")).toBeInTheDocument();
    expect(
      screen.getAllByText("The selected provider does not support verified minute bars in this backend.").length,
    ).toBeGreaterThan(0);
    expect(chartMockState.createChartMock).not.toHaveBeenCalled();
  });

  it("renders price average previous-close and volume data for available intraday points", async () => {
    render(<IntradayPriceChart points={createIntradayPoints()} previousClose={99.5} status="ok" />);

    await waitFor(() => {
      expect(chartMockState.createChartMock).toHaveBeenCalled();
    });

    expect(getSeriesTitles()).toEqual(expect.arrayContaining(["Intraday price", "Average price", "Volume"]));

    const priceSeriesCall = chartMockState.addSeriesCalls.find((call) => call.options.title === "Intraday price");
    expect(priceSeriesCall?.setDataMock).toHaveBeenCalledWith([
      { time: new Date("2026-07-03T09:30:00+08:00").getTime() / 1000, value: 100 },
      { time: new Date("2026-07-03T09:31:00+08:00").getTime() / 1000, value: 101 },
    ]);
    expect(priceSeriesCall?.createPriceLineMock).toHaveBeenCalledWith(
      expect.objectContaining({ price: 99.5, title: "Previous close" }),
    );

    expect(screen.getByText("Price")).toBeInTheDocument();
    expect(screen.getByText("101.00")).toBeInTheDocument();
    expect(screen.getByText("Average price")).toBeInTheDocument();
    expect(screen.getByText("100.50")).toBeInTheDocument();
    expect(screen.getByText("Previous close")).toBeInTheDocument();
    expect(screen.getByText("99.50")).toBeInTheDocument();
    expect(screen.getByText("1,200")).toBeInTheDocument();
  });

  it("filters invalid points before setting chart data", async () => {
    render(
      <IntradayPriceChart
        status="ok"
        points={[
          { timestamp: "not-a-date", close: 100, volume: 1_000 },
          { timestamp: "2026-07-03T09:30:00+08:00", close: Number.NaN, volume: 1_000 },
          { timestamp: "2026-07-03T09:31:00+08:00", close: 101, volume: 1_200 },
        ]}
      />,
    );

    await waitFor(() => {
      expect(chartMockState.createChartMock).toHaveBeenCalled();
    });

    const priceSeriesCall = chartMockState.addSeriesCalls.find((call) => call.options.title === "Intraday price");
    const priceData = priceSeriesCall?.setDataMock.mock.calls[0][0] as Array<{ value: number }>;
    expect(priceData).toHaveLength(1);
    expect(priceData[0].value).toBe(101);
  });
});
