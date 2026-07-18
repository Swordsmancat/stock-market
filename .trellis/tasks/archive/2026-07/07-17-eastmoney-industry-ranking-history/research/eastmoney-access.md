# Eastmoney industry access research

## Source contract

- Industry universe: `https://17.push2.eastmoney.com/api/qt/clist/get`
  with `fs=m:90 t:2 f:!50`; useful fields include `f12` code, `f14` name and
  `f3` daily percentage change.
- Industry daily history:
  `http://7.push2his.eastmoney.com/api/qt/stock/kline/get`, `secid=90.BKxxxx`,
  `klt=101`; `f51..f61` normalize to date, OHLC, volume, amount, amplitude,
  change percent, change amount and turnover.
- AkShare references:
  `stock_board_industry_name_em` and `stock_board_industry_hist_em`.

## Live result on 2026-07-17

- Direct `httpx`, `requests`, AkShare, Windows curl and `curl_cffi` Chrome
  impersonation all ended with the remote peer closing the connection.
- Eastmoney's quote HTML page loaded in the in-app browser, but its direct API
  URL was blocked by the browser client and no industry grid data was exposed
  in the rendered DOM.
- This is a provider/network-access blocker, not a response-normalization bug.

## Security boundary

Do not inspect or export browser cookies. If credentials become an allowed
input, accept only a manually supplied secret through existing masked settings
or environment configuration. Never persist it in task artifacts, logs,
database audit metadata or API responses.
