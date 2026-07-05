"use client";

import { useEffect, useRef, useState } from "react";
import { CandlestickSeries, createChart, HistogramSeries, LineSeries } from "lightweight-charts";
import type { CandlestickData, IChartApi, ISeriesApi, Time } from "lightweight-charts";
import { useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import {
  calculateBollingerBandsSeries,
  calculateKdjSeries,
  calculateMacdSeries,
  calculateMovingAverageSeries,
  computeRsiSeries,
  type BollingerBandsPoint,
  type KdjPoint,
  type MacdPoint,
} from "@/lib/chart-indicators";

interface BarData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface AdvancedCandlestickChartProps {
  data: BarData[];
  symbol?: string;
  height?: number;
  showMA?: boolean;
  showVolume?: boolean;
  className?: string;
  indicators?: AdvancedCandlestickIndicatorVisibility;
  indicatorParameters?: AdvancedCandlestickIndicatorParameters;
}

type AdvancedCandlestickIndicatorKey = "ma" | "boll" | "volume" | "macd" | "rsi" | "kdj";

type AdvancedCandlestickIndicatorVisibility = Partial<Record<AdvancedCandlestickIndicatorKey, boolean>>;

type ResolvedAdvancedCandlestickIndicatorVisibility = Record<AdvancedCandlestickIndicatorKey, boolean>;

type AdvancedCandlestickIndicatorParameters = {
  maPeriods?: number[];
  bollWindow?: number;
  bollStandardDeviationMultiplier?: number;
  macdFastWindow?: number;
  macdSlowWindow?: number;
  macdSignalWindow?: number;
  rsiPeriods?: number[];
  kdjWindow?: number;
  kdjKSmoothing?: number;
  kdjDSmoothing?: number;
};

type TimedBarData = BarData & {
  time: Time;
};

type LineSeriesDataPoint = {
  time: Time;
  value: number;
};

type HistogramSeriesDataPoint = LineSeriesDataPoint & {
  color?: string;
};

type TimeRange = "1D" | "5D" | "1M" | "3M" | "6M" | "1Y" | "YTD" | "ALL";

const timeRangeOptions: TimeRange[] = ["1D", "5D", "1M", "3M", "6M", "1Y", "YTD", "ALL"];

const DEFAULT_MA_PERIODS = [5, 10, 20, 60];
const DEFAULT_RSI_PERIODS = [6, 12, 24];
const DEFAULT_BOLL_WINDOW = 20;
const DEFAULT_BOLL_STANDARD_DEVIATION_MULTIPLIER = 2;
const DEFAULT_MACD_FAST_WINDOW = 12;
const DEFAULT_MACD_SLOW_WINDOW = 26;
const DEFAULT_MACD_SIGNAL_WINDOW = 9;
const DEFAULT_KDJ_WINDOW = 9;
const DEFAULT_KDJ_K_SMOOTHING = 3;
const DEFAULT_KDJ_D_SMOOTHING = 3;

const movingAverageColors = ["#2196F3", "#FF9800", "#9C27B0", "#00BCD4", "#22c55e", "#e11d48"];
const rsiColors = ["#38bdf8", "#a78bfa", "#f472b6"];

type ChartWorkspacePreset = {
  workspaceVersion: 1;
  selectedRange: TimeRange;
  visibleIndicators: ResolvedAdvancedCandlestickIndicatorVisibility;
  annotationNote: string;
  savedAt: string;
};

function getChartWorkspaceStorageKey(symbol: string): string {
  const normalizedSymbol = symbol.trim() || "default";
  return `chart-workspace:v1:${normalizedSymbol}`;
}

function isTimeRange(value: unknown): value is TimeRange {
  return typeof value === "string" && timeRangeOptions.includes(value as TimeRange);
}

function readChartWorkspacePreset(
  storageKey: string,
  fallbackVisibleIndicators: ResolvedAdvancedCandlestickIndicatorVisibility,
): ChartWorkspacePreset | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const rawPreset = window.localStorage.getItem(storageKey);
    if (!rawPreset) {
      return null;
    }

    const parsedPreset = JSON.parse(rawPreset) as Partial<ChartWorkspacePreset>;
    if (parsedPreset.workspaceVersion !== 1 || !isTimeRange(parsedPreset.selectedRange)) {
      return null;
    }

    return {
      workspaceVersion: 1,
      selectedRange: parsedPreset.selectedRange,
      visibleIndicators: normalizeStoredIndicatorVisibility(parsedPreset.visibleIndicators, fallbackVisibleIndicators),
      annotationNote: typeof parsedPreset.annotationNote === "string" ? parsedPreset.annotationNote : "",
      savedAt: typeof parsedPreset.savedAt === "string" ? parsedPreset.savedAt : new Date().toISOString(),
    };
  } catch (_error) {
    return null;
  }
}

function writeChartWorkspacePreset(storageKey: string, preset: ChartWorkspacePreset): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    window.localStorage.setItem(storageKey, JSON.stringify(preset));
    return true;
  } catch (_error) {
    return false;
  }
}

function removeChartWorkspacePreset(storageKey: string): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    window.localStorage.removeItem(storageKey);
    return true;
  } catch (_error) {
    return false;
  }
}

function normalizeStoredIndicatorVisibility(
  storedVisibility: unknown,
  fallbackVisibleIndicators: ResolvedAdvancedCandlestickIndicatorVisibility,
): ResolvedAdvancedCandlestickIndicatorVisibility {
  if (storedVisibility === null || typeof storedVisibility !== "object") {
    return fallbackVisibleIndicators;
  }

  const candidateVisibility = storedVisibility as Partial<Record<AdvancedCandlestickIndicatorKey, unknown>>;
  return {
    ma: typeof candidateVisibility.ma === "boolean" ? candidateVisibility.ma : fallbackVisibleIndicators.ma,
    boll: typeof candidateVisibility.boll === "boolean" ? candidateVisibility.boll : fallbackVisibleIndicators.boll,
    volume: typeof candidateVisibility.volume === "boolean" ? candidateVisibility.volume : fallbackVisibleIndicators.volume,
    macd: typeof candidateVisibility.macd === "boolean" ? candidateVisibility.macd : fallbackVisibleIndicators.macd,
    rsi: typeof candidateVisibility.rsi === "boolean" ? candidateVisibility.rsi : fallbackVisibleIndicators.rsi,
    kdj: typeof candidateVisibility.kdj === "boolean" ? candidateVisibility.kdj : fallbackVisibleIndicators.kdj,
  };
}

function resolveInitialIndicatorVisibility({
  indicators,
  showMA,
  showVolume,
}: {
  indicators?: AdvancedCandlestickIndicatorVisibility;
  showMA: boolean;
  showVolume: boolean;
}): ResolvedAdvancedCandlestickIndicatorVisibility {
  return {
    ma: indicators?.ma ?? showMA,
    boll: indicators?.boll ?? false,
    volume: indicators?.volume ?? showVolume,
    macd: indicators?.macd ?? false,
    rsi: indicators?.rsi ?? false,
    kdj: indicators?.kdj ?? false,
  };
}

function getFiniteLineSeriesData(
  chartBars: TimedBarData[],
  values: Array<number | null | undefined>,
): LineSeriesDataPoint[] {
  return values.flatMap((value, index) => {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return [];
    }

    return [{ time: chartBars[index].time, value }];
  });
}

function getFiniteHistogramSeriesData(
  chartBars: TimedBarData[],
  values: Array<number | null | undefined>,
  getColor: (value: number) => string,
): HistogramSeriesDataPoint[] {
  return values.flatMap((value, index) => {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return [];
    }

    return [{ time: chartBars[index].time, value, color: getColor(value) }];
  });
}

export function AdvancedCandlestickChart({
  data = [],
  symbol = "",
  height = 400,
  showMA = true,
  showVolume = true,
  className = "",
  indicators,
  indicatorParameters = {},
}: AdvancedCandlestickChartProps) {
  const t = useTranslations("AdvancedCandlestickChart");
  const { resolvedTheme } = useTheme();
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const [selectedRange, setSelectedRange] = useState<TimeRange>("3M");
  const [visibleIndicators, setVisibleIndicators] = useState<ResolvedAdvancedCandlestickIndicatorVisibility>(() =>
    resolveInitialIndicatorVisibility({ indicators, showMA, showVolume }),
  );
  const [annotationNote, setAnnotationNote] = useState("");
  const [workspaceMessage, setWorkspaceMessage] = useState<string | null>(null);
  const defaultVisibleIndicators = resolveInitialIndicatorVisibility({ indicators, showMA, showVolume });
  const workspaceStorageKey = getChartWorkspaceStorageKey(symbol);

  const toggleIndicator = (indicator: AdvancedCandlestickIndicatorKey) => {
    setVisibleIndicators((currentVisibility) => ({
      ...currentVisibility,
      [indicator]: !currentVisibility[indicator],
    }));
  };

  const indicatorOptions: Array<{ key: AdvancedCandlestickIndicatorKey; label: string }> = [
    { key: "ma", label: t("indicatorMa") },
    { key: "boll", label: t("indicatorBoll") },
    { key: "volume", label: t("indicatorVolume") },
    { key: "macd", label: t("indicatorMacd") },
    { key: "rsi", label: t("indicatorRsi") },
    { key: "kdj", label: t("indicatorKdj") },
  ];

  const applyTimeRangeToChart = (range: TimeRange) => {
    if (!chartRef.current || data.length === 0) return;

    const latestBarDate = new Date(data[data.length - 1].timestamp);
    const fallbackEndDate = Number.isNaN(latestBarDate.getTime()) ? new Date() : latestBarDate;
    const rangeEndTime = fallbackEndDate.getTime() / 1000;
    let daysToShow = 0;

    switch (range) {
      case "1D":
        daysToShow = 1;
        break;
      case "5D":
        daysToShow = 5;
        break;
      case "1M":
        daysToShow = 30;
        break;
      case "3M":
        daysToShow = 90;
        break;
      case "6M":
        daysToShow = 180;
        break;
      case "1Y":
        daysToShow = 365;
        break;
      case "YTD": {
        const startOfYear = new Date(fallbackEndDate.getFullYear(), 0, 1);
        chartRef.current.timeScale().setVisibleRange({
          from: (startOfYear.getTime() / 1000) as Time,
          to: rangeEndTime as Time,
        });
        return;
      }
      case "ALL":
        chartRef.current.timeScale().fitContent();
        return;
    }

    const fromTime = rangeEndTime - daysToShow * 24 * 60 * 60;
    chartRef.current.timeScale().setVisibleRange({
      from: fromTime as Time,
      to: rangeEndTime as Time,
    });
  };

  const handleSaveWorkspace = () => {
    const saved = writeChartWorkspacePreset(workspaceStorageKey, {
      workspaceVersion: 1,
      selectedRange,
      visibleIndicators,
      annotationNote,
      savedAt: new Date().toISOString(),
    });
    setWorkspaceMessage(saved ? t("workspaceSaved") : t("workspaceSaveFailed"));
  };

  const handleRestoreWorkspace = () => {
    const preset = readChartWorkspacePreset(workspaceStorageKey, defaultVisibleIndicators);
    if (!preset) {
      setWorkspaceMessage(t("workspaceNotFound"));
      return;
    }

    setSelectedRange(preset.selectedRange);
    setVisibleIndicators(preset.visibleIndicators);
    setAnnotationNote(preset.annotationNote);
    applyTimeRangeToChart(preset.selectedRange);
    setWorkspaceMessage(t("workspaceRestored"));
  };

  const handleResetWorkspace = () => {
    removeChartWorkspacePreset(workspaceStorageKey);
    setSelectedRange("3M");
    setVisibleIndicators(defaultVisibleIndicators);
    setAnnotationNote("");
    applyTimeRangeToChart("3M");
    setWorkspaceMessage(t("workspaceReset"));
  };

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    const isDarkTheme = resolvedTheme === "dark";
    const chartTheme = isDarkTheme
      ? {
          background: "#18181b",
          text: "#e4e4e7",
          grid: "#27272a",
          border: "#3f3f46",
        }
      : {
          background: "#ffffff",
          text: "#333333",
          grid: "#f0f0f0",
          border: "#e0e0e0",
        };

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: chartTheme.background },
        textColor: chartTheme.text,
      },
      grid: {
        vertLines: { color: chartTheme.grid },
        horzLines: { color: chartTheme.grid },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: chartTheme.border,
      },
      timeScale: {
        borderColor: chartTheme.border,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });

    candlestickSeriesRef.current = candlestickSeries;

    const chartBars: TimedBarData[] = data.map((bar) => ({
      ...bar,
      time: (new Date(bar.timestamp).getTime() / 1000) as Time,
    }));
    const candlestickData: CandlestickData[] = chartBars.map((bar) => ({
      time: bar.time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));
    const closes = chartBars.map((bar) => bar.close);

    candlestickSeries.setData(candlestickData);

    if (visibleIndicators.ma) {
      const maPeriods = indicatorParameters.maPeriods ?? DEFAULT_MA_PERIODS;
      maPeriods.forEach((period, periodIndex) => {
        const movingAverageData = getFiniteLineSeriesData(chartBars, calculateMovingAverageSeries(closes, period));
        const movingAverageSeries = chart.addSeries(LineSeries, {
          color: movingAverageColors[periodIndex % movingAverageColors.length],
          lineWidth: 1,
          title: t("seriesMovingAverage", { period }),
        });
        movingAverageSeries.setData(movingAverageData);
      });
    }

    if (visibleIndicators.boll) {
      const bollingerBands = calculateBollingerBandsSeries(
        closes,
        indicatorParameters.bollWindow ?? DEFAULT_BOLL_WINDOW,
        indicatorParameters.bollStandardDeviationMultiplier ?? DEFAULT_BOLL_STANDARD_DEVIATION_MULTIPLIER,
      );
      const bollingerSeriesConfigs: Array<{
        title: string;
        color: string;
        getValue: (point: BollingerBandsPoint) => number | null;
      }> = [
        { title: t("seriesBollUpper"), color: "#f59e0b", getValue: (point) => point.upper },
        { title: t("seriesBollMiddle"), color: "#94a3b8", getValue: (point) => point.middle },
        { title: t("seriesBollLower"), color: "#f59e0b", getValue: (point) => point.lower },
      ];

      bollingerSeriesConfigs.forEach((seriesConfig) => {
        const bollingerSeries = chart.addSeries(LineSeries, {
          color: seriesConfig.color,
          lineWidth: 1,
          title: seriesConfig.title,
        });
        bollingerSeries.setData(getFiniteLineSeriesData(chartBars, bollingerBands.map(seriesConfig.getValue)));
      });
    }

    if (visibleIndicators.volume && data.some((bar) => bar.volume !== undefined)) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: "#26a69a80",
        priceFormat: {
          type: "volume",
        },
        priceScaleId: "",
        title: t("seriesVolume"),
      });

      volumeSeriesRef.current = volumeSeries;

      chart.priceScale("").applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });

      const volumeData = chartBars.map((bar, index) => {
        const previousClose = index > 0 ? chartBars[index - 1].close : bar.open;
        const color = bar.close >= previousClose ? "#26a69a80" : "#ef535080";

        return { time: bar.time, value: bar.volume ?? 0, color };
      });

      volumeSeries.setData(volumeData);
    }

    if (visibleIndicators.macd) {
      const macdSeriesData = calculateMacdSeries(
        closes,
        indicatorParameters.macdFastWindow ?? DEFAULT_MACD_FAST_WINDOW,
        indicatorParameters.macdSlowWindow ?? DEFAULT_MACD_SLOW_WINDOW,
        indicatorParameters.macdSignalWindow ?? DEFAULT_MACD_SIGNAL_WINDOW,
      );
      const macdLineConfigs: Array<{
        title: string;
        color: string;
        getValue: (point: MacdPoint) => number | null;
      }> = [
        { title: t("seriesMacdDif"), color: "#22c55e", getValue: (point) => point.macd },
        { title: t("seriesMacdDea"), color: "#eab308", getValue: (point) => point.signal },
      ];

      macdLineConfigs.forEach((seriesConfig) => {
        const lineSeries = chart.addSeries(LineSeries, {
          color: seriesConfig.color,
          lineWidth: 1,
          priceScaleId: "macd",
          title: seriesConfig.title,
        });
        lineSeries.setData(getFiniteLineSeriesData(chartBars, macdSeriesData.map(seriesConfig.getValue)));
      });

      const histogramSeries = chart.addSeries(HistogramSeries, {
        color: "#64748b80",
        priceScaleId: "macd",
        title: t("seriesMacdHistogram"),
      });
      histogramSeries.setData(
        getFiniteHistogramSeriesData(chartBars, macdSeriesData.map((point) => point.histogram), (value) =>
          value >= 0 ? "#26a69a80" : "#ef535080",
        ),
      );
    }

    if (visibleIndicators.rsi) {
      const rsiPeriods = indicatorParameters.rsiPeriods ?? DEFAULT_RSI_PERIODS;
      rsiPeriods.forEach((period, periodIndex) => {
        const rsiSeries = chart.addSeries(LineSeries, {
          color: rsiColors[periodIndex % rsiColors.length],
          lineWidth: 1,
          priceScaleId: "rsi",
          title: t("seriesRsi", { period }),
        });
        rsiSeries.setData(getFiniteLineSeriesData(chartBars, computeRsiSeries(closes, period)));
      });
    }

    if (visibleIndicators.kdj) {
      const kdjSeriesData = calculateKdjSeries(
        chartBars,
        indicatorParameters.kdjWindow ?? DEFAULT_KDJ_WINDOW,
        indicatorParameters.kdjKSmoothing ?? DEFAULT_KDJ_K_SMOOTHING,
        indicatorParameters.kdjDSmoothing ?? DEFAULT_KDJ_D_SMOOTHING,
      );
      const kdjLineConfigs: Array<{
        title: string;
        color: string;
        getValue: (point: KdjPoint) => number | null;
      }> = [
        { title: t("seriesKdjK"), color: "#38bdf8", getValue: (point) => point.k },
        { title: t("seriesKdjD"), color: "#f97316", getValue: (point) => point.d },
        { title: t("seriesKdjJ"), color: "#a855f7", getValue: (point) => point.j },
      ];

      kdjLineConfigs.forEach((seriesConfig) => {
        const kdjSeries = chart.addSeries(LineSeries, {
          color: seriesConfig.color,
          lineWidth: 1,
          priceScaleId: "kdj",
          title: seriesConfig.title,
        });
        kdjSeries.setData(getFiniteLineSeriesData(chartBars, kdjSeriesData.map(seriesConfig.getValue)));
      });
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, height, indicatorParameters, resolvedTheme, t, visibleIndicators]);

  const handleTimeRangeChange = (range: TimeRange) => {
    setSelectedRange(range);
    applyTimeRangeToChart(range);
  };

  if (data.length === 0) {
    return (
      <div className={`flex items-center justify-center bg-muted/30 rounded ${className}`} style={{ height }}>
        <p className="text-sm text-muted-foreground">{t("emptyState")}</p>
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-medium">{symbol}</div>
        <div className="flex items-center gap-1">
          {timeRangeOptions.map((range) => (
            <Button
              key={range}
              variant={selectedRange === range ? "default" : "ghost"}
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={() => handleTimeRangeChange(range)}
            >
              {range}
            </Button>
          ))}
        </div>
      </div>
      <div className="rounded border bg-muted/20 p-3 text-xs text-muted-foreground">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="font-medium text-foreground">{t("workspaceTitle")}</div>
            <div>{t("workspaceDescription")}</div>
          </div>
          <div className="flex flex-wrap items-center gap-1">
            <Button type="button" variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={handleSaveWorkspace}>
              {t("workspaceSave")}
            </Button>
            <Button type="button" variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={handleRestoreWorkspace}>
              {t("workspaceRestore")}
            </Button>
            <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={handleResetWorkspace}>
              {t("workspaceResetAction")}
            </Button>
          </div>
        </div>
        <label className="mb-1 block font-medium text-foreground" htmlFor="chart-workspace-annotation">
          {t("annotationLabel")}
        </label>
        <textarea
          id="chart-workspace-annotation"
          aria-label={t("annotationLabel")}
          className="min-h-16 w-full rounded border bg-background px-2 py-1 text-xs text-foreground"
          placeholder={t("annotationPlaceholder")}
          value={annotationNote}
          onChange={(event) => setAnnotationNote(event.target.value)}
        />
        {annotationNote.trim() ? (
          <div className="mt-2 rounded bg-background/70 px-2 py-1">
            {t("annotationPreview", { note: annotationNote.trim() })}
          </div>
        ) : null}
        {workspaceMessage ? (
          <div className="mt-2" role="status">
            {workspaceMessage}
          </div>
        ) : null}
        <div className="mt-2">{t("workspaceLocalOnly")}</div>
      </div>
      <div className="flex flex-wrap items-center gap-1" aria-label={t("technicalIndicatorsLabel")}>
        {indicatorOptions.map((indicator) => (
          <Button
            key={indicator.key}
            type="button"
            variant={visibleIndicators[indicator.key] ? "default" : "outline"}
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={() => toggleIndicator(indicator.key)}
          >
            {indicator.label}
          </Button>
        ))}
      </div>
      <div ref={chartContainerRef} className="w-full rounded border bg-card" />
    </div>
  );
}
