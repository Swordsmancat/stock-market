# News Search Provider Contract

## Scenario: Configurable News Search Providers

### 1. Scope / Trigger

- Trigger: news discovery now supports configured search providers through platform settings and `/news/search` APIs.
- Scope: `packages/services/news_provider_registry.py`, `packages/services/news_search.py`, `packages/services/information_sources.py`, `packages/services/platform_settings.py`, `apps/api/routers/news.py`, `apps/api/routers/settings.py`, settings UI consumers, and focused tests.
- Non-goals: social crawling, cookie/proxy scraping, licensed full-text storage, LLM summarization, or automatic trading.

### 2. Signatures

- Settings file: `data/platform_settings.json`
- Settings fields:
  - `news_search_provider_order: list[str]`
  - `news_search_enabled_providers: list[str]`
  - `news_search_provider_keys: dict[str, str]`
  - `news_search_max_results: int`
  - `news_search_timeout_seconds: float`
- Public settings fields:
  - `news_search_provider_keys: {}`
  - `news_search_provider_keys_configured: dict[str, bool]`
  - `news_search_provider_capabilities: list[dict]`
- API:
  - `GET /news/search?symbol=<symbol>&query=<optional>`
  - `POST /news/search-ingest?symbol=<symbol>&query=<optional>`
- Service entry points:
  - `search_news_candidates(symbol, session=None, query=None, settings_payload=None, adapters=None)`
  - `search_and_ingest_news_candidates(symbol, session, query=None, settings_payload=None, adapters=None)`
  - `persist_news_search_candidates(candidates, session=...)`
- Candidate evidence boundary fields:
  - `evidence_boundary.is_live_search_candidate: true`
  - `evidence_boundary.is_ai_citable: false`
  - `evidence_boundary.can_persist_as_news: bool`
  - `evidence_boundary.evidence_strength: collection_candidate | low_social_signal`
- Search-ingest social fields:
  - `social_candidate_count: int`
  - `social_candidates_deferred: bool`

### 3. Contracts

- The provider registry must represent `anspire`, `serpapi_baidu`, `tavily`, `bocha`, `brave`, `minimax`, `yfinance`, `akshare`, `tushare`, and `mock`.
- Live adapter status is limited to `anspire` and `serpapi_baidu` for this slice.
- Provider keys are stored only in `news_search_provider_keys`; blank updates preserve existing saved keys.
- Public settings and diagnostics must never include raw provider keys, authorization headers, or full raw provider payloads.
- Search candidates are collection inputs. They become citable news evidence only after storage as `NewsArticle` with URL, source, summary, and publication or retrieval timestamp metadata.
- `search-ingest` reuses `NewsArticle` and `SentimentSignal`; it should not add a schema migration unless a future slice needs reviewed metadata that cannot fit existing columns.
- Social/public-opinion search candidates are lower-strength sentiment inputs, not verified news.
  - `result_kind` values `social` and `public_opinion` must not be persisted as `NewsArticle`.
  - They may remain visible in `/news/search` and `/news/search-ingest` response candidates with `evidence_strength="low_social_signal"`.
  - `search-ingest` must report deferred social candidates through `social_candidate_count` and `social_candidates_deferred`.
  - Source readiness may expose a future social-sentiment row, but that row is guidance only and not a citation.
- Tests must inject fake adapters or fake HTTP getters. CI must not call paid providers.

### 4. Validation & Error Matrix

- Provider disabled -> `PROVIDER_DISABLED` diagnostic, continue to next provider.
- Missing key for enabled credentialed provider -> `MISSING_CREDENTIALS`, continue.
- Provider has no live adapter in this slice -> `PROVIDER_NOT_IMPLEMENTED`, continue.
- Timeout -> `PROVIDER_TIMEOUT`, continue.
- Sanitized provider exception -> `PROVIDER_ERROR`, continue.
- Empty or unusable response -> `EMPTY_RESPONSE`, continue.
- At least one provider returns candidates -> `PROVIDER_OK` plus normalized candidates.
- No live candidates and stored news exists -> `DATABASE_FALLBACK_USED`.
- No live candidates and no stored news -> `DATABASE_FALLBACK_EMPTY`.
- Social/public-opinion candidate appears in ingest -> candidate is deferred from `NewsArticle`,
  `social_candidates_deferred=true`, and no sentiment row is generated from it in this slice.

### 5. Good/Base/Bad Cases

- Good: Anspire returns title, URL, content, score, and date; the adapter normalizes a candidate, `search-ingest` stores one deduped `NewsArticle`, and diagnostics expose only provider status.
- Good: SerpAPI Baidu returns both `news_results` and `organic_results`; candidates preserve result kind as `news` or `web`.
- Good: SerpAPI Baidu returns `social_results`; candidates are returned as low-strength social
  signals and are deferred from `NewsArticle` persistence.
- Base: both live providers are enabled but keys are missing; the search response uses stored local news fallback if available.
- Base: Tavily or Bocha is enabled before implementation; diagnostics say registry-only or needs-contract without failing the request.
- Bad: returning a search result as an assistant citation before local storage.
- Bad: storing social chatter in `NewsArticle` and then citing it as verified news.
- Bad: exposing `news_search_provider_keys`, Bearer headers, or provider API keys in a public route, log, diagnostic, test snapshot, or UI payload.
- Bad: fabricating a publication date, publisher, title, or sentiment when a provider fails.

### 6. Tests Required

- Registry/settings tests assert defaults, provider capabilities, enabled/provider order normalization, secret masking, and blank-key preservation.
- Adapter tests assert Anspire and SerpAPI Baidu normalization with fake HTTP getters only.
- Service tests assert disabled, missing key, timeout, provider error, empty response, provider success, dedupe, persistence, and database fallback diagnostics.
- Service tests assert social/public-opinion candidates include low-strength evidence boundary,
  are counted as deferred, and do not create `NewsArticle` / `SentimentSignal` rows.
- Information-source tests assert social sentiment remains a future, non-citable source family
  separate from stored news.
- API tests assert `/news/search` returns fallback diagnostics without live network access.
- Frontend tests assert settings UI renders provider rows, key placeholders, order, max results, timeout, and Server Action payload fields.

### 7. Wrong vs Correct

#### Wrong

```python
return {"provider": "anspire", "api_key": api_key, "raw": payload}
```

This leaks credentials and raw provider data across the service boundary.

#### Correct

```python
return {
    "provider": "anspire",
    "status": "ok",
    "code": "PROVIDER_OK",
    "message": "Anspire AI Search returned 3 candidates.",
}
```

Diagnostics stay sanitized; normalized candidates carry only citation-safe collection metadata.

#### Wrong

```python
citations.append({"id": "anspire:AAPL:latest", "label": candidate.title})
```

This treats a live search candidate as citable evidence before review/storage.

#### Correct

```python
article = NewsArticle(
    symbol=candidate.symbol,
    title=candidate.title,
    url=candidate.url,
    source=candidate.source,
    published_at=candidate.published_at or candidate.retrieved_at,
    summary=candidate.summary,
    dedupe_hash=make_dedupe_hash(candidate.title, candidate.url),
)
```

Only stored local rows enter the existing `news:*` citation path.

#### Wrong

```python
article = NewsArticle(title=social_candidate.title, source="Baidu social")
```

This stores social chatter as verified news evidence.

#### Correct

```python
if candidate.result_kind in {"social", "public_opinion"}:
    deferred_social_count += 1
```

Social candidates stay visible as low-strength collection inputs while waiting for a separate reviewed evidence model.
