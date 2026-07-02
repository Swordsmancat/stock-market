# API Proxy Test Implementation Report

## Selected Route

- Route under test: `apps/web/app/api/task-runs/[taskRunId]/retry/route.ts`
- Test file added: `apps/web/app/api/task-runs/[taskRunId]/retry/route.test.ts`

## Why This Route Was Selected

Task-run retry is a high-value operator workflow. When a backend task fails, the frontend uses this Next.js route handler to forward the retry request to the FastAPI backend. A regression in this proxy could make failed jobs unrecoverable from the UI even if the backend retry endpoint still works.

This route also exercises important proxy behavior that should stay stable:

- builds the upstream URL from `getBackendApiUrl()` and the dynamic `taskRunId` route parameter;
- forwards the request with `POST` and `cache: "no-store"`;
- preserves the upstream response status;
- preserves the upstream `content-type` header;
- returns the upstream payload without rewriting success or failure bodies.

## Implemented Coverage

The added Vitest route tests cover:

- successful retry forwarding to `/task-runs/<taskRunId>/retry` with the expected method and cache option;
- propagation of backend failure responses, including a `404` payload, without frontend-side rewriting.

## Validation

Validation passed with:

```bash
npm run test:web
```

Result at verification time:

- Test files: 11 passed
- Tests: 19 passed

## Scope Boundaries

- No backend Python files were modified.
- No backend API contracts were changed.
- No unrelated frontend page rewrites or i18n cleanup were included.
