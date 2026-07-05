# Website Entry Stability and Feature Gap Plan

## Goal

Confirm that the localized web entry point can be opened reliably after the reported Next.js runtime errors, fix any immediate entry blockers, then translate the current Phase 2 / Phase 3 implementation status into a professional-benchmark gap plan that can be executed through Trellis follow-up tasks.

## Requirements

- Verify that `http://localhost:3000/zh` can render without a blocking Next.js error overlay.
- Address the reported React Server Component boundary error where a function prop was passed into a Client Component.
- Classify the reported `next-themes` script warning as either blocking, non-blocking, or a separate follow-up, based on live page behavior.
- Preserve existing dashboard behavior, especially recommendation links and localized navigation.
- Run focused validation for the changed homepage area.
- Reconcile current implemented capabilities against the existing Phase 2 / Phase 3 manual and runbook status:
  - K-line interaction and technical indicators
  - smart recommendations
  - hot sector provider-backed MVP
  - yfinance intraday minute-bar MVP
  - market-depth provider-boundary MVP
  - AI market assistant MVP
- Compare the current product capabilities with professional financial websites or terminals, including TradingView, Bloomberg/Koyfin/AlphaSense-style research platforms, broker terminals, and CN retail-market terminals.
- Produce a prioritized optimization plan and decide which items should become Trellis follow-up tasks.

## Constraints

- Do not create or use fake market data to make a feature appear complete.
- Keep provider status explicit: `ok`, `no_data`, `degraded`, or `unavailable` as appropriate.
- Do not overwrite unrelated dirty work in the repository.
- Avoid broad refactors while stabilizing the website entry point.
- Keep this task focused on entry stability, status reconciliation, documentation, and planning; implementation-heavy feature work should be split into child tasks.

## Acceptance Criteria

- [x] `/zh` opens in the browser and renders the dashboard rather than a Next.js error overlay.
- [x] The function-prop Client Component error is removed or otherwise proven resolved.
- [x] The `next-themes` script warning is documented as non-blocking or split into a follow-up if it still appears.
- [x] Focused homepage test passes after the entry fix.
- [x] Current Phase 2 / Phase 3 status is summarized against professional financial platform capabilities.
- [x] A prioritized optimization plan exists with Trellis-ready follow-up items.
- [x] Validation evidence is recorded in `implement.md` before finishing the task.
