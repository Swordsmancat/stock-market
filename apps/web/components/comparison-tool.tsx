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
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  buildComparisonReportText,
  buildCorrelationMatrix,
  buildNormalizedComparisonChartData,
  calculateComparisonSummaries,
  type ComparisonInstrument,
  type ComparisonReportLabels,
} from "@/lib/comparison-utils";

export type ComparisonToolLabels = {
  title: string;
  description: string;
  insufficientTitle: string;
  insufficientDescription: string;
  insufficientBody: string;
  exportReport: string;
  selectAtLeastTwo: string;
  returnsTitle: string;
  correlationTitle: string;
  instrument: string;
  startClose: string;
  latestClose: string;
  intervalReturn: string;
  volatility: string;
  report: ComparisonReportLabels;
};

type ComparisonToolProps = {
  instruments: ComparisonInstrument[];
  labels: ComparisonToolLabels;
  locale: string;
  className?: string;
};

const COMPARISON_COLORS = ["#2563eb", "#16a34a", "#dc2626", "#9333ea"];
const MAX_SELECTED_INSTRUMENTS = 4;
const MIN_SELECTED_INSTRUMENTS = 2;

function formatPercent(value: number | null, locale: string): string {
  if (value === null) {
    return "--";
  }

  const formattedValue = new Intl.NumberFormat(locale, {
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

function formatNumber(value: number | null, locale: string): string {
  if (value === null) {
    return "--";
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

export function ComparisonTool({
  instruments,
  labels,
  locale,
  className = "",
}: ComparisonToolProps) {
  const availableInstruments = React.useMemo(
    () =>
      instruments
        .filter((instrument) => instrument.bars.length > 0)
        .slice(0, 12),
    [instruments],
  );
  const [selectedInstrumentIds, setSelectedInstrumentIds] = React.useState<
    string[]
  >(() =>
    availableInstruments
      .slice(0, MAX_SELECTED_INSTRUMENTS)
      .map((instrument) => instrument.id),
  );

  React.useEffect(() => {
    setSelectedInstrumentIds((currentSelectedIds) => {
      const availableIds = new Set(
        availableInstruments.map((instrument) => instrument.id),
      );
      const retainedSelectedIds = currentSelectedIds.filter((instrumentId) =>
        availableIds.has(instrumentId),
      );
      if (retainedSelectedIds.length >= MIN_SELECTED_INSTRUMENTS) {
        return retainedSelectedIds.slice(0, MAX_SELECTED_INSTRUMENTS);
      }
      return availableInstruments
        .slice(0, MAX_SELECTED_INSTRUMENTS)
        .map((instrument) => instrument.id);
    });
  }, [availableInstruments]);

  const selectedInstruments = React.useMemo(
    () =>
      availableInstruments.filter((instrument) =>
        selectedInstrumentIds.includes(instrument.id),
      ),
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
        return currentSelectedIds.filter(
          (selectedInstrumentId) => selectedInstrumentId !== instrumentId,
        );
      }
      if (currentSelectedIds.length >= MAX_SELECTED_INSTRUMENTS) {
        return currentSelectedIds;
      }
      return [...currentSelectedIds, instrumentId];
    });
  }

  function exportReport() {
    if (selectedInstruments.length < MIN_SELECTED_INSTRUMENTS) {
      return;
    }

    const reportText = buildComparisonReportText({
      selectedInstruments,
      summaries,
      correlationMatrix,
      labels: labels.report,
    });
    const reportBlob = new Blob([reportText], {
      type: "text/plain;charset=utf-8",
    });
    const reportUrl = URL.createObjectURL(reportBlob);
    const downloadLink = document.createElement("a");
    downloadLink.href = reportUrl;
    downloadLink.download = "comparison-report.txt";
    downloadLink.click();
    URL.revokeObjectURL(reportUrl);
  }

  if (availableInstruments.length < MIN_SELECTED_INSTRUMENTS) {
    return (
      <FinancialTerminalCard className={className}>
        <FinancialTerminalCardHeader>
          <CardTitle className="text-base">
            {labels.insufficientTitle}
          </CardTitle>
          <CardDescription className="text-xs">
            {labels.insufficientDescription}
          </CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent className="text-sm text-muted-foreground">
          {labels.insufficientBody}
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>
    );
  }

  return (
    <FinancialTerminalCard className={className}>
      <FinancialTerminalCardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{labels.title}</CardTitle>
            <CardDescription className="text-xs">
              {labels.description}
            </CardDescription>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={exportReport}
            disabled={selectedInstruments.length < MIN_SELECTED_INSTRUMENTS}
          >
            {labels.exportReport}
          </Button>
        </div>
      </FinancialTerminalCardHeader>
      <FinancialTerminalCardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {availableInstruments.map((instrument) => {
            const isSelected = selectedInstrumentIds.includes(instrument.id);
            const isDisabled =
              !isSelected &&
              selectedInstrumentIds.length >= MAX_SELECTED_INSTRUMENTS;

            return (
              <label
                key={instrument.id}
                className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-xs transition-colors ${
                  isSelected
                    ? "border-primary bg-primary/5"
                    : "hover:bg-muted/50"
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
          <FinancialTerminalSurface className="bg-muted/20 p-4 text-sm text-muted-foreground">
            {labels.selectAtLeastTwo}
          </FinancialTerminalSurface>
        ) : (
          <>
            <FinancialTerminalSurface className="h-72 p-3">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    domain={["dataMin - 2", "dataMax + 2"]}
                  />
                  <Tooltip
                    formatter={(value) =>
                      formatNumber(
                        typeof value === "number" ? value : null,
                        locale,
                      )
                    }
                  />
                  {selectedInstruments.map((instrument, instrumentIndex) => (
                    <Line
                      key={instrument.id}
                      type="monotone"
                      dataKey={instrument.id}
                      name={instrument.symbol}
                      dot={false}
                      stroke={
                        COMPARISON_COLORS[
                          instrumentIndex % COMPARISON_COLORS.length
                        ]
                      }
                      strokeWidth={2}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </FinancialTerminalSurface>

            <div className="grid gap-4 xl:grid-cols-2">
              <div className="space-y-2">
                <div className="text-sm font-semibold">
                  {labels.returnsTitle}
                </div>
                <div className="overflow-x-auto rounded-md border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 text-xs text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2 text-left">
                          {labels.instrument}
                        </th>
                        <th className="px-3 py-2 text-right">
                          {labels.startClose}
                        </th>
                        <th className="px-3 py-2 text-right">
                          {labels.latestClose}
                        </th>
                        <th className="px-3 py-2 text-right">
                          {labels.intervalReturn}
                        </th>
                        <th className="px-3 py-2 text-right">
                          {labels.volatility}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {summaries.map((summary) => (
                        <tr key={summary.id} className="border-t">
                          <td className="px-3 py-2">
                            <div className="font-medium">{summary.symbol}</div>
                            <div className="text-xs text-muted-foreground">
                              {summary.name}
                            </div>
                          </td>
                          <td className="px-3 py-2 text-right font-mono">
                            {formatNumber(summary.startClose, locale)}
                          </td>
                          <td className="px-3 py-2 text-right font-mono">
                            {formatNumber(summary.latestClose, locale)}
                          </td>
                          <td className="px-3 py-2 text-right font-mono">
                            <Badge
                              variant={
                                summary.percentChange >= 0
                                  ? "secondary"
                                  : "destructive"
                              }
                            >
                              {formatPercent(summary.percentChange, locale)}
                            </Badge>
                          </td>
                          <td className="px-3 py-2 text-right font-mono">
                            {formatPercent(summary.volatility, locale)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-semibold">
                  {labels.correlationTitle}
                </div>
                <div className="overflow-x-auto rounded-md border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 text-xs text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2 text-left">
                          {labels.instrument}
                        </th>
                        {selectedInstruments.map((instrument) => (
                          <th
                            key={instrument.id}
                            className="px-3 py-2 text-right"
                          >
                            {instrument.symbol}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {selectedInstruments.map((leftInstrument) => (
                        <tr key={leftInstrument.id} className="border-t">
                          <td className="px-3 py-2 font-medium">
                            {leftInstrument.symbol}
                          </td>
                          {selectedInstruments.map((rightInstrument) => {
                            const cell = correlationMatrix.find(
                              (matrixCell) =>
                                matrixCell.leftInstrumentId ===
                                  leftInstrument.id &&
                                matrixCell.rightInstrumentId ===
                                  rightInstrument.id,
                            );
                            return (
                              <td
                                key={rightInstrument.id}
                                className="px-3 py-2 text-right font-mono"
                              >
                                {cell?.value === null ||
                                cell?.value === undefined
                                  ? "--"
                                  : cell.value.toFixed(3)}
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
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}
