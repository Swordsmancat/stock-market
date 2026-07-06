"use client";

import * as React from "react";
import { CheckCircle2, FileUp, NotebookPen, Save, Search, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

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
  created_at?: string | null;
};

export type ResearchSourceNotebookLabels = {
  title: string;
  description: string;
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
  unavailableShort: string;
};

type ResearchSourceNotebookProps = {
  labels: ResearchSourceNotebookLabels;
  initialNotes: ResearchSourceNote[];
  loadFailed?: boolean;
};

type FormState = {
  title: string;
  sourceName: string;
  sourceType: string;
  sourceUrl: string;
  symbols: string;
  tags: string;
  asOf: string;
  publishedAt: string;
  excerpt: string;
  note: string;
  aiFollowUp: string;
  reviewStatus: "draft" | "reviewed" | "archived";
  isCitable: boolean;
};

const emptyForm: FormState = {
  title: "",
  sourceName: "",
  sourceType: "",
  sourceUrl: "",
  symbols: "",
  tags: "",
  asOf: "",
  publishedAt: "",
  excerpt: "",
  note: "",
  aiFollowUp: "",
  reviewStatus: "draft",
  isCitable: false,
};

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
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

export function ResearchSourceNotebook({ labels, initialNotes, loadFailed = false }: ResearchSourceNotebookProps) {
  const [form, setForm] = React.useState<FormState>(emptyForm);
  const [notes, setNotes] = React.useState<ResearchSourceNote[]>(initialNotes);
  const [filename, setFilename] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(loadFailed ? labels.loadFailed : null);
  const [isSaving, setIsSaving] = React.useState(false);
  const [filterText, setFilterText] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("all");
  const [citableOnly, setCitableOnly] = React.useState(false);
  const router = useRouter();

  const filteredNotes = notes.filter((note) => {
    const haystack = [
      note.title,
      note.source_name,
      note.source_type,
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

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (!file) {
      return;
    }

    try {
      const text = await file.text();
      setFilename(file.name);
      setMessage(null);
      setForm((current) => ({
        ...current,
        title: current.title || file.name.replace(/\.[^.]+$/, ""),
        excerpt: text,
      }));
    } catch {
      setMessage(labels.fileReadFailed);
    }
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
          symbols: splitList(form.symbols),
          tags: splitList(form.tags),
          as_of: form.asOf || null,
          published_at: form.publishedAt || null,
          excerpt: form.excerpt || null,
          note: form.note || null,
          ai_follow_up: form.aiFollowUp || null,
          review_status: form.reviewStatus,
          is_citable: form.isCitable,
          metadata: filename ? { browser_filename: filename } : {},
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
              {filteredNotes.map((note) => (
                <article key={note.id} className="border bg-background p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <h4 className="font-semibold">{note.title}</h4>
                      <p className="text-sm text-muted-foreground">
                        {[note.source_name, note.source_type].filter(Boolean).join(" / ") || labels.unavailableShort}
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
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
