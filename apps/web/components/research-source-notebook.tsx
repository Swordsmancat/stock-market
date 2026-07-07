"use client";

import * as React from "react";
import { CheckCircle2, FileUp, Link2, NotebookPen, Save, Search, Sparkles, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export type ResearchSourceReviewChecklist = {
  source_identity?: boolean;
  source_url_or_document?: boolean;
  date_metadata?: boolean;
  excerpt?: boolean;
  methodology?: boolean;
  targets?: boolean;
  license_note?: boolean;
};

export type ResearchSourceCompleteness = {
  score?: number;
  total?: number;
  status?: "complete" | "partial" | "missing" | string;
};

export type ResearchSourceWorkflowMetadata = {
  source_id?: string | null;
  source_label?: string | null;
  source_category?: string | null;
  target_indicator_codes?: string[];
  component_role?: string | null;
  methodology_note?: string | null;
  license_note?: string | null;
  review_checklist?: ResearchSourceReviewChecklist;
  completeness?: ResearchSourceCompleteness;
  [key: string]: unknown;
};

export type ResearchSourceNote = {
  id: string;
  title: string;
  source_url?: string | null;
  source_name: string;
  source_type: string;
  symbols?: string[];
  tags?: string[];
  published_at?: string | null;
  as_of?: string | null;
  retrieved_at?: string | null;
  excerpt?: string | null;
  note?: string | null;
  ai_follow_up?: string | null;
  review_status: "draft" | "reviewed" | "archived" | string;
  is_citable: boolean;
  citation_id?: string | null;
  metadata?: ResearchSourceWorkflowMetadata;
  created_at?: string | null;
};

export type ResearchSourceTargetOption = {
  id: string;
  label: string;
  category: string;
  status?: string | null;
  targetIndicatorCodes?: string[];
};

export type ResearchSourceNotebookLabels = {
  title: string;
  description: string;
  ingestionTitle: string;
  ingestionDescription: string;
  acceptedFormats: string;
  extractAction: string;
  extracting: string;
  extractFailed: string;
  extractionContentRequired: string;
  applyExtraction: string;
  extractionBoundary: string;
  extractionStatusOk: string;
  extractionStatusFallback: string;
  extractionStatusInvalid: string;
  extractionModelLlm: string;
  extractionModelFallback: string;
  extractionFallbackReason: string;
  extractionSummaryTitle: string;
  extractionIndicatorsTitle: string;
  extractionCitationCluesTitle: string;
  extractionFollowUpsTitle: string;
  extractionSuggestedFieldsTitle: string;
  extractionDiagnosticsTitle: string;
  selectedFile: string;
  fileLabel: string;
  fileReadFailed: string;
  titleLabel: string;
  titlePlaceholder: string;
  sourceNameLabel: string;
  sourceNamePlaceholder: string;
  sourceTypeLabel: string;
  sourceTypePlaceholder: string;
  sourceUrlLabel: string;
  sourceUrlPlaceholder: string;
  sourceTargetLabel: string;
  sourceTargetPlaceholder: string;
  targetIndicatorsLabel: string;
  targetIndicatorsPlaceholder: string;
  componentRoleLabel: string;
  componentRoleGeneral: string;
  componentRoleMarketCap: string;
  componentRoleGdp: string;
  componentRoleCpi: string;
  componentRoleM2: string;
  componentRoleRate: string;
  componentRoleYieldSpread: string;
  componentRoleFiling: string;
  componentRoleContext: string;
  symbolsLabel: string;
  symbolsPlaceholder: string;
  tagsLabel: string;
  tagsPlaceholder: string;
  asOfLabel: string;
  publishedAtLabel: string;
  excerptLabel: string;
  excerptPlaceholder: string;
  noteLabel: string;
  notePlaceholder: string;
  methodologyNoteLabel: string;
  methodologyNotePlaceholder: string;
  licenseNoteLabel: string;
  licenseNotePlaceholder: string;
  aiFollowUpLabel: string;
  aiFollowUpPlaceholder: string;
  reviewStatusLabel: string;
  statusDraft: string;
  statusReviewed: string;
  statusArchived: string;
  citableLabel: string;
  saveAction: string;
  saving: string;
  clearAction: string;
  saveSuccess: string;
  saveFailed: string;
  contentRequired: string;
  citableBoundary: string;
  recentTitle: string;
  loadFailed: string;
  noNotes: string;
  filterLabel: string;
  filterPlaceholder: string;
  statusFilterLabel: string;
  allStatuses: string;
  citableOnlyLabel: string;
  citableBadge: string;
  collectionBadge: string;
  citationId: string;
  sourceLink: string;
  linkedSourceBadge: string;
  targetIndicatorsBadge: string;
  componentRoleBadge: string;
  reviewChecklistTitle: string;
  completenessSummary: string;
  completenessComplete: string;
  completenessPartial: string;
  completenessMissing: string;
  checklistSourceIdentity: string;
  checklistSourceUrlOrDocument: string;
  checklistDateMetadata: string;
  checklistExcerpt: string;
  checklistMethodology: string;
  checklistTargets: string;
  checklistLicenseNote: string;
  unavailableShort: string;
};

type ResearchSourceNotebookProps = {
  labels: ResearchSourceNotebookLabels;
  initialNotes: ResearchSourceNote[];
  sourceTargets?: ResearchSourceTargetOption[];
  loadFailed?: boolean;
};

type FormState = {
  title: string;
  sourceName: string;
  sourceType: string;
  sourceUrl: string;
  sourceId: string;
  targetIndicatorCodes: string;
  componentRole: string;
  symbols: string;
  tags: string;
  asOf: string;
  publishedAt: string;
  excerpt: string;
  note: string;
  methodologyNote: string;
  licenseNote: string;
  aiFollowUp: string;
  reviewStatus: "draft" | "reviewed" | "archived";
  isCitable: boolean;
};

type SourceIngestionExtractionModel = {
  provider?: string;
  name?: string;
  used_llm?: boolean;
  fallback_reason?: string | null;
};

type SourceIngestionKeyIndicator = {
  label: string;
  code?: string;
  reason?: string;
};

type SourceIngestionCitationClue = {
  kind: string;
  label: string;
  value: string;
};

type SourceIngestionSuggestedFields = {
  title?: string;
  source_name?: string;
  source_type?: string;
  tags?: string[];
  target_indicator_codes?: string[];
  methodology_note?: string;
  license_note?: string;
  ai_follow_up?: string;
};

type SourceIngestionDiagnostic = {
  code?: string;
  message?: string;
};

type SourceIngestionExtractionResult = {
  status: string;
  summary: string;
  key_indicators: SourceIngestionKeyIndicator[];
  citation_clues: SourceIngestionCitationClue[];
  follow_up_questions: string[];
  suggested_fields: SourceIngestionSuggestedFields;
  model: SourceIngestionExtractionModel;
  diagnostics: SourceIngestionDiagnostic[];
};

const emptyForm: FormState = {
  title: "",
  sourceName: "",
  sourceType: "",
  sourceUrl: "",
  sourceId: "",
  targetIndicatorCodes: "",
  componentRole: "",
  symbols: "",
  tags: "",
  asOf: "",
  publishedAt: "",
  excerpt: "",
  note: "",
  methodologyNote: "",
  licenseNote: "",
  aiFollowUp: "",
  reviewStatus: "draft",
  isCitable: false,
};

type ChecklistLabelKey =
  | "checklistSourceIdentity"
  | "checklistSourceUrlOrDocument"
  | "checklistDateMetadata"
  | "checklistExcerpt"
  | "checklistMethodology"
  | "checklistTargets"
  | "checklistLicenseNote";

const reviewChecklistItems: Array<{ key: keyof ResearchSourceReviewChecklist; labelKey: ChecklistLabelKey }> = [
  { key: "source_identity", labelKey: "checklistSourceIdentity" },
  { key: "source_url_or_document", labelKey: "checklistSourceUrlOrDocument" },
  { key: "date_metadata", labelKey: "checklistDateMetadata" },
  { key: "excerpt", labelKey: "checklistExcerpt" },
  { key: "methodology", labelKey: "checklistMethodology" },
  { key: "targets", labelKey: "checklistTargets" },
  { key: "license_note", labelKey: "checklistLicenseNote" },
];

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function getNoteMetadata(note: ResearchSourceNote): ResearchSourceWorkflowMetadata {
  return note.metadata && typeof note.metadata === "object" ? note.metadata : {};
}

function metadataString(metadata: ResearchSourceWorkflowMetadata, key: keyof ResearchSourceWorkflowMetadata): string {
  const value = metadata[key];
  return typeof value === "string" ? value : "";
}

function metadataStringList(metadata: ResearchSourceWorkflowMetadata, key: keyof ResearchSourceWorkflowMetadata): string[] {
  const value = metadata[key];
  return Array.isArray(value) ? value.map((item) => String(item).trim()).filter(Boolean) : [];
}

function getCompletenessStatusLabel(status: string | undefined, labels: ResearchSourceNotebookLabels): string {
  if (status === "complete") {
    return labels.completenessComplete;
  }
  if (status === "missing") {
    return labels.completenessMissing;
  }
  return labels.completenessPartial;
}

function buildCompleteness(checklist: ResearchSourceReviewChecklist): ResearchSourceCompleteness {
  const total = reviewChecklistItems.length;
  const score = reviewChecklistItems.filter((item) => Boolean(checklist[item.key])).length;
  if (score === total) {
    return { score, total, status: "complete" };
  }
  if (score > 0) {
    return { score, total, status: "partial" };
  }
  return { score, total, status: "missing" };
}

function getStoredCompleteness(
  metadata: ResearchSourceWorkflowMetadata,
  fallbackChecklist: ResearchSourceReviewChecklist,
): ResearchSourceCompleteness {
  const value = metadata.completeness;
  if (value && typeof value === "object") {
    return {
      score: typeof value.score === "number" ? value.score : undefined,
      total: typeof value.total === "number" ? value.total : undefined,
      status: typeof value.status === "string" ? value.status : undefined,
    };
  }
  return buildCompleteness(fallbackChecklist);
}

function getStoredChecklist(metadata: ResearchSourceWorkflowMetadata): ResearchSourceReviewChecklist | null {
  const value = metadata.review_checklist;
  if (!value || typeof value !== "object") {
    return null;
  }
  return reviewChecklistItems.reduce<ResearchSourceReviewChecklist>((accumulator, item) => {
    accumulator[item.key] = Boolean(value[item.key]);
    return accumulator;
  }, {});
}

function buildFormChecklist(form: FormState, filename: string | null): ResearchSourceReviewChecklist {
  return {
    source_identity: Boolean(form.title.trim() && form.sourceName.trim() && form.sourceType.trim()),
    source_url_or_document: Boolean(form.sourceUrl.trim() || filename),
    date_metadata: Boolean(form.asOf || form.publishedAt),
    excerpt: Boolean(form.excerpt.trim()),
    methodology: Boolean(form.note.trim() || form.methodologyNote.trim()),
    targets: Boolean(
      form.sourceId ||
        form.targetIndicatorCodes.trim() ||
        form.tags.trim() ||
        form.symbols.trim(),
    ),
    license_note: Boolean(form.licenseNote.trim()),
  };
}

function buildNoteFallbackChecklist(note: ResearchSourceNote): ResearchSourceReviewChecklist {
  const metadata = getNoteMetadata(note);
  return {
    source_identity: Boolean(note.title && note.source_name && note.source_type),
    source_url_or_document: Boolean(note.source_url || metadataString(metadata, "browser_filename")),
    date_metadata: Boolean(note.as_of || note.published_at || note.retrieved_at),
    excerpt: Boolean(note.excerpt),
    methodology: Boolean(note.note || metadataString(metadata, "methodology_note")),
    targets: Boolean(
      metadataString(metadata, "source_id") ||
        metadataStringList(metadata, "target_indicator_codes").length > 0 ||
        (note.tags ?? []).length > 0 ||
        (note.symbols ?? []).length > 0,
    ),
    license_note: Boolean(metadataString(metadata, "license_note")),
  };
}

function labelForStatus(status: string, labels: ResearchSourceNotebookLabels): string {
  if (status === "reviewed") {
    return labels.statusReviewed;
  }
  if (status === "archived") {
    return labels.statusArchived;
  }
  return labels.statusDraft;
}

function badgeVariant(status: string, isCitable = false): "secondary" | "outline" | "destructive" {
  if (isCitable || status === "reviewed") {
    return "secondary";
  }
  if (status === "archived") {
    return "outline";
  }
  return "destructive";
}

function readPayload(payload: Record<string, unknown>): Record<string, unknown> {
  const detail = payload.detail;
  return detail && typeof detail === "object" ? (detail as Record<string, unknown>) : payload;
}

async function readJsonSafe(response: Response): Promise<Record<string, unknown>> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item).trim()).filter(Boolean) : [];
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function normalizeExtractionIndicators(value: unknown): SourceIngestionKeyIndicator[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => objectValue(item))
    .map((item) => ({
      label: stringValue(item.label),
      code: stringValue(item.code),
      reason: stringValue(item.reason),
    }))
    .filter((item) => item.label);
}

function normalizeExtractionClues(value: unknown): SourceIngestionCitationClue[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => objectValue(item))
    .map((item) => ({
      kind: stringValue(item.kind) || "source",
      label: stringValue(item.label),
      value: stringValue(item.value),
    }))
    .filter((item) => item.label && item.value);
}

function normalizeExtractionDiagnostics(value: unknown): SourceIngestionDiagnostic[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => objectValue(item))
    .map((item) => ({
      code: stringValue(item.code),
      message: stringValue(item.message),
    }))
    .filter((item) => item.code || item.message);
}

function normalizeExtractionResult(payload: Record<string, unknown>): SourceIngestionExtractionResult {
  const model = objectValue(payload.model);
  const suggestedFields = objectValue(payload.suggested_fields);
  return {
    status: stringValue(payload.status) || "fallback",
    summary: stringValue(payload.summary),
    key_indicators: normalizeExtractionIndicators(payload.key_indicators),
    citation_clues: normalizeExtractionClues(payload.citation_clues),
    follow_up_questions: stringList(payload.follow_up_questions),
    suggested_fields: {
      title: stringValue(suggestedFields.title),
      source_name: stringValue(suggestedFields.source_name),
      source_type: stringValue(suggestedFields.source_type),
      tags: stringList(suggestedFields.tags),
      target_indicator_codes: stringList(suggestedFields.target_indicator_codes),
      methodology_note: stringValue(suggestedFields.methodology_note),
      license_note: stringValue(suggestedFields.license_note),
      ai_follow_up: stringValue(suggestedFields.ai_follow_up),
    },
    model: {
      provider: stringValue(model.provider),
      name: stringValue(model.name),
      used_llm: model.used_llm === true,
      fallback_reason: stringValue(model.fallback_reason) || null,
    },
    diagnostics: normalizeExtractionDiagnostics(payload.diagnostics),
  };
}

function mergeCommaValues(current: string, suggestions: string[] | undefined): string {
  const merged = new Set([...splitList(current), ...(suggestions ?? [])]);
  return Array.from(merged).join(", ");
}

function extractionStatusLabel(status: string, labels: ResearchSourceNotebookLabels): string {
  if (status === "ok") {
    return labels.extractionStatusOk;
  }
  if (status === "invalid_input") {
    return labels.extractionStatusInvalid;
  }
  return labels.extractionStatusFallback;
}

export function ResearchSourceNotebook({
  labels,
  initialNotes,
  sourceTargets = [],
  loadFailed = false,
}: ResearchSourceNotebookProps) {
  const [form, setForm] = React.useState<FormState>(emptyForm);
  const [notes, setNotes] = React.useState<ResearchSourceNote[]>(initialNotes);
  const [filename, setFilename] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(loadFailed ? labels.loadFailed : null);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isExtracting, setIsExtracting] = React.useState(false);
  const [extraction, setExtraction] = React.useState<SourceIngestionExtractionResult | null>(null);
  const [filterText, setFilterText] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("all");
  const [citableOnly, setCitableOnly] = React.useState(false);
  const router = useRouter();
  const selectedSourceTarget = sourceTargets.find((target) => target.id === form.sourceId) ?? null;
  const formChecklist = buildFormChecklist(form, filename);
  const formCompleteness = buildCompleteness(formChecklist);
  const componentRoleOptions = [
    { value: "", label: labels.componentRoleGeneral },
    { value: "market_cap", label: labels.componentRoleMarketCap },
    { value: "gdp", label: labels.componentRoleGdp },
    { value: "cpi_source", label: labels.componentRoleCpi },
    { value: "m2_source", label: labels.componentRoleM2 },
    { value: "rate_source", label: labels.componentRoleRate },
    { value: "yield_spread_source", label: labels.componentRoleYieldSpread },
    { value: "filing_note", label: labels.componentRoleFiling },
    { value: "general_context", label: labels.componentRoleContext },
  ];

  const filteredNotes = notes.filter((note) => {
    const haystack = [
      note.title,
      note.source_name,
      note.source_type,
      metadataString(getNoteMetadata(note), "source_label"),
      metadataString(getNoteMetadata(note), "source_category"),
      metadataString(getNoteMetadata(note), "component_role"),
      ...metadataStringList(getNoteMetadata(note), "target_indicator_codes"),
      ...(note.symbols ?? []),
      ...(note.tags ?? []),
      note.excerpt ?? "",
      note.note ?? "",
    ]
      .join(" ")
      .toLowerCase();
    const matchesText = !filterText.trim() || haystack.includes(filterText.trim().toLowerCase());
    const matchesStatus = statusFilter === "all" || note.review_status === statusFilter;
    const matchesCitable = !citableOnly || note.is_citable;
    return matchesText && matchesStatus && matchesCitable;
  });

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleSourceTargetChange(sourceId: string) {
    const target = sourceTargets.find((item) => item.id === sourceId) ?? null;
    setForm((current) => ({
      ...current,
      sourceId,
      sourceName: current.sourceName || target?.label || "",
      sourceType: current.sourceType || target?.category || "",
      targetIndicatorCodes:
        current.targetIndicatorCodes || (target?.targetIndicatorCodes ?? []).join(", "),
    }));
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (!file) {
      return;
    }

    try {
      const text = await file.text();
      setFilename(file.name);
      setMessage(null);
      setExtraction(null);
      setForm((current) => ({
        ...current,
        title: current.title || file.name.replace(/\.[^.]+$/, ""),
        excerpt: text,
      }));
    } catch {
      setMessage(labels.fileReadFailed);
    }
  }

  async function handleExtract() {
    if (!form.excerpt.trim() && !form.sourceUrl.trim()) {
      setMessage(labels.extractionContentRequired);
      return;
    }

    setIsExtracting(true);
    setMessage(null);
    try {
      const response = await fetch("/api/source-ingestion/extract", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          content: form.excerpt,
          filename,
          source_url: form.sourceUrl || null,
          source_id: form.sourceId || null,
          source_label: selectedSourceTarget?.label ?? null,
          source_category: selectedSourceTarget?.category ?? null,
          target_indicator_codes: splitList(form.targetIndicatorCodes),
          component_role: form.componentRole || null,
          locale: document.documentElement.lang.toLowerCase().startsWith("zh") ? "zh" : "en",
        }),
      });
      const payload = readPayload(await readJsonSafe(response));
      if (!response.ok) {
        setMessage(labels.extractFailed);
        return;
      }
      setExtraction(normalizeExtractionResult(payload));
    } catch {
      setMessage(labels.extractFailed);
    } finally {
      setIsExtracting(false);
    }
  }

  function handleApplyExtraction() {
    if (!extraction) {
      return;
    }
    const suggestions = extraction.suggested_fields;
    setForm((current) => ({
      ...current,
      title: suggestions.title || current.title,
      sourceName: suggestions.source_name || current.sourceName,
      sourceType: suggestions.source_type || current.sourceType,
      targetIndicatorCodes: mergeCommaValues(current.targetIndicatorCodes, suggestions.target_indicator_codes),
      tags: mergeCommaValues(current.tags, suggestions.tags),
      note: current.note || extraction.summary || "",
      methodologyNote: current.methodologyNote || suggestions.methodology_note || "",
      licenseNote: current.licenseNote || suggestions.license_note || "",
      aiFollowUp:
        current.aiFollowUp ||
        suggestions.ai_follow_up ||
        extraction.follow_up_questions[0] ||
        "",
    }));
  }

  async function handleSave() {
    if (!form.title.trim() || !form.sourceName.trim() || !form.sourceType.trim() || (!form.sourceUrl.trim() && !form.excerpt.trim())) {
      setMessage(labels.contentRequired);
      return;
    }

    setIsSaving(true);
    setMessage(null);
    try {
      const response = await fetch("/api/research-source-notes", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title: form.title,
          source_name: form.sourceName,
          source_type: form.sourceType,
          source_url: form.sourceUrl || null,
          source_id: form.sourceId || null,
          source_label: selectedSourceTarget?.label ?? null,
          source_category: selectedSourceTarget?.category ?? null,
          target_indicator_codes: splitList(form.targetIndicatorCodes),
          component_role: form.componentRole || null,
          symbols: splitList(form.symbols),
          tags: splitList(form.tags),
          as_of: form.asOf || null,
          published_at: form.publishedAt || null,
          excerpt: form.excerpt || null,
          note: form.note || null,
          methodology_note: form.methodologyNote || null,
          license_note: form.licenseNote || null,
          ai_follow_up: form.aiFollowUp || null,
          review_status: form.reviewStatus,
          is_citable: form.isCitable,
          metadata: {
            ...(filename ? { browser_filename: filename } : {}),
            ...(extraction
              ? {
                  ingestion_extraction: {
                    status: extraction.status,
                    summary: extraction.summary,
                    key_indicators: extraction.key_indicators,
                    citation_clues: extraction.citation_clues,
                    follow_up_questions: extraction.follow_up_questions,
                    model: extraction.model,
                    diagnostics: extraction.diagnostics,
                  },
                }
              : {}),
          },
        }),
      });
      const payload = readPayload(await readJsonSafe(response));
      if (!response.ok) {
        setMessage(labels.saveFailed);
        return;
      }

      setNotes((current) => [payload as ResearchSourceNote, ...current]);
      setMessage(labels.saveSuccess);
      setForm(emptyForm);
      setFilename(null);
      setExtraction(null);
      router.refresh();
    } catch {
      setMessage(labels.saveFailed);
    } finally {
      setIsSaving(false);
    }
  }

  function handleClear() {
    setForm(emptyForm);
    setFilename(null);
    setExtraction(null);
    setMessage(null);
  }

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">
            <NotebookPen className="h-3 w-3" />
            {labels.title}
          </Badge>
          {filename ? <Badge variant="outline">{labels.selectedFile.replace("{name}", filename)}</Badge> : null}
        </div>
        <CardTitle className="flex items-center gap-2 text-xl">
          <NotebookPen className="h-5 w-5" />
          {labels.title}
        </CardTitle>
        <CardDescription>{labels.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 xl:grid-cols-[minmax(18rem,0.9fr)_minmax(0,1.1fr)]">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <label className="text-sm font-medium" htmlFor="source-note-file">
                {labels.fileLabel}
              </label>
              <Input
                id="source-note-file"
                type="file"
                accept=".txt,.md,.csv,.json,text/plain,text/markdown,text/csv,application/json"
                onChange={handleFileChange}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <label className="text-sm font-medium" htmlFor="source-note-source-target">
                {labels.sourceTargetLabel}
              </label>
              <select
                id="source-note-source-target"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.sourceId}
                onChange={(event) => handleSourceTargetChange(event.target.value)}
              >
                <option value="">{labels.sourceTargetPlaceholder}</option>
                {sourceTargets.map((target) => (
                  <option key={target.id} value={target.id}>
                    {target.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <label className="text-sm font-medium" htmlFor="source-note-title">
                {labels.titleLabel}
              </label>
              <Input
                id="source-note-title"
                value={form.title}
                placeholder={labels.titlePlaceholder}
                onChange={(event) => updateField("title", event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="source-note-source-name">
                {labels.sourceNameLabel}
              </label>
              <Input
                id="source-note-source-name"
                value={form.sourceName}
                placeholder={labels.sourceNamePlaceholder}
                onChange={(event) => updateField("sourceName", event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="source-note-source-type">
                {labels.sourceTypeLabel}
              </label>
              <Input
                id="source-note-source-type"
                value={form.sourceType}
                placeholder={labels.sourceTypePlaceholder}
                onChange={(event) => updateField("sourceType", event.target.value)}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <label className="text-sm font-medium" htmlFor="source-note-component-role">
                {labels.componentRoleLabel}
              </label>
              <select
                id="source-note-component-role"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.componentRole}
                onChange={(event) => updateField("componentRole", event.target.value)}
              >
                {componentRoleOptions.map((option) => (
                  <option key={option.value || "general"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <label className="text-sm font-medium" htmlFor="source-note-source-url">
                {labels.sourceUrlLabel}
              </label>
              <Input
                id="source-note-source-url"
                value={form.sourceUrl}
                placeholder={labels.sourceUrlPlaceholder}
                onChange={(event) => updateField("sourceUrl", event.target.value)}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <label className="text-sm font-medium" htmlFor="source-note-target-indicators">
                {labels.targetIndicatorsLabel}
              </label>
              <Input
                id="source-note-target-indicators"
                value={form.targetIndicatorCodes}
                placeholder={labels.targetIndicatorsPlaceholder}
                onChange={(event) => updateField("targetIndicatorCodes", event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="source-note-symbols">
                {labels.symbolsLabel}
              </label>
              <Input
                id="source-note-symbols"
                value={form.symbols}
                placeholder={labels.symbolsPlaceholder}
                onChange={(event) => updateField("symbols", event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="source-note-tags">
                {labels.tagsLabel}
              </label>
              <Input
                id="source-note-tags"
                value={form.tags}
                placeholder={labels.tagsPlaceholder}
                onChange={(event) => updateField("tags", event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="source-note-as-of">
                {labels.asOfLabel}
              </label>
              <Input
                id="source-note-as-of"
                type="date"
                value={form.asOf}
                onChange={(event) => updateField("asOf", event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="source-note-published-at">
                {labels.publishedAtLabel}
              </label>
              <Input
                id="source-note-published-at"
                type="datetime-local"
                value={form.publishedAt}
                onChange={(event) => updateField("publishedAt", event.target.value)}
              />
            </div>
          </div>

          <div className="space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="source-note-excerpt">
                {labels.excerptLabel}
              </label>
              <textarea
                id="source-note-excerpt"
                className="min-h-40 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={form.excerpt}
                placeholder={labels.excerptPlaceholder}
                onChange={(event) => updateField("excerpt", event.target.value)}
              />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="source-note-note">
                  {labels.noteLabel}
                </label>
                <textarea
                  id="source-note-note"
                  className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={form.note}
                  placeholder={labels.notePlaceholder}
                  onChange={(event) => updateField("note", event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="source-note-ai-follow-up">
                  {labels.aiFollowUpLabel}
                </label>
                <textarea
                  id="source-note-ai-follow-up"
                  className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={form.aiFollowUp}
                  placeholder={labels.aiFollowUpPlaceholder}
                  onChange={(event) => updateField("aiFollowUp", event.target.value)}
                />
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="source-note-methodology-note">
                  {labels.methodologyNoteLabel}
                </label>
                <textarea
                  id="source-note-methodology-note"
                  className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={form.methodologyNote}
                  placeholder={labels.methodologyNotePlaceholder}
                  onChange={(event) => updateField("methodologyNote", event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="source-note-license-note">
                  {labels.licenseNoteLabel}
                </label>
                <textarea
                  id="source-note-license-note"
                  className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={form.licenseNote}
                  placeholder={labels.licenseNotePlaceholder}
                  onChange={(event) => updateField("licenseNote", event.target.value)}
                />
              </div>
            </div>
            <div className="border bg-muted/20 p-3">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">
                      <Sparkles className="h-3 w-3" />
                      {labels.ingestionTitle}
                    </Badge>
                    {extraction ? (
                      <Badge variant={extraction.status === "ok" ? "secondary" : "outline"}>
                        {extractionStatusLabel(extraction.status, labels)}
                      </Badge>
                    ) : null}
                    {extraction ? (
                      <Badge variant={extraction.model.used_llm ? "secondary" : "outline"}>
                        {extraction.model.used_llm ? labels.extractionModelLlm : labels.extractionModelFallback}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{labels.ingestionDescription}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{labels.acceptedFormats}</p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  <Button type="button" variant="outline" onClick={handleExtract} disabled={isExtracting}>
                    <Sparkles className={isExtracting ? "h-4 w-4 animate-pulse" : "h-4 w-4"} />
                    {isExtracting ? labels.extracting : labels.extractAction}
                  </Button>
                  {extraction ? (
                    <Button type="button" variant="outline" onClick={handleApplyExtraction}>
                      {labels.applyExtraction}
                    </Button>
                  ) : null}
                </div>
              </div>

              {extraction ? (
                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold">{labels.extractionSummaryTitle}</h4>
                    <p className="rounded border bg-background p-3 text-sm text-muted-foreground">
                      {extraction.summary || labels.unavailableShort}
                    </p>
                    {extraction.model.fallback_reason ? (
                      <p className="text-xs text-muted-foreground">
                        {labels.extractionFallbackReason.replace("{reason}", extraction.model.fallback_reason)}
                      </p>
                    ) : null}
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold">{labels.extractionIndicatorsTitle}</h4>
                    <div className="flex flex-wrap gap-1">
                      {extraction.key_indicators.length > 0 ? (
                        extraction.key_indicators.map((indicator) => (
                          <Badge key={`${indicator.label}-${indicator.code ?? ""}`} variant="outline">
                            {indicator.code ? `${indicator.label} / ${indicator.code}` : indicator.label}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-sm text-muted-foreground">{labels.unavailableShort}</span>
                      )}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold">{labels.extractionCitationCluesTitle}</h4>
                    {extraction.citation_clues.length > 0 ? (
                      <ul className="space-y-1 text-sm text-muted-foreground">
                        {extraction.citation_clues.map((clue) => (
                          <li key={`${clue.kind}-${clue.label}-${clue.value}`}>
                            <span className="font-medium text-foreground">{clue.label}</span>: {clue.value}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">{labels.unavailableShort}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold">{labels.extractionFollowUpsTitle}</h4>
                    {extraction.follow_up_questions.length > 0 ? (
                      <ul className="space-y-1 text-sm text-muted-foreground">
                        {extraction.follow_up_questions.map((question) => (
                          <li key={question}>{question}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">{labels.unavailableShort}</p>
                    )}
                  </div>
                  <div className="space-y-2 lg:col-span-2">
                    <h4 className="text-sm font-semibold">{labels.extractionSuggestedFieldsTitle}</h4>
                    <div className="flex flex-wrap gap-1">
                      {(extraction.suggested_fields.tags ?? []).map((tag) => (
                        <Badge key={`suggested-tag-${tag}`} variant="outline">
                          {tag}
                        </Badge>
                      ))}
                      {(extraction.suggested_fields.target_indicator_codes ?? []).map((code) => (
                        <Badge key={`suggested-code-${code}`} variant="outline">
                          {code}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  {extraction.diagnostics.length > 0 ? (
                    <div className="space-y-2 lg:col-span-2">
                      <h4 className="text-sm font-semibold">{labels.extractionDiagnosticsTitle}</h4>
                      <ul className="space-y-1 text-xs text-muted-foreground">
                        {extraction.diagnostics.map((diagnostic) => (
                          <li key={`${diagnostic.code ?? ""}-${diagnostic.message ?? ""}`}>
                            {[diagnostic.code, diagnostic.message].filter(Boolean).join(": ")}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : null}
              <p className="mt-3 text-xs text-muted-foreground">{labels.extractionBoundary}</p>
            </div>
            <div className="border bg-muted/20 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <div className="text-sm font-semibold">{labels.reviewChecklistTitle}</div>
                <Badge variant={formCompleteness.status === "complete" ? "secondary" : "outline"}>
                  {labels.completenessSummary
                    .replace("{score}", String(formCompleteness.score ?? 0))
                    .replace("{total}", String(formCompleteness.total ?? reviewChecklistItems.length))}
                </Badge>
                <Badge variant={formCompleteness.status === "complete" ? "secondary" : "outline"}>
                  {getCompletenessStatusLabel(formCompleteness.status, labels)}
                </Badge>
              </div>
              <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                {reviewChecklistItems.map((item) => {
                  const complete = Boolean(formChecklist[item.key]);
                  return (
                    <div key={item.key} className="flex items-center gap-2 text-muted-foreground">
                      {complete ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5" />
                      )}
                      <span>{labels[item.labelKey]}</span>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex flex-col gap-3 border bg-muted/20 p-3 md:flex-row md:items-center md:justify-between">
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="space-y-1 text-sm font-medium" htmlFor="source-note-review-status">
                  <span>{labels.reviewStatusLabel}</span>
                  <select
                    id="source-note-review-status"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={form.reviewStatus}
                    onChange={(event) => updateField("reviewStatus", event.target.value as FormState["reviewStatus"])}
                  >
                    <option value="draft">{labels.statusDraft}</option>
                    <option value="reviewed">{labels.statusReviewed}</option>
                    <option value="archived">{labels.statusArchived}</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 pt-6 text-sm">
                  <input
                    type="checkbox"
                    checked={form.isCitable}
                    onChange={(event) => {
                      updateField("isCitable", event.target.checked);
                      if (event.target.checked) {
                        updateField("reviewStatus", "reviewed");
                      }
                    }}
                  />
                  <span>{labels.citableLabel}</span>
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button type="button" onClick={handleSave} disabled={isSaving}>
                  <Save className={isSaving ? "h-4 w-4 animate-pulse" : "h-4 w-4"} />
                  {isSaving ? labels.saving : labels.saveAction}
                </Button>
                <Button type="button" variant="outline" onClick={handleClear} disabled={isSaving}>
                  {labels.clearAction}
                </Button>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">{labels.citableBoundary}</p>
          </div>
        </div>

        {message ? (
          <div className="flex items-center gap-2 border bg-muted/30 p-3 text-sm text-muted-foreground">
            {message === labels.saveSuccess ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            <span>{message}</span>
          </div>
        ) : null}

        <div className="space-y-3 border-t pt-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-lg font-semibold">{labels.recentTitle}</h3>
              <p className="text-sm text-muted-foreground">
                {notes.length > 0 ? `${filteredNotes.length} / ${notes.length}` : labels.noNotes}
              </p>
            </div>
            <div className="grid gap-2 md:grid-cols-[minmax(12rem,1fr)_10rem_8rem]">
              <label className="sr-only" htmlFor="source-note-filter">
                {labels.filterLabel}
              </label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="source-note-filter"
                  className="pl-8"
                  value={filterText}
                  placeholder={labels.filterPlaceholder}
                  onChange={(event) => setFilterText(event.target.value)}
                />
              </div>
              <label className="sr-only" htmlFor="source-note-status-filter">
                {labels.statusFilterLabel}
              </label>
              <select
                id="source-note-status-filter"
                className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="all">{labels.allStatuses}</option>
                <option value="draft">{labels.statusDraft}</option>
                <option value="reviewed">{labels.statusReviewed}</option>
                <option value="archived">{labels.statusArchived}</option>
              </select>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={citableOnly}
                  onChange={(event) => setCitableOnly(event.target.checked)}
                />
                <span>{labels.citableOnlyLabel}</span>
              </label>
            </div>
          </div>

          {filteredNotes.length === 0 ? (
            <div className="border bg-muted/20 p-4 text-sm text-muted-foreground">{labels.noNotes}</div>
          ) : (
            <div className="grid gap-3 xl:grid-cols-2">
              {filteredNotes.map((note) => {
                const metadata = getNoteMetadata(note);
                const checklist = getStoredChecklist(metadata) ?? buildNoteFallbackChecklist(note);
                const completeness = getStoredCompleteness(metadata, checklist);
                const sourceLabel = metadataString(metadata, "source_label");
                const sourceCategory = metadataString(metadata, "source_category");
                const targetCodes = metadataStringList(metadata, "target_indicator_codes");
                const componentRole = metadataString(metadata, "component_role");
                return (
                  <article key={note.id} className="border bg-background p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <h4 className="font-semibold">{note.title}</h4>
                        <p className="text-sm text-muted-foreground">
                          {[note.source_name, note.source_type].filter(Boolean).join(" / ") ||
                            labels.unavailableShort}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-wrap gap-2">
                        <Badge variant={badgeVariant(note.review_status, note.is_citable)}>
                          {labelForStatus(note.review_status, labels)}
                        </Badge>
                        <Badge variant={note.is_citable ? "secondary" : "outline"}>
                          {note.is_citable ? labels.citableBadge : labels.collectionBadge}
                        </Badge>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-1">
                      {sourceLabel ? (
                        <Badge variant="outline" className="text-[10px]">
                          <Link2 className="h-3 w-3" />
                          {labels.linkedSourceBadge.replace("{label}", sourceLabel)}
                        </Badge>
                      ) : null}
                      {sourceCategory ? (
                        <Badge variant="outline" className="text-[10px]">
                          {sourceCategory}
                        </Badge>
                      ) : null}
                      {componentRole ? (
                        <Badge variant="outline" className="text-[10px]">
                          {labels.componentRoleBadge.replace("{role}", componentRole)}
                        </Badge>
                      ) : null}
                      {targetCodes.map((code) => (
                        <Badge key={`${note.id}-target-${code}`} variant="outline" className="text-[10px]">
                          {labels.targetIndicatorsBadge.replace("{code}", code)}
                        </Badge>
                      ))}
                      {(note.symbols ?? []).map((symbol) => (
                        <Badge key={`${note.id}-${symbol}`} variant="outline" className="text-[10px]">
                          {symbol}
                        </Badge>
                      ))}
                      {(note.tags ?? []).map((tag) => (
                        <Badge key={`${note.id}-${tag}`} variant="outline" className="text-[10px]">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                    {note.excerpt ? (
                      <p className="mt-3 line-clamp-3 text-sm text-muted-foreground">{note.excerpt}</p>
                    ) : null}
                    {note.note ? <p className="mt-2 line-clamp-2 text-sm">{note.note}</p> : null}
                    <div className="mt-3 border bg-muted/20 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="text-sm font-semibold">{labels.reviewChecklistTitle}</div>
                        <Badge variant={completeness.status === "complete" ? "secondary" : "outline"}>
                          {labels.completenessSummary
                            .replace("{score}", String(completeness.score ?? 0))
                            .replace("{total}", String(completeness.total ?? reviewChecklistItems.length))}
                        </Badge>
                        <Badge variant={completeness.status === "complete" ? "secondary" : "outline"}>
                          {getCompletenessStatusLabel(completeness.status, labels)}
                        </Badge>
                      </div>
                      <div className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
                        {reviewChecklistItems.map((item) => {
                          const complete = Boolean(checklist[item.key]);
                          return (
                            <div key={`${note.id}-${item.key}`} className="flex items-center gap-2 text-muted-foreground">
                              {complete ? (
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                              ) : (
                                <XCircle className="h-3.5 w-3.5" />
                              )}
                              <span>{labels[item.labelKey]}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{note.as_of ?? note.published_at ?? note.retrieved_at ?? labels.unavailableShort}</span>
                      {note.citation_id ? (
                        <span className="font-mono">{labels.citationId.replace("{id}", note.citation_id)}</span>
                      ) : null}
                      {note.source_url ? (
                        <a
                          href={note.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline"
                        >
                          <FileUp className="h-3 w-3" />
                          {labels.sourceLink}
                        </a>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
