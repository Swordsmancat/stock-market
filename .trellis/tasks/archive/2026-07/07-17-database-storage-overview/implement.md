# Database Storage Overview Implementation

## Implementation Order

1. Add service-level table classification and database inventory projection.
2. Add the read-only FastAPI router and register it in the application.
3. Add focused service/API tests for PostgreSQL projection, SQLite fallback,
   aggregation, unknown tables, and safe errors.
4. Add typed frontend payload normalization/formatting utilities.
5. Add localized `/storage` page, domain cards, inventory table, breadcrumbs,
   and desktop-only sidebar navigation.
6. Add page, utility, localization, and navigation tests.
7. Run focused checks, then full backend/frontend quality gates.
8. Verify desktop/mobile layouts and dark/light rendering in the browser.

## Validation

- `pytest` focused storage service/API tests
- Web Vitest focused page/navigation tests
- Web TypeScript check
- locale JSON parsing
- `git diff --check`
- Trellis Check
- Browser acceptance at 1280x720 and 390x844

## Risks And Rollback Points

- PostgreSQL catalog SQL must remain read-only and portable across supported
  server versions.
- Production row estimates can be stale; UI copy must not imply exactness.
- Table classification can lag new migrations; the `other` group prevents data
  from being hidden.
- A catalog permission failure must degrade the page explicitly rather than
  falling back to fabricated zeroes.
