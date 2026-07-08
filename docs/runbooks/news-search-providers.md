# News Search Providers

This runbook covers the first news-search provider slice:

- provider registry and platform settings;
- Anspire AI Search adapter;
- SerpAPI Baidu adapter;
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

The existing endpoints remain unchanged:

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

If all live providers fail or are skipped, the service falls back to stored local news for the symbol.
It does not fabricate titles, publication dates, sentiment, or movement.

## Citation Boundary

Live search candidates are collection inputs only. AI-facing evidence may cite news only after a row is
stored locally with URL, source/publisher, and publication or retrieval timestamp metadata.

The MVP reuses `NewsArticle` and `SentimentSignal`; no schema migration is required for this slice.

## Quota And Tests

Automated tests inject fake adapters or fake HTTP getters. They must not call paid providers or consume quota.

Manual live searches may consume Anspire or SerpAPI quota. Keep provider responses out of logs and do not store
licensed full text unless the provider plan allows storage.
