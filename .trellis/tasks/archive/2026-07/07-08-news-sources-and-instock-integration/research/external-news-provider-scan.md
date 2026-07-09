# External News Provider Scan

Date: 2026-07-08

## Sources Checked

- Anspire AI Search API docs: https://open.anspire.cn/document/docs/searchApi?share_code=QFBC0FYC
- SerpAPI Baidu Search API docs: https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis
- Tavily Search docs: https://docs.tavily.com/documentation/api-reference/endpoint/search
- Bocha landing/docs entry: https://open.bocha.cn/
- Brave Search API: https://brave.com/search/api/
- MiniMax Token Plan web search MCP docs: https://platform.minimaxi.com/docs/token-plan/mcp-guide

## Provider Notes

### Anspire AI Search

- GET endpoint: `https://plugin.anspire.cn/api/ntsearch/search`.
- Auth: `Authorization: Bearer {API KEY}`.
- Parameters include query, top_k, Insite, FromTime, ToTime, search_type, and region_mode.
- Results include title, content, URL, score, and date.
- Fit: strong candidate for cross-region financial/public-opinion search.

### SerpAPI Baidu

- Required query parameter: `q`.
- Required engine parameter: `engine=baidu`.
- Required credential: `api_key`.
- Useful filters include language, pagination, max results, and time period.
- Result families include Baidu news and social/media results.
- Fit: useful Chinese search supplement; must normalize result categories carefully.

### Tavily

- Search endpoint returns answer and result list.
- Results include title, URL, content, score, and related metadata.
- SDK exists, but direct HTTP via `httpx` may better match this repo's provider style.
- Fit: general-purpose web/news discovery adapter.

### Bocha

- Landing page describes Web Search API over news, images, video, encyclopedia, travel, academic, and other sources.
- Precise endpoint/auth schema needs follow-up because linked docs are hosted outside the landing page and were not fully retrievable in this scan.
- Fit: likely Chinese search optimization candidate, but do not implement before contract is confirmed.

### Brave Search

- Example endpoint: `https://api.search.brave.com/res/v1/web/search`.
- Auth header: `X-Subscription-Token`.
- Parameters include q, count, country, and search_lang.
- Docs mention specialized endpoints including news and warn that storage rights depend on plan terms.
- Fit: US/global coverage and privacy-oriented search, with explicit storage-right caveat.

### MiniMax

- Current docs point to Token Plan MCP `web_search` and MiniMax CLI `mmx search`.
- The documented MCP tool takes a required query string and returns search results plus suggestions.
- This is not yet a normal in-app REST adapter contract.
- Fit: candidate for operator/agent workflows or an optional CLI/MCP bridge, not a first backend adapter unless a stable server API is confirmed.

## Cross-Provider Normalization Needs

- Title, URL, snippet/content, provider, publisher/source, published_at/date/retrieved_at, score, result kind, region/language, and diagnostics.
- Timeout and retry policy must be per provider.
- Tests must mock HTTP responses and never consume paid provider quota.

## Open Follow-Up

- Confirm Bocha API endpoint, auth header, response schema, quota behavior, and storage terms.
- Confirm MiniMax production integration path: REST API, CLI bridge, MCP bridge, or defer.
- Decide whether search results are stored as articles immediately or first reviewed as candidates.
