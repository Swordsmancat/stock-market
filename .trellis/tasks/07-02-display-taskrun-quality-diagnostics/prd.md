# Display TaskRun quality diagnostics

## Goal

Add a dedicated TaskRun detail UI section that renders persisted ingestion quality diagnostics in a user-readable, localized, and defensive way.

## Requirements

- Use the archived design `.trellis/tasks/archive/2026-07/07-02-design-taskrun-quality-diagnostics/design.md` as the source of truth.
- Read diagnostics from `taskRun.result_json.quality_diagnostics` when present.
- Defensively parse unknown JSON and avoid throwing on malformed or partial diagnostics.
- Render clear states for missing diagnostics, `OK`, `WARN`, and `FAIL`.
- Show per-instrument diagnostic details where available, including missing dates, invalid OHLC details, volume warnings, and quality errors.
- Keep raw `result_json` visible as a fallback/debug aid.
- Add English and Chinese translations for user-visible labels.
- Preserve existing retry button, report link extraction, status badge, and raw JSON behavior.

## Acceptance Criteria

- [x] TaskRun detail renders normally when `quality_diagnostics` is missing.
- [x] `OK` diagnostics show a concise successful summary.
- [x] `WARN` diagnostics show warnings without presenting the TaskRun as failed.
- [x] `FAIL` diagnostics show failure details separately from worker execution status.
- [x] Unknown diagnostic issue objects render with a safe fallback instead of crashing.
- [x] Raw `result_json` remains visible.
- [x] English and Chinese message catalogs are updated together.
- [x] Frontend tests pass.

## Validation

```bash
npm run test:web
```

## Notes

- Expected page file: `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx`.
- Expected translation files: `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Final integration should align with the backend persisted shape from `07-02-persist-taskrun-quality-diagnostics`.
