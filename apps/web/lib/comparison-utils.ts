export type ComparisonBar = {
  timestamp: string;
  close: number | null | undefined;
};

export type ComparisonInstrument = {
  id: string;
  symbol: string;
  name: string;
  market?: string | null;
  bars: ComparisonBar[];
};

export type NormalizedComparisonPoint = {
  timestamp: string;
  [instrumentId: string]: number | string | null;
};

export type ComparisonSummary = {
  id: string;
  symbol: string;
  name: string;
  market?: string | null;
  startClose: number;
  latestClose: number;
  percentChange: number;
  volatility: number | null;
};

export type CorrelationCell = {
  leftInstrumentId: string;
  rightInstrumentId: string;
  value: number | null;
};

type ComparableBar = {
  timestamp: string;
  close: number;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function getComparableBars(instrument: ComparisonInstrument): ComparableBar[] {
  return instrument.bars
    .filter((bar): bar is ComparableBar => Boolean(bar.timestamp) && isFiniteNumber(bar.close))
    .sort((leftBar, rightBar) => leftBar.timestamp.localeCompare(rightBar.timestamp));
}

export function normalizeComparisonSeries(instrument: ComparisonInstrument): Array<{ timestamp: string; value: number }> {
  const comparableBars = getComparableBars(instrument);
  const firstBarWithPrice = comparableBars.find((bar) => bar.close !== 0);

  if (firstBarWithPrice === undefined) {
    return [];
  }

  const baseClose = firstBarWithPrice.close;
  return comparableBars.map((bar) => ({
    timestamp: bar.timestamp,
    value: (bar.close / baseClose) * 100,
  }));
}

export function buildNormalizedComparisonChartData(
  instruments: ComparisonInstrument[],
): NormalizedComparisonPoint[] {
  const pointsByTimestamp = new Map<string, NormalizedComparisonPoint>();

  for (const instrument of instruments) {
    const normalizedSeries = normalizeComparisonSeries(instrument);

    for (const point of normalizedSeries) {
      const existingPoint = pointsByTimestamp.get(point.timestamp) ?? { timestamp: point.timestamp };
      existingPoint[instrument.id] = Number(point.value.toFixed(4));
      pointsByTimestamp.set(point.timestamp, existingPoint);
    }
  }

  return Array.from(pointsByTimestamp.values()).sort((leftPoint, rightPoint) =>
    String(leftPoint.timestamp).localeCompare(String(rightPoint.timestamp)),
  );
}

export function calculatePercentChange(instrument: ComparisonInstrument): number | null {
  const comparableBars = getComparableBars(instrument);
  const firstBar = comparableBars[0];
  const latestBar = comparableBars.at(-1);

  if (firstBar === undefined || latestBar === undefined || firstBar.close === 0) {
    return null;
  }

  return (latestBar.close - firstBar.close) / firstBar.close;
}

export function calculateVolatility(instrument: ComparisonInstrument): number | null {
  const comparableBars = getComparableBars(instrument);
  if (comparableBars.length < 3) {
    return null;
  }

  const returns: number[] = [];
  for (let barIndex = 1; barIndex < comparableBars.length; barIndex += 1) {
    const previousClose = comparableBars[barIndex - 1].close;
    const currentClose = comparableBars[barIndex].close;
    if (previousClose !== 0) {
      returns.push((currentClose - previousClose) / previousClose);
    }
  }

  if (returns.length < 2) {
    return null;
  }

  const averageReturn = returns.reduce((total, value) => total + value, 0) / returns.length;
  const variance =
    returns.reduce((total, value) => total + (value - averageReturn) ** 2, 0) / (returns.length - 1);

  return Math.sqrt(variance);
}

export function calculateComparisonSummaries(instruments: ComparisonInstrument[]): ComparisonSummary[] {
  return instruments.flatMap((instrument) => {
    const comparableBars = getComparableBars(instrument);
    const firstBar = comparableBars[0];
    const latestBar = comparableBars.at(-1);
    const percentChange = calculatePercentChange(instrument);

    if (firstBar === undefined || latestBar === undefined || percentChange === null) {
      return [];
    }

    return [
      {
        id: instrument.id,
        symbol: instrument.symbol,
        name: instrument.name,
        market: instrument.market,
        startClose: firstBar.close,
        latestClose: latestBar.close,
        percentChange,
        volatility: calculateVolatility(instrument),
      },
    ];
  });
}

export function calculatePearsonCorrelation(
  leftInstrument: ComparisonInstrument,
  rightInstrument: ComparisonInstrument,
): number | null {
  const leftBarsByTimestamp = new Map(
    getComparableBars(leftInstrument).map((bar) => [bar.timestamp, bar.close]),
  );
  const alignedPairs = getComparableBars(rightInstrument).flatMap((rightBar) => {
    const leftClose = leftBarsByTimestamp.get(rightBar.timestamp);
    return leftClose === undefined ? [] : [{ leftClose, rightClose: rightBar.close }];
  });

  if (alignedPairs.length < 2) {
    return null;
  }

  const leftAverage = alignedPairs.reduce((total, pair) => total + pair.leftClose, 0) / alignedPairs.length;
  const rightAverage = alignedPairs.reduce((total, pair) => total + pair.rightClose, 0) / alignedPairs.length;

  let covariance = 0;
  let leftVariance = 0;
  let rightVariance = 0;

  for (const pair of alignedPairs) {
    const leftDeviation = pair.leftClose - leftAverage;
    const rightDeviation = pair.rightClose - rightAverage;
    covariance += leftDeviation * rightDeviation;
    leftVariance += leftDeviation ** 2;
    rightVariance += rightDeviation ** 2;
  }

  if (leftVariance === 0 || rightVariance === 0) {
    return null;
  }

  return covariance / Math.sqrt(leftVariance * rightVariance);
}

export function buildCorrelationMatrix(instruments: ComparisonInstrument[]): CorrelationCell[] {
  const matrixCells: CorrelationCell[] = [];

  for (const leftInstrument of instruments) {
    for (const rightInstrument of instruments) {
      matrixCells.push({
        leftInstrumentId: leftInstrument.id,
        rightInstrumentId: rightInstrument.id,
        value:
          leftInstrument.id === rightInstrument.id
            ? 1
            : calculatePearsonCorrelation(leftInstrument, rightInstrument),
      });
    }
  }

  return matrixCells;
}

function formatReportNumber(value: number | null): string {
  if (value === null) {
    return "--";
  }

  return value.toFixed(2);
}

function formatReportPercent(value: number | null): string {
  if (value === null) {
    return "--";
  }

  const formattedPercent = `${Math.abs(value * 100).toFixed(2)}%`;
  if (value > 0) {
    return `+${formattedPercent}`;
  }
  if (value < 0) {
    return `-${formattedPercent}`;
  }
  return formattedPercent;
}

function formatCorrelationValue(value: number | null | undefined): string {
  return value === null || value === undefined ? "--" : value.toFixed(3);
}

export type ComparisonReportLabels = {
  title: string;
  generatedAt: string;
  selectedInstruments: string;
  summaryMetrics: string;
  correlationMatrix: string;
  instrument: string;
  name: string;
  market: string;
  startClose: string;
  latestClose: string;
  intervalReturn: string;
  volatility: string;
};

const DEFAULT_COMPARISON_REPORT_LABELS: ComparisonReportLabels = {
  title: "Comparison analysis report",
  generatedAt: "Generated at",
  selectedInstruments: "Selected instruments",
  summaryMetrics: "Summary metrics",
  correlationMatrix: "Correlation matrix",
  instrument: "Instrument",
  name: "Name",
  market: "Market",
  startClose: "Start close",
  latestClose: "Latest close",
  intervalReturn: "Interval return",
  volatility: "Volatility",
};

export function buildComparisonReportText({
  selectedInstruments,
  summaries,
  correlationMatrix,
  generatedAtIso = new Date().toISOString(),
  labels = DEFAULT_COMPARISON_REPORT_LABELS,
}: {
  selectedInstruments: ComparisonInstrument[];
  summaries: ComparisonSummary[];
  correlationMatrix: CorrelationCell[];
  generatedAtIso?: string;
  labels?: ComparisonReportLabels;
}): string {
  const summaryLines = summaries.map((summary) =>
    [
      summary.symbol,
      summary.name,
      summary.market ?? "--",
      formatReportNumber(summary.startClose),
      formatReportNumber(summary.latestClose),
      formatReportPercent(summary.percentChange),
      formatReportPercent(summary.volatility),
    ].join("\t"),
  );

  const correlationHeader = [labels.instrument, ...selectedInstruments.map((instrument) => instrument.symbol)].join("\t");
  const correlationRows = selectedInstruments.map((leftInstrument) => {
    const rowValues = selectedInstruments.map((rightInstrument) => {
      const cell = correlationMatrix.find(
        (matrixCell) =>
          matrixCell.leftInstrumentId === leftInstrument.id &&
          matrixCell.rightInstrumentId === rightInstrument.id,
      );
      return formatCorrelationValue(cell?.value);
    });

    return [leftInstrument.symbol, ...rowValues].join("\t");
  });

  return [
    labels.title,
    `${labels.generatedAt}: ${generatedAtIso}`,
    "",
    `${labels.selectedInstruments}:`,
    ...selectedInstruments.map((instrument) =>
      `- ${instrument.symbol} ${instrument.name}${instrument.market ? ` (${instrument.market})` : ""}`,
    ),
    "",
    `${labels.summaryMetrics}:`,
    [
      labels.instrument,
      labels.name,
      labels.market,
      labels.startClose,
      labels.latestClose,
      labels.intervalReturn,
      labels.volatility,
    ].join("\t"),
    ...summaryLines,
    "",
    `${labels.correlationMatrix}:`,
    correlationHeader,
    ...correlationRows,
  ].join("\n");
}
