import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { DataTrustBadge } from "./data-trust-badge";
import { createDataTrustSignal } from "@/lib/data-trust";

afterEach(() => {
  cleanup();
});

it("renders a compact trust badge with accessible details", () => {
  const signal = createDataTrustSignal({ status: "ok", freshness: "fresh", provider: "yfinance", source: "database" });

  render(<DataTrustBadge signal={signal} />);

  expect(screen.getByText("新鲜")).toBeInTheDocument();
  expect(screen.getByLabelText(/provider: yfinance/)).toBeInTheDocument();
  expect(screen.getByLabelText(/source: database/)).toBeInTheDocument();
});

it("renders a summary with visible provider and source details", () => {
  const signal = createDataTrustSignal({ status: "degraded", provider: "mock", source: "static_fixture", no_data_reason: "provider unsupported" });

  render(<DataTrustBadge signal={signal} mode="summary" />);

  expect(screen.getByText("模拟")).toBeInTheDocument();
  expect(screen.getByText("provider: mock")).toBeInTheDocument();
  expect(screen.getByText("source: static_fixture")).toBeInTheDocument();
  expect(screen.getByText("provider unsupported")).toBeInTheDocument();
});
