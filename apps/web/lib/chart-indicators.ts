export type OhlcBar = {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

export type ChartPoint = OhlcBar & {
  date: string;
  ma20: number | null;
  bollUpper: number | null;
  bollMiddle: number | null;
  bollLower: number | null;
  rsi: number | null;
};

export type BollingerBandsPoint = {
  upper: number | null;
  middle: number | null;
  lower: number | null;
};

export type MacdPoint = {
  macd: number | null;
  signal: number | null;
  histogram: number | null;
};

export type KdjPoint = {
  k: number | null;
  d: number | null;
  j: number | null;
};

export function calculateMovingAverageSeries(values: number[], window: number): (number | null)[] {
  return values.map((_, index) => {
    if (index + 1 < window) {
      return null;
    }
    const slice = values.slice(index + 1 - window, index + 1);
    return slice.reduce((sum, value) => sum + value, 0) / window;
  });
}

function rollingStd(values: number[], window: number): (number | null)[] {
  return values.map((_, index) => {
    if (index + 1 < window) {
      return null;
    }
    const slice = values.slice(index + 1 - window, index + 1);
    const mean = slice.reduce((sum, value) => sum + value, 0) / window;
    const variance =
      slice.reduce((sum, value) => sum + (value - mean) ** 2, 0) / window;
    return Math.sqrt(variance);
  });
}

function calculateExponentialMovingAverageSeries(values: number[], span: number): number[] {
  if (values.length === 0) {
    return [];
  }

  const smoothingMultiplier = 2 / (span + 1);
  const result: number[] = [values[0]];

  for (let index = 1; index < values.length; index += 1) {
    const previousAverage = result[index - 1];
    const currentAverage = values[index] * smoothingMultiplier + previousAverage * (1 - smoothingMultiplier);
    result.push(currentAverage);
  }

  return result;
}

export function calculateBollingerBandsSeries(
  closes: number[],
  window = 20,
  standardDeviationMultiplier = 2,
): BollingerBandsPoint[] {
  const middleSeries = calculateMovingAverageSeries(closes, window);
  const standardDeviationSeries = rollingStd(closes, window);

  return closes.map((_close, index) => {
    const middle = middleSeries[index];
    const standardDeviation = standardDeviationSeries[index];
    return {
      upper: middle !== null && standardDeviation !== null ? middle + standardDeviation * standardDeviationMultiplier : null,
      middle,
      lower: middle !== null && standardDeviation !== null ? middle - standardDeviation * standardDeviationMultiplier : null,
    };
  });
}

export function calculateMacdSeries(
  closes: number[],
  fastWindow = 12,
  slowWindow = 26,
  signalWindow = 9,
): MacdPoint[] {
  if (closes.length === 0) {
    return [];
  }

  const fastAverageSeries = calculateExponentialMovingAverageSeries(closes, fastWindow);
  const slowAverageSeries = calculateExponentialMovingAverageSeries(closes, slowWindow);
  const macdLineSeries = closes.map((_close, index) => fastAverageSeries[index] - slowAverageSeries[index]);
  const signalLineSeries = calculateExponentialMovingAverageSeries(macdLineSeries, signalWindow);

  return macdLineSeries.map((macdValue, index) => {
    const signalValue = signalLineSeries[index];
    return {
      macd: macdValue,
      signal: signalValue,
      histogram: macdValue - signalValue,
    };
  });
}

export function calculateKdjSeries(
  bars: OhlcBar[],
  rsvWindow = 9,
  kSmoothing = 3,
  dSmoothing = 3,
): KdjPoint[] {
  const result: KdjPoint[] = [];
  let previousK = 50;
  let previousD = 50;

  for (let index = 0; index < bars.length; index += 1) {
    if (index + 1 < rsvWindow) {
      result.push({ k: null, d: null, j: null });
      continue;
    }

    const windowBars = bars.slice(index + 1 - rsvWindow, index + 1);
    const highestHigh = Math.max(...windowBars.map((bar) => bar.high));
    const lowestLow = Math.min(...windowBars.map((bar) => bar.low));
    const priceRange = highestHigh - lowestLow;
    const rawStochasticValue = priceRange === 0 ? 50 : ((bars[index].close - lowestLow) / priceRange) * 100;
    const currentK = ((kSmoothing - 1) * previousK + rawStochasticValue) / kSmoothing;
    const currentD = ((dSmoothing - 1) * previousD + currentK) / dSmoothing;
    const currentJ = 3 * currentK - 2 * currentD;

    result.push({ k: currentK, d: currentD, j: currentJ });
    previousK = currentK;
    previousD = currentD;
  }

  return result;
}

export function computeRsiSeries(closes: number[], window = 14): (number | null)[] {
  const result: (number | null)[] = Array(closes.length).fill(null);
  if (closes.length <= window) {
    return result;
  }

  let avgGain = 0;
  let avgLoss = 0;
  for (let index = 1; index <= window; index += 1) {
    const change = closes[index] - closes[index - 1];
    avgGain += Math.max(change, 0);
    avgLoss += Math.max(-change, 0);
  }
  avgGain /= window;
  avgLoss /= window;

  result[window] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let index = window + 1; index < closes.length; index += 1) {
    const change = closes[index] - closes[index - 1];
    avgGain = (avgGain * (window - 1) + Math.max(change, 0)) / window;
    avgLoss = (avgLoss * (window - 1) + Math.max(-change, 0)) / window;
    result[index] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }

  return result;
}

export function buildChartPoints(data: OhlcBar[]): ChartPoint[] {
  const closes = data.map((bar) => bar.close);
  const bollingerBandsSeries = calculateBollingerBandsSeries(closes, 20, 2);
  const rsiSeries = computeRsiSeries(closes);

  return data.map((bar, index) => {
    const bollingerBands = bollingerBandsSeries[index];
    return {
      ...bar,
      date: new Date(bar.timestamp).toLocaleDateString(),
      ma20: bollingerBands.middle,
      bollUpper: bollingerBands.upper,
      bollMiddle: bollingerBands.middle,
      bollLower: bollingerBands.lower,
      rsi: rsiSeries[index],
    };
  });
}

export function deriveOhlcBar(
  bar: Partial<OhlcBar> & { timestamp: string; close: number },
): OhlcBar {
  const close = bar.close;
  return {
    timestamp: bar.timestamp,
    open: bar.open ?? close,
    high: bar.high ?? close,
    low: bar.low ?? close,
    close,
    volume: bar.volume,
  };
}
