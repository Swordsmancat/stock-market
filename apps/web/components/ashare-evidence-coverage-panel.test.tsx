import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it, vi } from "vitest";

import enMessages from "../messages/en.json";
import { AshareEvidenceCoveragePanel, type EvidenceCoveragePayload } from "./ashare-evidence-coverage-panel";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

const coverage: EvidenceCoveragePayload = {
  status: "needs_attention",
  market: "CN",
  provider: "akshare",
  as_of: "2026-07-10",
  universe: { active_count: 5200, exchange_counts: { BSE: 250, SSE: 2300, SZSE: 2650 } },
  evidence: {
    daily_bars: {
      ready_count: 5000, missing_count: 200, total_count: 5200, coverage_ratio: 0.962,
      threshold: 0.95, passes_threshold: true,
      by_exchange: { BSE: { ready_count: 230, total_count: 250, coverage_ratio: 0.92 }, SSE: { ready_count: 2250, total_count: 2300, coverage_ratio: 0.978 }, SZSE: { ready_count: 2520, total_count: 2650, coverage_ratio: 0.951 } },
    },
    technical_indicators: {
      ready_count: 4800, missing_count: 400, total_count: 5200, coverage_ratio: 0.923,
      threshold: 0.9, passes_threshold: true,
      by_exchange: { BSE: { ready_count: 220, total_count: 250, coverage_ratio: 0.88 }, SSE: { ready_count: 2150, total_count: 2300, coverage_ratio: 0.935 }, SZSE: { ready_count: 2430, total_count: 2650, coverage_ratio: 0.917 } },
    },
    fundamentals: {
      ready_count: 3900, missing_count: 1300, total_count: 5200, coverage_ratio: 0.75,
      threshold: 0.8, passes_threshold: false,
      by_exchange: { BSE: { ready_count: 150, total_count: 250, coverage_ratio: 0.6 }, SSE: { ready_count: 1750, total_count: 2300, coverage_ratio: 0.761 }, SZSE: { ready_count: 2000, total_count: 2650, coverage_ratio: 0.755 } },
    },
  },
  latest_run: null,
};

function renderPanel(payload: EvidenceCoveragePayload = coverage) {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <AshareEvidenceCoveragePanel initialCoverage={payload} />
    </NextIntlClientProvider>,
  );
}

it("shows evidence and exchange coverage, then starts a fixed canary", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({ backfill: { id: "run-1" } })))
    .mockResolvedValueOnce(new Response(JSON.stringify(coverage)));

  renderPanel();

  expect(screen.getByText("5,200")).toBeInTheDocument();
  expect(screen.getByRole("progressbar", { name: "Coverage for Daily bars" })).toHaveAttribute("aria-valuenow", "96");
  expect(screen.getByText("75% / 80%")).toBeInTheDocument();
  expect(screen.getByText("92% (230/250)")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Start 50-stock canary" }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/ingestion/a-share-evidence-backfills", expect.objectContaining({ method: "POST" }));
  expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
    run_kind: "canary", market: "CN", provider: "akshare",
    evidence_kinds: ["daily_bars", "technical_indicators", "fundamentals"],
    batch_size: 25, cohort_size: 50,
  });
  expect(await screen.findByText("The evidence backfill was created.")).toBeInTheDocument();
});

it("requires confirmation for a full baseline and active-run cancellation", async () => {
  const activeCoverage: EvidenceCoveragePayload = {
    ...coverage,
    latest_run: {
      id: "run-active", task_run_id: "task-1", run_kind: "baseline", status: "running",
      phase: "daily_bars", cursor: 25, phase_total: 100, processed_count: 25,
      heartbeat_at: "2026-07-10T08:00:00Z", retry: {}, diagnostics: [],
    },
  };
  const confirmMock = vi.spyOn(window, "confirm").mockReturnValue(false);
  const fetchMock = vi.spyOn(globalThis, "fetch");

  renderPanel(activeCoverage);
  expect(screen.getByRole("link", { name: "Open task run" })).toHaveAttribute("href", "/task-runs/task-1");
  expect(screen.getByRole("progressbar", { name: "Current phase progress" })).toHaveAttribute("aria-valuenow", "25");
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(confirmMock).toHaveBeenCalledOnce();
  expect(fetchMock).not.toHaveBeenCalled();
});

it("does not start a full baseline when confirmation is declined", () => {
  const confirmMock = vi.spyOn(window, "confirm").mockReturnValue(false);
  const fetchMock = vi.spyOn(globalThis, "fetch");

  renderPanel();
  fireEvent.click(screen.getByRole("button", { name: "Start full baseline" }));

  expect(confirmMock).toHaveBeenCalledOnce();
  expect(fetchMock).not.toHaveBeenCalled();
});

it("polls active runs and leaves terminal runs idle", async () => {
  vi.useFakeTimers();
  const activeCoverage: EvidenceCoveragePayload = {
    ...coverage,
    latest_run: {
      id: "active", run_kind: "baseline", status: "running", phase: "daily_bars",
      cursor: 1, phase_total: 10, processed_count: 1, retry: {}, diagnostics: [],
    },
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(activeCoverage)));
  const view = renderPanel(activeCoverage);

  await vi.advanceTimersByTimeAsync(5_000);
  expect(fetchMock).toHaveBeenCalledWith("/api/stock-selection/evidence-coverage", { cache: "no-store" });

  fetchMock.mockClear();
  view.unmount();
  renderPanel({ ...coverage, latest_run: { ...activeCoverage.latest_run!, status: "succeeded" } });
  await vi.advanceTimersByTimeAsync(5_000);
  expect(fetchMock).not.toHaveBeenCalled();
});
