# External Source Feasibility

Checked on 2026-07-07 for the online macro source adapter planning task.

## Product Direction

The site should remain a personal information aggregation and AI research cockpit. It should prioritize online/API-backed macro evidence, source transparency, and AI summaries over professional trading-terminal parity.

## Source Assessment

| Source | Fit | Feasibility | Recommended Use |
|---|---:|---|---|
| FRED | High | Already implemented as an opt-in official adapter. It requires `FRED_API_KEY`, uses `/series/observations`, skips missing `"."` values, and writes audited observations. | Keep as the baseline official-source adapter for US rates, spread, CPI YoY, and M2 YoY. |
| World Bank API | High | Public API shape is stable enough for a first new adapter. Direct local network probing timed out in this environment, so implementation should use mocked HTTP tests and sanitized runtime diagnostics. | First new adapter for Buffett Indicator ratio and GDP/market-cap component metadata. |
| National Bureau of Statistics China | Medium | Official data portal exists, but direct `data.stats.gov.cn/easyquery.htm` probing returned HTTP 403 in this environment. The official database was announced as a trial/online service, but public API stability and access policy need a spike. | Defer from MVP. Keep China macro as manual seed/source-readiness until a validated official/API path is confirmed. |
| PBOC | Medium | Good official source for monetary statistics, but existing project already models it as manual/reviewed seed guidance. | Keep as manual seed in MVP; later add a validated adapter if an official machine-readable endpoint is confirmed. |
| Trading Economics | Medium | Broad macro coverage, but product/API usage usually depends on commercial access or keys. | Treat as optional paid adapter, not core MVP. |
| Tushare Pro | Medium | Good for China market/fundamental data when a token is available. Existing `.env.example` already has `TUSHARE_TOKEN`. | Useful for stock/fundamental extensions, not the first macro adapter unless the user has a token and accepts the dependency. |
| AkShare | Medium/Low | Convenient Python source for China data, already optional under `cn-market`, but interface stability and source provenance vary by endpoint. | Supplemental adapter only; not a citation-critical core source without endpoint-level validation. |
| yfinance | Medium | Already a market-data dependency. Useful for historical stock prices, less suitable as an authoritative macro source. | Keep for market/watchlist data, not macro source-of-truth. |
| Eastmoney / Snowball / THS reverse-engineered APIs | Low | Often useful for human reference, but terms/schema stability and scraping/reverse-engineering risk make them poor core evidence sources. | Reference links or later optional experiments only; do not make them default AI-citable macro evidence. |

## Local Probe Notes

- `https://api.worldbank.org/v2/country/USA/indicator/CM.MKT.LCAP.GD.ZS?format=json&mrnev=3` timed out from local PowerShell.
- `https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&mrnev=3` timed out from local PowerShell.
- `https://data.stats.gov.cn/easyquery.htm?...` returned HTTP 403 from local PowerShell.

These probe failures should not block an adapter design when the public contract is documented, but tests must not depend on live network availability.

## MVP Recommendation

Start with a World Bank adapter for the existing `buffett_indicator_us`, `buffett_indicator_cn`, and `buffett_indicator_hk` codes:

- fetch the market-cap-to-GDP percentage indicator where available;
- optionally fetch GDP current USD for component context;
- write through `MarketIndicatorObservationSeed` and `upsert_market_indicator_observation(...)`;
- include country code, World Bank indicator ID, source URL, retrieved time, latest source date, and calculation/methodology metadata;
- skip missing/null values instead of storing zeros;
- surface no-data, timeout, and unsupported-country diagnostics without exposing raw stack traces.

Defer NBS, Trading Economics, AkShare macro endpoints, and reverse-engineered aggregator feeds until a later task validates access, licensing, and schema stability.

## References

- FRED API series observations: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- World Bank API call structure: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures
- World Bank market capitalization to GDP indicator: https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS
- World Bank GDP current USD indicator: https://data.worldbank.org/indicator/NY.GDP.MKTP.CD
- National Bureau of Statistics database announcement: https://www.stats.gov.cn/xw/tjxw/tzgg/202603/t20260325_1962844.html
- Trading Economics API entry: https://tradingeconomics.com/analytics/api.aspx
- Tushare Pro documentation: https://tushare.pro/document/2
- AkShare documentation: https://akshare.akfamily.xyz/
