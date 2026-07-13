# A-share official disclosures research corpus

## Goal

Give stock discovery and AI research access to auditable A-share disclosure evidence from official publication channels, so conclusions can cite the exact document identity and publication time instead of relying only on prices, indicators, fundamentals, and news.

## Background

- Full-market A-share price, indicator, and fundamental coverage has already passed live acceptance.
- The platform currently treats filings, exchange announcements, transcripts, and document corpora as future/non-citable sources.
- The existing Source Notebook supports reviewed manual excerpts, but it does not provide durable official-document identity, automated deduplication, or official metadata refresh.

## Requirements

- Build the capability as independently verifiable vertical slices rather than a single bulk crawler.
- Preserve an explicit distinction between official document metadata, reviewed document text, and AI-generated summaries.
- Retain source authority, external document identity, canonical URL, symbols, publication time, retrieval time, category, and deduplication identity.
- Only locally persisted, validated evidence may enter AI citation allowlists.
- Provider failures and missing coverage must remain visible and must not be replaced by fabricated records.
- Respect source rights and operational limits; bulk scraping, paid research, and unlicensed transcript storage are excluded.
- Keep all outputs research-only: no buy/sell/hold calls, target prices, position sizing, or automated trading.

## Child Deliverables

1. `07-13-official-disclosure-metadata`: official CNINFO metadata refresh, persistence, retrieval, dedupe, and metadata-only citations.
2. Follow-up: reviewed document-content ingestion with content hashing, section anchors, and storage policy.
3. Follow-up: Evidence Center and AI Research document search/monitoring workflows.
4. Follow-up: incremental watchlist/universe scheduling and coverage/SLA reporting.

## Acceptance Criteria

- [ ] Official metadata can be refreshed and persisted without storing document bodies.
- [ ] Repeated refreshes are idempotent and preserve stable citation identifiers.
- [ ] Reviewed document content, when added later, remains distinguishable from metadata-only evidence.
- [ ] AI surfaces use only persisted evidence and expose exact source links and boundaries.
- [ ] Provider-wide failures produce sanitized diagnostics and preserve existing data.
- [ ] Documentation states the source-rights, citation, and research-only boundaries.

## Out of Scope

- Licensed sell-side research corpora.
- Telephone-call transcripts without an explicit legal source and storage policy.
- Unbounded full-market PDF crawling in the first slice.
- Vector search before document identity and content provenance are stable.
- Trading execution or investment recommendations.
