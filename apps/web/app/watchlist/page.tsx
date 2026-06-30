type Instrument = {
  symbol: string;
  name: string;
  market: string;
  is_active?: boolean;
  alert_rules?: Record<string, unknown>;
};

type WatchlistPayload = {
  name: string;
  source: string;
  items: Instrument[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchOptionalJson<T>(path: string, fallback: T): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    return fallback;
  }
  return response.json() as Promise<T>;
}

export default async function WatchlistPage() {
  const watchlistPayload = await fetchOptionalJson<WatchlistPayload>("/watchlist", {
    name: "default",
    source: "unavailable",
    items: [],
  });
  const activeItems = watchlistPayload.items.filter((instrument) => instrument.is_active !== false);

  return (
    <main>
      <h1>关注列表</h1>
      <section>
        <h2>默认关注标的</h2>
        <p>
          列表：{watchlistPayload.name}，来源：{watchlistPayload.source}
        </p>
        {activeItems.length > 0 ? (
          <ul>
            {activeItems.map((instrument) => (
              <li key={instrument.symbol}>
                <a href={`/instruments/${instrument.symbol}`}>
                  {instrument.market} - {instrument.symbol} - {instrument.name}
                </a>
                <p>
                  提醒规则：
                  {instrument.alert_rules && Object.keys(instrument.alert_rules).length > 0
                    ? "已配置"
                    : "未配置，等待后续价格/指标提醒。"}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p>暂无关注标的。</p>
        )}
      </section>
    </main>
  );
}
