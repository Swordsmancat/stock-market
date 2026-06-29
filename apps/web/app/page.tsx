const instruments = [
  { symbol: "600519", name: "Kweichow Moutai", market: "A股" },
  { symbol: "0700", name: "Tencent Holdings", market: "港股" },
  { symbol: "AAPL", name: "Apple Inc.", market: "美股" },
];

export default function HomePage() {
  return (
    <main>
      <h1>股票分析平台</h1>
      <section>
        <h2>市场概览</h2>
        <ul>
          {instruments.map((item) => (
            <li key={item.symbol}>
              {item.market} - {item.symbol} - {item.name}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
