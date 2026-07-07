import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SmartRecommendations, type SmartRecommendationsLabels } from "./smart-recommendations";

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

const englishLabels: SmartRecommendationsLabels = {
  title: "Research candidates",
  description: "Technical signal candidates from available data: 1",
  loadingMessage: "Loading research candidates...",
  emptyMessage: "No research candidates yet. Keep monitoring the available data.",
  safetyNotice:
    "These are unbacktested technical signals from available data. Realtime status depends on the upstream provider, and historical evaluation requires sample size, window returns, and diagnostics. This is not investment advice.",
  diagnosticsTitle: "Recommendation diagnostics",
  confidence: "Confidence",
  sourceStatus: "Status",
  sourceProvider: "Provider",
  source: "Source",
  generatedAt: "Generated at",
  signalBreakout: "Breakout",
  signalVolumeAnomaly: "Volume anomaly",
  signalOversoldRebound: "Oversold rebound",
  signalStrongMomentum: "Strong momentum",
  signalUnknown: "Signal",
};

it("does not claim realtime recommendations without supporting metadata", () => {
  render(
    <SmartRecommendations
      locale="en"
      labels={englishLabels}
      recommendations={[recommendation]}
      status="ok"
      provider="yfinance"
      source="database"
    />,
  );

  expect(screen.queryByText(/实时推荐/)).not.toBeInTheDocument();
  expect(screen.queryByText(/实时技术信号/)).not.toBeInTheDocument();
  expect(screen.queryByText(/今日推荐/)).not.toBeInTheDocument();
  expect(screen.getByText("Research candidates")).toBeInTheDocument();
  expect(screen.getByText("Technical signal candidates from available data: 1")).toBeInTheDocument();
  expect(screen.getByText(/unbacktested technical signals/)).toBeInTheDocument();
  expect(screen.getByText("Provider: yfinance")).toBeInTheDocument();
  expect(screen.getByText("Source: database")).toBeInTheDocument();
  expect(screen.getByText("Breakout")).toBeInTheDocument();
  expect(screen.getByText("Confidence: 82%")).toBeInTheDocument();
});

it("renders recommendation diagnostics when the provider reports gaps", () => {
  render(
    <SmartRecommendations
      locale="en"
      labels={englishLabels}
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

  expect(screen.getByText("Recommendation diagnostics")).toBeInTheDocument();
  expect(screen.getByText(/PROVIDER_ERROR/)).toBeInTheDocument();
  expect(screen.getByText(/Provider: akshare/)).toBeInTheDocument();
  expect(screen.getByText(/provider returned no usable rows/)).toBeInTheDocument();
});
