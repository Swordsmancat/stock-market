# Real Market Depth Provider Pipeline Live Smoke Evidence

## Attempted command

```bash
python scripts/provider_readiness.py --provider akshare --market CN --symbol 600519 --check-depth --depth-levels 3 --real-network
```

## Result

Status: failed.

The readiness script returned:

```text
FAIL provider depth readiness: akshare returned no verified market-depth sections for 600519.
provider=akshare
market=CN
symbol=600519
depth_levels=3
availability_reason=AkShare market-depth endpoint failed or changed schema.
availability_exception_type=ConnectionError
database_writes=none
```

## Interpretation

This confirms that the current AkShare depth implementation is still a fixture-tested candidate path, not a production-verified Level-2 provider. The latest diagnostic run exposed `availability_exception_type=ConnectionError`, so the current environment is failing before a usable schema sample can be normalized.

The backend must continue to return degraded/no-data semantics for live AkShare depth failures and must not fall back to daily bars, minute bars, mock rows, or estimated distributions.

## Follow-up

- Re-run the opt-in live smoke from a network environment that can reach the AkShare endpoint and capture the safe diagnostics emitted by readiness (`availability_exception_type`, `availability_raw_shape`, `availability_raw_columns`, `availability_raw_fields_sample`) before adapting parser fields.
- Add parser support only after schema fields are verified with fixture-backed tests.
- Keep the smoke check opt-in and non-writing.
- Do not promote AkShare Level-2 capability until at least one live smoke succeeds and the capability matrix is updated.

## 2026-07-05 Rerun

The same opt-in command was rerun:

```bash
python scripts/provider_readiness.py --provider akshare --market CN --symbol 600519 --check-depth --depth-levels 3 --real-network
```

Result remained `FAIL` with `availability_exception_type=ConnectionError` and `database_writes=none`. This keeps the current status unchanged: fixture-tested candidate path only, not production-verified Level-2.
