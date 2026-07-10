import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { routerRefreshMock } = vi.hoisted(() => ({
  routerRefreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: routerRefreshMock }),
}));

import {
  MarketDailyEvidencePanel,
  type MarketDailyEvidencePanelLabels,
  type MarketDailyEvidencePayload,
} from "./market-daily-evidence-panel";

const labels: MarketDailyEvidencePanelLabels = {
  title: "Stored market daily evidence",
  description: "Persist provider-normalized daily market rows before AI citation.",
  refreshAction: "Refresh today's market evidence",
  refreshing: "Refreshing market evidence...",
  totalRows: "Stored rows",
  latestImport: "Latest import",
  latestTradeDate: "Latest trade date",
  citationsTitle: "Recent citation IDs",
  emptyTitle: "No stored market daily evidence",
  emptyDescription: "Run refresh to import provider-verified rows.",
  loadFailedTitle: "Market daily evidence is unavailable",
  loadFailedDescription: "Could not load stored market daily evidence.",
  persistedOnly: "Only persisted rows are citable",
  notAdvice: "Not investment advice",
  refreshSuccess: "Refresh complete",
  insertedCount: "Inserted: {count}",
  updatedCount: "Updated: {count}",
  skippedCount: "Skipped: {count}",
  diagnosticsTitle: "Diagnostics",
  diagnosticsEmpty: "No import diagnostics.",
  refreshFailed: "Market evidence refresh failed.",
  unavailableShort: "N/A",
  eventTypeLabels: {
    stock_fund_flow: "Stock fund flow",
    hot_sector: "Hot sector",
  },
};

function payload(total = 2): MarketDailyEvidencePayload {
  return {
    summary: {
      total,
      returned: total,
      counts_by_event_type: { stock_fund_flow: 1, hot_sector: 1 },
      latest_imported_at: "2026-07-10T08:00:00+00:00",
      latest_trade_date: "2026-07-10",
    },
    citations: [
      {
        id: "market_daily_event:stock_fund_flow:000001:2026-07-10",
        label: "Stock fund flow: Ping An Bank",
        source: "market_daily_evidence",
        source_type: "market_daily_event",
      },
    ],
    safety: { persisted_rows_only: true, not_investment_advice: true },
  };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  routerRefreshMock.mockReset();
});

it("renders stored counts, latest import metadata, and citation IDs", () => {
  render(<MarketDailyEvidencePanel initialPayload={payload()} loadFailed={false} labels={labels} />);

  expect(screen.getByText("Stored market daily evidence")).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(screen.getByText("Stock fund flow: 1")).toBeInTheDocument();
  expect(screen.getByText("Hot sector: 1")).toBeInTheDocument();
  expect(screen.getByText("2026-07-10T08:00:00+00:00")).toBeInTheDocument();
  expect(
    screen.getByText("market_daily_event:stock_fund_flow:000001:2026-07-10"),
  ).toBeInTheDocument();
  expect(screen.getByText("Only persisted rows are citable")).toBeInTheDocument();
});

it("refreshes today's default event types and replaces the visible summary", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch");
  fetchMock
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "ok",
          inserted: 3,
          updated: 1,
          skipped: 2,
          diagnostics: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(payload(6)), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

  render(<MarketDailyEvidencePanel initialPayload={payload()} loadFailed={false} labels={labels} />);
  fireEvent.click(screen.getByRole("button", { name: "Refresh today's market evidence" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/market-daily-evidence", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ market: "CN", limit: 20 }),
    });
  });
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    "/api/market-daily-evidence?limit=12&citable_only=true",
    { cache: "no-store" },
  );
  expect(await screen.findByText("Refresh complete")).toBeInTheDocument();
  expect(screen.getByText("Inserted: 3")).toBeInTheDocument();
  expect(screen.getByText("Updated: 1")).toBeInTheDocument();
  expect(screen.getByText("Skipped: 2")).toBeInTheDocument();
  expect(screen.getByText("6")).toBeInTheDocument();
  expect(routerRefreshMock).toHaveBeenCalledOnce();
});

it("shows sanitized import errors without replacing stored evidence", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: { errors: ["Provider is not configured."] } }), {
      status: 422,
      headers: { "content-type": "application/json" },
    }),
  );

  render(<MarketDailyEvidencePanel initialPayload={payload()} loadFailed={false} labels={labels} />);
  fireEvent.click(screen.getByRole("button", { name: "Refresh today's market evidence" }));

  expect(await screen.findByText("Provider is not configured.")).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(routerRefreshMock).not.toHaveBeenCalled();
});
