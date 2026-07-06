# Source Notebook Macro Evidence Workflow Design

## Architecture

This task extends the existing Source Notebook workflow rather than creating a new evidence store.

Primary layers:

- Backend source registry: reuse `packages/services/information_sources.py` as the source-readiness target catalog.
- Backend notebook service: extend `packages/services/research_source_notes.py` to normalize and serialize workflow metadata stored in `ResearchSourceNote.metadata_json`.
- API: extend `apps/api/routers/research_source_notes.py` request shape additively. Existing `metadata` remains supported.
- Frontend page: `apps/web/app/[locale]/evidence/page.tsx` already has source-readiness data from market overview; pass source targets into `ResearchSourceNotebook`.
- Frontend component: extend `apps/web/components/research-source-notebook.tsx` with source target selection, target indicator chips, component role, review checklist, and linked-entry display.
- AI context: keep existing dashboard/assistant citation flow but include source workflow metadata in citation metadata when a note is citable.

## Data Model

No database migration is needed for the MVP. Store workflow fields in `ResearchSourceNote.metadata_json`:

```json
{
  "source_id": "buffett_manual_valuation_components",
  "source_label": "Buffett Indicator manual valuation components",
  "source_category": "valuation",
  "target_indicator_codes": ["buffett_indicator_us"],
  "component_role": "gdp",
  "methodology_note": "Reviewed GDP component and ratio calculation method.",
  "license_note": "Public World Bank data page reviewed manually.",
  "review_checklist": {
    "source_identity": true,
    "source_url_or_document": true,
    "date_metadata": true,
    "excerpt": true,
    "methodology": true,
    "targets": true,
    "license_note": true
  },
  "completeness": {
    "score": 7,
    "total": 7,
    "status": "complete"
  }
}
```

The service should preserve unknown existing metadata keys and merge normalized workflow keys into the stored metadata.

## Completeness Rules

MVP checklist items:

- `source_identity`: title, source name, and source type are present.
- `source_url_or_document`: `source_url` is present or excerpt indicates a reviewed source document.
- `date_metadata`: `as_of`, `published_at`, or `retrieved_at` is present.
- `excerpt`: excerpt is non-empty.
- `methodology`: note, methodology note, or calculation metadata is present.
- `targets`: source ID, target indicator codes, tags, or symbols are present.
- `license_note`: license/usage note is present when provided by the user.

Status:

- `complete`: all required review items are true.
- `partial`: at least one review item is true but required items remain missing.
- `missing`: no meaningful review item is true.

Completeness is advisory. It should not override the existing citable requirements in `ResearchSourceNoteInput`.

## Data Flow

Create flow:

1. Evidence page fetches market overview and source-readiness items.
2. Page passes source targets and initial notes to the notebook client component.
3. User selects a source target, component role, optional methodology/license notes, and target indicator codes.
4. Browser file upload still uses `File.text()` to prefill editable excerpt text.
5. Client posts existing note fields plus workflow metadata to `/api/research-source-notes`.
6. Next proxy forwards JSON to FastAPI.
7. Service validates existing note rules, normalizes metadata, computes completeness, stores row, and returns serialized metadata.

List/display flow:

1. API list returns notes with metadata.
2. Component renders source target, indicator codes, component role, completeness status, and checklist.
3. Evidence Center source-readiness area can show linked note counts or a source-linked note summary without turning guidance links into citations.

AI citation flow:

1. `list_citable_research_source_note_citations` still filters `review_status=reviewed` and `is_citable=true`.
2. `build_research_source_note_citation` includes workflow metadata fields under citation `metadata`.
3. Dashboard and assistant remain allowed-citation only; source-readiness links, seed templates, and draft notes remain non-citable.

## Compatibility

- Existing API clients can continue sending only `metadata` or no metadata.
- Existing saved notes without workflow metadata serialize with empty/missing workflow fields and should display as unlinked notes.
- The MVP avoids JSON-column SQL filtering for cross-database compatibility; client display can filter already returned recent notes.
- Existing citation IDs and route paths remain unchanged.

## Trade-offs

- Using `metadata_json` avoids a migration and keeps this MVP fast to ship. If source linkage becomes a primary query dimension later, promote fields to columns.
- Completeness is advisory instead of a hard citable gate. This preserves the current explicit review/citable workflow and avoids breaking existing valid notes.
- The task focuses on macro/source workflow rather than AI follow-up queue execution, keeping the implementation bounded.

## Rollback

- UI changes can be removed without deleting saved notes.
- Metadata keys are additive and can be ignored by older code.
- No database rollback is required because there is no new schema.
