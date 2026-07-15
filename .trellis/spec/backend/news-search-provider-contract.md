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

## Scenario: Exact-Instrument Sequential News Refresh

### 1. Scope / Trigger

- Trigger: exact instrument detail has no stored news and must recover one
  auditable local evidence projection without manual provider switching.
- Scope: built-in/provider adapters, sequential persistence, FastAPI routes,
  detail-page one-shot recovery, and homepage stored-news aggregation.
- Non-goals: background universe crawling, generic/authenticated scraping,
  Cookie replay, licensed full-text storage, or direct AI/trading actions.

### 2. Signatures

- Stored read: `GET /news/{symbol}` remains read-only.
- Refresh mutation: `POST /news/{symbol}/refresh?market=<market>`.
- Homepage read: `GET /news/latest?limit=<1..50>` returns bounded stored rows
  across symbols and performs no provider search.
- Refresh payload includes `status`, `selected_provider`, persisted counts,
  sanitized `attempts`/`diagnostics`, and `news`, the final stored-news
  projection.
- Shared write boundary:
  `persist_news_search_candidates(..., expected_symbol=None, expected_provider=None)`.
- Frontend decoders:
  `isInstrumentNewsPayload(value, expectedSymbol?)`,
  `isNewsRefreshPayload(value, expectedSymbol?)`, and
  `isLatestStoredNewsPayload(value)`.

### 3. Contracts

- Refresh checks stored `NewsArticle` rows first. A hit returns
  `status="database_hit"` and performs zero external calls.
- The fixed source order is configured executable search providers in saved
  order, eligible AkShare stock news for an exact CN six-digit symbol, then
  market-aware yfinance. Built-in AkShare/yfinance fallback is not dependent on
  membership in `news_search_enabled_providers`; AkShare still respects the
  platform-wide `akshare_enabled` gate.
- Each executable source is called at most once with no retry. Stop immediately
  after the first source persists at least one deduplicated news row and return
  `status="refreshed"` plus a fresh stored projection.
- All executable sources returning legitimate empty results is `no_data`.
  Provider timeout/transport/schema failure with no persisted result is
  `provider_error`. A market unsupported by every built-in path is
  `unsupported`.
- Candidate normalization may retain only title, URL, source, summary,
  publication/retrieval time, language/region, result kind, and evidence-boundary
  metadata. Diagnostics never include keys, cookies, authorization headers,
  raw provider bodies, credential URLs, prompts, stack traces, or exception
  messages.
- Every provider batch is validated before it is returned by search, accepted
  by refresh, or written by the shared persistence function. Each candidate
  must match the requested normalized symbol and expected provider, use an
  absolute HTTP(S) URL with a hostname and no embedded username/password, and
  fit `NewsArticle` symbol/title/URL/source column limits. Query and fragment
  keys that carry tokens, API keys, signatures, authorization, Cookies,
  passwords, secrets, or session credentials invalidate the URL; ordinary
  public query parameters remain unchanged.
- Candidate summaries are parsed as HTML with the standard-library parser,
  script/style/template content is discarded, whitespace is normalized, and
  stored/returned summary text is capped at 1000 characters. Visible bare
  `Bearer <token>` text and Cookie/authorization/key/token assignments,
  including quoted JSON fields, invalidate the candidate. The legacy yfinance,
  AkShare, and mock ingestion entry points use the same sanitizer and single
  `NewsArticle` write helper.
- Any invalid member rejects the whole provider batch as
  `PROVIDER_INVALID_CANDIDATE`; shared persistence performs zero writes for a
  mixed valid/invalid batch. Diagnostics contain no candidate fields.
- `POST /news/search-ingest` uses the same validation and binds persistence to
  the requested symbol. Shared persistence validates again so future callers
  cannot bypass the route/service checks.
- Social/public-opinion candidates remain non-citable and are never persisted
  as `NewsArticle`. Only stored rows may enter `news:*` assistant citations.

#### Browser behavior

- Exact instrument detail automatically refreshes only when its stored news is
  empty, once per `news-fallback:v1:{market}:{symbol}:{local-date}` browser
  session key. It replaces only the local news projection.
- A failed stored-news GET is not an empty result: detail shows provider-error
  and must not launch an automatic refresh mutation from that failed preflight.
- Automatic failure is not retried. `no_data` and `provider_error` may expose
  one explicit manual retry; `unsupported` links to Settings and does not retry.
- Recovering, no-data, provider-error, and unsupported states use localized
  stable-code mappings. Backend free-text messages are never rendered.
- Homepage consumes only `/news/latest?limit=6`; it distinguishes a successful
  empty result from a failed read and never fans out searches across symbols.
- Browser decoders reject wrong-symbol detail/refresh projections, unsafe or
  credential-bearing URLs, empty titles, contradictory item counts, and status
  combinations such as `no_data` with non-empty items.

#### Crawling and credentials boundary

- Generic crawling, browser-Cookie extraction/storage/replay, authenticated
  scraping, CAPTCHA/paywall bypass, proxy rotation, and raw HTML storage remain
  forbidden.
- A future public-web adapter must be site-specific, public/no-login,
  allowlisted, rate-limited, terms/robots aware, and disabled by default.
- Login-only material uses the existing manual visible-text/link import and
  reviewed Source Notebook citation gate. Browser credentials never cross into
  the backend refresh service.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Stored news exists | `database_hit`; zero external calls |
| Enabled credentialed source lacks key | Sanitized `MISSING_CREDENTIALS`; continue |
| Source returns persistable candidates | Persist/dedupe, return `refreshed`, stop |
| Source returns only social candidates | Defer; do not persist; continue |
| Candidate symbol/provider/URL/field bounds are invalid | `PROVIDER_INVALID_CANDIDATE`; reject batch and continue |
| Source times out/fails/malformed | Sanitized diagnostic; no retry; continue |
| All executable sources return empty | `no_data` with final stored projection |
| Failure occurs and no later source succeeds | `provider_error` |
| Market has no supported built-in path | `unsupported` |
| Homepage latest read fails | Explicit failed load, not an empty projection |

### 5. Good / Base / Bad Cases

- Good: no stored CN news, configured sources are unavailable, AkShare returns
  verified candidates, one deduplicated batch is stored, and yfinance is not
  called.
- Good: AkShare is empty and market-aware yfinance maps `000001` to
  `000001.SZ`, persists news, and only stored rows become citable.
- Base: every source returns a legitimate empty result; detail shows a localized
  no-data state and permits one explicit retry.
- Bad: call every provider after success, retry a timeout, render raw provider
  text, persist an unsafe search-ingest candidate, persist social chatter as
  news, or forward browser Cookie/auth headers.

### 6. Tests Required

- Adapter tests use injected frames/tickers and assert CN/HK/US symbol mapping,
  normalized fields, timezones, malformed shapes, and empty results without
  live network access.
- Service/API tests cover DB-first zero calls, fixed order, first-persist stop,
  dedupe, social deferral, sanitized errors, no-data/provider-error/unsupported,
  unsafe candidate rejection on refresh and search-ingest, shared persistence
  defense, credential query/fragment rejection, plain bounded summaries,
  bare-Bearer and quoted-JSON credential text rejection, invalid-batch
  atomicity, legacy ingestion safety, GET read-only behavior, and bounded
  cross-symbol latest ordering.
- Route/component/page tests cover header/body non-forwarding, generic transport
  502, stored-news zero POST, one automatic POST, direct projection replacement,
  pending and terminal states, one manual retry, homepage no-fan-out, and
  failed-versus-empty display.
- Assistant regressions keep live candidates outside citation allowlists and
  accept only persisted `news:*` rows.

### 7. Wrong vs Correct

#### Wrong

```python
for provider in every_provider:
    candidates.extend(provider.search(symbol))
return {"items": candidates}
```

This creates uncontrolled calls and exposes non-persisted candidates as if they
were evidence.

#### Correct

```python
stored = get_news_sentiment_payload(symbol, session=session)
if stored["summary"]["article_count"]:
    return database_hit(stored)
for source in sequential_sources(symbol, market):
    candidates = source.search_once(symbol)
    if not candidates_are_safe(candidates, symbol=symbol):
        continue
    if persist_first_success(candidates, expected_symbol=symbol):
        return refreshed(get_news_sentiment_payload(symbol, session=session))
return terminal_empty_or_error(stored)
```
