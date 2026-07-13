# Official disclosure runtime acceptance

## Rollout

- Date: 2026-07-13, Asia/Shanghai.
- Preflight database revision: `0016_daily_bar_provenance`.
- Final database revision: `0019_official_disclosure_monitoring (head)`.
- Migration created `official_disclosures`, `official_disclosure_documents`, `official_disclosure_sections`, and `official_disclosure_monitor_states`.
- The port-3000 frontend process was not restarted and retained PID `17740` throughout rollout.
- Final process PIDs: API `33880`, Celery worker `108452`, Celery Beat `34776`.
- Final HTTP state: frontend 200, API `/health` `ok`, and all three official-disclosure operations routes present in OpenAPI.
- Final Celery state: one worker, one Beat, disclosure execution/scheduler tasks registered, broker queue length 0, and active/reserved/scheduled queues empty.

## Backup

- Local ignored path: `.trellis/.runtime/backups/stock-before-official-disclosure-20260713-152725.dump`.
- Custom PostgreSQL archive size: 79,179 bytes.
- SHA-256: `525BD54A76A3FF232240DB47E2C2E97855D4B4C642FA4F31B908D9CDAD9457D4`.
- `pg_restore --list` successfully read the archive before migration.
- The archive is intentionally excluded from Git because it contains local database data.

## Live canary

- The original default watchlist had no `000001:CN` row. One temporary row was created and later deleted; final canary watchlist row count is 0.
- Initial incremental TaskRun: `a6694aa2-12f2-4b09-8990-c5f7eb60d78a`.
- Initial result: TaskRun `succeeded`, result `ok`, two new metadata identities, one bounded PDF download, one extracted two-page document, two page sections, zero diagnostics.
- Persisted document: `202a8841-d1f4-4cdc-a9bb-9ff59b21f60d`, SHA-256 `46788a3c913ba3d51796b401d00203cbf9b7a670a78ec6b077b4bc24f44c3bd2`.
- A one-day repeat exposed AkShare's zero-row DataFrame `KeyError`; TaskRun `ca93bf82-fbc5-4a2a-af0c-1c543007750a` preserved the last success cursor and recorded sanitized `CNINFO_REQUEST_REJECTED` retry state.
- After the fail-closed empty-result compatibility fix, recovery TaskRun `44f0f38f-0149-42c6-85e6-e6aa531e83e3` and incremental TaskRun `b2df63af-786f-4b79-822f-1fc00e59775f` both returned `no_data`, zero diagnostics, zero candidate/processed documents.
- Counts stayed stable across both repeat runs: two metadata rows, one document version, two sections, one monitor-state row.
- Final monitor state: `succeeded`, cursor document `1225406051`, zero consecutive failures, no next retry, no error code.

## Provider finding

- CNINFO's official one-day response was HTTP 200 with `totalAnnouncement=0` and `announcements=null`.
- AkShare builds an empty DataFrame and then selects required columns, producing `KeyError` instead of an empty frame.
- The adapter now converts this to `no_data` only after a separate HTTPS official probe confirms the exact unfiltered symbol/date range is empty.
- Category-filtered calls, nonzero counts, malformed payloads, and probe failures remain provider errors, so schema changes are not hidden.

## Queue note

- Redis contained one historical A-share canary backfill when the first worker started. The single worker consumed it before disclosure acceptance; it completed with its existing bounded `partial` result.
- The queue and active task list were confirmed empty before every official-disclosure canary/restart, so no AkShare backfill overlapped the disclosure tasks.
