import { describe, expect, it } from "vitest";

import {
  buildComparisonReportText,
  buildCorrelationMatrix,
  buildNormalizedComparisonChartData,
  calculateComparisonSummaries,
  calculatePearsonCorrelation,
  normalizeComparisonSeries,
  type ComparisonInstrument,
} from "./comparison-utils";

const leftInstrument: ComparisonInstrument = {
  id: "left",
  symbol: "LEFT",
  name: "Left Instrument",
  bars: [
    { timestamp: "2026-01-01", close: 100 },
    { timestamp: "2026-01-02", close: 110 },
    { timestamp: "2026-01-03", close: 120 },
  ],
};

const rightInstrument: ComparisonInstrument = {
  id: "right",
  symbol: "RIGHT",
  name: "Right Instrument",
  bars: [
    { timestamp: "2026-01-01", close: 50 },
    { timestamp: "2026-01-02", close: 55 },
    { timestamp: "2026-01-03", close: 60 },
  ],
};

describe("comparison-utils", () => {
  it("normalizes each series to an indexed base of 100", () => {
    expect(normalizeComparisonSeries(leftInstrument)).toEqual([
      { timestamp: "2026-01-01", value: 100 },
      { timestamp: "2026-01-02", value: 110.00000000000001 },
      { timestamp: "2026-01-03", value: 120 },
    ]);
  });

  it("builds aligned chart rows across selected instruments", () => {
    expect(buildNormalizedComparisonChartData([leftInstrument, rightInstrument])).toEqual([
      { timestamp: "2026-01-01", left: 100, right: 100 },
      { timestamp: "2026-01-02", left: 110, right: 110 },
      { timestamp: "2026-01-03", left: 120, right: 120 },
    ]);
  });

  it("calculates percentage summaries and Pearson correlation", () => {
    const summaries = calculateComparisonSummaries([leftInstrument, rightInstrument]);

    expect(summaries).toHaveLength(2);
    expect(summaries[0].percentChange).toBeCloseTo(0.2);
    expect(calculatePearsonCorrelation(leftInstrument, rightInstrument)).toBeCloseTo(1);
  });

  it("builds a full correlation matrix for selected instruments", () => {
    const matrix = buildCorrelationMatrix([leftInstrument, rightInstrument]);

    expect(matrix).toHaveLength(4);
    expect(matrix.find((cell) => cell.leftInstrumentId === "left" && cell.rightInstrumentId === "left")?.value).toBe(1);
    expect(matrix.find((cell) => cell.leftInstrumentId === "left" && cell.rightInstrumentId === "right")?.value).toBeCloseTo(1);
  });

  it("exports selected summaries and correlation matrix in report text", () => {
    const selectedInstruments = [leftInstrument, rightInstrument];
    const reportText = buildComparisonReportText({
      selectedInstruments,
      summaries: calculateComparisonSummaries(selectedInstruments),
      correlationMatrix: buildCorrelationMatrix(selectedInstruments),
      generatedAtIso: "2026-01-04T00:00:00.000Z",
    });

    expect(reportText).toContain("对比分析报告");
    expect(reportText).toContain("生成时间: 2026-01-04T00:00:00.000Z");
    expect(reportText).toContain("已选标的:");
    expect(reportText).toContain("汇总指标:");
    expect(reportText).toContain("LEFT\tLeft Instrument\t--\t100.00\t120.00\t+20.00%");
    expect(reportText).toContain("RIGHT\tRight Instrument\t--\t50.00\t60.00\t+20.00%");
    expect(reportText).toContain("相关系数矩阵:");
    expect(reportText).toContain("标的\tLEFT\tRIGHT");
    expect(reportText).toContain("LEFT\t1.000\t1.000");
  });

  it("uses a placeholder for unavailable correlation values in report text", () => {
    const flatInstrument: ComparisonInstrument = {
      id: "flat",
      symbol: "FLAT",
      name: "Flat Instrument",
      bars: [
        { timestamp: "2026-01-01", close: 100 },
        { timestamp: "2026-01-02", close: 100 },
        { timestamp: "2026-01-03", close: 100 },
      ],
    };

    const selectedInstruments = [leftInstrument, flatInstrument];
    const reportText = buildComparisonReportText({
      selectedInstruments,
      summaries: calculateComparisonSummaries(selectedInstruments),
      correlationMatrix: buildCorrelationMatrix(selectedInstruments),
      generatedAtIso: "2026-01-04T00:00:00.000Z",
    });

    expect(reportText).toContain("标的\tLEFT\tFLAT");
    expect(reportText).toContain("LEFT\t1.000\t--");
    expect(reportText).toContain("FLAT\t--\t1.000");
  });
});
