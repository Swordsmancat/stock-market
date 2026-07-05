# Website Entry Stability and Feature Gap Plan Implementation Plan

## Slice 1: Entry Stability Verification

1. Confirm whether a local Next.js dev server is already running before starting another one.
2. Open `http://localhost:3000/zh` in the browser.
3. Capture a browser snapshot and verify that the localized dashboard renders instead of a Next.js error overlay.
4. Record any remaining warnings as blocking or non-blocking based on observed page behavior.

## Slice 2: Immediate Entry Fix

1. Remove the Server Component to Client Component function prop from the homepage `SmartRecommendations` usage.
2. Preserve recommendation link behavior through the client component default href generation.
3. Avoid touching theme-provider infrastructure unless the script warning blocks page entry.

## Slice 3: Focused Validation

1. Run homepage-focused tests:

   ```bash
   npx vitest run "apps/web/app/[locale]/page.test.tsx" --reporter=dot
   ```

2. Read IDE lint diagnostics for changed frontend files when available.
3. Use browser snapshot evidence to confirm live page render.

## Slice 4: Feature Status and Professional Gap Reconciliation

1. Summarize current Phase 2 / Phase 3 implementation status from README, user manual, and developer runbook.
2. Classify each feature as complete, provider-backed MVP, provider-boundary MVP, partial, or future enhancement.
3. Compare current capabilities with professional financial platforms:
   - TradingView-style charting
   - Bloomberg/Koyfin/AlphaSense-style research
   - broker Level-2/order-flow terminals
   - CN retail-market terminals
4. Produce a prioritized follow-up plan with Trellis-ready task candidates.

## Slice 5: Follow-up Task Decisions

1. Do not create extra follow-up tasks for tiny documentation-only adjustments.
2. Create or reuse Trellis tasks for larger independently verifiable improvements.
3. Keep provider-dependent tasks honest about degraded/no-data behavior.

## Validation Commands

- `npx vitest run "apps/web/app/[locale]/page.test.tsx" --reporter=dot`
- Browser snapshot for `http://localhost:3000/zh`
- Optional later: `npm run test:web` if additional frontend files are changed

## Completed Evidence So Far

- `/zh` browser snapshot rendered the dashboard successfully with title `Stock Analysis Platform` and localized navigation/content.
- The reported function-prop error was addressed by removing the `getInstrumentHref` prop from homepage `SmartRecommendations` usage.
- Focused homepage test passed: `npx vitest run "apps/web/app/[locale]/page.test.tsx" --reporter=dot` -> `1 passed`, `2 tests passed`.
- IDE lint diagnostics previously returned `0` diagnostics for the checked frontend files.
- The `next-themes` script warning did not block the observed `/zh` render; treat as a follow-up only if it remains reproducible as a blocking overlay.
- Professional benchmark reconciliation was recorded in `professional-gap-plan.md`, including current capability classification, TradingView/Bloomberg/Koyfin/AlphaSense/broker/CN-terminal gaps, prioritized improvements, and recommended Trellis execution order.

## Rollback Notes

- If recommendation links regress, restore equivalent href generation as serialized string data rather than passing functions across the Server/Client boundary.
- If theme warnings become blocking, split a focused theme-provider task and avoid mixing it with provider/data feature work.
