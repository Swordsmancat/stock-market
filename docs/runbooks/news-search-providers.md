# News Search Providers

This runbook covers configured news search and exact-instrument fallback:

- provider registry and platform settings;
- Anspire AI Search adapter;
- SerpAPI Baidu adapter;
- built-in AkShare and market-aware yfinance fallback;
- DB-first detail refresh and homepage stored-news aggregation;
- fallback diagnostics;
- the citation boundary for stored news.

## Configure Providers

Open the web settings page and use **News Search Sources**.

Stored settings live in `data/platform_settings.json`:

- `news_search_provider_order`: ordered provider IDs.
- `news_search_enabled_providers`: enabled provider IDs.
- `news_search_provider_keys`: provider key map. Public settings responses mask this field.
- `news_search_max_results`: bounded to `1..20`.
- `news_search_timeout_seconds`: bounded to `1..30`.

MVP key fields:

- `anspire`: Anspire AI Search API key.
- `serpapi_baidu`: SerpAPI key for Baidu search.

Leaving a key input blank preserves the existing saved key. Public settings expose only
`news_search_provider_keys_configured`, never raw keys.

## API Usage

Search without persisting:

```powershell
curl "http://localhost:8000/news/search?symbol=AAPL"
```

Search and persist normalized candidates into `NewsArticle` / `SentimentSignal`:

```powershell
curl -X POST "http://localhost:8000/news/search-ingest?symbol=AAPL"
```

Refresh one exact instrument using stored news, configured providers, and then
built-in fallbacks:

```powershell
curl -X POST "http://localhost:8000/news/000001/refresh?market=CN"
```

Read the latest stored rows across symbols without calling a provider:

```powershell
curl "http://localhost:8000/news/latest?limit=6"
```

The existing read endpoint remains unchanged and read-only:

- `POST /news/mock-ingest?symbol=AAPL`
- `GET /news/{symbol}`

## Fallback Diagnostics

Search responses include `diagnostics[]` entries with sanitized provider status. Expected codes include:

- `PROVIDER_DISABLED`
- `MISSING_CREDENTIALS`
- `PROVIDER_NOT_IMPLEMENTED`
- `PROVIDER_TIMEOUT`
- `PROVIDER_ERROR`
- `EMPTY_RESPONSE`
- `PROVIDER_OK`
- `DATABASE_FALLBACK_USED`
- `DATABASE_FALLBACK_EMPTY`
- `PROVIDER_PERSISTED`
- `PROVIDER_INVALID_CANDIDATE`
- `NO_PERSISTABLE_CANDIDATES`
- `PERSISTENCE_ERROR`
- `UNSUPPORTED_IDENTITY`
- `UNSUPPORTED_MARKET`

If all live providers fail or are skipped, the service falls back to stored local news for the symbol.
It does not fabricate titles, publication dates, sentiment, or movement.

The dedicated refresh mutation is sequential and DB-first. It stops after the
first persisted success and calls each source at most once. For exact CN stocks,
AkShare runs after configured executable providers when platform-wide AkShare
support is enabled; market-aware yfinance is the final built-in fallback.

Every search and refresh candidate must match the requested symbol and provider,
fit the stored field limits, and use an absolute HTTP(S) URL without embedded
credentials. One invalid candidate rejects that provider batch with
`PROVIDER_INVALID_CANDIDATE`; the service then continues to the next source.
The shared persistence function repeats this check, including for
`/news/search-ingest`.

## Citation Boundary

Live search candidates are collection inputs only. AI-facing evidence may cite news only after a row is
stored locally with URL, source/publisher, and publication or retrieval timestamp metadata.

The MVP reuses `NewsArticle` and `SentimentSignal`; no schema migration is required for this slice.

## Social Sentiment Boundary

Provider result families such as SerpAPI Baidu `social_results` remain visible as live search
candidates, but they are not verified news. Candidate payloads include an `evidence_boundary`
object:

- `is_live_search_candidate=true`
- `is_ai_citable=false`
- `can_persist_as_news=false` for `social` and `public_opinion`
- `evidence_strength=low_social_signal` for social/public-opinion candidates

`POST /news/search-ingest` defers social/public-opinion candidates from `NewsArticle` and
`SentimentSignal` persistence and reports:

- `social_candidate_count`
- `social_candidates_deferred`

Future social sentiment storage must use official APIs, licensed provider result families, or
user-reviewed notes. Until that separate model exists, social sentiment is lower-strength context
and not AI-citable market fact.

## Crawling And Cookie Boundary

The application does not extract, store, or replay browser Cookies. It does not
perform authenticated scraping, CAPTCHA/paywall bypass, proxy rotation, or raw
HTML storage. Login-only material should be pasted or imported as visible text
through the reviewed Source Notebook workflow.

A future public-web fallback must be a site-specific, public/no-login adapter
with an explicit domain allowlist, rate limit, terms/robots review, normalized
metadata only, and a disabled-by-default setting. Do not add a generic crawler
to the refresh route.

## Quota And Tests

Automated tests inject fake adapters or fake HTTP getters. They must not call paid providers or consume quota.

Manual live searches may consume Anspire or SerpAPI quota. Keep provider responses out of logs and do not store
licensed full text unless the provider plan allows storage.
