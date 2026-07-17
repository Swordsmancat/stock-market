# Add focused topic research workspace

## Goal

Add one compact, database-only topic research workspace for agriculture,
China consumption, real estate, and non-ferrous metals. The page should help
one person scan stored evidence without creating four duplicate destinations
or turning the product into a broad market terminal.

## Background

The reference sidebar exposes these topics as separate modules. The existing
repository already stores news articles, Eastmoney industry ranking history,
research source notes, and company metadata inside fundamental snapshots.
Read-only production sampling on 2026-07-18 confirmed uneven but useful
coverage: agriculture and consumption have industry history, consumption and
non-ferrous metals have recent news, and company metadata partially covers
consumption, real estate, and non-ferrous metals. Empty sections must remain
explicit rather than being filled with fixtures or live provider calls.

## Requirements

- Add one route, `/[locale]/topic-research`, with four URL-owned topic choices:
  `agriculture`, `consumption`, `real_estate`, and `nonferrous`.
- Add one bounded GET API projection backed only by the injected database
  session. Page reads must never call providers, crawlers, ingestion,
  backfills, AI, portfolio mutations, orders, or trading paths.
- Define a centralized, versioned bilingual topic taxonomy with conservative
  keywords. Return the matched keyword/category reason for every item so the
  relationship is inspectable rather than inferred silently.
- Project three stored evidence sections when available:
  recent news, Eastmoney industry ranking history, and related companies from
  the latest stored fundamental company metadata.
- Keep each section independently bounded and return counts, latest evidence
  date, source/provenance, and explicit `ready|empty` section states.
- Do not treat missing evidence as an API failure. Preserve a valid topic page
  with localized empty states and a visible storage-only coverage summary.
- Use GET-only topic and time-window controls. Supported windows are
  `30d|90d|180d`, defaulting to `90d`.
- Add one compact desktop-sidebar entry and a link from Market Research while
  preserving the existing five-item mobile navigation.
- Keep the content descriptive and research-only. Do not add recommendations,
  target prices, position sizing, broker actions, or automated trading.

## Acceptance Criteria

- [ ] Service tests prove topic/window validation, conservative matching,
      latest-company deduplication, stable ordering, bounded sections,
      provenance, and explicit empty/ready states.
- [ ] API tests prove query validation and injected-session delegation.
- [ ] Frontend decoder/proxy tests reject malformed or non-database payloads
      and preserve GET query state without caching.
- [ ] The page renders four topic controls, coverage metrics, evidence dates,
      news timestamps, industry history, related-company links, and distinct
      section-level empty/error states.
- [ ] Page/API reads are GET-only and no test observes provider or mutation
      requests.
- [ ] Desktop and `390x844` browser acceptance show no incoherent overlap or
      page-level horizontal overflow; mobile navigation remains five items.
- [ ] Focused and full backend/frontend tests, Ruff, TypeScript, locale JSON,
      Trellis validation, and scoped `git diff --check` pass.

## Out of Scope

- Automatic topic classification with an LLM or embeddings.
- Creating or refreshing evidence from this page.
- Topic-specific databases, saved dashboards, alerts, or custom topic editing.
- FX, futures, commodity contracts, live prices, and professional terminal
  parity.
