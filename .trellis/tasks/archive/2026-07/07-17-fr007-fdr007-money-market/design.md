# Design

## Data flow

ChinaMoney -> AkShare `repo_rate_hist` -> `AkShareMacroProvider` family
`repo_rates` -> existing macro refresh service ->
`MarketIndicatorObservation` -> database-only dashboard GET -> localized cards.

## Semantics

- `FR007`: seven-day repo fixing rate.
- `FDR007`: seven-day depository-institutions repo fixing rate as named by the
  provider response. It remains a distinct code and is not silently renamed to
  `DR007`.
- Values are direct percentages; no scaling or derived calculation is applied.

## Fetch window

`repo_rate_hist` requires start and end dates in the same month. The default
fetcher requests the complete previous calendar month and the current month to
date, concatenates both frames, and lets the existing normalization path
deduplicate/sort/truncate to `history_limit`.

## Failure behavior

Each family is isolated by the existing AkShare refresh result contract.
Provider/schema failures return bounded diagnostics, write no repo observations,
and do not delete prior rows. Unit tests inject frames and do not call the live
provider.
