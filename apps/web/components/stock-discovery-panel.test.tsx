import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { StockDiscoveryPanel } from "./stock-discovery-panel";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const profiles = {
  status: "ok",
  items: [
    {
      id: "balanced_research",
      label: "Balanced research",
      description: "Balances valuation, growth, trend, and liquidity.",
      criteria: {
        max_pe_ratio: 35,
        min_revenue_growth: 0.05,
        require_price_above_ma: true,
      },
    },
  ],
};

const universeStatus = {
  status: "ok",
  active_instrument_count: 5200,
  managed_instrument_count: 5198,
  latest_sync: { created_at: "2026-07-10T08:00:00+00:00", total_count: 5198 },
};

it("keeps discovery visible while universe maintenance starts collapsed", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "degraded",
        shortlist: [
          {
            symbol: "600519",
            name: "Kweichow Moutai",
            score: 1,
            matched_rules: [{ code: "max_pe_ratio", status: "matched" }],
          },
        ],
        shortlist_count: 1,
        explanation_markdown: "### Shortlist\n`600519` matched stored evidence.",
        citations: [{ id: "bars_1d:600519:2026-07-10", symbol: "600519" }],
        diagnostics: [],
        coverage: {
          candidate_count: 5200,
          evaluated_count: 5200,
          matched_count: 1,
          evidence: { daily_bars: { coverage_ratio: 0.92, missing_count: 416 } },
        },
        model: { used_llm: false, name: "deterministic-stock-discovery-v1" },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  const handoff = vi.fn();
  window.addEventListener("stock-discovery:select-symbol", handoff);
  Element.prototype.scrollIntoView = vi.fn();

  render(
    <StockDiscoveryPanel
      initialProfiles={profiles}
      initialUniverseStatus={universeStatus}
    />,
  );

  const maintenanceSummary = screen
    .getByText("Universe status", { selector: "span" })
    .closest("summary")!;
  const maintenanceDetails = maintenanceSummary.closest("details");
  const refreshButton = screen.getByRole("button", {
    name: "Refresh A-share universe",
  });
  const discoveryButton = screen.getByRole("button", {
    name: "Run full-universe discovery",
  });

  expect(maintenanceDetails).not.toHaveAttribute("open");
  expect(maintenanceDetails).toContainElement(screen.getByText("5,200"));
  expect(maintenanceDetails).toContainElement(refreshButton);
  expect(refreshButton).not.toBeVisible();
  expect(discoveryButton).toBeVisible();
  expect(screen.getByText("Balanced research")).toBeInTheDocument();
  expect(screen.getByText("Visible, editable criteria")).toBeInTheDocument();
  fireEvent.click(discoveryButton);

  await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
  const [, request] = fetchMock.mock.calls[0];
  expect(request).toMatchObject({ method: "POST" });
  expect(JSON.parse(String(request?.body))).toMatchObject({
    profile_id: "balanced_research",
    market: "CN",
    overrides: {
      max_pe_ratio: 35,
      min_revenue_growth: 0.05,
      require_price_above_ma: true,
    },
  });
  expect(await screen.findByText("600519")).toBeInTheDocument();
  expect(screen.getByText("daily bars: 92%")).toBeInTheDocument();
  expect(screen.getByText("bars_1d:600519:2026-07-10")).toBeInTheDocument();
  expect(screen.getByText("Deterministic explanation")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Use in desk" }));
  expect(handoff).toHaveBeenCalledOnce();
  window.removeEventListener("stock-discovery:select-symbol", handoff);
});

it("queues an A-share universe refresh and links to its TaskRun", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ task_run: { id: "universe-task-1" } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(universeStatus), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

  render(
    <StockDiscoveryPanel
      initialProfiles={profiles}
      initialUniverseStatus={universeStatus}
    />,
  );
  const maintenanceSummary = screen
    .getByText("Universe status", { selector: "span" })
    .closest("summary")!;
  const maintenanceDetails = maintenanceSummary.closest("details");
  expect(maintenanceDetails).not.toHaveAttribute("open");

  fireEvent.click(maintenanceSummary);
  expect(maintenanceDetails).toHaveAttribute("open");

  const refreshButton = screen.getByRole("button", {
    name: "Refresh A-share universe",
  });
  expect(refreshButton).toBeVisible();
  fireEvent.click(refreshButton);

  expect(await screen.findByText(/universe refresh task was created/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open task run" })).toHaveAttribute(
    "href",
    "/task-runs/universe-task-1",
  );
  expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/ingestion/instrument-universe", {
    method: "POST",
  });
  expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/stock-selection/universe-status", {
    cache: "no-store",
  });
});

it("renders explicit empty and failed discovery states", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "no_matches",
          shortlist: [],
          coverage: { evaluated_count: 5200, matched_count: 0, evidence: {} },
          explanation_markdown: "No locally evidenced candidate matched.",
          citations: [],
          diagnostics: [],
          model: { used_llm: false },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "provider unavailable" }), {
        status: 503,
        headers: { "content-type": "application/json" },
      }),
    );

  render(
    <StockDiscoveryPanel
      initialProfiles={profiles}
      initialUniverseStatus={universeStatus}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Run full-universe discovery" }));
  expect(await screen.findByText(/No candidate matched all selected criteria/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Run full-universe discovery" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("provider unavailable");
  expect(fetchMock).toHaveBeenCalledTimes(2);
});
