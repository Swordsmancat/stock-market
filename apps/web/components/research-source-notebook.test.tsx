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
  ResearchSourceNotebook,
  type ResearchSourceNotebookLabels,
  type ResearchSourceNote,
} from "./research-source-notebook";

const labels: ResearchSourceNotebookLabels = {
  title: "Source notebook",
  description: "Collect reviewed source notes.",
  ingestionTitle: "Source ingestion hub",
  ingestionDescription: "Extract summary and clues.",
  acceptedFormats: "Accepted files: .txt, .md, .csv, .json.",
  extractAction: "Extract with AI",
  extracting: "Extracting...",
  extractFailed: "Source extraction failed.",
  extractionContentRequired: "Paste or upload source text before extraction.",
  applyExtraction: "Apply suggestions",
  extractionBoundary: "Extraction suggestions are collection notes only.",
  extractionStatusOk: "LLM extracted",
  extractionStatusFallback: "Fallback extraction",
  extractionStatusInvalid: "Needs source text",
  extractionModelLlm: "LLM",
  extractionModelFallback: "Deterministic",
  extractionFallbackReason: "Fallback reason: {reason}",
  extractionSummaryTitle: "Source summary",
  extractionIndicatorsTitle: "Key indicators",
  extractionCitationCluesTitle: "Citation clues",
  extractionFollowUpsTitle: "Follow-up questions",
  extractionSuggestedFieldsTitle: "Suggested metadata",
  extractionDiagnosticsTitle: "Extraction diagnostics",
  selectedFile: "File: {name}",
  fileLabel: "Browser file",
  fileReadFailed: "File read failed.",
  titleLabel: "Title",
  titlePlaceholder: "Buffett Indicator review",
  sourceNameLabel: "Source name",
  sourceNamePlaceholder: "FRED",
  sourceTypeLabel: "Source type",
  sourceTypePlaceholder: "macro_indicator",
  sourceUrlLabel: "Source URL",
  sourceUrlPlaceholder: "https://...",
  sourceTargetLabel: "Source-readiness target",
  sourceTargetPlaceholder: "Unlinked collection note",
  targetIndicatorsLabel: "Target indicator codes",
  targetIndicatorsPlaceholder: "buffett_indicator_us",
  componentRoleLabel: "Component role",
  componentRoleGeneral: "General",
  componentRoleMarketCap: "Market cap source",
  componentRoleGdp: "GDP source",
  componentRoleCpi: "CPI source",
  componentRoleM2: "M2 source",
  componentRoleRate: "Rate source",
  componentRoleYieldSpread: "Yield-spread source",
  componentRoleFiling: "Filing note",
  componentRoleContext: "General context",
  symbolsLabel: "Symbols",
  symbolsPlaceholder: "AAPL",
  tagsLabel: "Tags",
  tagsPlaceholder: "macro",
  asOfLabel: "As of",
  publishedAtLabel: "Published at",
  excerptLabel: "Reviewed excerpt",
  excerptPlaceholder: "Paste excerpt",
  noteLabel: "Calculation note",
  notePlaceholder: "Record method",
  methodologyNoteLabel: "Methodology note",
  methodologyNotePlaceholder: "Record methodology",
  licenseNoteLabel: "License / usage note",
  licenseNotePlaceholder: "Record usage limits",
  aiFollowUpLabel: "AI follow-up",
  aiFollowUpPlaceholder: "Follow up",
  reviewStatusLabel: "Review status",
  statusDraft: "Draft",
  statusReviewed: "Reviewed",
  statusArchived: "Archived",
  citableLabel: "Allow AI citation",
  saveAction: "Save note",
  saving: "Saving...",
  clearAction: "Clear",
  saveSuccess: "Source note saved.",
  saveFailed: "Source note could not be saved.",
  contentRequired: "Required fields missing.",
  citableBoundary: "Draft notes stay collection notes.",
  recentTitle: "Recent source notes",
  loadFailed: "Source notebook entries could not be loaded.",
  noNotes: "No source notes match the current filters.",
  filterLabel: "Filter notes",
  filterPlaceholder: "Search notes",
  statusFilterLabel: "Status filter",
  allStatuses: "All statuses",
  citableOnlyLabel: "Citable",
  citableBadge: "AI-citable",
  collectionBadge: "Collection note",
  citationId: "Citation: {id}",
  sourceLink: "Source link",
  linkedSourceBadge: "Linked: {label}",
  targetIndicatorsBadge: "Target: {code}",
  componentRoleBadge: "Role: {role}",
  reviewChecklistTitle: "Review completeness",
  completenessSummary: "{score}/{total} checks",
  completenessComplete: "Complete",
  completenessPartial: "Partial",
  completenessMissing: "Missing",
  checklistSourceIdentity: "Source identity",
  checklistSourceUrlOrDocument: "URL or source document",
  checklistDateMetadata: "Date metadata",
  checklistExcerpt: "Reviewed excerpt",
  checklistMethodology: "Methodology note",
  checklistTargets: "Tags or indicator targets",
  checklistLicenseNote: "License / usage note",
  unavailableShort: "N/A",
};

const initialNotes: ResearchSourceNote[] = [
  {
    id: "note-1",
    title: "AAPL valuation source",
    source_name: "Manual notebook",
    source_type: "valuation_component",
    source_url: "https://example.com/aapl",
    symbols: ["AAPL"],
    tags: ["valuation"],
    excerpt: "Reviewed AAPL source excerpt.",
    note: "Use for Buffett Indicator comparison.",
    review_status: "reviewed",
    is_citable: true,
    citation_id: "research_source_note:note-1",
    retrieved_at: "2026-07-03T12:00:00+00:00",
    metadata: {
      source_id: "buffett_manual_valuation_components",
      source_label: "Buffett Indicator manual valuation components",
      source_category: "valuation",
      target_indicator_codes: ["buffett_indicator_us"],
      component_role: "gdp",
      methodology_note: "Reviewed GDP component.",
      license_note: "Public source for personal review.",
      review_checklist: {
        source_identity: true,
        source_url_or_document: true,
        date_metadata: true,
        excerpt: true,
        methodology: true,
        targets: true,
        license_note: true,
      },
      completeness: { score: 7, total: 7, status: "complete" },
    },
  },
];

const sourceTargets = [
  {
    id: "buffett_manual_valuation_components",
    label: "Buffett Indicator manual valuation components",
    category: "valuation",
    status: "needs_manual_seed",
    targetIndicatorCodes: ["buffett_indicator_us"],
  },
];

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  routerRefreshMock.mockReset();
});

it("renders saved notes with provenance, status, citation id, and safe source link", () => {
  render(<ResearchSourceNotebook labels={labels} initialNotes={initialNotes} />);

  expect(screen.getByText("AAPL valuation source")).toBeInTheDocument();
  expect(screen.getByText("Manual notebook / valuation_component")).toBeInTheDocument();
  expect(screen.getByText("AI-citable")).toBeInTheDocument();
  expect(screen.getByText("Linked: Buffett Indicator manual valuation components")).toBeInTheDocument();
  expect(screen.getByText("Target: buffett_indicator_us")).toBeInTheDocument();
  expect(screen.getByText("7/7 checks")).toBeInTheDocument();
  expect(screen.getByText("Complete")).toBeInTheDocument();
  expect(screen.getByText("Citation: research_source_note:note-1")).toBeInTheDocument();
  const sourceLink = screen.getByRole("link", { name: "Source link" });
  expect(sourceLink).toHaveAttribute("href", "https://example.com/aapl");
  expect(sourceLink).toHaveAttribute("target", "_blank");
  expect(sourceLink).toHaveAttribute("rel", "noreferrer");
});

it("reads a browser file into the editable excerpt field", async () => {
  render(<ResearchSourceNotebook labels={labels} initialNotes={[]} />);
  const file = new File(["Reviewed uploaded excerpt."], "buffett-note.md", { type: "text/markdown" });
  Object.defineProperty(file, "text", {
    value: () => Promise.resolve("Reviewed uploaded excerpt."),
  });

  fireEvent.change(screen.getByLabelText("Browser file"), {
    target: { files: [file] },
  });

  expect(await screen.findByDisplayValue("Reviewed uploaded excerpt.")).toBeInTheDocument();
  expect(screen.getByDisplayValue("buffett-note")).toBeInTheDocument();
  expect(screen.getByText("File: buffett-note.md")).toBeInTheDocument();
});

it("extracts source suggestions and applies them without making the draft citable", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "fallback",
        summary: "World Bank market cap and GDP source summary.",
        key_indicators: [
          {
            label: "Buffett Indicator",
            code: "buffett_indicator_us",
            reason: "Market cap and GDP were mentioned.",
          },
        ],
        citation_clues: [{ kind: "date", label: "As-of date", value: "2026-07-07" }],
        follow_up_questions: ["Verify component timing before import."],
        suggested_fields: {
          title: "Buffett source review",
          source_name: "World Bank",
          source_type: "valuation",
          tags: ["macro", "valuation"],
          target_indicator_codes: ["buffett_indicator_us"],
          methodology_note: "Review ratio calculation.",
          license_note: "Confirm public-source usage.",
          ai_follow_up: "Verify component timing before import.",
        },
        model: {
          provider: "deterministic",
          name: "source-ingestion-deterministic-fallback",
          used_llm: false,
          fallback_reason: "OpenAI-compatible LLM provider is not configured.",
        },
        diagnostics: [
          {
            code: "SOURCE_INGESTION_FALLBACK_USED",
            message: "Source extraction used deterministic fallback instead of an LLM answer.",
          },
        ],
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  render(<ResearchSourceNotebook labels={labels} initialNotes={[]} sourceTargets={sourceTargets} />);

  fireEvent.change(screen.getByLabelText("Source-readiness target"), {
    target: { value: "buffett_manual_valuation_components" },
  });
  fireEvent.change(screen.getByLabelText("Reviewed excerpt"), {
    target: { value: "World Bank market cap and GDP source." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Extract with AI" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith("/api/source-ingestion/extract", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        content: "World Bank market cap and GDP source.",
        filename: null,
        source_url: null,
        source_id: "buffett_manual_valuation_components",
        source_label: "Buffett Indicator manual valuation components",
        source_category: "valuation",
        target_indicator_codes: ["buffett_indicator_us"],
        component_role: null,
        locale: "en",
      }),
    });
  });
  expect(await screen.findByText("World Bank market cap and GDP source summary.")).toBeInTheDocument();
  expect(screen.getByText("Buffett Indicator / buffett_indicator_us")).toBeInTheDocument();
  expect(screen.getByText(/Fallback reason:/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Apply suggestions" }));

  expect(screen.getByDisplayValue("Buffett source review")).toBeInTheDocument();
  expect(screen.getByDisplayValue("World Bank")).toBeInTheDocument();
  expect(screen.getByDisplayValue("valuation")).toBeInTheDocument();
  expect(screen.getByDisplayValue("macro, valuation")).toBeInTheDocument();
  expect(screen.getByDisplayValue("Review ratio calculation.")).toBeInTheDocument();
  expect(screen.getByDisplayValue("Confirm public-source usage.")).toBeInTheDocument();
  expect(screen.getByDisplayValue("Verify component timing before import.")).toBeInTheDocument();
  expect(screen.getByLabelText("Allow AI citation")).not.toBeChecked();
});

it("saves reviewed citable notes through the browser proxy and refreshes server data", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        id: "note-2",
        title: "Buffett component source",
        source_name: "World Bank",
        source_type: "valuation_component",
        source_url: "https://example.com/gdp",
        symbols: ["AAPL"],
        tags: ["macro"],
        excerpt: "Reviewed source excerpt.",
        note: "Calculation note.",
        review_status: "reviewed",
        is_citable: true,
        citation_id: "research_source_note:note-2",
        metadata: {
          source_id: "buffett_manual_valuation_components",
          source_label: "Buffett Indicator manual valuation components",
          source_category: "valuation",
          target_indicator_codes: ["buffett_indicator_us"],
          component_role: "gdp",
          methodology_note: "Reviewed methodology.",
          license_note: "Public source.",
          review_checklist: {
            source_identity: true,
            source_url_or_document: true,
            date_metadata: false,
            excerpt: true,
            methodology: true,
            targets: true,
            license_note: true,
          },
          completeness: { score: 6, total: 7, status: "partial" },
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  render(<ResearchSourceNotebook labels={labels} initialNotes={[]} sourceTargets={sourceTargets} />);

  fireEvent.change(screen.getByLabelText("Source-readiness target"), {
    target: { value: "buffett_manual_valuation_components" },
  });
  fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Buffett component source" } });
  fireEvent.change(screen.getByLabelText("Source name"), { target: { value: "World Bank" } });
  fireEvent.change(screen.getByLabelText("Source type"), { target: { value: "valuation_component" } });
  fireEvent.change(screen.getByLabelText("Source URL"), { target: { value: "https://example.com/gdp" } });
  fireEvent.change(screen.getByLabelText("Component role"), { target: { value: "gdp" } });
  fireEvent.change(screen.getByLabelText("Methodology note"), { target: { value: "Reviewed methodology." } });
  fireEvent.change(screen.getByLabelText("License / usage note"), { target: { value: "Public source." } });
  fireEvent.change(screen.getByLabelText("Symbols"), { target: { value: "aapl" } });
  fireEvent.change(screen.getByLabelText("Tags"), { target: { value: "macro" } });
  fireEvent.change(screen.getByLabelText("Reviewed excerpt"), { target: { value: "Reviewed source excerpt." } });
  fireEvent.change(screen.getByLabelText("Calculation note"), { target: { value: "Calculation note." } });
  fireEvent.click(screen.getByLabelText("Allow AI citation"));
  fireEvent.click(screen.getByRole("button", { name: "Save note" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith("/api/research-source-notes", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        title: "Buffett component source",
        source_name: "World Bank",
        source_type: "valuation_component",
        source_url: "https://example.com/gdp",
        source_id: "buffett_manual_valuation_components",
        source_label: "Buffett Indicator manual valuation components",
        source_category: "valuation",
        target_indicator_codes: ["buffett_indicator_us"],
        component_role: "gdp",
        symbols: ["aapl"],
        tags: ["macro"],
        as_of: null,
        published_at: null,
        excerpt: "Reviewed source excerpt.",
        note: "Calculation note.",
        methodology_note: "Reviewed methodology.",
        license_note: "Public source.",
        ai_follow_up: null,
        review_status: "reviewed",
        is_citable: true,
        metadata: {},
      }),
    });
  });
  expect(await screen.findByText("Source note saved.")).toBeInTheDocument();
  expect(screen.getByText("Buffett component source")).toBeInTheDocument();
  expect(routerRefreshMock).toHaveBeenCalledOnce();
});

it("keeps nonmatching collection notes out of citable-only filters", () => {
  render(
    <ResearchSourceNotebook
      labels={labels}
      initialNotes={[
        ...initialNotes,
        {
          id: "note-2",
          title: "Draft filing search",
          source_name: "SEC",
          source_type: "filing_note",
          source_url: "https://example.com/sec",
          symbols: [],
          tags: ["filing"],
          review_status: "draft",
          is_citable: false,
        },
      ]}
    />,
  );

  fireEvent.click(screen.getByLabelText("Citable"));

  expect(screen.getByText("AAPL valuation source")).toBeInTheDocument();
  expect(screen.queryByText("Draft filing search")).not.toBeInTheDocument();
});
