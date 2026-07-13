# Implementation plan

## Ordered Checklist

1. Add the `OfficialDisclosure` ORM model and a SQLite/PostgreSQL-compatible Alembic revision.
2. Add the CNINFO disclosure provider adapter with lazy AkShare import, injectable fetcher, normalization, URL/identity parsing, and sanitized errors.
3. Add the disclosure service for validation, batch upsert, listing, serialization, diagnostics, and metadata-only citation construction.
4. Add thin FastAPI list/refresh routes and register the router.
5. Add recent disclosure metadata to the symbol-level market assistant context and citation allowlist.
6. Add provider, domain/migration, service, API, and assistant tests with fake provider data only.
7. Update README/user documentation to describe current capability and its metadata-only boundary.
8. Run focused tests, Ruff, full backend tests, migration tests, and `git diff --check`.

## Validation Commands

```powershell
python -m pytest -q tests/providers/test_cninfo_disclosure_provider.py tests/services/test_official_disclosures.py tests/api/test_official_disclosures_api.py tests/ai/test_market_assistant.py tests/domain/test_models.py tests/domain/test_migrations.py
python -m ruff check packages/providers/cninfo_disclosure_provider.py packages/services/official_disclosures.py apps/api/routers/official_disclosures.py packages/domain/models.py tests/providers/test_cninfo_disclosure_provider.py tests/services/test_official_disclosures.py tests/api/test_official_disclosures_api.py
python -m pytest -q
git diff --check
```

## Risk and Rollback Points

- AkShare/CNINFO dataframe columns can change: keep all mapping in the adapter and cover schema failure with a deterministic provider error.
- Official detail URLs currently use HTTP: allow the exact CNINFO host while preserving the returned canonical link; do not broaden the host allowlist.
- Assistant prompt growth: cap disclosure citations and excerpt lengths.
- Migration risk: verify both SQLAlchemy `create_all()` and Alembic chain tests.
- No implementation step may fetch live provider data during tests.

## Review Gates

- Confirm no metadata candidate becomes citeable before persistence.
- Confirm metadata-only citations cannot be confused with document-content evidence.
- Confirm repeated refresh is idempotent and provider failure never deletes stored rows.
- Confirm API diagnostics contain no raw payloads, headers, or secrets.

## Validation Result

- Focused disclosure/domain/assistant suite: 44 passed.
- Full backend suite after final changes: 596 passed.
- Ruff on all changed Python files: passed.
- Mypy on the three new provider/service/router modules with imports skipped: passed.
- Alembic reports a single `0017_official_disclosures` head; the isolated migration test passes on SQLite.
- A fresh full SQLite Alembic chain remains blocked by the pre-existing `0008_alerts_report_run` SQLite foreign-key ALTER limitation; this occurs before revision 0017 and is outside this task. The repository's migration regression tests remain green.
- Repository-wide Ruff still reports 41 pre-existing findings in Trellis scripts and unrelated legacy modules; changed-file Ruff is green.
- `git diff --check`: passed (line-ending conversion warnings only).
