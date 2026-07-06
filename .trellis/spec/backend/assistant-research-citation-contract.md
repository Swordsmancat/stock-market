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
- Citation required fields: `id`, `label`, `source`, `url`
- Citation optional fields: `source_type`, `as_of`, `provider`, `retrieved_at`, `excerpt`, `metadata`
- Diagnostic required fields: `source`, `status`, `message`
- Diagnostic optional fields: `severity`, `code`, `citation_id`, `details`

### 3. Contracts

- Daily bars remain the core evidence gate. If required market data is unavailable, the assistant must return `no_data` / degraded-safe output and avoid LLM generation.
- Existing top-level response fields and old minimal citation payloads must remain backward compatible.
- Evidence may come from existing platform sources only: daily bars, stored technical indicators, fundamentals snapshots, news / sentiment payloads, generated reports, and reviewed/citable research source notebook entries.
- Missing optional sources must produce diagnostics, not fabricated evidence or fake citations.
- Citation IDs must be deterministic and source-specific, such as `bars_1d:{symbol}:{as_of}`, `technical_indicators:{symbol}:{as_of}`, `fundamentals:{symbol}:{as_of}`, `news:{symbol}:...`, `generated_report:{id}`, or `research_source_note:{id}`.
- LLM prompts must list available citation IDs and instruct the model to use only those IDs.
- LLM output citation IDs must be validated against the payload citations. Unknown IDs must produce `CITATION_UNKNOWN_ID` diagnostics and should fall back to deterministic output when needed.
- Diagnostics may include safe severity/code metadata, but must not include API keys, prompt internals, stack traces, raw provider secrets, or hidden chain-of-thought.
- The assistant must preserve no-investment-advice and no direct buy/sell/hold/target-price/position-sizing/execution-instruction boundaries.

### 4. Validation & Error Matrix

- Core daily bars unavailable -> response does not call LLM; returns no-data/degraded diagnostics.
- Optional indicators/fundamentals/news/reports missing -> non-blocking diagnostics such as `SOURCE_NO_DATA` or `SOURCE_OMITTED`.
- Source service failure -> sanitized `SOURCE_UNAVAILABLE` diagnostics; no raw secret or stack trace.
- Draft or non-citable research source notes -> remain collection records; they are not included in allowed assistant citation IDs.
- LLM returns unknown inline citation ID -> `CITATION_UNKNOWN_ID` diagnostic and degraded/fallback output; unknown citation is not presented as valid.
- User asks for direct trading instruction -> assistant refuses/reframes per safety policy.
- Old frontend payload with only `id`, `label`, `source`, `url` citations -> still renders.
- Citation URL present -> frontend renders safe link without changing backend API contract.

### 5. Good/Base/Bad Cases

- Good: daily bars, indicators, fundamentals, news, a generated report, and reviewed/citable source notebook entries are available; response contains deterministic citation IDs, optional metadata/excerpts, compact diagnostics, and an answer using only known citation IDs.
- Base: only daily bars are available; answer remains traceable to bars and diagnostics state missing optional sources.
- Bad: a missing filing/transcript is represented as a live citation. These sources are not production integrations in this slice.
- Bad: an LLM-invented citation ID is rendered as if it existed in `citations`.
- Bad: direct buy/sell/hold advice, target prices, or position sizing is emitted because citations exist.

### 6. Tests Required

- Service/AI tests assert citations are generated for available bars, indicators, fundamentals, news, generated reports, and reviewed/citable research source notes.
- Service tests assert missing optional evidence produces diagnostics rather than fabricated citation items.
- AI tests assert unknown LLM citation IDs are detected and handled with diagnostics/fallback behavior.
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

## Scenario: Reviewed Source Notebook Citations

### 1. Scope / Trigger

- Trigger: `/evidence` can persist user-reviewed hard-to-find research source notes and expose only reviewed/citable rows to dashboard and assistant evidence.
- Scope: `ResearchSourceNote` in `packages/domain/models.py`, migration `0011_research_source_notes`, service logic in `packages/services/research_source_notes.py`, FastAPI router `apps/api/routers/research_source_notes.py`, Next proxy/UI under `apps/web`, dashboard citation assembly in `packages/services/market_dashboard.py`, and assistant citation assembly in `packages/services/market_assistant.py`.
- Non-goals: scraping, scheduled crawling, OCR/PDF parsing, raw binary file storage, licensed corpus ingestion, vector search, multi-user permissions, trading advice, target prices, position sizing, or broker execution.

### 2. Signatures

- DB table: `research_source_notes`
- Model fields: `id`, `title`, `source_url`, `source_name`, `source_type`, `symbols_json`, `tags_json`, `published_at`, `as_of`, `retrieved_at`, `excerpt`, `note`, `ai_follow_up`, `review_status`, `is_citable`, `metadata_json`, `created_at`, `updated_at`
- Service input: `ResearchSourceNoteInput`
- Service create: `create_research_source_note(payload, *, session)`
- Service list: `list_research_source_notes(*, session, limit=50, review_status=None, source_type=None, citable_only=False)`
- Citation list: `list_citable_research_source_note_citations(*, session, symbols=None, limit=6)`
- API: `GET /research-source-notes`, `POST /research-source-notes`
- Web proxy: `GET/POST /api/research-source-notes`
- Citation ID prefix: `research_source_note:`

### 3. Contracts

- `title`, `source_name`, and `source_type` are required.
- At least one of `source_url` or `excerpt` is required for every row.
- `review_status` must be one of `draft`, `reviewed`, or `archived`.
- `is_citable=true` requires `review_status=reviewed`, a non-empty reviewed excerpt, and either `source_url` or `source_name` plus date metadata (`as_of` or `published_at`).
- Browser upload is client-side text extraction into editable fields. The backend receives JSON only and stores reviewed excerpt/note text, not raw files.
- Tags are trimmed and de-duplicated. Symbols are trimmed, de-duplicated, and uppercased.
- AI citation payloads may include `url`, `as_of`, `provider`, `retrieved_at`, clipped `excerpt`, and metadata for source name/type, symbols, tags, and review status.
- Dashboard and assistant citation builders must request only reviewed/citable notebook entries. Draft, archived, and non-citable notes remain visible in the notebook but are not allowed citation IDs.
- Symbol filtering is advisory: if requested symbols are present and a note has symbols, include only notes whose symbols intersect; untagged citable notes may still serve as general macro/context evidence.

### 4. Validation & Error Matrix

- Missing `title`, `source_name`, or `source_type` -> validation error / HTTP 422.
- Missing both `source_url` and `excerpt` -> validation error / HTTP 422.
- Unknown `review_status` -> validation error / HTTP 422.
- `is_citable=true` with `review_status!=reviewed` -> validation error / HTTP 422.
- `is_citable=true` without excerpt -> validation error / HTTP 422.
- `is_citable=true` without `source_url` and without date metadata -> validation error / HTTP 422.
- Oversized excerpt/note fields -> service clips to the configured prompt/storage limits rather than expanding AI context unbounded.
- Source note creation succeeds -> market overview cache is cleared so the dashboard can pick up new citable evidence.

### 5. Good/Base/Bad Cases

- Good: a reviewed Buffett Indicator component note with source URL, excerpt, tags, symbols, and `is_citable=true` appears as `research_source_note:<uuid>` in dashboard/assistant allowed citations.
- Good: a draft browser-upload excerpt is saved and visible in `/evidence`, but no AI prompt receives its citation ID.
- Base: a reviewed note without symbol tags can support general macro/valuation context when citable.
- Bad: uploaded raw file bytes are persisted or treated as a managed document corpus.
- Bad: a draft link or source-readiness collection URL is included as a dashboard or assistant citation.
- Bad: a source notebook citation is used to produce buy/sell/hold, target price, position sizing, or execution advice.

### 6. Tests Required

- Domain/migration tests assert `research_source_notes` schema exists and model metadata aligns with `Base.metadata.create_all()`.
- Service tests cover create/list, normalization, validation failures, citable-only listing, citation ID prefix, excerpt clipping, and draft/non-citable exclusion.
- API tests cover `GET /research-source-notes`, `POST /research-source-notes`, HTTP 422 validation, and cache-clearing metadata.
- Frontend route tests cover proxy status/content-type/payload forwarding for list and create.
- Component/page tests cover paste entry, browser file text prefill, status/citable controls, saved-entry display, filters, localized labels, and error/success states.
- Dashboard and assistant tests assert reviewed/citable source notes are included in allowed citations and draft/non-citable rows are excluded.

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
