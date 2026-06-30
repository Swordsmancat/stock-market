type InstrumentsPayload = {
  items: Array<{
    symbol: string;
    name: string;
    market: string;
  }>;
};

type BarsPayload = {
  source: string;
  items: Array<{ close: number }>;
};

type IndicatorsPayload = {
  source: string;
  indicators: {
    ma?: number;
    rsi?: number;
  };
};

type FundamentalsPayload = {
  source: string;
  item?: {
    summary: string;
  } | null;
};

type NewsPayload = {
  source: string;
  items: Array<{
    title: string;
    sentiment: string;
    confidence: number;
  }>;
};

type ReportPayload = {
  content_markdown?: string;
  citations?: string[];
};

type InstrumentPageProps = {
  params: Promise<{ symbol: string }>;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchOptionalJson<T>(path: string, fallback: T): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    return fallback;
  }
  return response.json() as Promise<T>;
}

function citationUrl(citation: string): string | null {
  return citation.match(/https?:\/\/\S+/)?.[0] ?? null;
}

function renderCitation(citation: string) {
  const url = citationUrl(citation);
  if (url === null) {
    return citation;
  }

  return <a href={url}>{citation}</a>;
}

export default async function InstrumentDetailPage({ params }: InstrumentPageProps) {
  const { symbol: rawSymbol } = await params;
  const symbol = decodeURIComponent(rawSymbol).toUpperCase();
  const instrumentsPayload = await fetchOptionalJson<InstrumentsPayload>("/instruments", {
    items: [],
  });
  const instrument = instrumentsPayload.items.find((item) => item.symbol === symbol);
  const [
    barsPayload,
    indicatorsPayload,
    fundamentalsPayload,
    newsPayload,
    reportPayload,
  ] = await Promise.all([
    fetchOptionalJson<BarsPayload>(
      `/market-data/${symbol}/bars?timeframe=1d&start=2026-01-01&end=2026-01-20`,
      { source: "unavailable", items: [] },
    ),
    fetchOptionalJson<IndicatorsPayload>(`/indicators/${symbol}`, {
      source: "unavailable",
      indicators: {},
    }),
    fetchOptionalJson<FundamentalsPayload>(`/fundamentals/${symbol}`, {
      source: "unavailable",
      item: null,
    }),
    fetchOptionalJson<NewsPayload>(
      `/news/${symbol}`,
      {
        source: "unavailable",
        items: [],
      },
    ),
    fetchOptionalJson<ReportPayload>(
      `/reports/${symbol}/stock?start=2026-01-01&end=2026-01-20`,
      {},
    ),
  ]);

  const latestClose = barsPayload.items.at(-1)?.close;
  const ma = indicatorsPayload.indicators.ma;
  const rsi = indicatorsPayload.indicators.rsi;
  const fundamentalSummary = fundamentalsPayload.item?.summary;
  const latestNews = newsPayload.items[0];
  const citations = reportPayload.citations ?? [];

  return (
    <main>
      <h1>{symbol} 个股详情</h1>
      <section>
        <h2>标的信息</h2>
        <p>
          {instrument?.market ?? "未知市场"} - {symbol} - {instrument?.name ?? "未知标的"}
        </p>
      </section>
      <section>
        <h2>行情快照</h2>
        {latestClose !== undefined ? (
          <p>
            最新收盘价：{latestClose}，来源：{barsPayload.source}
          </p>
        ) : (
          <p>暂无行情数据，来源：{barsPayload.source}</p>
        )}
      </section>
      <section>
        <h2>技术指标</h2>
        {ma !== undefined || rsi !== undefined ? (
          <p>
            MA：{ma ?? "暂无"}，RSI：{rsi ?? "暂无"}，来源：{indicatorsPayload.source}
          </p>
        ) : (
          <p>暂无技术指标数据，来源：{indicatorsPayload.source}</p>
        )}
      </section>
      <section>
        <h2>基本面指标</h2>
        {fundamentalSummary ? (
          <p>
            {fundamentalSummary}，来源：{fundamentalsPayload.source}
          </p>
        ) : (
          <p>暂无基本面指标数据，来源：{fundamentalsPayload.source}</p>
        )}
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
        <h2>AI 摘要</h2>
        {reportPayload.content_markdown ? (
          <>
            <p>{reportPayload.content_markdown}</p>
            {citations.length > 0 ? (
              <>
                <h3>引用来源</h3>
                <ul>
                  {citations.map((citation) => (
                    <li key={citation}>{renderCitation(citation)}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </>
        ) : (
          <p>暂无 AI 个股报告。</p>
        )}
      </section>
    </main>
  );
}
