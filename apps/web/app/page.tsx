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
  citations?: string[];
};

type DailyReportPayload = {
  as_of?: string;
  content_markdown?: string;
  citations?: string[];
};

type DailyReportHistoryPayload = {
  items: Array<{
    as_of: string;
    content_markdown: string;
  }>;
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

type TaskRunPayload = {
  status: string;
  duration_ms?: number;
  result_json?: {
    item_count?: number;
  };
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed: ${path}`);
  }
  return response.json() as Promise<T>;
}

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

export default async function HomePage() {
  const instrumentsPayload = await fetchJson<InstrumentsPayload>("/instruments");
  const primaryInstrument = instrumentsPayload.items[0];
  const [
    barsPayload,
    reportPayload,
    dailyReportPayload,
    dailyReportHistoryPayload,
    portfolioPayload,
    indicatorsPayload,
    fundamentalsPayload,
    newsPayload,
    taskRunPayload,
  ] =
    await Promise.all([
      fetchJson<BarsPayload>(
        `/market-data/${primaryInstrument.symbol}/bars?timeframe=1d&start=2026-01-01&end=2026-01-02`,
      ),
      fetchJson<ReportPayload>(
        `/reports/${primaryInstrument.symbol}/stock?start=2026-01-01&end=2026-01-02`,
      ),
      fetchOptionalJson<DailyReportPayload>(`/reports/${primaryInstrument.symbol}/daily/latest`, {}),
      fetchOptionalJson<DailyReportHistoryPayload>(
        `/reports/${primaryInstrument.symbol}/daily/history?limit=5`,
        { items: [] },
      ),
      fetchJson<PortfolioPayload>("/portfolios/demo"),
      fetchOptionalJson<IndicatorsPayload>(`/indicators/${primaryInstrument.symbol}`, {
        source: "unavailable",
        indicators: {},
      }),
      fetchOptionalJson<FundamentalsPayload>(`/fundamentals/${primaryInstrument.symbol}`, {
        source: "unavailable",
        item: null,
      }),
      fetchOptionalJson<NewsPayload>(
        `/news/${primaryInstrument.symbol}`,
        {
          source: "unavailable",
          items: [],
        },
      ),
      fetchOptionalJson<TaskRunPayload>(
        "/task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis",
        { status: "unknown" },
      ),
    ]);

  const latestClose = barsPayload.items.at(-1)?.close;
  const portfolioValue = portfolioPayload.positions[0]?.market_value;
  const ma = indicatorsPayload.indicators.ma;
  const rsi = indicatorsPayload.indicators.rsi;
  const fundamentalSummary = fundamentalsPayload.item?.summary;
  const latestNews = newsPayload.items[0];
  const reportCitations = reportPayload.citations ?? [];
  const dailyReportCitations = dailyReportPayload.citations ?? [];

  return (
    <main>
      <h1>股票分析平台</h1>
      <section>
        <h2>市场概览</h2>
        <ul>
          {instrumentsPayload.items.map((item) => (
            <li key={item.symbol}>
              <a href={`/instruments/${item.symbol}`}>
                {item.market} - {item.symbol} - {item.name}
              </a>
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
        <h2>AI 报告</h2>
        <p>{reportPayload.content_markdown}</p>
        {reportCitations.length > 0 ? (
          <>
            <h3>报告引用</h3>
            <ul>
              {reportCitations.map((citation) => (
                <li key={citation}>{renderCitation(citation)}</li>
              ))}
            </ul>
          </>
        ) : null}
      </section>
      <section>
        <h2>每日报告</h2>
        {dailyReportPayload.content_markdown ? (
          <>
            <p>最新日报日期：{dailyReportPayload.as_of}</p>
            <p>{dailyReportPayload.content_markdown}</p>
            {dailyReportCitations.length > 0 ? (
              <>
                <h3>日报引用</h3>
                <ul>
                  {dailyReportCitations.map((citation) => (
                    <li key={citation}>{renderCitation(citation)}</li>
                  ))}
                </ul>
              </>
            ) : null}
            <h3>历史日报</h3>
            <ul>
              {dailyReportHistoryPayload.items.map((item) => (
                <li key={item.as_of}>历史日报：{item.as_of}</li>
              ))}
            </ul>
          </>
        ) : (
          <p>暂无持久化每日报告</p>
        )}
      </section>
      <section>
        <h2>自动任务状态</h2>
        <p>
          最近日报调度：{taskRunPayload.status}，处理股票数：
          {taskRunPayload.result_json?.item_count ?? 0}，耗时：{taskRunPayload.duration_ms ?? 0}ms
        </p>
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
