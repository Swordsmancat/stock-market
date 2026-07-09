# Homepage terminal panel actions and layout polish design

## Boundaries

- Frontend-only implementation inside the Next.js app.
- Primary files:
  - `apps/web/app/[locale]/page.tsx`
  - `apps/web/app/[locale]/page.test.tsx`
  - `apps/web/messages/en.json`
  - `apps/web/messages/zh.json`
- No new backend endpoints, settings fields, routes, or global client state.

## UI Structure

- Reuse `TerminalPanel.action` for module-level actions.
- Add a small reusable action helper in `page.tsx` if it reduces duplicated button/link markup.
- Keep actions compact and terminal-like:
  - outline/ghost-style `Button` where consistent with the existing homepage
  - Lucide icons only where they add clarity
  - 44px interactive height on mobile where feasible, without enlarging desktop density excessively
- Use localized labels:
  - `terminalActionMore`
  - `terminalActionAddCustomIndicator`

## Middle Panel Layout

The three center panels should share a stable shell:

- Panel shell: fixed height matching the current `15.5rem` intent at both required visual-check sizes.
- Header: owned by `TerminalPanel`; it must not be part of the scrollable/clipped body.
- Body: flex column with `min-h-0` so table/list content can be constrained inside the fixed shell.
- Column headers: remain visible at the top of macro and sector panels.
- Rows: fixed minimum row heights with truncation/line-clamp for long labels.
- Empty states: vertically placed inside the body and constrained to the same height as the populated state.

## Routing Choices

- Use existing localized `Link` routes.
- Macro add custom action links to the existing settings textarea anchor, `/settings#favorite_macro_indicator_codes`.
- Latest news routes to the primary instrument detail page because that surface already renders stored latest news.
- Hot sectors and fund flow route to `/instruments` until a dedicated sector surface exists.

## Compatibility

- Existing homepage data loading remains server-side.
- Existing tests using mocked backend fetches should continue to work.
- The provider strip continues to show capability/status metadata only; no secrets are rendered.

## Visual Verification

- Use Chrome with Playwright at:
  - desktop `1920x1080`
  - mobile `1080x1920`
- Confirm no panel-header overlap, no horizontal overflow, and no body content escaping the fixed center panels.
