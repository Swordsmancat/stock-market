type Instrument = {
  symbol: string;
  name: string;
  market: string;
};

type InstrumentsPayload = {
  items: Instrument[];
};

type BarsPayload = {
  source: string;
  items: Array<{ close: number }>;
};

type ReportPayload = {
  content_markdown: string;
};

type PortfolioPayload = {
  source: string;
  positions: Array<{ market_value: number }>;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }
  return response.json() as Promise<T>;
}

export default async function HomePage() {
  const instrumentsPayload = await fetchJson<InstrumentsPayload>("/instruments");
  const primaryInstrument = instrumentsPayload.items[0];
  const [barsPayload, reportPayload, portfolioPayload] = await Promise.all([
    fetchJson<BarsPayload>(
      `/market-data/${primaryInstrument.symbol}/bars?timeframe=1d&start=2026-01-01&end=2026-01-02`,
    ),
    fetchJson<ReportPayload>(
      `/reports/${primaryInstrument.symbol}/stock?start=2026-01-01&end=2026-01-02`,
    ),
    fetchJson<PortfolioPayload>("/portfolios/demo"),
  ]);

  const latestClose = barsPayload.items.at(-1)?.close;
  const portfolioValue = portfolioPayload.positions[0]?.market_value;

  return (
    <main>
      <h1>股票分析平台</h1>
      <section>
        <h2>市场概览</h2>
        <ul>
          {instrumentsPayload.items.map((item) => (
            <li key={item.symbol}>
              {item.market} - {item.symbol} - {item.name}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2>行情快照</h2>
        <p>
          {primaryInstrument.symbol} 最新收盘价：{latestClose}，来源：{barsPayload.source}
        </p>
      </section>
      <section>
        <h2>AI 报告</h2>
        <p>{reportPayload.content_markdown}</p>
      </section>
      <section>
        <h2>模拟组合</h2>
        <p>
          模拟组合市值：{portfolioValue}，来源：{portfolioPayload.source}
        </p>
      </section>
    </main>
  );
}
