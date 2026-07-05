# Real Intraday Minute Data Pipeline Live Smoke Evidence

## Attempted command

```bash
python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL --check-intraday --trade-date 2026-07-03 --real-network
```

## Result

Status: failed.

The readiness script returned:

```text
FAIL provider intraday readiness: yfinance returned no verified intraday bars for AAPL.
provider=yfinance
market=US
symbol=AAPL
trade_date=2026-07-03
timeframe=1m
database_writes=none
```

The provider stderr included:

```text
$AAPL: possibly delisted; no price data found  (1m 2026-07-03 -> 2026-07-04)
```

## Interpretation

This does not invalidate the fixture-backed and service/API intraday implementation, but it means the current environment cannot mark yfinance live `1m` readiness as production verified for this symbol/date.

The endpoint and UI should continue to treat this as `no_data` / readiness failure rather than fabricated minute rows.

## Follow-up

- Run the windowed diagnostic when no specific date is required: `python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL --check-intraday --real-network`. It now tries a bounded recent-weekday window controlled by `--intraday-lookback-days`.
- Try an explicit provider-known recent real trading date that is inside yfinance's actual 1m retention window when investigating a specific session.
- Add deeper provider-specific diagnostics for yfinance date availability if the windowed smoke still returns no verified rows.
- Keep the live smoke opt-in and non-writing.
- Do not promote broader intraday production readiness until a successful live smoke is recorded.
