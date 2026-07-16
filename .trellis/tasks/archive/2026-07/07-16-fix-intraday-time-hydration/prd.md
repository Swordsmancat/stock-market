# Fix intraday time hydration

## Goal

Prevent instrument-detail hydration failures by formatting intraday timestamps
with explicit locale and market time-zone inputs on both server and client.

## Requirements

- Preserve the existing intraday payload, chart data, trust metadata, and API behavior.
- Format displayed intraday time with the active page locale and an explicit
  market time zone instead of host defaults.
- Use `Asia/Shanghai` for CN, `Asia/Hong_Kong` for HK, and
  `America/New_York` for US; use UTC for unknown markets.
- Keep the change limited to the instrument-detail intraday presentation.
- Preserve unrelated five-day acceptance and worktree metadata.

## Acceptance Criteria

- [x] A component regression proves the same timestamp uses the supplied locale
      and time zone rather than the host environment.
- [x] TypeScript, focused/full Web tests, and Trellis validation pass.
- [x] A rebuilt local Web page no longer logs the intraday time hydration mismatch.
- [x] The task is committed, archived, journaled, and pushed.
