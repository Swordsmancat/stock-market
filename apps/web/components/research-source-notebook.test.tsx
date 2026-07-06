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
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  render(<ResearchSourceNotebook labels={labels} initialNotes={[]} />);

  fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Buffett component source" } });
  fireEvent.change(screen.getByLabelText("Source name"), { target: { value: "World Bank" } });
  fireEvent.change(screen.getByLabelText("Source type"), { target: { value: "valuation_component" } });
  fireEvent.change(screen.getByLabelText("Source URL"), { target: { value: "https://example.com/gdp" } });
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
        symbols: ["aapl"],
        tags: ["macro"],
        as_of: null,
        published_at: null,
        excerpt: "Reviewed source excerpt.",
        note: "Calculation note.",
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
