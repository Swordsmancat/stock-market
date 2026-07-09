# Entrance page terminal visual alignment design

## Boundaries

- Frontend-only work in `apps/web`.
- Primary candidate files:
  - `apps/web/app/[locale]/instruments/page.tsx`
  - `apps/web/components/instrument-detail-client.tsx`
  - `apps/web/app/[locale]/evidence/page.tsx`
  - `apps/web/app/[locale]/settings/page.tsx`
  - `apps/web/components/ai-research-desk.tsx`
  - relevant colocated tests under `apps/web/app/[locale]/**`
  - `apps/web/messages/en.json` and `apps/web/messages/zh.json` only if new visible copy is needed
- No backend endpoint, schema, storage, or provider configuration changes.

## Visual System

- Treat the homepage terminal style as the visual source of truth:
  - compact spacing
  - 8px radius or less
  - `border-border/80` style boundaries
  - `bg-card/95` section bodies
  - `bg-background/60` or similar section headers
  - monospaced numeric values where data is tabular
  - lightweight Lucide icons where already used or clearly useful
- Keep page headers through `FinancialPageHeader`; it already matches the dense finance page convention.
- Align downstream sections by changing card/header/content classes before adding new components.
- Consider a shared `TerminalSection`/`FinancialTerminalSection` component only if the same card/header/content pattern is repeated across at least three pages in a way that would otherwise drift.

## Page Strategy

### Instruments

- Keep the current search form and table behavior.
- Make filter/search and health summary sections visually closer to homepage panels.
- Preserve table columns, links, and comparison tool ownership.

### Instrument Detail

- Keep `InstrumentDetailClient` client-side behavior and existing data shape.
- Align report, technical indicator, fundamentals, latest news, intraday, and K-line cards.
- Preserve back button, external links, `MarketAssistantCard`, `MarketDepthCard`, and trust badges.

### Evidence

- Preserve macro/citation/source semantics.
- Align brief/evidence/cards and source rows without hiding warnings or diagnostics.
- Keep advanced tools collapsed behavior intact.

### Settings

- Preserve server action form wiring and input names.
- Align settings cards while keeping provider/key secrecy behavior and helper text.
- Do not introduce client state for settings.

### AI Research

- Keep `AiResearchDesk` as the owning component.
- Align shell/cards/lists with terminal surfaces.
- Preserve research-only copy and no-trading-instruction boundary.

## Testing Strategy

- Prefer updating existing colocated page tests.
- Assert stable visible behavior rather than class names where possible.
- For purely visual class changes, keep tests focused on route actions, headings, forms, and important empty/error states.
- Use TypeScript and focused Vitest page/component tests as the primary automated guard.

## Visual Verification

- Use Chrome desktop and tall mobile screenshots after implementation.
- Recommended minimum:
  - `/zh/instruments`
  - `/zh/evidence`
  - `/zh/settings`
  - `/zh/ai-research`
  - one `/zh/instruments/{symbol}` fixture route if backend data is available
- Check no horizontal overflow, no text overlap in buttons/cards, and terminal style continuity from the homepage.
