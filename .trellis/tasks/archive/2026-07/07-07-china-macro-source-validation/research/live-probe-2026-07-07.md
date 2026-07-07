# Live Probe Snapshot: China Macro Source Validation

Run date: 2026-07-07

Command:

```powershell
python scripts/validate_china_macro_sources.py --live-network --timeout 8
```

## Result Summary

| Source | Result | Interpretation |
|---|---:|---|
| `nbs_cn_macro` | `FAIL` / HTTP 403 | Keep as candidate/manual until access pattern, schema, and usage terms are validated. Do not build a production adapter from this probe alone. |
| `pboc_cn_m2` | `OK` / HTTP 200 | Public page is reachable and contains expected M2 marker, but current capability remains `manual_only` because no stable machine-readable endpoint has been validated. |
| `world_bank_china_macro` | `OK` / HTTP 200 | Public API is reachable and matches expected China marker. It remains the safest low-frequency follow-up candidate. |
| `imf_china_macro` | `FAIL` / HTTP 403 | Keep as candidate/manual until API access behavior is validated. |
| `trading_economics_china_macro` | `WARN` / skipped | Vendor API requires credential/license review before use. |
| `akshare_tushare_cn_macro` | `WARN` / skipped | Library wrapper path requires dependency, token/upstream-source, license, and schema validation before use. |

## Citation Boundary

This probe wrote no database rows and created no AI citations. Source capability metadata, HTTP status, collection links, and probe diagnostics are guidance only. AI may cite China macro data only after a follow-up adapter or audited seed import stores validated `MarketIndicatorObservation` rows with source and methodology metadata.

## Recommended Next Adapter Candidate

World Bank China annual macro context is the safest next adapter candidate because the project already has a World Bank provider/refresh pattern and the live probe succeeded. It should be limited to low-frequency context such as GDP and annual valuation support. Monthly China CPI/PPI/PMI/M2 still needs NBS/PBOC validation or manual seed workflow.
