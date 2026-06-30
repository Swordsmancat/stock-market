type PortfolioPayload = {
  name?: string;
  base_currency?: string;
  source: string;
  positions: Array<{
    symbol: string;
    market: string;
    quantity: number;
    avg_cost: number;
    latest_price: number;
    market_value: number;
  }>;
  recommendation?: {
    status: string;
    risk_summary: string;
    actions: Array<{
      symbol: string;
      action: string;
      target_weight: number;
      reason: string;
    }>;
  };
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchOptionalJson<T>(path: string, fallback: T): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
  if (!response.ok) {
    return fallback;
  }
  return response.json() as Promise<T>;
}

export default async function PortfoliosPage() {
  const portfolio = await fetchOptionalJson<PortfolioPayload>("/portfolios/demo", {
    name: "Demo Portfolio",
    base_currency: "USD",
    source: "unavailable",
    positions: [],
    recommendation: {
      status: "unavailable",
      risk_summary: "暂无模拟组合建议。",
      actions: [],
    },
  });
  const totalValue = portfolio.positions.reduce((sum, position) => sum + position.market_value, 0);
  const recommendation = portfolio.recommendation;

  return (
    <main>
      <h1>模拟组合</h1>
      <section>
        <h2>{portfolio.name ?? "Demo Portfolio"}</h2>
        <p>
          基准币种：{portfolio.base_currency ?? "USD"}，组合市值：{totalValue}，来源：
          {portfolio.source}
        </p>
      </section>
      <section>
        <h2>持仓</h2>
        {portfolio.positions.length > 0 ? (
          <ul>
            {portfolio.positions.map((position) => (
              <li key={position.symbol}>
                {position.market} - {position.symbol}，数量：{position.quantity}，成本：
                {position.avg_cost}，最新价：{position.latest_price}，市值：
                {position.market_value}
              </li>
            ))}
          </ul>
        ) : (
          <p>暂无持仓数据。</p>
        )}
      </section>
      <section>
        <h2>AI 调仓建议</h2>
        <p>
          状态：{recommendation?.status ?? "unavailable"}，风险摘要：
          {recommendation?.risk_summary ?? "暂无模拟组合建议。"}
        </p>
        {recommendation?.actions.length ? (
          <ul>
            {recommendation.actions.map((action) => (
              <li key={`${action.symbol}-${action.action}`}>
                {action.symbol}：{action.action}，目标权重：{action.target_weight}，理由：
                {action.reason}
              </li>
            ))}
          </ul>
        ) : (
          <p>暂无调仓动作。</p>
        )}
      </section>
    </main>
  );
}
