import { describe, expect, it } from "vitest";

import {
  calculateBollingerBandsSeries,
  calculateKdjSeries,
  calculateMacdSeries,
  calculateMovingAverageSeries,
} from "./chart-indicators";

describe("chart indicator helpers", () => {
  it("calculates moving averages after the warm-up window", () => {
    const result = calculateMovingAverageSeries([1, 2, 3, 4], 3);

    expect(result).toEqual([null, null, 2, 3]);
  });

  it("calculates bollinger bands from moving averages and standard deviation", () => {
    const result = calculateBollingerBandsSeries([1, 2, 3], 3, 2);
    const latest = result.at(-1)!;

    expect(result[0]).toEqual({ upper: null, middle: null, lower: null });
    expect(latest.middle).toBe(2);
    expect(latest.upper).toBeCloseTo(3.632993, 6);
    expect(latest.lower).toBeCloseTo(0.367007, 6);
  });

  it("calculates MACD signal and histogram with EMA smoothing", () => {
    const result = calculateMacdSeries([1, 2, 3], 2, 3, 2);
    const latest = result.at(-1)!;

    expect(latest.macd).toBeCloseTo(0.305556, 6);
    expect(latest.signal).toBeCloseTo(0.240741, 6);
    expect(latest.histogram).toBeCloseTo(0.064815, 6);
  });

  it("calculates KDJ values with the same smoothing defaults as the backend", () => {
    const result = calculateKdjSeries(
      [
        { timestamp: "2026-01-01T00:00:00.000Z", open: 9, high: 10, low: 8, close: 9 },
        { timestamp: "2026-01-02T00:00:00.000Z", open: 11, high: 12, low: 9, close: 11 },
        { timestamp: "2026-01-03T00:00:00.000Z", open: 13, high: 14, low: 10, close: 13 },
      ],
      3,
    );
    const latest = result.at(-1)!;

    expect(result[0]).toEqual({ k: null, d: null, j: null });
    expect(latest.k).toBeCloseTo(61.111111, 6);
    expect(latest.d).toBeCloseTo(53.703704, 6);
    expect(latest.j).toBeCloseTo(75.925926, 6);
  });

  it("keeps KDJ finite when the price range is flat", () => {
    const result = calculateKdjSeries(
      [
        { timestamp: "2026-01-01T00:00:00.000Z", open: 10, high: 10, low: 10, close: 10 },
        { timestamp: "2026-01-02T00:00:00.000Z", open: 10, high: 10, low: 10, close: 10 },
        { timestamp: "2026-01-03T00:00:00.000Z", open: 10, high: 10, low: 10, close: 10 },
      ],
      3,
    );
    const latest = result.at(-1)!;

    expect(latest.k).toBe(50);
    expect(latest.d).toBe(50);
    expect(latest.j).toBe(50);
  });
});
