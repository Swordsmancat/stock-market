"use client";

import * as React from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  buildCorrelationMatrix,
  buildNormalizedComparisonChartData,
  calculateComparisonSummaries,
  type ComparisonInstrument,
} from "@/lib/comparison-utils";

type ComparisonToolProps = {
  instruments: ComparisonInstrument[];
  className?: string;
};

const COMPARISON_COLORS = ["#2563eb", "#16a34a", "#dc2626", "#9333ea"];
const MAX_SELECTED_INSTRUMENTS = 4;
const MIN_SELECTED_INSTRUMENTS = 2;

function formatPercent(value: number | null): string {
  if (value === null) {
    return "--";
  }

  const formattedValue = new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
    style: "percent",
  }).format(Math.abs(value));

  if (value > 0) {
    return `+${formattedValue}`;
  }
  if (value < 0) {
    return `-${formattedValue}`;
  }
  return formattedValue;
}

function formatNumber(value: number | null): string {
  if (value === null) {
    return "--";
  }

  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function buildReportText(selectedInstruments: ComparisonInstrument[]): string {
  const summaries = calculateComparisonSummaries(selectedInstruments);
  const reportLines = [
    "对比分析报告",
    `生成时间: ${new Date().toISOString()}`,
    "",
    "标的表现:",
    ...summaries.map(
      (summary) =>
        `${summary.symbol} ${summary.name}: 收益 ${formatPercent(summary.percentChange)}, 最新价 ${formatNumber(summary.latestClose)}`,
    ),
  ];

  return reportLines.join("\n");
}

export function ComparisonTool({ instruments, className = "" }: ComparisonToolProps) {
  const availableInstruments = React.useMemo(
    () => instruments.filter((instrument) => instrument.bars.length > 0).slice(0, 12),
    [instruments],
  );
  const [selectedInstrumentIds, setSelectedInstrumentIds] = React.useState<string[]>(() =>
    availableInstruments.slice(0, MAX_SELECTED_INSTRUMENTS).map((instrument) => instrument.id),
  );

  React.useEffect(() => {
    setSelectedInstrumentIds((currentSelectedIds) => {
      const availableIds = new Set(availableInstruments.map((instrument) => instrument.id));
      const retainedSelectedIds = currentSelectedIds.filter((instrumentId) => availableIds.has(instrumentId));
      if (retainedSelectedIds.length >= MIN_SELECTED_INSTRUMENTS) {
        return retainedSelectedIds.slice(0, MAX_SELECTED_INSTRUMENTS);
      }
      return availableInstruments.slice(0, MAX_SELECTED_INSTRUMENTS).map((instrument) => instrument.id);
    });
  }, [availableInstruments]);

  const selectedInstruments = React.useMemo(
    () => availableInstruments.filter((instrument) => selectedInstrumentIds.includes(instrument.id)),
    [availableInstruments, selectedInstrumentIds],
  );
  const chartData = React.useMemo(
    () => buildNormalizedComparisonChartData(selectedInstruments),
    [selectedInstruments],
  );
  const summaries = React.useMemo(
    () => calculateComparisonSummaries(selectedInstruments),
    [selectedInstruments],
  );
  const correlationMatrix = React.useMemo(
    () => buildCorrelationMatrix(selectedInstruments),
    [selectedInstruments],
  );

  function toggleInstrument(instrumentId: string) {
    setSelectedInstrumentIds((currentSelectedIds) => {
      if (currentSelectedIds.includes(instrumentId)) {
        return currentSelectedIds.filter((selectedInstrumentId) => selectedInstrumentId !== instrumentId);
      }
      if (currentSelectedIds.length >= MAX_SELECTED_INSTRUMENTS) {
        return currentSelectedIds;
      }
      return [...currentSelectedIds, instrumentId];
    });
  }

  function exportReport() {
    const reportBlob = new Blob([buildReportText(selectedInstruments)], { type: "text/plain;charset=utf-8" });
    const reportUrl = URL.createObjectURL(reportBlob);
    const downloadLink = document.createElement("a");
    downloadLink.href = reportUrl;
    downloadLink.download = "comparison-report.txt";
    downloadLink.click();
    URL.revokeObjectURL(reportUrl);
  }

  if (availableInstruments.length < MIN_SELECTED_INSTRUMENTS) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">对比分析</CardTitle>
          <CardDescription className="text-xs">需要至少 2 个有历史数据的标的</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">暂无足够标的用于对比。</CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">对比分析</CardTitle>
            <CardDescription className="text-xs">
              支持选择 2-4 个指数/标的，查看归一化走势、收益和相关性
            </CardDescription>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={exportReport}>
            导出对比报告
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {availableInstruments.map((instrument) => {
            const isSelected = selectedInstrumentIds.includes(instrument.id);
            const isDisabled = !isSelected && selectedInstrumentIds.length >= MAX_SELECTED_INSTRUMENTS;

            return (
              <label
                key={instrument.id}
                className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-xs transition-colors ${
                  isSelected ? "border-primary bg-primary/5" : "hover:bg-muted/50"
                } ${isDisabled ? "cursor-not-allowed opacity-50" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  disabled={isDisabled}
                  onChange={() => toggleInstrument(instrument.id)}
                />
                <span className="font-medium">{instrument.symbol}</span>
                <span className="text-muted-foreground">{instrument.name}</span>
              </label>
            );
          })}
        </div>

        {selectedInstruments.length < MIN_SELECTED_INSTRUMENTS ? (
          <div className="rounded-md border bg-muted/30 p-4 text-sm text-muted-foreground">
            请至少选择 2 个标的进行对比。
          </div>
        ) : (
          <>
            <div className="h-72 rounded-md border p-3">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} domain={["dataMin - 2", "dataMax + 2"]} />
                  <Tooltip formatter={(value) => formatNumber(typeof value === "number" ? value : null)} />
                  {selectedInstruments.map((instrument, instrumentIndex) => (
                    <Line
                      key={instrument.id}
                      type="monotone"
                      dataKey={instrument.id}
                      name={instrument.symbol}
                      dot={false}
                      stroke={COMPARISON_COLORS[instrumentIndex % COMPARISON_COLORS.length]}
                      strokeWidth={2}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="grid gap-4 xl:grid-cols-2">
              <div className="space-y-2">
                <div className="text-sm font-semibold">涨跌幅对比</div>
                <div className="overflow-x-auto rounded-md border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 text-xs text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2 text-left">标的</th>
                        <th className="px-3 py-2 text-right">起始价</th>
                        <th className="px-3 py-2 text-right">最新价</th>
                        <th className="px-3 py-2 text-right">区间收益</th>
                        <th className="px-3 py-2 text-right">波动率</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summaries.map((summary) => (
                        <tr key={summary.id} className="border-t">
                          <td className="px-3 py-2">
                            <div className="font-medium">{summary.symbol}</div>
                            <div className="text-xs text-muted-foreground">{summary.name}</div>
                          </td>
                          <td className="px-3 py-2 text-right font-mono">{formatNumber(summary.startClose)}</td>
                          <td className="px-3 py-2 text-right font-mono">{formatNumber(summary.latestClose)}</td>
                          <td className="px-3 py-2 text-right font-mono">
                            <Badge variant={summary.percentChange >= 0 ? "secondary" : "destructive"}>
                              {formatPercent(summary.percentChange)}
                            </Badge>
                          </td>
                          <td className="px-3 py-2 text-right font-mono">{formatPercent(summary.volatility)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-semibold">皮尔逊相关系数</div>
                <div className="overflow-x-auto rounded-md border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 text-xs text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2 text-left">标的</th>
                        {selectedInstruments.map((instrument) => (
                          <th key={instrument.id} className="px-3 py-2 text-right">
                            {instrument.symbol}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {selectedInstruments.map((leftInstrument) => (
                        <tr key={leftInstrument.id} className="border-t">
                          <td className="px-3 py-2 font-medium">{leftInstrument.symbol}</td>
                          {selectedInstruments.map((rightInstrument) => {
                            const cell = correlationMatrix.find(
                              (matrixCell) =>
                                matrixCell.leftInstrumentId === leftInstrument.id &&
                                matrixCell.rightInstrumentId === rightInstrument.id,
                            );
                            return (
                              <td key={rightInstrument.id} className="px-3 py-2 text-right font-mono">
                                {cell?.value === null || cell?.value === undefined ? "--" : cell.value.toFixed(3)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
