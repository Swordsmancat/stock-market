# Eastmoney Industry Ranking History Contract

- The provider owns the Eastmoney `push2` industry universe and `push2his`
  daily K-line schemas. Normalized records contain code, name, trade date,
  finite daily change percent, and retrieval time.
- Requests are direct-first. An optional configured HTTP(S) proxy receives at
  most one fallback attempt per failed request. A manually supplied Cookie may
  be attached; browser state is never harvested automatically.
- Proxy URLs and Cookies are secrets. Public settings expose only configured
  booleans, and diagnostics never include headers, credential URLs, upstream
  bodies, exception text, or stored secret values.
- Explicit refresh gathers and validates records before committing a complete
  revision. Provider failure preserves stored history. Rank order is change
  percent descending with industry code as the deterministic tie breaker.
- GET and page render are database-only and bounded to 20 dates by 20 ranks.
  Empty storage and failed loading are distinct localized states.
- The Evidence Center matrix is horizontally scrollable. It is research
  context only and must not initiate login, orders, or automated trading.

Implementation anchors:

- `packages/providers/eastmoney_industry_rankings.py`
- `packages/services/industry_rankings.py`
- `apps/api/routers/sectors.py`
- `apps/web/components/industry-ranking-history-panel.tsx`
- `docs/runbooks/eastmoney-industry-ranking-history.md`
