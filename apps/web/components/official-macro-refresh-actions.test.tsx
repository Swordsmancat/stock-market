import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { routerRefreshMock } = vi.hoisted(() => ({
  routerRefreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: routerRefreshMock,
  }),
}));

import {
  OfficialMacroRefreshActions,
  type OfficialMacroRefreshActionsLabels,
} from "./official-macro-refresh-actions";

const labels: OfficialMacroRefreshActionsLabels = {
  dryRunAction: "Run dry-run",
  dryRunRunning: "Checking...",
  writeAction: "Write observations",
  writeRunning: "Writing...",
  writeStoresObservation: "Write refresh stores audited local observations.",
  resultDryRun: "Dry-run complete",
  resultWrite: "Write refresh complete",
  resultObservations: "Observations: {count}",
  resultFetched: "Fetched: {count}",
  resultSkipped: "Skipped: {count}",
  resultCodes: "Codes: {codes}",
  resultLatestAsOf: "Latest as-of: {date}",
  resultCacheCleared: "Cache cleared: {count}",
  diagnosticsTitle: "Diagnostics",
  diagnosticsEmpty: "No provider diagnostics.",
  failed: "Refresh failed.",
  unavailableShort: "N/A",
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  routerRefreshMock.mockReset();
});

it("runs a dry-run refresh without refreshing the page", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "ok",
        provider: "fred",
        dry_run: true,
        observations: 1,
        fetched: 2,
        skipped: 1,
        codes: ["us_10y_yield"],
        latest_as_of: "2026-07-01",
        diagnostics: ["FRED DGS10 skipped 1 missing or invalid observations."],
        cache: { market_overview_cleared: 0 },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  render(
    <OfficialMacroRefreshActions
      endpoint="/api/market-indicators/official-refresh/fred"
      defaultPayload={{ series: "all", latest_only: true }}
      labels={labels}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Run dry-run" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith("/api/market-indicators/official-refresh/fred", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ series: "all", latest_only: true, dry_run: true }),
    });
  });
  expect(await screen.findByText("Dry-run complete")).toBeInTheDocument();
  expect(screen.getByText("Observations: 1")).toBeInTheDocument();
  expect(screen.getByText("Fetched: 2")).toBeInTheDocument();
  expect(screen.getByText("Skipped: 1")).toBeInTheDocument();
  expect(screen.getByText("Codes: us_10y_yield")).toBeInTheDocument();
  expect(screen.getByText("Latest as-of: 2026-07-01")).toBeInTheDocument();
  expect(screen.getByText("Cache cleared: 0")).toBeInTheDocument();
  expect(screen.getByText("FRED DGS10 skipped 1 missing or invalid observations.")).toBeInTheDocument();
  expect(routerRefreshMock).not.toHaveBeenCalled();
});

it("runs a write refresh and refreshes server-rendered coverage", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "ok",
        provider: "world_bank",
        dry_run: false,
        observations: 3,
        fetched: 6,
        skipped: 0,
        codes: ["buffett_indicator_us", "buffett_indicator_cn", "buffett_indicator_hk"],
        latest_as_of: "2024-12-31",
        diagnostics: [],
        cache: { market_overview_cleared: 4 },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  render(
    <OfficialMacroRefreshActions
      endpoint="/api/market-indicators/official-refresh/world-bank"
      defaultPayload={{ target: "all", latest_only: true }}
      labels={labels}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Write observations" }));

  expect(await screen.findByText("Write refresh complete")).toBeInTheDocument();
  expect(screen.getByText("Observations: 3")).toBeInTheDocument();
  expect(screen.getByText("Cache cleared: 4")).toBeInTheDocument();
  expect(screen.getByText("No provider diagnostics.")).toBeInTheDocument();
  expect(routerRefreshMock).toHaveBeenCalledOnce();
});

it("shows sanitized refresh failures without refreshing the page", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        detail: {
          status: "error",
          provider: "fred",
          message: "FRED API key is not configured.",
        },
      }),
      { status: 503, headers: { "content-type": "application/json" } },
    ),
  );
  render(
    <OfficialMacroRefreshActions
      endpoint="/api/market-indicators/official-refresh/fred"
      defaultPayload={{ series: "all", latest_only: true }}
      labels={labels}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Write observations" }));

  expect(await screen.findByText("FRED API key is not configured.")).toBeInTheDocument();
  expect(routerRefreshMock).not.toHaveBeenCalled();
});
