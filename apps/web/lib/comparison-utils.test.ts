import { describe, expect, it } from "vitest";

import {
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
});
