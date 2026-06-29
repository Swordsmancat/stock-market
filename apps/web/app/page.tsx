import { AnalysisRefreshButton } from "./AnalysisRefreshButton";
import { IngestionButton } from "./IngestionButton";

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

type IndicatorsPayload = {
  source: string;
  indicators: {
    ma?: number;
    rsi?: number;
  };
};

type NewsPayload = {
  source: string;
  items: Array<{
    title: string;
    sentiment: string;
    confidence: number;
  }>;
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
  const [barsPayload, reportPayload, portfolioPayload, indicatorsPayload, newsPayload] =
    await Promise.all([
      fetchJson<BarsPayload>(
        `/market-data/${primaryInstrument.symbol}/bars?timeframe=1d&start=2026-01-01&end=2026-01-02`,
      ),
      fetchJson<ReportPayload>(
        `/reports/${primaryInstrument.symbol}/stock?start=2026-01-01&end=2026-01-02`,
      ),
      fetchJson<PortfolioPayload>("/portfolios/demo"),
      fetchJson<IndicatorsPayload>(`/indicators/${primaryInstrument.symbol}`),
      fetchJson<NewsPayload>(`/news/${primaryInstrument.symbol}`),
    ]);

  const latestClose = barsPayload.items.at(-1)?.close;
  const portfolioValue = portfolioPayload.positions[0]?.market_value;
  const ma = indicatorsPayload.indicators.ma;
  const rsi = indicatorsPayload.indicators.rsi;
  const latestNews = newsPayload.items[0];

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
        <h2>数据采集</h2>
        <p>触发一次开发用 Mock 行情采集，并写入后端数据库。</p>
        <IngestionButton market={primaryInstrument.market} start="2026-01-01" end="2026-01-02" />
        <p>一键刷新当前股票的行情、技术指标、新闻舆情和 AI 报告。</p>
        <AnalysisRefreshButton
          symbol={primaryInstrument.symbol}
          market={primaryInstrument.market}
          start="2026-01-01"
          end="2026-01-20"
          maWindow={3}
        />
      </section>
      <section>
        <h2>技术指标</h2>
        <p>
          MA：{ma}，RSI：{rsi}，来源：{indicatorsPayload.source}
        </p>
      </section>
      <section>
        <h2>新闻舆情</h2>
        {latestNews ? (
          <p>
            新闻：{latestNews.title}，情绪：{latestNews.sentiment}，置信度：
            {latestNews.confidence}
          </p>
        ) : (
          <p>暂无新闻舆情数据，来源：{newsPayload.source}</p>
        )}
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
