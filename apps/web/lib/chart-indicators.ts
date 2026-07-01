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

function rollingMean(values: number[], window: number): (number | null)[] {
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
  const ma20 = rollingMean(closes, 20);
  const std20 = rollingStd(closes, 20);
  const rsiSeries = computeRsiSeries(closes);

  return data.map((bar, index) => {
    const middle = ma20[index];
    const std = std20[index];
    return {
      ...bar,
      date: new Date(bar.timestamp).toLocaleDateString(),
      ma20: middle,
      bollUpper: middle !== null && std !== null ? middle + std * 2 : null,
      bollMiddle: middle,
      bollLower: middle !== null && std !== null ? middle - std * 2 : null,
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
