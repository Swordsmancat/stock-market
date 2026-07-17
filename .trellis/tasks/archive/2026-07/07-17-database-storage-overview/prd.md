# Add database storage overview

## Goal

Give the personal research user a truthful, scan-first view of what the local
database currently stores, how records are distributed across research data
domains, and how much disk space each domain consumes.

## Background

- The application uses PostgreSQL and SQLAlchemy, not MongoDB.
- The supplied reference establishes the desired hierarchy: one database
  summary followed by compact data-domain inventory cards.
- The application already has a desktop-only Market Research navigation item
  and keeps the mobile bottom navigation fixed at five primary destinations.

## Requirements

- Add a localized `/storage` page and a desktop-sidebar `Data Storage` entry.
- Keep the mobile bottom navigation unchanged.
- Add a read-only backend endpoint that returns database-wide and per-table
  storage statistics without exposing connection URLs, credentials, hostnames,
  SQL text, or unrelated database metadata.
- Group known application tables into stable product-facing domains while
  preserving an `other` fallback for future tables.
- Show database engine, table count, estimated record count, data size, index
  size, total size, and collection time when PostgreSQL exposes them.
- Show compact domain cards with record count, table count, and total size, and
  an accessible table-level inventory for inspection.
- Label PostgreSQL row counts as estimates. Do not run full-table `COUNT(*)`
  queries on production-sized tables during a normal page read.
- Distinguish failed loading from a genuinely empty database.
- Reuse existing financial-terminal components, semantic theme tokens,
  `lucide-react` icons, and project localization conventions.
- The page is informational only. It must not expose delete, truncate, vacuum,
  migration, refresh, ingestion, or arbitrary-query controls.

## Data Domains

- reference data
- market prices
- technical analysis
- fundamentals
- macro economy
- market structure
- news and disclosures
- research outputs
- personal data and operations
- other (fallback)

## Out of Scope

- Database mutation or administration.
- Live provider ingestion and backfill controls.
- MongoDB support or introducing a second database.
- Exact production row counts that require scanning every table.

## Acceptance Criteria

- [x] `GET /storage/overview` returns a secret-safe database summary, stable
      domain groups, and table statistics from a PostgreSQL session.
- [x] SQLite-backed tests receive a usable compatibility projection without
      relying on PostgreSQL catalog functions.
- [x] `/zh/storage` and `/en/storage` render localized summary metrics, domain
      cards, and a table inventory with explicit empty/error states.
- [x] Desktop sidebar exposes the localized route with correct active state;
      mobile navigation remains five items and excludes it.
- [x] Backend and frontend tests cover grouping, aggregation, failure handling,
      localization, navigation ownership, and secret-safe payload fields.
- [x] Desktop and mobile browser checks show no horizontal overflow and the
      route remains usable in light and dark themes.

## Notes

- The reference image informs density and hierarchy, not technology naming or
  hard-coded sample numbers.
