# Assistant Research Citation Contract

## Scenario: Research Evidence and Citation-Enriched Market Assistant

### 1. Scope / Trigger

- Trigger: `POST /assistant/market` now returns enriched research citations and diagnostics built from existing platform evidence.
- Scope: assistant service logic in `packages/services/market_assistant.py`, prompt/citation validation in `packages/ai/market_assistant.py`, FastAPI route behavior in `apps/api/routers/assistant.py`, frontend route/card consumers under `apps/web`, and focused assistant tests.
- Non-goals: production filings/transcripts/announcements ingestion, embeddings/vector search, raw document corpus storage, streaming responses, watchlist-level monitoring, paid research entitlements, or direct trading recommendations.

### 2. Signatures

- API: `POST /assistant/market`
- Service entry: market-assistant payload builder in `packages/services/market_assistant.py`
- AI generation: prompt construction and citation validation in `packages/ai/market_assistant.py`
- Response fields preserved: `answer_markdown`, `model`, `context`, `citations`, `diagnostics`, `safety`
- Citation required fields: `id`, `label`, `source`
- Citation optional fields: `url`, `source_type`, `as_of`, `provider`, `retrieved_at`, `excerpt`, `metadata`
- Diagnostic required fields: `source`, `status`, `message`
- Diagnostic optional fields: `severity`, `code`, `citation_id`, `details`

### 3. Contracts

- Daily bars remain the core evidence gate. If required market data is unavailable, the assistant must return `no_data` / degraded-safe output and avoid LLM generation.
- Existing top-level response fields and old minimal citation payloads must remain backward compatible.
- Evidence may come from existing platform sources only: daily bars, stored technical indicators, stored macro / valuation indicator observations, fundamentals snapshots, news / sentiment payloads, generated reports, reviewed/citable research source notebook entries, and persisted/citable `MarketDailyEvidenceEvent` rows.
- Missing optional sources must produce diagnostics, not fabricated evidence or fake citations.
- Citation IDs must be deterministic and source-specific, such as `bars_1d:{symbol}:{as_of}`, `technical_indicators:{symbol}:{as_of}`, `market_indicator:{code}:{as_of}`, `fundamentals:{symbol}:{as_of}`, `news:{symbol}:...`, `generated_report:{id}`, `research_source_note:{id}`, or `market_daily_event:{event_type}:{identity}:{trade_date}`.
- `market_daily_event:*` citations are allowed only for persisted rows with `is_citable=true`. Live `/market-daily-data/*` and `/sectors/hot` payloads remain non-citable even when their provider status is `ok` or `degraded`.
- `market_indicator:*` citations are allowed only for stored local macro / valuation observations with value, as-of date, and source metadata. Official source status rows, collection links, seed templates, and missing indicator rows remain guidance or diagnostics only.
- LLM prompts must list available citation IDs and instruct the model to use only those IDs.
- LLM output citation IDs must be validated against the payload citations. Unknown IDs must produce `CITATION_UNKNOWN_ID` diagnostics and should fall back to deterministic output when needed.
- Diagnostics may include safe severity/code metadata, but must not include API keys, prompt internals, stack traces, raw provider secrets, or hidden chain-of-thought.
- The assistant must preserve no-investment-advice and no direct buy/sell/hold/target-price/position-sizing/execution-instruction boundaries.

### 4. Validation & Error Matrix

- Core daily bars unavailable -> response does not call LLM; returns no-data/degraded diagnostics.
- Optional indicators/fundamentals/news/reports missing -> non-blocking diagnostics such as `SOURCE_NO_DATA` or `SOURCE_OMITTED`.
- Optional macro / valuation indicators missing -> non-blocking `MACRO_INDICATOR_NO_DATA` diagnostics; no `market_indicator:*` citation is emitted until a local observation exists.
- Source service failure -> sanitized `SOURCE_UNAVAILABLE` diagnostics; no raw secret or stack trace.
- Draft or non-citable research source notes -> remain collection records; they are not included in allowed assistant citation IDs.
- Official source readiness/status rows -> remain maintenance guidance; they are not included in allowed assistant citation IDs.
- Live market daily rows, mock/static sector fixtures, or unknown `market_daily_event:*` IDs -> remain context or diagnostics; they are not accepted as stored evidence citations.
- LLM returns unknown inline citation ID -> `CITATION_UNKNOWN_ID` diagnostic and degraded/fallback output; unknown citation is not presented as valid.
- User asks for direct trading instruction -> assistant refuses/reframes per safety policy.
- Old frontend payload with only `id`, `label`, `source`, `url` citations -> still renders.
- Citation URL present -> frontend renders safe link without changing backend API contract.

### 5. Good/Base/Bad Cases

- Good: daily bars, technical indicators, stored macro observations, fundamentals, news, a generated report, and reviewed/citable source notebook entries are available; response contains deterministic citation IDs, optional metadata/excerpts, compact diagnostics, and an answer using only known citation IDs.
- Base: only daily bars are available; answer remains traceable to bars and diagnostics state missing optional sources.
- Bad: a missing filing/transcript is represented as a live citation. These sources are not production integrations in this slice.
- Bad: `fred`, `world_bank`, source-readiness IDs, collection links, or seed-template IDs are cited instead of stored `market_indicator:{code}:{as_of}` observations.
- Bad: an LLM-invented citation ID is rendered as if it existed in `citations`.
- Bad: direct buy/sell/hold advice, target prices, or position sizing is emitted because citations exist.

### 6. Tests Required

- Service/AI tests assert citations are generated for available bars, indicators, stored macro observations, fundamentals, news, generated reports, reviewed/citable research source notes, and persisted/citable market daily events.
- Service tests assert missing optional evidence produces diagnostics rather than fabricated citation items.
- Service tests assert missing macro observations produce diagnostics rather than fabricated `market_indicator:*` citation items.
- AI tests assert unknown LLM citation IDs are detected and handled with diagnostics/fallback behavior.
- AI/dashboard/research-brief tests assert unknown `market_daily_event:*` IDs are rejected and live provider rows never enter the allowed citation list.
- API tests assert backward compatibility and enriched optional fields.
- Frontend route/card tests assert citation links, metadata, diagnostic severity/code, and legacy rendering.
- Safety tests assert direct trading instructions are refused or reframed.
- Full validation should include assistant-focused backend tests, assistant-focused frontend tests, `python -m pytest -q`, and `npm run test:web`.

### 7. Wrong vs Correct

#### Wrong

```python
citations.append({
    "id": "filing:AAPL:latest",
    "label": "Latest filing",
    "source": "filings",
})
```

This fabricates a production filing source when no filings provider exists.

#### Correct

```python
diagnostics.append({
    "source": "filings",
    "status": "omitted",
    "severity": "info",
    "code": "SOURCE_OMITTED",
    "message": "Production filings retrieval is not configured for this assistant slice.",
})
```

#### Wrong

```python
citations.append({
    "id": "source_status:fred",
    "label": "FRED US macro source",
    "source": "official_source_status",
})
```

This turns refresh readiness into evidence before a validated local macro observation exists.

#### Correct

```python
citations.append({
    "id": f"market_indicator:{code}:{as_of}",
    "label": indicator_name,
    "source": "market_indicators",
    "source_type": "macro_indicator",
})
```

This cites the stored local observation. Missing official-source coverage should be reported as diagnostics or UI guidance, not as an assistant citation.

## Scenario: Reviewed Source Notebook Citations

### 1. Scope / Trigger

- Trigger: `/evidence` can persist user-reviewed hard-to-find research source notes and expose only reviewed/citable rows to dashboard and assistant evidence.
- Scope: `ResearchSourceNote` in `packages/domain/models.py`, migration `0011_research_source_notes`, service logic in `packages/services/research_source_notes.py`, FastAPI router `apps/api/routers/research_source_notes.py`, Next proxy/UI under `apps/web`, dashboard citation assembly in `packages/services/market_dashboard.py`, and assistant citation assembly in `packages/services/market_assistant.py`.
- Non-goals: scraping, scheduled crawling, OCR/PDF parsing, raw binary file storage, licensed corpus ingestion, vector search, multi-user permissions, trading advice, target prices, position sizing, or broker execution.

### 2. Signatures

- DB table: `research_source_notes`
- Model fields: `id`, `title`, `source_url`, `source_name`, `source_type`, `symbols_json`, `tags_json`, `published_at`, `as_of`, `retrieved_at`, `excerpt`, `note`, `ai_follow_up`, `review_status`, `is_citable`, `metadata_json`, `created_at`, `updated_at`
- Service input: `ResearchSourceNoteInput`
- Additive service/API workflow fields: `source_id`, `source_label`, `source_category`, `target_indicator_codes`, `component_role`, `methodology_note`, `license_note`
- Workflow storage keys in `metadata_json`: `source_id`, `source_label`, `source_category`, `target_indicator_codes`, `component_role`, `methodology_note`, `license_note`, `review_checklist`, `completeness`
- Review checklist keys: `source_identity`, `source_url_or_document`, `date_metadata`, `excerpt`, `methodology`, `targets`, `license_note`
- Completeness payload: `{ "score": int, "total": int, "status": "complete" | "partial" | "missing" }`
- Service create: `create_research_source_note(payload, *, session)`
- Service list: `list_research_source_notes(*, session, limit=50, review_status=None, source_type=None, citable_only=False)`
- Citation list: `list_citable_research_source_note_citations(*, session, symbols=None, limit=6)`
- API: `GET /research-source-notes`, `POST /research-source-notes`
- Web proxy: `GET/POST /api/research-source-notes`
- Citation ID prefix: `research_source_note:`

### 3. Contracts

- `title`, `source_name`, and `source_type` are required.
- At least one of `source_url` or `excerpt` is required for every row.
- When `source_url` is provided, it must be an absolute `http://` or `https://` URL.
- `review_status` must be one of `draft`, `reviewed`, or `archived`.
- `is_citable=true` requires `review_status=reviewed`, a non-empty reviewed excerpt, and either `source_url` or `source_name` plus date metadata (`as_of` or `published_at`).
- Browser upload is client-side text extraction into editable fields. The backend receives JSON only and stores reviewed excerpt/note text, not raw files.
- Tags are trimmed and de-duplicated. Symbols are trimmed, de-duplicated, and uppercased.
- Source Notebook entries may link to information-source readiness IDs such as `fred_us_rates`, `pboc_cn_m2_public_manual`, or `buffett_manual_valuation_components`. If a known `source_id` is provided and `target_indicator_codes` is empty, the service derives target indicator codes from that readiness source's seed template, indicator codes, or coverage.
- Workflow metadata is additive and stored in `metadata_json`; unknown existing metadata keys must be preserved.
- Review completeness is advisory. `review_checklist` and `completeness` help users prepare source evidence, but they do not automatically import macro observations and do not override the explicit `reviewed + is_citable` citation gate.
- AI citation payloads may include `url`, `as_of`, `provider`, `retrieved_at`, clipped `excerpt`, and metadata for source name/type, symbols, tags, review status, source linkage, target indicator codes, component role, methodology/license notes, and completeness state.
- Dashboard and assistant citation builders must request only reviewed/citable notebook entries. Draft, archived, and non-citable notes remain visible in the notebook but are not allowed citation IDs.
- Symbol filtering is advisory: if requested symbols are present and a note has symbols, include only notes whose symbols intersect; untagged citable notes may still serve as general macro/context evidence.
- Evidence Center UI may display source-linked notebook entries near the matching source-readiness card. Those linked notebook entries remain collection/review records unless the row also satisfies `reviewed + is_citable`.

### 4. Validation & Error Matrix

- Missing `title`, `source_name`, or `source_type` -> validation error / HTTP 422.
- Missing both `source_url` and `excerpt` -> validation error / HTTP 422.
- `source_url` uses an unsafe or relative scheme -> validation error / HTTP 422.
- Unknown `review_status` -> validation error / HTTP 422.
- `is_citable=true` with `review_status!=reviewed` -> validation error / HTTP 422.
- `is_citable=true` without excerpt -> validation error / HTTP 422.
- `is_citable=true` without `source_url` and without date metadata -> validation error / HTTP 422.
- Oversized excerpt/note fields -> service clips to the configured prompt/storage limits rather than expanding AI context unbounded.
- Unknown `source_id` -> preserve the user-provided ID in metadata without deriving label/category/target codes.
- Known `source_id` with no explicit targets -> derive target indicator codes from the source-readiness registry.
- Incomplete checklist -> return `completeness.status="partial"` or `"missing"` without failing creation.
- Source note creation succeeds -> market overview cache is cleared so the dashboard can pick up new citable evidence.

### 5. Good/Base/Bad Cases

- Good: a reviewed Buffett Indicator component note with source URL, excerpt, tags, symbols, source-readiness link, target indicator codes, and `is_citable=true` appears as `research_source_note:<uuid>` in dashboard/assistant allowed citations with workflow metadata.
- Good: a draft browser-upload excerpt is saved and visible in `/evidence`, but no AI prompt receives its citation ID.
- Good: a FRED-linked note with `source_id="fred_us_rates"` and no explicit targets stores the seed template's rates indicator codes as review guidance.
- Base: a reviewed note without symbol tags can support general macro/valuation context when citable.
- Base: a complete checklist on a draft note shows source-review readiness but still remains outside assistant/dashboard allowed citations.
- Bad: uploaded raw file bytes are persisted or treated as a managed document corpus.
- Bad: a draft link or source-readiness collection URL is included as a dashboard or assistant citation.
- Bad: a source-readiness ID, seed template, or linked notebook draft is cited as evidence before a reviewed/citable local row or imported observation exists.
- Bad: a source notebook citation is used to produce buy/sell/hold, target price, position sizing, or execution advice.

### 6. Tests Required

- Domain/migration tests assert `research_source_notes` schema exists and model metadata aligns with `Base.metadata.create_all()`.
- Service tests cover create/list, normalization, URL-scheme validation, validation failures, citable-only listing, citation ID prefix, excerpt clipping, workflow metadata storage, registry-derived targets, completeness calculation, citation metadata, and draft/non-citable exclusion.
- API tests cover `GET /research-source-notes`, `POST /research-source-notes`, additive workflow fields, HTTP 422 validation, and cache-clearing metadata.
- Frontend route tests cover proxy status/content-type/payload forwarding for list and create.
- Component/page tests cover paste entry, browser file text prefill, source target selection, component role, target indicator display, review checklist/completeness, linked source-readiness summaries, status/citable controls, saved-entry display, filters, localized labels, and error/success states.
- Dashboard and assistant tests assert reviewed/citable source notes are included in allowed citations with workflow metadata and draft/non-citable rows are excluded.

### 7. Wrong vs Correct

#### Wrong

```python
citations.append({
    "id": f"research_source_note:{note.id}",
    "label": note.title,
    "source": "research_source_notes",
})
```

This cites any notebook row regardless of review state or excerpt quality.

#### Correct

```python
citations = list_citable_research_source_note_citations(session=session, symbols=[symbol])
```

This centralizes the `reviewed` plus `is_citable` boundary and applies the stable `research_source_note:<id>` prefix.

## Scenario: Source Ingestion Extraction

### 1. Scope / Trigger

- Trigger: `/evidence` can request LLM-assisted extraction for pasted or browser-uploaded text before saving a Source Notebook entry.
- Scope: extraction service in `packages/services/source_ingestion.py`, FastAPI route `apps/api/routers/source_ingestion.py`, Next proxy `apps/web/app/api/source-ingestion/extract/route.ts`, Source Notebook UI, localization, and focused backend/frontend tests.
- Non-goals: PDF/OCR parsing, raw binary storage, automatic web scraping, persistent document corpus, vector search, automatic macro observation import, full AI recommendation panels, or trading recommendations.

### 2. Signatures

- API: `POST /source-ingestion/extract`
- Web proxy: `POST /api/source-ingestion/extract`
- Service input: `SourceIngestionExtractionInput`
- Request fields:
  - `content: str`
  - `filename?: str`
  - `source_url?: str`
  - `source_id?: str`
  - `source_label?: str`
  - `source_category?: str`
  - `target_indicator_codes?: list[str]`
  - `component_role?: str`
  - `locale: "en" | "zh"`
- Response fields:
  - `status: "ok" | "fallback" | "invalid_input"`
  - `summary: str`
  - `key_indicators: list[{ label, code, reason }]`
  - `citation_clues: list[{ kind, label, value }]`
  - `follow_up_questions: list[str]`
  - `suggested_fields: { title, source_name, source_type, tags, target_indicator_codes, methodology_note, license_note, ai_follow_up }`
  - `model: { provider, name, used_llm, fallback_reason }`
  - `diagnostics: list[{ source, status, severity, code, message, details? }]`
  - `safety: { not_investment_advice, drafts_are_not_citations, no_automated_trading }`

### 3. Contracts

- Browser file reading remains client-side text extraction into editable fields. The backend receives JSON only.
- LLM extraction may run only when `get_platform_settings()` reports `llm_provider == "openai"` and a non-empty `llm_api_key`.
- Use `get_llm_provider()` for generation so tests can monkeypatch the provider without live network calls.
- LLM prompts must request JSON only and must tell the model not to invent market data, source URLs, dates, citation IDs, buy/sell/hold calls, target prices, or position sizing.
- The service must bound content before prompting the LLM and must normalize/clamp returned strings and arrays.
- LLM extraction suggestions are collection guidance only. They must not create `research_source_note:<id>` IDs and must not mark notes reviewed or citable.
- The UI may apply suggestions into editable Source Notebook fields, but saving still uses the existing `POST /research-source-notes` review/citation gate.
- Extraction metadata may be saved inside `ResearchSourceNote.metadata_json` for auditability, but it does not alter source-note citation eligibility.

### 4. Validation & Error Matrix

- Empty or too-short `content` -> response `status="invalid_input"` with `SOURCE_INGESTION_CONTENT_REQUIRED`; no LLM call.
- LLM not configured -> deterministic response `status="fallback"` with `SOURCE_INGESTION_FALLBACK_USED`.
- LLM raises -> deterministic fallback with sanitized reason `LLM extraction failed: <ExceptionClass>.`
- LLM returns empty content -> deterministic fallback.
- LLM returns invalid JSON or unsupported required structure -> deterministic fallback.
- Staged content mentions broad macro terms -> fallback may suggest indicators, but should prefer selected source-target codes over ambiguous regional guesses.
- Extraction suggestions saved to a draft note -> note remains non-citable unless the existing source-note validation passes `reviewed + is_citable`.

### 5. Good/Base/Bad Cases

- Good: a Buffett Indicator source excerpt plus `source_id="buffett_manual_valuation_components"` returns a summary, Buffett indicator code suggestions, market-cap/GDP citation clues, and follow-up questions; applying them fills editable fields only.
- Good: an OpenAI-compatible provider returns valid JSON and the response has `model.used_llm=true`.
- Base: no LLM key is configured; deterministic extraction still suggests tags, target codes, methodology/license placeholders, and follow-up questions.
- Base: source target is selected but source name is incomplete; applying suggestions may replace the target label with an actual source name such as World Bank.
- Bad: extraction output creates a `research_source_note:<id>` before saving a reviewed/citable note.
- Bad: an LLM-suggested source URL or date is treated as verified evidence without user review.
- Bad: extracted follow-up questions are presented as completed AI recommendations or trading actions.

### 6. Tests Required

- Service tests assert deterministic fallback without LLM configuration, LLM success with a fake provider, invalid-JSON fallback, invalid-input status, macro/valuation indicator suggestions, and sanitized diagnostics.
- API tests assert `POST /source-ingestion/extract` returns the extraction contract and invalid-input payload.
- Web proxy tests assert method/body/status/content-type forwarding.
- Component tests assert browser text can be extracted, extraction results render, applying suggestions updates editable fields, and the citable checkbox remains off.
- Existing Source Notebook service/API tests must continue to prove draft/non-citable notes are excluded from AI citations.

### 7. Wrong vs Correct

#### Wrong

```python
return {
    "citation_id": f"research_source_note:{uuid4()}",
    "summary": generated_summary,
}
```

This turns an extraction suggestion into evidence before the user reviewed and saved a citable Source Notebook row.

#### Correct

```python
return {
    "status": "fallback",
    "summary": summary,
    "suggested_fields": {"ai_follow_up": follow_up_question},
    "safety": {"drafts_are_not_citations": True},
}
```

The extraction result stays editable guidance. Citation IDs remain owned by the existing reviewed/citable Source Notebook contract.

## Scenario: Citation-aware Dashboard Brief Narrative

### 1. Scope / Trigger

- Trigger: `GET /dashboard/market-overview` returns an additive `dashboard_brief.narrative` payload.
- Scope: dashboard service logic in `packages/services/market_dashboard.py`, dashboard API tests, homepage local payload types/rendering, and dashboard documentation.
- Non-goals: new external macro adapters, filings/transcript ingestion, vector search, persisted brief history, broker execution, terminal parity, or trading instructions.

### 2. Signatures

- API: `GET /dashboard/market-overview`
- Service entry: `get_market_overview_payload(...)`
- Existing `dashboard_brief` fields preserved: `status`, `generated_at`, `sections`, `citations`, `diagnostics`, `safety`
- Additive field: `dashboard_brief.narrative`
- Narrative fields:
  - `answer_markdown`
  - `model.provider`
  - `model.name`
  - `model.used_llm`
  - `model.fallback_reason`
  - `context.source_mix.macro_citations`
  - `context.source_mix.report_citations`
  - `context.source_mix.news_citations`
  - `context.source_mix.research_source_note_citations`
  - `context.source_mix.information_source_gaps`

### 3. Contracts

- The narrative may summarize only existing dashboard brief sections, dashboard citations, dashboard diagnostics, safety flags, and information-source readiness gaps.
- LLM generation is allowed only when `get_platform_settings()` reports `llm_provider == "openai"` and a non-empty `llm_api_key`.
- Use `get_llm_provider()` for generation so tests can monkeypatch the provider without live network calls.
- LLM prompts must list the allowed citation IDs and instruct the model to use only those IDs.
- `needs_adapter`, `needs_manual_seed`, `no_data`, and `future` information-source items are context gaps/next actions, not citations.
- Missing LLM configuration, provider errors, empty responses, or unknown inline citation IDs must return deterministic fallback metadata:
  - `provider = "deterministic"`
  - `name = "dashboard-brief-deterministic-fallback"`
  - `used_llm = false`
  - `fallback_reason = <sanitized reason>`
- Diagnostics may include safe codes such as `FALLBACK_USED` and `CITATION_UNKNOWN_ID`, but must not include API keys, hidden prompts, raw stack traces, or provider secrets.

### 4. Validation & Error Matrix

- No OpenAI-compatible provider/API key -> deterministic fallback, `FALLBACK_USED`.
- LLM provider raises -> deterministic fallback with sanitized `LLM generation failed: <ExceptionClass>.`
- LLM returns empty/whitespace -> deterministic fallback.
- LLM response cites an ID not present in `dashboard_brief.citations` -> `CITATION_UNKNOWN_ID` diagnostic and deterministic fallback.
- Information-source registry has missing adapters/manual seeds/future entries -> increment `information_source_gaps`; do not add citations for those entries.
- Old clients ignore `dashboard_brief.narrative` -> existing fields remain usable.

### 5. Good/Base/Bad Cases

- Good: macro observation, generated report, and news citations exist; LLM returns markdown using only those citation IDs; `used_llm=true`.
- Base: no LLM configured; deterministic narrative summarizes available sections and source gaps with fallback metadata.
- Base: no citable dashboard evidence exists; deterministic or LLM narrative may state the limitation but must not invent citations.
- Bad: source-readiness entry such as `fred_us_rates` is cited as `[fred_us_rates]` before an adapter/seed creates actual evidence.
- Bad: LLM output with `[generated_report:not-present]` is rendered as valid evidence.
- Bad: narrative produces buy/sell/hold, target price, position sizing, or execution advice.

### 6. Tests Required

- Service test for no LLM config asserting deterministic fallback metadata, `FALLBACK_USED`, and source-mix gap counts.
- Service test for LLM success with monkeypatched settings/provider asserting `used_llm=true` and known citation use.
- Service test for unknown citation IDs asserting `CITATION_UNKNOWN_ID` and deterministic fallback.
- API test asserting `dashboard_brief.narrative` is present without breaking existing fields.
- Frontend homepage test asserting narrative markdown-ish text, model/fallback state, citations, and diagnostics remain visible.

### 7. Wrong vs Correct

#### Wrong

```python
return {
    "id": "fred_us_rates",
    "label": "FRED US Treasury rates",
    "source": "information_sources",
}
```

This turns source readiness into evidence before a configured adapter or audited seed observation exists.

#### Correct

```python
diagnostics.append({
    "source": "information_sources",
    "status": "needs_adapter",
    "severity": "warning",
    "code": "FRED_US_RATES_NEEDS_ADAPTER",
    "message": "FRED US rates need an adapter or reviewed seed import before they can be cited.",
})
```

## Scenario: Research Follow-up Queue

### 1. Scope / Trigger

- Trigger: `GET /dashboard/market-overview` returns an additive `research_follow_up_queue` payload for the Evidence Center.
- Scope: queue derivation in `packages/services/research_follow_up_queue.py`, dashboard aggregation in `packages/services/market_dashboard.py`, Evidence Center payload typing/rendering under `apps/web`, and focused service/API/page tests.
- Non-goals: LLM execution of follow-up prompts, selected-item AI brief generation, persistent queue tables, alerts/scheduling, scraping/OCR/vector search/document corpus storage, production filings/transcripts ingestion, or trading recommendations.

### 2. Signatures

- Service helper: `build_research_follow_up_queue(*, notes, information_sources_payload, generated_at=None, limit=20, diagnostics=None)`
- Dashboard API: `GET /dashboard/market-overview`
- Additive response field: `research_follow_up_queue`
- Queue item kind values: `source_review`, `seed_prep`, `ai_summary_question`, `source_gap`, `research_note`
- Queue item citation policy values: `citable`, `collection_only`, `guidance_only`

### 3. Contracts

- Queue items are derived workflow actions, not evidence by default.
- Source Notebook `ai_follow_up` creates `ai_summary_question` items but does not call an LLM.
- A queue item may expose `citation_id="research_source_note:<id>"` only when the underlying Source Notebook row is already `reviewed`, `is_citable=true`, and has that existing citation ID.
- Draft, archived, and non-citable Source Notebook rows may create collection/review tasks but must not expose citation IDs.
- Source-readiness statuses `needs_adapter`, `needs_manual_seed`, `no_data`, and `future` may create `source_gap` actions.
- Seed templates and manual-seed sources may create `seed_prep` actions.
- Source-readiness links, seed templates, template rows, source IDs, and readiness gap IDs must remain `guidance_only` and must never appear in dashboard or assistant citation lists.
- Queue summary counts should be based on all derived items; returned items may be capped by the service limit.

### 4. Validation & Error Matrix

- Source Notebook lookup fails -> queue returns `status="degraded"` with sanitized `SOURCE_UNAVAILABLE` diagnostics and no fabricated note items.
- Empty notes and no source gaps -> queue returns an empty item list with safety flags intact.
- Non-citable note has `ai_follow_up` -> queue item uses `citation_policy="collection_only"` and omits `citation_id`.
- Reviewed/citable note has `ai_follow_up` -> queue item may include the existing `research_source_note:<id>` citation ID.
- Source-readiness gap or seed template exists -> queue item uses `citation_policy="guidance_only"` and omits `citation_id`.
- Unknown item kind or policy reaches frontend -> frontend may display the raw value, but must not infer citation permission from unknown values.

### 5. Good/Base/Bad Cases

- Good: a reviewed/citable Buffett component note with `ai_follow_up`, source linkage, target indicator code, component role, and complete checklist appears as an AI-summary question with `research_source_note:<id>`.
- Good: a draft FRED-linked note with `ai_follow_up` appears as collection-only review work and has no citation ID.
- Good: `fred_us_rates` with `needs_adapter` appears as a source-gap action that points to adapter/seed work without becoming evidence.
- Base: seed-template readiness appears as seed-prep guidance even when no linked notes are ready.
- Bad: `fred_us_rates`, `seed_template:fred_us_rates`, or a collection link appears as a citation ID.
- Bad: queue rendering implies the LLM has already summarized or executed the follow-up item.
- Bad: queue items produce buy/sell/hold, target price, position sizing, or execution instructions.

### 6. Tests Required

- Service tests assert queue derivation for citable notes, non-citable notes, source-review tasks, seed-prep tasks, source gaps, summary counts, and limit behavior.
- Dashboard service/API tests assert `research_follow_up_queue` is additive on `GET /dashboard/market-overview`.
- Citation-boundary tests assert draft/non-citable notes and source-readiness/seed-template items never expose citation IDs.
- Frontend page tests assert localized queue labels, citation-policy rendering, metadata chips, and no-trading-advice safety wording.
- Type-check should cover the shared `ResearchFollowUpQueuePayload` frontend contract.

### 7. Wrong vs Correct

#### Wrong

```python
items.append({
    "id": "source_gap:fred_us_rates",
    "kind": "source_gap",
    "citation_policy": "citable",
    "citation_id": "fred_us_rates",
})
```

This turns a source-readiness gap into evidence before a local observation or reviewed/citable note exists.

#### Correct

```python
items.append({
    "id": "source_gap:fred_us_rates",
    "kind": "source_gap",
    "citation_policy": "guidance_only",
    "next_action": "Add an official-source adapter or reviewed seed import.",
})
```

This keeps the queue item actionable while preserving the citation boundary.

## Scenario: Saved Research Brief Inbox

### 1. Scope / Trigger

- Trigger: `/evidence` can generate and persist saved AI research briefs from the current Evidence Center context.
- Scope: `ResearchBrief` in `packages/domain/models.py`, migration `0012_research_briefs`, service logic in `packages/services/research_briefs.py`, FastAPI router `apps/api/routers/research_briefs.py`, Next proxy/UI under `apps/web`, and focused service/API/component/page tests.
- Non-goals: professional trading-terminal parity, scheduled scraping, raw document corpus storage, vector search, automatic external source ingestion, licensed research storage, buy/sell/hold calls, target prices, position sizing, or trade execution.

### 2. Signatures

- DB table: `research_briefs`
- Model fields: `id`, `title`, `brief_type`, `scope_json`, `content_markdown`, `citations_json`, `source_summary_json`, `diagnostics_json`, `model_json`, `safety_json`, `created_at`
- Service input: `ResearchBriefGenerateInput`
- Service create: `generate_and_store_research_brief(payload, *, session)`
- Service list: `list_research_briefs(*, session, limit=20)`
- Serializer: `serialize_research_brief(brief)`
- API: `GET /research-briefs?limit=20`
- API: `POST /research-briefs/generate`
- Web proxy: `GET /api/research-briefs`
- Web proxy: `POST /api/research-briefs`
- Request fields: `provider?: str`, `locale?: "en" | "zh"`, `title?: str`
- Allowed saved-brief citation ID prefixes: `market_indicator:`, `generated_report:`, `news:`, `research_source_note:`

### 3. Contracts

- Saved briefs are generated from current `get_market_overview_payload(...)` context: dashboard brief sections/citations/diagnostics, information-source readiness gaps, and research follow-up queue items.
- `research_briefs` is the durable history table for Evidence Center research summaries. Do not overload symbol-oriented `generated_reports` for this workflow.
- `limit` on list is bounded to `1..100`; default is `20`.
- `locale` normalizes to `zh` only for exact `zh`; every other value becomes `en`.
- `title` is optional and clipped to 180 characters in service input; missing titles use a generated Evidence Center timestamp title.
- LLM generation may run only when `get_platform_settings()` reports `llm_provider == "openai"` and a non-empty `llm_api_key`.
- Use `get_llm_provider()` for generation so tests can monkeypatch the provider without live network calls.
- LLM prompts must list allowed citation IDs and instruct the model to use only those IDs.
- Source-readiness entries, seed templates, draft notes, browser-upload suggestions, and follow-up queue items without an existing allowed citation ID are gaps/prompts, not evidence citations.
- LLM output is acceptable only when inline citation IDs with the allowed prefixes are present in the assembled citation list.
- Persisted payloads must include `content_markdown`, allowed `citations`, `source_summary`, sanitized `diagnostics`, `model`, and `safety` metadata.
- Safety metadata must preserve the personal research boundary: not investment advice, no buy/sell/hold, no target price, no position sizing, no automated trading, and no fabricated macro data.

### 4. Validation & Error Matrix

- Missing OpenAI-compatible provider/API key -> deterministic fallback with `RESEARCH_BRIEF_FALLBACK_USED`.
- LLM provider raises -> deterministic fallback with sanitized reason `LLM generation failed: <ExceptionClass>.`
- LLM returns empty/whitespace -> deterministic fallback.
- LLM returns an inline citation ID with an allowed prefix but not present in assembled citations -> `CITATION_UNKNOWN_ID` diagnostic and deterministic fallback.
- LLM references a source-readiness ID, seed-template ID, draft note, upload suggestion, or queue-only item as evidence -> reject by citation validation or keep it as a source gap/research prompt.
- Dashboard brief or follow-up queue diagnostics are present -> include sanitized diagnostics in the saved brief; do not expose API keys, hidden prompts, raw stack traces, or provider secrets.
- No local citations exist -> saved brief may still be stored, but content must state the evidence limitation and must not invent citation IDs.
- Frontend generation request fails -> UI shows a failure state and does not append a fabricated brief.

### 5. Good/Base/Bad Cases

- Good: current Evidence Center context includes a Buffett Indicator macro observation and a reviewed/citable Source Notebook note; the saved brief cites only `market_indicator:...` and `research_source_note:...` IDs already present in dashboard citations.
- Good: an OpenAI-compatible provider returns concise markdown with only known citation IDs; the stored `model.used_llm` is `true`.
- Base: no LLM is configured; deterministic fallback stores summary, key evidence, source/data gaps, follow-up questions, diagnostics, and safety metadata.
- Base: source-readiness gaps for Buffett components or macro adapters appear in `source_summary.source_gaps` and the markdown's gap section, not in `citations`.
- Bad: `buffett_manual_valuation_components`, `seed_template:fred_us_rates`, or a browser-upload suggestion appears as a saved-brief citation.
- Bad: an LLM-invented `[market_indicator:not-present:2026-07-01]` is persisted as valid evidence.
- Bad: the saved brief emits a buy/sell/hold recommendation, target price, position size, or execution instruction because citable evidence exists.

### 6. Tests Required

- Domain/migration tests assert `research_briefs` schema exists with JSON/markdown/model/safety columns and aligns with `Base.metadata.create_all()`.
- Service tests assert deterministic fallback without LLM configuration, successful LLM storage with a fake provider, unknown citation fallback, title/locale normalization, citation/source mix summaries, saved safety metadata, and recent list ordering/limit behavior.
- API tests assert `GET /research-briefs` list behavior and `POST /research-briefs/generate` stores and returns a saved brief.
- Web proxy tests assert list/generate method, body, query, status, content-type, and no-store forwarding.
- Component/page tests assert `/evidence` renders the inbox, empty/load-failed states, generate action, generated/fallback model labels, brief markdown, counts, diagnostics, and safety badges.
- Full validation should include focused research-brief backend tests, focused web tests, `python -m pytest -q`, `npm run test:web`, TypeScript, ruff for touched Python files, JSON message parsing, and `git diff --check`.

### 7. Wrong vs Correct

#### Wrong

```python
brief = ResearchBrief(
    title="AI summary",
    citations_json=[{"id": "buffett_manual_valuation_components"}],
    content_markdown="Buffett source is ready [buffett_manual_valuation_components].",
)
```

This turns source-readiness guidance into persisted evidence before a local observation or reviewed/citable note exists.

#### Correct

```python
brief = ResearchBrief(
    title=title,
    citations_json=assembled["citations"],
    source_summary_json=assembled["source_summary"],
    content_markdown=generated["content_markdown"],
    safety_json=_safety_payload(),
)
```

The saved brief stores only the assembled, validated local citations and keeps source-readiness work in the gap summary.

## Scenario: Information Source Collection Guidance

### 1. Scope / Trigger

- Trigger: `GET /dashboard/market-overview` includes additive source-readiness collection guidance fields from `get_information_source_readiness_payload(...)`.
- Scope: source definitions in `packages/services/information_sources.py`, dashboard aggregation in `packages/services/market_dashboard.py`, API compatibility tests, homepage rendering, and user documentation.
- Non-goals: live FRED/PBOC/SEC adapters, scraping, document ingestion, licensed corpus storage, vector search, broker features, or professional trading-terminal parity.

### 2. Signatures

- Service entry: `get_information_source_readiness_payload(session=...)`
- Source item existing fields preserved: `id`, `label`, `category`, `authority`, `status`, `freshness_policy`, `ai_usage`, `next_action`, `evidence_count`, `latest_as_of`, `coverage`
- Additive source item fields:
  - `collection_note: str`
  - `citation_policy: str`
  - `collection_links: list[{ label: str, url: str, source_type: str }]`
- These fields appear in both `information_sources.items[]` and grouped `information_sources.groups[].items[]` because groups reuse the source item payloads.

### 3. Contracts

- Collection links are source-gathering guidance only. They must not be copied into `dashboard_brief.citations` or assistant `citations` unless an audited local evidence object exists.
- Citable evidence still comes from configured local sources such as `MarketIndicatorObservation`, `GeneratedReport`, and `NewsArticle`.
- `needs_adapter`, `needs_manual_seed`, `no_data`, and `future` statuses keep their existing meaning after collection guidance is added.
- `future` document sources such as filings/transcripts must remain non-citeable until ingestion, licensing, storage, and citation metadata are implemented.
- Tests must not fetch collection links or depend on external network availability.
- Frontend links must use safe external navigation (`target="_blank"` and `rel="noreferrer"`).
- Documentation must state that this is not scraping, not automatic ingestion, not licensed document storage, and not investment advice.

### 4. Validation & Error Matrix

- Source has collection links but no local observations -> source remains `needs_adapter` or `needs_manual_seed`, not `configured`.
- Future SEC/document source has official search links -> source remains `future`; no dashboard citation is created.
- Generated reports/news exist locally -> those evidence-backed sources may become `configured`; collection guidance remains descriptive metadata.
- Old consumers ignore collection guidance fields -> existing readiness payload remains backward compatible.

### 5. Good/Base/Bad Cases

- Good: FRED rates source lists DGS10/DGS2/T10Y2Y official links and says rates become citeable only after reviewed observations are stored locally.
- Good: Buffett Indicator source lists market-cap/GDP and GDP component links and says the ratio is citeable only after components and calculation method are stored locally.
- Base: a source has no collection links but still exposes a collection note and citation policy.
- Bad: `fred_us_rates` appears as a dashboard or assistant citation before a reviewed `MarketIndicatorObservation` exists.
- Bad: SEC filing search links are treated as proof that filings/transcripts have been ingested.

### 6. Tests Required

- Service tests cover one official macro source, one manual valuation source, and one future document source.
- API/dashboard tests assert source guidance fields are additive on `information_sources`.
- Frontend tests assert collection guidance, citation boundary text, and safe external links render.
- Focused validation should include source service tests, dashboard API tests, homepage tests, TypeScript, ruff for touched Python files, and `git diff --check`.

## Scenario: Source-to-Seed Template Guidance

### 1. Scope / Trigger

- Trigger: `get_information_source_readiness_payload(...)` returns additive `seed_template` metadata for macro/valuation source-readiness items.
- Scope: source definitions in `packages/services/information_sources.py`, dashboard payload compatibility, homepage rendering, seed-import documentation, and focused tests.
- Non-goals: live official-source adapters, automatic imports, scraping, document ingestion, database writes, LLM-generated observations, or trading recommendations.

### 2. Signatures

- Source item additive field: `seed_template | null`
- `seed_template` fields:
  - `label`
  - `description`
  - `target_indicator_codes`
  - `required_fields`
  - `json_template`
  - `csv_header`
  - `csv_example_rows`
  - `review_checklist`
  - `warnings`
  - `import_command`
  - `citation_boundary`

### 3. Contracts

- Seed templates are operator guidance only. They must not affect `status`, `evidence_count`, `latest_as_of`, `dashboard_brief.citations`, or assistant `citations`.
- Template rows must use visible placeholders such as `YYYY-MM-DD`, `<reviewed decimal>`, and `<operator review note>`.
- CSV examples must preserve the existing seed import contract: `code,as_of,value,source,components_json`, where `components_json` is valid JSON text after placeholder replacement.
- Template checklist items should map to the importer contract: known code, ISO date, decimal value, reviewed source note, source reference metadata, and method/review metadata.
- Citable macro/valuation evidence still begins only after `scripts/import_market_indicator_seeds.py` validates and stores local `MarketIndicatorObservation` rows.

### 4. Good/Base/Bad Cases

- Good: FRED rates source shows target codes, placeholder JSON/CSV rows, review checklist, and import command while staying `needs_adapter`.
- Good: Buffett source shows component-oriented calculation placeholders and source URLs while staying `needs_manual_seed`.
- Bad: a template row with fake numeric market values is presented as sample evidence.
- Bad: source/template IDs appear in dashboard or assistant citation lists.
- Bad: the frontend implies the import command has already run or that source links are locally stored evidence.

### 5. Tests Required

- Service tests assert seed templates for FRED rates, Buffett components, and generic user seed files.
- API tests assert `seed_template` is additive and dashboard citations exclude source/template IDs.
- Frontend tests assert template label, target codes, required fields, JSON/CSV previews, placeholder value, checklist, warnings, and citation boundary render.
- Docs/spec updates must preserve no-fetch/no-scrape/no-advice/no-citation-until-imported boundaries.

## Deterministic Stock-Discovery Explanation Addendum

- Stock discovery uses its own prompt/fallback module in
  `packages/ai/stock_discovery.py`; it does not replace the single-symbol market
  assistant contract.
- The deterministic screener owns shortlist membership and ranking. The model
  receives a bounded already-ranked list and may explain it only.
- Allowed inline citation IDs come from each shortlist item's stored
  `evidence_citations`. Unknown IDs produce `CITATION_UNKNOWN_ID` and fallback.
- Candidate symbols in model output must be backticked. Any backtick symbol not
  in the deterministic shortlist produces `SHORTLIST_UNKNOWN_SYMBOL` and
  fallback.
- Provider missing/disabled/failure/empty-output and empty-shortlist cases use
  deterministic explanations with explicit evidence and no-trading boundaries.
