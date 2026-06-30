type Instrument = {
  symbol: string;
  name: string;
  market: string;
};

type InstrumentsPayload = {
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
  const instrumentsPayload = await fetchOptionalJson<InstrumentsPayload>("/instruments", {
    items: [],
  });

  return (
    <main>
      <h1>关注列表</h1>
      <section>
        <h2>默认关注标的</h2>
        {instrumentsPayload.items.length > 0 ? (
          <ul>
            {instrumentsPayload.items.map((instrument) => (
              <li key={instrument.symbol}>
                <a href={`/instruments/${instrument.symbol}`}>
                  {instrument.market} - {instrument.symbol} - {instrument.name}
                </a>
                <p>关键变化提醒：等待下一次自动日报刷新后更新。</p>
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
