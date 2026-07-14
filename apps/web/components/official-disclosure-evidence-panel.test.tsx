import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { OfficialDisclosureEvidencePanel } from "./official-disclosure-evidence-panel";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

const labels = {
  title: "Official disclosure document evidence",
  description: "Watchlist disclosure coverage",
  maintenanceSummary: "Disclosure ingestion operations",
  batchAction: "Ingest watchlist disclosures",
  batchPending: "Queueing...",
  batchQueued: "Batch queued",
  monitorAction: "Run incremental monitor",
  monitorPending: "Queueing monitor...",
  monitoringTitle: "Incremental monitoring freshness",
  monitoringDescription: "Durable cursors and retry backoff.",
  freshSymbols: "Fresh symbols",
  staleSymbols: "Stale symbols",
  backoffSymbols: "Retry backoff",
  newDisclosures: "New on last run",
  lastSuccess: "Last success",
  openTaskRun: "Open task run",
  eligibleSymbols: "Eligible symbols",
  metadataRows: "Metadata rows",
  extractedDocuments: "Extracted documents",
  citableSections: "Citable sections",
  symbol: "Symbol",
  disclosure: "Disclosure",
  publishedAt: "Published",
  status: "Status",
  sections: "Sections",
  action: "Action",
  ingestAction: "Ingest PDF",
  ingestPending: "Ingesting...",
  officialSource: "Official source",
  emptyTitle: "No disclosures",
  emptyDescription: "Add an A-share.",
  loadFailedTitle: "Unavailable",
  loadFailedDescription: "Could not load.",
  operationFailed: "Operation failed.",
  metadataBoundary: "Metadata boundary",
  contentBoundary: "Content boundary",
  watchlistOnly: "Watchlist only",
  statusLabels: { metadata_only: "Metadata only", extracted: "Text extracted" },
  freshnessLabels: { fresh: "Fresh", stale: "Stale", backoff: "Retry backoff", never: "Never" },
};

const payload = {
  status: "ok",
  summary: {
    eligible_symbol_count: 1,
    metadata_disclosure_count: 1,
    extracted_document_count: 0,
    citable_section_count: 0,
  },
  monitoring: {
    enabled: true,
    interval_minutes: 60,
    freshness_sla_hours: 24,
    summary: {
      fresh_symbol_count: 1,
      stale_symbol_count: 0,
      backoff_symbol_count: 0,
      never_succeeded_symbol_count: 0,
      new_disclosure_count: 2,
    },
    items: [{
      symbol: "000001",
      freshness: "fresh",
      last_success_at: "2026-07-13T08:00:00+00:00",
      last_new_disclosure_count: 2,
    }],
  },
  items: [{
    id: "11111111-2222-3333-4444-555555555555",
    symbol: "000001",
    title: "2025 Annual Report",
    published_at: "2026-03-21T00:00:00+00:00",
    source_url: "https://www.cninfo.com.cn/disclosure/1",
    citation_id: "official_disclosure:11111111-2222-3333-4444-555555555555",
    status: "metadata_only",
    section_count: 0,
    content_citable: false,
  }],
};

function getMaintenanceDetails(): HTMLDetailsElement {
  const summary = screen.getByText(labels.maintenanceSummary).closest("summary");
  const details = summary?.closest("details");
  if (!details) throw new Error("Disclosure maintenance details not found");
  return details;
}

function openMaintenanceDetails(): HTMLDetailsElement {
  const details = getMaintenanceDetails();
  expect(details).not.toHaveAttribute("open");
  fireEvent.click(details.querySelector("summary")!);
  expect(details).toHaveAttribute("open");
  return details;
}

beforeEach(() => {
  vi.restoreAllMocks();
  refresh.mockReset();
});

afterEach(() => cleanup());

it("keeps disclosure rows visible while grouping mutation controls in closed maintenance", () => {
  render(<OfficialDisclosureEvidencePanel initialPayload={payload} loadFailed={false} labels={labels} />);

  const maintenanceDetails = getMaintenanceDetails();
  const disclosureLink = screen.getByRole("link", { name: "2025 Annual Report" });
  expect(maintenanceDetails).not.toHaveAttribute("open");
  expect(maintenanceDetails).not.toContainElement(disclosureLink);
  expect(
    within(maintenanceDetails).getByRole("button", {
      name: "Ingest watchlist disclosures",
      hidden: true,
    }),
  ).toBeInTheDocument();
  expect(
    within(maintenanceDetails).getByRole("button", {
      name: "Run incremental monitor",
      hidden: true,
    }),
  ).toBeInTheDocument();
  expect(
    within(maintenanceDetails).getByRole("button", { name: "Ingest PDF", hidden: true }),
  ).toBeInTheDocument();
});

it("queues a bounded watchlist batch and links the task run", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "dispatched", task_run: { id: "task-123" } })),
  );
  render(<OfficialDisclosureEvidencePanel initialPayload={payload} loadFailed={false} labels={labels} />);
  openMaintenanceDetails();

  fireEvent.click(screen.getByRole("button", { name: "Ingest watchlist disclosures" }));

  expect(await screen.findByText("Batch queued")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open task run" })).toHaveAttribute("href", "/task-runs/task-123");
  expect(fetchMock).toHaveBeenCalledWith("/api/official-disclosures/watchlist-ingest", expect.objectContaining({
    method: "POST",
    body: JSON.stringify({ lookback_days: 30, max_documents: 20 }),
  }));
  expect(refresh).toHaveBeenCalled();
});

it("shows freshness and queues an incremental monitor", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "dispatched", task_run: { id: "task-monitor" } })),
  );
  render(<OfficialDisclosureEvidencePanel initialPayload={payload} loadFailed={false} labels={labels} />);
  openMaintenanceDetails();

  expect(screen.getByText("Incremental monitoring freshness")).toBeInTheDocument();
  expect(screen.getByText("New on last run")).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Run incremental monitor" }));

  await waitFor(() => expect(refresh).toHaveBeenCalled());
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/official-disclosures/watchlist-monitor",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ lookback_days: 30, max_documents: 20 }),
    }),
  );
});

it("ingests one exact disclosure and refreshes server state", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok", action: "created" })),
  );
  render(<OfficialDisclosureEvidencePanel initialPayload={payload} loadFailed={false} labels={labels} />);
  openMaintenanceDetails();

  fireEvent.click(screen.getByRole("button", { name: "Ingest PDF" }));

  await waitFor(() => expect(refresh).toHaveBeenCalled());
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/official-disclosures/11111111-2222-3333-4444-555555555555/ingest-document",
    { method: "POST" },
  );
});

it("keeps failed loading distinct from an empty watchlist", () => {
  render(<OfficialDisclosureEvidencePanel initialPayload={null} loadFailed labels={labels} />);
  expect(screen.getByText("Unavailable")).toBeInTheDocument();
  expect(screen.queryByText("No disclosures")).not.toBeInTheDocument();
});
