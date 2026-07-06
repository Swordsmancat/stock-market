"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createChart, HistogramSeries, LineSeries } from "lightweight-charts";
import type { IChartApi, ISeriesApi, Time } from "lightweight-charts";
import { useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { DataTrustBadge } from "@/components/data-trust-badge";
import { createDataTrustSignal } from "@/lib/data-trust";

export type IntradayPricePoint = {
  timestamp?: string;
  price?: number;
  close?: number;
  averagePrice?: number | null;
  average_price?: number | null;
  volume?: number | null;
};

type IntradayChartStatus = "ok" | "no_data" | "degraded";

type IntradayTrustAvailability = {
  status?: string | null;
  reason?: string | null;
  is_realtime?: boolean | null;
  is_delayed?: boolean | null;
  delay_minutes?: number | null;
} | null;

type IntradayTrustFreshness = {
  status?: string | null;
  reason?: string | null;
  cache_status?: string | null;
  data_as_of?: string | null;
  fetched_at?: string | null;
  cached_at?: string | null;
} | null;

type IntradayTrustSession = {
  status?: string | null;
  reason?: string | null;
} | null;

type IntradayPriceChartProps = {
  points: IntradayPricePoint[];
  previousClose?: number | null;
  status?: IntradayChartStatus;
  reason?: string | null;
  source?: string | null;
  provider?: string | null;
  requestedProvider?: string | null;
  effectiveProvider?: string | null;
  availability?: IntradayTrustAvailability;
  freshness?: IntradayTrustFreshness;
  session?: IntradayTrustSession;
  height?: number;
  className?: string;
};

type NormalizedIntradayPoint = {
  timestamp: string;
  time: Time;
  price: number;
  averagePrice: number | null;
  volume: number | null;
};

function getFiniteNumber(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeIntradayPoint(point: IntradayPricePoint): NormalizedIntradayPoint | null {
  if (!point.timestamp) {
    return null;
  }

  const timestampMilliseconds = new Date(point.timestamp).getTime();
  if (!Number.isFinite(timestampMilliseconds)) {
    return null;
  }

  const price = getFiniteNumber(point.price ?? point.close);
  if (price === null) {
    return null;
  }

  return {
    timestamp: point.timestamp,
    time: (timestampMilliseconds / 1000) as Time,
    price,
    averagePrice: getFiniteNumber(point.averagePrice ?? point.average_price),
    volume: getFiniteNumber(point.volume),
  };
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "--";
  }

  return value.toFixed(2);
}

function formatVolume(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "--";
  }

  return Math.round(value).toLocaleString();
}

function formatIntradayTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function IntradayPriceChart({
  points,
  previousClose = null,
  status = "degraded",
  reason = null,
  source = null,
  provider = null,
  requestedProvider = null,
  effectiveProvider = null,
  availability = null,
  freshness = null,
  session = null,
  height = 280,
  className = "",
}: IntradayPriceChartProps) {
  const t = useTranslations("IntradayPriceChart");
  const { resolvedTheme } = useTheme();
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<NormalizedIntradayPoint | null>(null);
  const normalizedPoints = useMemo(
    () => points.map(normalizeIntradayPoint).filter((point): point is NormalizedIntradayPoint => point !== null),
    [points],
  );
  const activePoint = hoveredPoint ?? normalizedPoints.at(-1) ?? null;
  const finitePreviousClose = getFiniteNumber(previousClose);
  const hasAveragePrice = normalizedPoints.some((point) => point.averagePrice !== null);
  const hasVolume = normalizedPoints.some((point) => point.volume !== null);
  const trustSignal = createDataTrustSignal({
    status,
    source,
    provider,
    requestedProvider,
    effectiveProvider,
    availability,
    freshness,
    session,
    reason,
  });

  useEffect(() => {
    if (!chartContainerRef.current || normalizedPoints.length === 0 || status !== "ok") {
      return;
    }

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
      height,
      layout: {
        background: { color: chartTheme.background },
        textColor: chartTheme.text,
      },
      grid: {
        vertLines: { color: chartTheme.grid },
        horzLines: { color: chartTheme.grid },
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
    const priceSeries = chart.addSeries(LineSeries, {
      color: "#2563eb",
      lineWidth: 2,
      title: t("priceSeries"),
    });
    priceSeriesRef.current = priceSeries;
    priceSeries.setData(normalizedPoints.map((point) => ({ time: point.time, value: point.price })));

    if (finitePreviousClose !== null && "createPriceLine" in priceSeries) {
      priceSeries.createPriceLine({
        price: finitePreviousClose,
        color: "#94a3b8",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: t("previousCloseLabel"),
      });
    }

    if (hasAveragePrice) {
      const averageSeries = chart.addSeries(LineSeries, {
        color: "#f97316",
        lineWidth: 1,
        title: t("averagePriceSeries"),
      });
      averageSeries.setData(
        normalizedPoints.flatMap((point) =>
          point.averagePrice === null ? [] : [{ time: point.time, value: point.averagePrice }],
        ),
      );
    }

    if (hasVolume) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: "#26a69a80",
        priceFormat: { type: "volume" },
        priceScaleId: "",
        title: t("volumeSeries"),
      });
      chart.priceScale("").applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });
      volumeSeries.setData(
        normalizedPoints.flatMap((point, index) => {
          if (point.volume === null) {
            return [];
          }
          const previousPrice = index > 0 ? normalizedPoints[index - 1].price : point.price;
          return [
            {
              time: point.time,
              value: point.volume,
              color: point.price >= previousPrice ? "#26a69a80" : "#ef535080",
            },
          ];
        }),
      );
    }

    const pointsByTime = new Map(normalizedPoints.map((point) => [String(point.time), point]));
    const handleCrosshairMove = (param: { time?: Time }) => {
      if (param.time === undefined) {
        setHoveredPoint(null);
        return;
      }
      setHoveredPoint(pointsByTime.get(String(param.time)) ?? null);
    };
    chart.subscribeCrosshairMove?.(handleCrosshairMove);
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.unsubscribeCrosshairMove?.(handleCrosshairMove);
      chart.remove();
    };
  }, [finitePreviousClose, hasAveragePrice, hasVolume, height, normalizedPoints, resolvedTheme, status, t]);

  if (status !== "ok" || normalizedPoints.length === 0) {
    return (
      <div className={`flex min-h-48 items-center justify-center rounded border bg-muted/30 p-6 ${className}`}>
        <div className="space-y-2 text-center">
          <DataTrustBadge signal={trustSignal} mode="summary" className="items-center" />
          <p className="text-sm font-medium text-muted-foreground">
            {status === "degraded" ? t("degradedState") : t("emptyState")}
          </p>
          {reason ? <p className="text-xs text-muted-foreground">{reason}</p> : null}
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <DataTrustBadge signal={trustSignal} mode="summary" />
      <div className="grid gap-2 rounded border bg-muted/20 p-3 text-xs text-muted-foreground sm:grid-cols-5">
        <div>
          <div className="font-medium text-foreground">{t("timeLabel")}</div>
          <div>{activePoint ? formatIntradayTime(activePoint.timestamp) : "--"}</div>
        </div>
        <div>
          <div className="font-medium text-foreground">{t("priceLabel")}</div>
          <div>{formatNumber(activePoint?.price)}</div>
        </div>
        <div>
          <div className="font-medium text-foreground">{t("averagePriceLabel")}</div>
          <div>{formatNumber(activePoint?.averagePrice)}</div>
        </div>
        <div>
          <div className="font-medium text-foreground">{t("previousCloseLabel")}</div>
          <div>{formatNumber(finitePreviousClose)}</div>
        </div>
        <div>
          <div className="font-medium text-foreground">{t("volumeLabel")}</div>
          <div>{formatVolume(activePoint?.volume)}</div>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full rounded border bg-card" />
    </div>
  );
}
