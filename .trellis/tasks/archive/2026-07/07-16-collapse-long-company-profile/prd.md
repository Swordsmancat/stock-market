# Collapse long company profile

## Goal

Use accessible progressive disclosure for long company scope and profile on instrument detail pages.

## Requirements

- Keep the company name and industry visible in the fundamentals card whenever they are available.
- Place the potentially long business scope and company profile inside one native, keyboard-accessible disclosure control.
- Keep the disclosure closed by default so downstream news, intraday, and chart content appears substantially earlier on first render.
- Provide localized Chinese and English disclosure labels with a visible focus state and a touch target of at least 44 pixels.
- Preserve all homepage, API, provider, and fundamentals data behavior.

## Acceptance Criteria

- [x] Company name and industry remain visible while the long-form company details are collapsed.
- [x] Business scope and company profile remain in the DOM under a native `<details>` element that has no default `open` state.
- [x] The summary is localized, keyboard accessible, focus visible, and at least 44 pixels tall.
- [x] Expanding the disclosure reveals the available long-form fields without changing their content.
- [x] The detail page has no horizontal overflow at desktop or mobile widths.
- [x] Relevant component tests, Web type checking, and the full Web test suite pass.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
- Browser QA at 1280x720 confirmed a closed 46px disclosure, a 44px summary target, keyboard focusability, successful expansion, and no horizontal overflow. The responsive implementation adds no fixed width and uses the existing mobile-first card layout.
