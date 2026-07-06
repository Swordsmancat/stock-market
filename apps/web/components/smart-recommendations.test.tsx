import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SmartRecommendations } from "./smart-recommendations";

vi.mock("@/src/i18n/routing", () => ({
  Link: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

afterEach(() => {
  cleanup();
});

const recommendation = {
  symbol: "AAPL",
  type: "breakout" as const,
  title: "AAPL 突破20日均线",
  reason: "价格重新站上关键均线，短线动能改善。",
  confidence: 0.82,
  timestamp: "2026-07-03T10:00:00Z",
  data: { close: 102 },
};

it("does not claim realtime recommendations without supporting metadata", () => {
  render(<SmartRecommendations recommendations={[recommendation]} status="ok" provider="yfinance" source="database" />);

  expect(screen.queryByText(/实时推荐/)).not.toBeInTheDocument();
  expect(screen.queryByText(/实时技术信号/)).not.toBeInTheDocument();
  expect(screen.getByText(/基于可用数据的技术信号/)).toBeInTheDocument();
  expect(screen.getByText("provider: yfinance")).toBeInTheDocument();
  expect(screen.getByText("source: database")).toBeInTheDocument();
});

it("renders recommendation diagnostics when the provider reports gaps", () => {
  render(
    <SmartRecommendations
      recommendations={[recommendation]}
      diagnostics={[
        {
          code: "PROVIDER_ERROR",
          status: "provider_error",
          provider: "akshare",
          source: "recommendations",
          message: "provider returned no usable rows",
        },
      ]}
    />,
  );

  expect(screen.getByText("推荐诊断")).toBeInTheDocument();
  expect(screen.getByText(/PROVIDER_ERROR/)).toBeInTheDocument();
  expect(screen.getByText(/provider: akshare/)).toBeInTheDocument();
  expect(screen.getByText(/provider returned no usable rows/)).toBeInTheDocument();
});
