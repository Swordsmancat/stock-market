# Post-Merge Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan step-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize frontend mutations and API connectivity after merging feat/platform-priority-2-7 to master.

**Architecture:** Unify backend URL via `getBackendApiUrl()` / `backendFetch()`; convert remaining client-side portfolio/instrument mutations to Server Actions with flash banners; clean up dead code and gitignore.

**Tech Stack:** Next.js Server Actions, FastAPI, next-intl

---

### Task 1: Unify API base URL

**Files:**
- Modify: `apps/web/lib/backend-api.ts`
- Modify: all `apps/web/app/api/**/route.ts`
- Modify: server pages using `apiBaseUrl` constant

- [x] Export `getBackendApiUrl()` as single source; default `http://127.0.0.1:8000`
- [x] Replace inline `process.env... ?? "http://localhost:8000"` in API routes
- [x] Replace server page `fetch(apiBaseUrl...)` with `backendFetch(...)`

### Task 2: Gitignore & docs

**Files:**
- Modify: `.gitignore`, `.env.example`, `README.md`
- Modify: `apps/web/messages/en.json`, `apps/web/messages/zh.json` (System banner)

- [x] Ignore `.env.local`, `*.tsbuildinfo`
- [x] Document `API_BASE_URL` in `.env.example`

### Task 3: Portfolio Server Actions

**Files:**
- Modify: `apps/web/app/[locale]/actions.ts`
- Create: `apps/web/components/portfolio-forms.tsx`
- Modify: `apps/web/app/[locale]/portfolios/page.tsx`
- Delete: `apps/web/components/portfolio-actions.tsx`

- [x] Add create/add/remove/rename/delete portfolio actions
- [x] Server form components with flash via `?op=` query params

### Task 4: Instrument watchlist Server Action

**Files:**
- Create: `apps/web/components/instrument-watchlist-form.tsx`
- Modify: `apps/web/components/instrument-actions.tsx`
- Modify: `apps/web/app/[locale]/instruments/[symbol]/page.tsx`

- [x] Replace client fetch watchlist add with server form action

### Task 5: Cleanup & verify

**Files:**
- Delete: `apps/web/components/watchlist-actions.tsx` (unused)

- [x] Run `pytest` and `npm run test:web`
