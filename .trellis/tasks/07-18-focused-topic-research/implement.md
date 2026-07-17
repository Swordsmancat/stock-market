# Implementation plan

1. Add service taxonomy, normalization, bounded database queries, serializers,
   and tests for all topics, windows, match reasons, states, and ordering.
2. Add the validated FastAPI GET router, register it, and cover delegation and
   validation with API tests.
3. Add the frontend decoder and GET proxy with malformed-payload and query
   preservation tests.
4. Build the localized topic research page with URL-owned controls, provenance,
   independent empty states, news times, industry history, and company links.
5. Add one compact desktop navigation item and a Market Research link while
   preserving the five-item mobile navigation.
6. Run focused tests, full backend/frontend suites, Ruff, TypeScript, locale
   validation, Trellis validation, scoped diff checks, and desktop/mobile
   browser acceptance against stored production data.
7. Isolate shared-file hunks from unrelated dirty work, commit the feature,
   archive the task, record the journal, and only push after remote ownership
   is explicitly resolved.

## Risk And Rollback

- Shared navigation, translations, `apps/api/main.py`, and the parent task
  metadata contain unrelated work and require hunk-level staging.
- Topic keyword changes can alter coverage; keep the taxonomy versioned and
  cover each mapping in tests.
- No migration is added, so rollback is code-only.
