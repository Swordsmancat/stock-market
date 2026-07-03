"use client";

import { useEffect, useRef, useState } from "react";
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from "lightweight-charts";
import { Button } from "@/components/ui/button";

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
}

type TimeRange = "1D" | "5D" | "1M" | "3M" | "6M" | "1Y" | "ALL";

const timeRangeOptions: TimeRange[] = ["1D", "5D", "1M", "3M", "6M", "1Y", "ALL"];

export function AdvancedCandlestickChart({
  data = [],
  symbol = "",
  height = 400,
  showMA = true,
  showVolume = true,
  className = "",
}: AdvancedCandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const [selectedRange, setSelectedRange] = useState<TimeRange>("3M");

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: "#ffffff" },
        textColor: "#333",
      },
      grid: {
        vertLines: { color: "#f0f0f0" },
        horzLines: { color: "#f0f0f0" },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: "#e0e0e0",
      },
      timeScale: {
        borderColor: "#e0e0e0",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });

    candlestickSeriesRef.current = candlestickSeries;

    const candlestickData: CandlestickData[] = data.map((bar) => ({
      time: (new Date(bar.timestamp).getTime() / 1000) as Time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));

    candlestickSeries.setData(candlestickData);

    if (showMA) {
      const ma5Data = calculateMA(candlestickData, 5);
      const ma10Data = calculateMA(candlestickData, 10);
      const ma20Data = calculateMA(candlestickData, 20);

      const ma5Series = chart.addLineSeries({
        color: "#2196F3",
        lineWidth: 1,
        title: "MA5",
      });
      ma5Series.setData(ma5Data);

      const ma10Series = chart.addLineSeries({
        color: "#FF9800",
        lineWidth: 1,
        title: "MA10",
      });
      ma10Series.setData(ma10Data);

      const ma20Series = chart.addLineSeries({
        color: "#9C27B0",
        lineWidth: 1,
        title: "MA20",
      });
      ma20Series.setData(ma20Data);
    }

    if (showVolume && data.some((bar) => bar.volume !== undefined)) {
      const volumeSeries = chart.addHistogramSeries({
        color: "#26a69a",
        priceFormat: {
          type: "volume",
        },
        priceScaleId: "",
      });

      volumeSeriesRef.current = volumeSeries;

      chart.priceScale("").applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });

      const volumeData = data.map((bar, index) => {
        const prevClose = index > 0 ? data[index - 1].close : bar.open;
        const color = bar.close >= prevClose ? "#26a69a80" : "#ef535080";

        return {
          time: (new Date(bar.timestamp).getTime() / 1000) as Time,
          value: bar.volume || 0,
          color,
        };
      });

      volumeSeries.setData(volumeData);
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
  }, [data, height, showMA, showVolume]);

  const calculateMA = (data: CandlestickData[], period: number) => {
    const result: { time: Time; value: number }[] = [];

    for (let i = period - 1; i < data.length; i++) {
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += data[i - j].close;
      }
      result.push({
        time: data[i].time,
        value: sum / period,
      });
    }

    return result;
  };

  const handleTimeRangeChange = (range: TimeRange) => {
    setSelectedRange(range);
    if (!chartRef.current || data.length === 0) return;

    const now = new Date();
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
      case "ALL":
        chartRef.current.timeScale().fitContent();
        return;
    }

    const fromTime = (now.getTime() - daysToShow * 24 * 60 * 60 * 1000) / 1000;
    chartRef.current.timeScale().setVisibleRange({
      from: fromTime as Time,
      to: (now.getTime() / 1000) as Time,
    });
  };

  if (data.length === 0) {
    return (
      <div className={`flex items-center justify-center bg-muted/30 rounded ${className}`} style={{ height }}>
        <p className="text-sm text-muted-foreground">暂无K线数据</p>
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between">
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
      <div ref={chartContainerRef} className="w-full rounded border" />
    </div>
  );
}
