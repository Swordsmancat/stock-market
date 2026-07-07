# Source Ingestion Hub Design

## Architecture

Add an ingestion/extraction layer beside the existing Source Notebook workflow.

Primary layers:

- Backend service: new `packages/services/source_ingestion.py` for extraction input validation, deterministic fallback extraction, LLM prompt construction, LLM response parsing, and payload normalization.
- Backend API: new `apps/api/routers/source_ingestion.py` with `POST /source-ingestion/extract`.
- API registration: include the router in `apps/api/main.py`.
- Web proxy: new Next route `apps/web/app/api/source-ingestion/extract/route.ts`.
- Frontend UI: extend `apps/web/components/research-source-notebook.tsx` with a Source Ingestion Hub / AI extraction panel above the save controls, reusing the existing form state and source target options.
- Evidence page: pass new localized labels from `apps/web/app/[locale]/evidence/page.tsx`.
- Localization: update `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Documentation: update README/manual after implementation to describe the new ingestion/extraction workflow and citation boundary.

No database migration is planned. Extraction results are review suggestions. When saved, selected suggestions are persisted through existing `ResearchSourceNote` fields and `metadata_json`.

## Backend Contract

`POST /source-ingestion/extract` accepts JSON:

```json
{
  "content": "reviewed source excerpt or pasted text",
  "filename": "optional-browser-file.md",
  "source_url": "https://optional.example/source",
  "source_id": "buffett_manual_valuation_components",
  "source_label": "Buffett Indicator manual valuation components",
  "source_category": "valuation",
  "target_indicator_codes": ["buffett_indicator_us"],
  "component_role": "gdp",
  "locale": "zh"
}
```

Response shape:

```json
{
  "status": "ok",
  "summary": "Concise reviewed-source summary.",
  "key_indicators": [
    {"label": "Buffett Indicator", "code": "buffett_indicator_us", "reason": "mentioned market cap and GDP"}
  ],
  "citation_clues": [
    {"kind": "date", "label": "as-of date", "value": "2026-07-07"}
  ],
  "follow_up_questions": [
    "Verify whether the market-cap and GDP components use the same region and period."
  ],
  "suggested_fields": {
    "title": "Buffett Indicator source review",
    "source_name": "World Bank",
    "source_type": "valuation",
    "tags": ["macro", "valuation", "buffett_indicator"],
    "target_indicator_codes": ["buffett_indicator_us"],
    "methodology_note": "Review calculation method before import.",
    "license_note": "Confirm public-source usage before AI citation.",
    "ai_follow_up": "Verify whether the market-cap and GDP components use the same region and period."
  },
  "model": {
    "provider": "openai",
    "name": "gpt-4o-mini",
    "used_llm": true,
    "fallback_reason": null
  },
  "diagnostics": [],
  "safety": {
    "not_investment_advice": true,
    "drafts_are_not_citations": true,
    "no_automated_trading": true
  }
}
```

`status` values:

- `ok`: extraction succeeded, either by LLM or deterministic fallback.
- `fallback`: deterministic fallback was used because LLM was unavailable, failed, returned empty text, or returned invalid JSON.
- `invalid_input`: request content was missing or too short to extract.

The service should bound input size before sending to the LLM. The MVP can clip staged content to a fixed prompt budget and preserve the full editable excerpt in the browser form.

## LLM Extraction

Use `get_platform_settings()` to decide whether `llm_provider=openai` and a non-empty `llm_api_key` are configured. If not, skip the provider call and return deterministic fallback.

When configured:

1. Build a prompt that describes the personal research use case, citation boundary, and allowed source-target context.
2. Ask for JSON only with the response fields above.
3. Call `get_llm_provider().generate(prompt)`.
4. Parse JSON strictly. If parsing fails or required top-level fields are absent, use deterministic fallback and append a diagnostic.
5. Normalize arrays, clip long strings, and ignore unsupported fields.

The LLM may suggest citations clues but must not create `research_source_note:<id>` citation IDs. Citation IDs are created only by existing Source Notebook save/list logic when a row is reviewed and citable.

## Deterministic Fallback

Fallback extraction should be deterministic and testable:

- Summary: first useful lines/sentences clipped to a concise paragraph.
- Key indicators: keyword/source-target matching for Buffett Indicator, market cap, GDP, CPI, M2, rates, 10Y/2Y spread, inflation, liquidity, FRED, PBOC, World Bank, SEC/filing context.
- Citation clues: URL regex, date/as-of patterns, filename, source target, methodology/calculation/source/license lines.
- Suggested fields:
  - title from filename or source label;
  - source name from source label, URL host, or existing form value;
  - source type from source category or keyword matches;
  - target indicator codes from request or source-readiness target;
  - tags from matched macro/valuation terms;
  - methodology/license notes from clue lines or safe review placeholders;
  - AI follow-up from generated questions.
- Follow-up questions: source-target-aware questions focused on review, methodology, component consistency, citation readiness, and seed-prep readiness.

## Frontend Flow

Reuse the existing Source Notebook form state:

1. User chooses a source-readiness target, uploads a browser-readable text-like file, or pastes excerpt text.
2. The form shows the selected filename and editable excerpt, as it does today.
3. User clicks an AI extraction button.
4. The component POSTs current form content and source-target context to `/api/source-ingestion/extract`.
5. The UI displays extraction status, model/fallback badge, summary, key indicators, citation clues, and follow-up questions.
6. User can apply suggestions into existing editable fields before saving:
   - note/source summary;
   - target indicator codes;
   - tags;
   - methodology note;
   - license note;
   - AI follow-up prompt.
7. User saves through the existing `/api/research-source-notes` route.

The UI must continue to make citation boundaries clear: extracted suggestions and drafts are collection notes only; only reviewed/citable saved notes become AI citations.

## Compatibility

- Existing `ResearchSourceNote` schema and API remain backward compatible.
- Existing Source Notebook save/list behavior remains unchanged.
- Existing dashboard/assistant citation payloads continue to include only reviewed/citable source notes.
- Existing research follow-up queue can use the saved `ai_follow_up` field after the note is saved.
- Inline Codex workflow skips `implement.jsonl` / `check.jsonl` curation; implementation will load specs through `trellis-before-dev`.

## Trade-offs

- Keeping PDF/OCR out of scope lets the MVP focus on the user-visible collection and AI-extraction loop without adding binary storage, parser dependency, or rights-management complexity.
- Extending the current Source Notebook component avoids duplicate draft state and keeps the save/citation boundary in one place.
- LLM extraction improves the AI feel of the workflow, while deterministic fallback keeps tests stable and the app useful without API keys.

## Rollback

- Remove the new source-ingestion router/proxy and extraction UI controls.
- Leave existing Source Notebook rows untouched because extraction suggestions are persisted only when the user saves through the existing note API.
- No migration rollback is required.
