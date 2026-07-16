# Verified Eastmoney public fundamentals endpoints

Read-only probes on 2026-07-16 used no Cookie, authorization, redirects, POST,
or persistent writes.

## Financial summary

- Host/path: `datacenter.eastmoney.com/securities/api/data/get`
- Dataset: `RPT_F10_FINANCE_MAINFINADATA`
- Fixed identity filter: `SECUCODE="<symbol.exchange>"`
- Sorting: `REPORT_DATE` descending
- Verified fields: `REPORT_DATE`, `CURRENCY`, `TOTALOPERATEREVETZ`, `XSJLL`,
  `ZCFZL`, `SECURITY_CODE`, `SECUCODE`.
- Response: HTTP 200 JSON reported as `text/plain;charset=UTF-8`.

## Company survey

- Host/path: `emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax`
- Fixed query: exchange-prefixed code such as `SH600519`.
- Verified section: one `jbzl` row with `SECURITY_CODE`, `SECUCODE`, `ORG_NAME`,
  `INDUSTRYCSRC1`, `BUSINESS_SCOPE`, and `ORG_PROFILE`.
- Response: HTTP 200 `application/json`.

## Constraints

- Endpoints are undocumented web internals and may drift.
- Public reachability is not permission for bulk storage or redistribution.
- Use local personal low-frequency fallback only, with strict schemas, bounds,
  attribution, short cache, provider kill switch, and sanitized diagnostics.
- PE is not present in the verified financial report and must remain null.
