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
