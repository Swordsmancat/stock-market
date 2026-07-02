# Bootstrap backend guidelines

## Goal

Populate backend Trellis guidelines with the stock analysis platform's actual FastAPI, SQLAlchemy, Celery, testing, and diagnostics conventions so future subagents follow project-specific patterns instead of generic defaults.

## Requirements

- Inspect existing backend implementation and tests before writing guidelines.
- Fill the backend spec files with observed conventions, not aspirational rules.
- Cover directory structure, database/migration patterns, error handling, logging, and quality/testing expectations.
- Include real file path examples from the repository.
- Update `.trellis/spec/backend/index.md` statuses from placeholder values to reflect completed guideline content.
- Avoid modifying frontend specs, source code, tests, or git history.

## Acceptance Criteria

- [x] `.trellis/spec/backend/directory-structure.md` describes actual route/service/provider/domain/script layout.
- [x] `.trellis/spec/backend/database-guidelines.md` describes current SQLAlchemy session, model, and Alembic patterns.
- [x] `.trellis/spec/backend/error-handling.md` describes current exception mapping and diagnostic-script error handling patterns.
- [x] `.trellis/spec/backend/logging-guidelines.md` documents current logging state and sensitive-data boundaries.
- [x] `.trellis/spec/backend/quality-guidelines.md` documents focused pytest and non-mutating diagnostics expectations.
- [x] Backend index status table reflects filled guideline files.
- [x] Every guideline includes real repository path examples.

## Notes

- Lightweight documentation task; PRD-only is sufficient.
- Validation target: `python ./.trellis/scripts/task.py validate 00-bootstrap-guidelines` after backend and frontend guideline tasks are both complete.
