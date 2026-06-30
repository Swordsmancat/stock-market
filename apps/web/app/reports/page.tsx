type DailyReportPayload = {
  as_of?: string;
  content_markdown?: string;
  citations?: string[];
};

type DailyReportHistoryPayload = {
  items: Array<{
    as_of: string;
    content_markdown: string;
    citations?: string[];
  }>;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const defaultSymbol = "AAPL";

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

export default async function ReportsPage() {
  const [latestReport, reportHistory] = await Promise.all([
    fetchOptionalJson<DailyReportPayload>(`/reports/${defaultSymbol}/daily/latest`, {}),
    fetchOptionalJson<DailyReportHistoryPayload>(`/reports/${defaultSymbol}/daily/history?limit=5`, {
      items: [],
    }),
  ]);
  const latestCitations = latestReport.citations ?? [];

  return (
    <main>
      <h1>报告中心</h1>
      <section>
        <h2>{defaultSymbol} 最新日报</h2>
        {latestReport.content_markdown ? (
          <>
            <p>报告日期：{latestReport.as_of}</p>
            <p>{latestReport.content_markdown}</p>
            {latestCitations.length > 0 ? (
              <>
                <h3>引用来源</h3>
                <ul>
                  {latestCitations.map((citation) => (
                    <li key={citation}>{renderCitation(citation)}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </>
        ) : (
          <p>暂无最新日报。</p>
        )}
      </section>
      <section>
        <h2>历史日报</h2>
        {reportHistory.items.length > 0 ? (
          <ul>
            {reportHistory.items.map((report) => (
              <li key={report.as_of}>
                {report.as_of} - {report.content_markdown}
              </li>
            ))}
          </ul>
        ) : (
          <p>暂无历史日报。</p>
        )}
      </section>
    </main>
  );
}
