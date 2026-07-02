# Bootstrap frontend guidelines

## Goal

Populate frontend Trellis guidelines with the stock analysis platform's actual Next.js App Router, next-intl, Server Actions, component, state, type-safety, and Vitest conventions.

## Requirements

- Inspect existing frontend pages, components, API proxies, translations, and tests before writing guidelines.
- Fill the frontend spec files with observed conventions, not aspirational rules.
- Cover directory structure, component patterns, hook usage, state management, type-safety, and quality/testing expectations.
- Include real file path examples from the repository.
- Update `.trellis/spec/frontend/index.md` statuses from placeholder values to reflect completed guideline content.
- Avoid modifying backend specs, backend source code, API contracts, or git history.

## Acceptance Criteria

- [x] `.trellis/spec/frontend/directory-structure.md` describes actual `apps/web` App Router organization.
- [x] `.trellis/spec/frontend/component-guidelines.md` describes current component and UI composition patterns.
- [x] `.trellis/spec/frontend/hook-guidelines.md` documents current hook usage and notes when hooks are absent or minimal.
- [x] `.trellis/spec/frontend/state-management.md` describes server state, URL state, forms, and local state patterns.
- [x] `.trellis/spec/frontend/type-safety.md` documents current type patterns, `as any` debt, and preferred future direction grounded in existing code.
- [x] `.trellis/spec/frontend/quality-guidelines.md` documents Vitest/page-test/i18n expectations.
- [x] Frontend index status table reflects filled guideline files.
- [x] Every guideline includes real repository path examples.

## Notes

- Lightweight documentation task; PRD-only is sufficient.
- Validation target: `python ./.trellis/scripts/task.py validate 00-bootstrap-guidelines` after backend and frontend guideline tasks are both complete.
