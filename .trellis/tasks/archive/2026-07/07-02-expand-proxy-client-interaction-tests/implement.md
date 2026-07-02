# Expand Proxy Client Interaction Tests Report

## Selected Route

- Route under test: `apps/web/app/api/reports/[symbol]/daily/generate/route.ts`
- Test file added: `apps/web/app/api/reports/[symbol]/daily/generate/route.test.ts`

## Why This Route Was Selected

Daily report generation is a high-value operator workflow and a good regression target for route-handler proxy behavior. It uses a dynamic `symbol` path segment, forwards optional query parameters, and must preserve upstream status, content type, and payload. It also does not overlap the TaskRun detail diagnostics UI lane.

## Implemented Coverage

- Successful `POST` forwarding to `/reports/<symbol>/daily/generate`.
- Dynamic symbol URL encoding, including `BRK/B` -> `BRK%2FB`.
- Query parameter passthrough for values such as `force=true`, `task_run_id=task-123`, and `provider=tushare`.
- `method: "POST"` and `cache: "no-store"` forwarding options.
- Successful upstream response propagation with status, content type, and JSON payload.
- Upstream failure propagation without rewriting `503 application/problem+json` responses.

## Validation

```bash
npm run test:web
```

Result after full frontend validation:

- Test files: 12 passed
- Tests: 25 passed

## Scope Boundaries

- No backend Python files were modified for this lane.
- No backend API contracts were changed.
- No TaskRun detail UI files or translation files were touched by this lane.
