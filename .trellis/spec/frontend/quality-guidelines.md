# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

Frontend quality is enforced mainly through Vitest, Testing Library, and focused page/component tests. Tests should cover behavior that can regress, including request forwarding, user-visible messages, i18n strings, and empty/error state distinctions.

---

## Required Patterns

- Run `npm run test:web` after frontend behavior changes.
- Update `apps/web/messages/en.json` and `apps/web/messages/zh.json` together for user-visible text.
- Add or update colocated tests when page rendering behavior changes.
- Use `cleanup()` and mock restoration when a test file renders multiple components/pages.
- Prefer focused assertions on visible behavior and request calls over snapshot-like tests.

### Keep clean-install images reproducible

- Declare the package-manager version in the root `package.json` and use the
  same version in container builds that run `npm ci`. A lock file accepted by a
  newer npm release may be rejected by the npm release bundled with the base
  image, especially around optional peer dependencies.
- Root Docker ignore rules for generated frontend directories must match nested
  workspaces recursively (for example, `**/.next` and `**/node_modules`).
- Validate an acceptance image with a clean build before starting its Compose
  stack. Building images is non-mutating; starting a database-backed acceptance
  stack must still respect that stack's explicit write gates.
- Add a focused configuration regression when changing these rules so a local
  warm install cannot hide a broken clean build.

## Scenario: Loopback Dev Origins and Client Hydration

### 1. Scope / Trigger

- Trigger: the Next.js development server is opened through `localhost`,
  `127.0.0.1`, or another explicitly supported local hostname and the page
  contains client islands such as `GlobalSearch`.
- Scope: `apps/web/next.config.mjs`, local development startup, client chunk
  delivery, and browser interaction smoke checks.
- Non-goals: production CORS policy, public network exposure, wildcard origin
  access, or changing component interaction behavior.

### 2. Signatures

- Next config field: `allowedDevOrigins: string[]`.
- Required loopback entries: `127.0.0.1` and `localhost`.
- Regression: `apps/web/next-config.test.ts` loads the real Next config in a
  Node process and asserts both entries.
- Runtime probe: request one client chunk with
  `Origin: http://127.0.0.1:3000` and require HTTP 200.

### 3. Contracts

- A local hostname used to open the development UI must be present in
  `allowedDevOrigins`; add other required development hosts explicitly.
- HTTP 200 for the document is insufficient evidence that the UI is usable.
  At least one client chunk and one real client interaction must also pass.
- Text rendered by both the server and a client component must not inherit the
  host locale or time zone. Date/time formatters receive the active page locale
  plus an explicit market or product time zone so container UTC and browser
  local settings cannot produce different hydration text.
- A page whose document renders but whose client chunks return HTTP 403 is a
  failed state: server HTML may look complete while buttons have no handlers.
- Keep the allowlist limited to known local development hosts. Do not use a
  wildcard to hide an origin mismatch.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Document 200, client chunk 403 with loopback Origin | Add the exact local host to `allowedDevOrigins`, restart/reload Next, and repeat the probe |
| Document and chunk both 200, interaction still fails | Diagnose component hydration/runtime behavior; do not blame CORS without evidence |
| New local hostname is required | Add one explicit hostname plus a config regression |
| Production build | Must remain independent of the development-origin allowlist |
| Server/client time text differs | Pass explicit locale and time zone to the formatter and add a cross-zone component regression |

### 5. Good / Base / Bad Cases

- Good: `/zh` returns 200, a referenced `/_next/static/chunks/*` request with
  the `127.0.0.1` Origin returns 200, and clicking search opens its dialog.
- Base: the developer uses `localhost`; the same allowlist and interaction
  checks pass without special browser configuration.
- Bad: only curl the HTML, see the search button text, and declare the frontend
  healthy while every client chunk is rejected with 403.
- Bad: allow every development origin instead of listing the hosts actually
  used by this personal installation.
- Bad: call `toLocaleTimeString([])` during SSR and rely on the server and
  browser having identical defaults.

### 6. Tests Required

- Config test asserts the real exported Next config contains `127.0.0.1` and
  `localhost`.
- Browser acceptance clicks global search, exercises `Ctrl/Meta+K` and Escape,
  and verifies a result preserves `market` in the detail URL.
- SSR client components that render dates or times include a regression with a
  timestamp whose expected output differs from the test host's local zone.
- Environment recovery reruns the Origin-bearing client-chunk request and
  records the transition from 403 to 200.
- Run the full frontend suite, TypeScript, and a production Next build after a
  config change.

### 7. Wrong vs Correct

#### Wrong

```js
const nextConfig = {
  turbopack: { root },
};
```

This may return complete server HTML while Next rejects loopback-origin client
chunks, leaving visible controls inert.

#### Correct

```js
const nextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  turbopack: { root },
};
```

The known local hosts can load client chunks and hydrate interactive islands.

---

## Forbidden Patterns

- Do not add hardcoded UI text when a translation namespace already exists.
- Do not silently render empty state on fetch failures.
- Do not change backend API contracts from frontend tests.
- Do not commit or push from implementation subagents.

## Common Mistakes

### Raw JSON In `next-intl` Messages

**Symptom**: A page renders in tests but the browser console reports `INVALID_MESSAGE: MALFORMED_ARGUMENT` from `next-intl`.

**Cause**: User-visible messages are ICU-formatted. Literal JSON examples such as `{"observations":[...]}` inside `apps/web/messages/*.json` are parsed as interpolation arguments unless every brace is escaped correctly.

**Fix**: Avoid raw JSON with braces in translated message values. Prefer a text placeholder that names the expected fields, or pass dynamic examples from code through an explicit argument.

Wrong:

```json
{
  "pastePlaceholder": "{\"observations\":[{\"code\":\"us_10y_yield\"}]}"
}
```

Correct:

```json
{
  "pastePlaceholder": "JSON or CSV with observations: code, as_of, value, source"
}
```

**Tests Required**: When adding complex translated placeholders, browser-smoke the route or render the page through the server component path so malformed ICU messages are caught before delivery.

---

## Testing Requirements

- Page tests should render the server component and assert important visible text, table rows, links, and state branches.
- Client interaction tests should mock `fetch`, click controls, and assert loading/success/failure messages.
- Route proxy tests should call exported route handlers directly and assert upstream URL, method, status, content type, and payload propagation.
- Server Action tests should mock `backendFetch`, `redirect`, and `revalidatePath`, following `apps/web/app/[locale]/actions.test.ts`.

### Homepage Cold-Read And Locale Regressions

- A homepage timeout test must mock an AbortSignal-aware response at the real
  server-component fetch boundary. Wait until the target request is registered
  before advancing fake timers; otherwise the test can advance before the
  timeout exists.
- Prove that a market-overview response after six seconds still renders stored
  data and issues no POST. Separately prove that it is not aborted before
  twenty seconds and that the bounded abort retains the explicit failure state.
- Restore real timers in cleanup. Do not use `runAllTimersAsync()` for the
  success case because it also advances the terminal timeout and hides the
  ordering under test.
- For structured macro labels, render Chinese success and failure projections,
  English success, all built-in codes, and an unknown stored-name fallback.
  Assert raw codes are absent from visible homepage text and keep both locale
  catalogs symmetric.

```tsx
const pagePromise = HomePage({ params, searchParams });
await overviewRequestStarted;
await vi.advanceTimersByTimeAsync(6_000);
render(await pagePromise);
```

Browser acceptance for homepage layout changes covers `1440x1000` and
`1920x1080` two-column/three-row geometry, `1280x720` internal wheel scrolling,
and `390x844` single-column flow with no page-level horizontal overflow.

---

## Code Review Checklist

- Are user-visible strings localized in both languages?
- Are loading, empty, and error states distinct where users need diagnostics?
- Are mocks reset between tests?
- Does the test verify behavior rather than implementation details only?
- Are dynamic route casts or `any` uses existing debt, or did this change introduce new ones?

---

## Examples

- Page behavior tests: `apps/web/app/[locale]/task-runs/page.test.tsx`
- Server Action tests: `apps/web/app/[locale]/actions.test.ts`
- API proxy test: `apps/web/app/api/task-runs/[taskRunId]/retry/route.test.ts`
- Vitest config and aliases: `vitest.config.ts`
