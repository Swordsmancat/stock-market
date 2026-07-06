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
  EvidenceSeedImportReview,
  type EvidenceSeedImportReviewLabels,
} from "./evidence-seed-import-review";

const labels: EvidenceSeedImportReviewLabels = {
  title: "Import reviewed seed evidence",
  description: "Preview seed content before import.",
  fileLabel: "Local seed file",
  fileButton: "Select file",
  selectedFile: "File: {name}",
  pasteLabel: "Seed content",
  pastePlaceholder: "Paste JSON or CSV",
  formatLabel: "Format",
  formatAuto: "Auto",
  formatJson: "JSON",
  formatCsv: "CSV",
  previewAction: "Preview",
  previewing: "Previewing...",
  importAction: "Import",
  importing: "Importing...",
  clearAction: "Clear",
  contentRequired: "Content required.",
  fileReadFailed: "File read failed.",
  previewFailed: "Preview failed.",
  importFailed: "Import failed.",
  importSuccess: "Import complete.",
  invalidNoImport: "No observations were imported.",
  overwriteWarning: "Confirm overwrite.",
  overwriteCheckbox: "I reviewed updates.",
  citationBoundary: "Rows become AI-citable only after confirmed import.",
  summaryRows: "Rows",
  summaryValid: "Valid",
  summaryInvalid: "Invalid",
  summaryInserts: "Inserts",
  summaryUpdates: "Updates",
  rowColumn: "Row",
  stateColumn: "State",
  intentColumn: "Intent",
  indicatorColumn: "Indicator",
  asOfColumn: "As of",
  valueColumn: "Value",
  sourceColumn: "Source",
  metadataColumn: "Metadata",
  errorsColumn: "Errors",
  stateValid: "Valid",
  stateInvalid: "Invalid",
  intentInsert: "Insert",
  intentUpdate: "Update",
  intentInvalid: "Invalid",
  metadataComplete: "Source + method",
  metadataMissing: "Metadata missing",
  noRows: "No rows.",
  returnToEvidence: "Review Evidence Center",
  unavailableShort: "N/A",
};

function validPreview(updates = 0) {
  return {
    status: "valid",
    can_import: true,
    format: "json",
    filename: "macro-seeds.json",
    summary: {
      rows: 1,
      valid_rows: 1,
      invalid_rows: 0,
      inserts: updates ? 0 : 1,
      updates,
      affected_codes: ["us_10y_yield"],
      latest_as_of: "2026-07-03",
    },
    rows: [
      {
        row_label: "row 1",
        status: "valid",
        intent: updates ? "update" : "insert",
        code: "us_10y_yield",
        name: "US 10Y Treasury Yield",
        category: "rates",
        region: "US",
        unit: "percent",
        as_of: "2026-07-03",
        value: "4.250000",
        source: "Audited seed: FRED DGS10",
        metadata: {
          source_present: true,
          method_present: true,
        },
        errors: [],
      },
    ],
    errors: [],
  };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  routerRefreshMock.mockReset();
});

it("previews pasted seed content and renders row-level intent", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(validPreview()), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  render(<EvidenceSeedImportReview labels={labels} />);

  fireEvent.change(screen.getByLabelText("Seed content"), {
    target: { value: "{\"observations\":[]}" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Preview" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith("/api/market-indicators/seeds/preview", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        content: "{\"observations\":[]}",
        format: "auto",
        filename: null,
      }),
    });
  });
  expect(await screen.findByText("US 10Y Treasury Yield")).toBeInTheDocument();
  expect(screen.getByText("Insert")).toBeInTheDocument();
  expect(screen.getByText("Source + method")).toBeInTheDocument();
});

it("renders invalid preview errors without enabling import", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "invalid",
        can_import: false,
        format: "json",
        filename: null,
        summary: {
          rows: 1,
          valid_rows: 0,
          invalid_rows: 1,
          inserts: 0,
          updates: 0,
          affected_codes: [],
          latest_as_of: null,
        },
        rows: [
          {
            row_label: "row 1",
            status: "invalid",
            intent: "invalid",
            code: "unknown_code",
            source: "Audited seed",
            metadata: {
              source_present: true,
              method_present: false,
            },
            errors: ["unknown indicator code"],
          },
        ],
        errors: [],
      }),
      {
        status: 200,
        headers: { "content-type": "application/json" },
      },
    ),
  );
  render(<EvidenceSeedImportReview labels={labels} />);

  fireEvent.change(screen.getByLabelText("Seed content"), {
    target: { value: "{\"observations\":[]}" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Preview" }));

  expect(await screen.findByText("No observations were imported.")).toBeInTheDocument();
  expect(screen.getByText("unknown indicator code")).toBeInTheDocument();
  expect(screen.getAllByText("unknown_code").length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();
});

it("reads a selected browser file into the paste area without uploading raw storage", async () => {
  render(<EvidenceSeedImportReview labels={labels} />);
  const fileContent = "{\"observations\":[]}";
  const file = new File([fileContent], "macro-seeds.json", { type: "application/json" });
  Object.defineProperty(file, "text", {
    value: () => Promise.resolve(fileContent),
  });

  fireEvent.change(screen.getByLabelText("Local seed file"), {
    target: { files: [file] },
  });

  expect(await screen.findByDisplayValue(fileContent)).toBeInTheDocument();
  expect(screen.getByText("File: macro-seeds.json")).toBeInTheDocument();
});

it("requires overwrite acknowledgement before importing update rows", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(validPreview(1)), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  render(<EvidenceSeedImportReview labels={labels} />);

  fireEvent.change(screen.getByLabelText("Seed content"), {
    target: { value: "{\"observations\":[]}" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Preview" }));

  expect(await screen.findByText("Update")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();

  fireEvent.click(screen.getByLabelText("I reviewed updates."));

  expect(screen.getByRole("button", { name: "Import" })).not.toBeDisabled();
});

it("imports a valid preview and refreshes the evidence page", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify(validPreview()), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "imported",
          observations: 1,
          codes: ["us_10y_yield"],
          latest_as_of: "2026-07-03",
          summary: { inserts: 1, updates: 0 },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
  render(<EvidenceSeedImportReview labels={labels} />);

  fireEvent.change(screen.getByLabelText("Seed content"), {
    target: { value: "{\"observations\":[]}" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Preview" }));
  expect(await screen.findByText("US 10Y Treasury Yield")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Import" }));

  expect(await screen.findByText(/Import complete/)).toBeInTheDocument();
  expect(routerRefreshMock).toHaveBeenCalledOnce();
  expect(fetchMock).toHaveBeenLastCalledWith("/api/market-indicators/seeds/import", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      content: "{\"observations\":[]}",
      format: "auto",
      filename: null,
      overwrite_acknowledged: false,
    }),
  });
});
