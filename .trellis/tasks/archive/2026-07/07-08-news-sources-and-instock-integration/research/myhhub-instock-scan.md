# myhhub/stock InStock Scan

Date: 2026-07-08

## Source

- Repository: https://github.com/myhhub/stock
- Inspected HEAD: `b6e0ca2268cfbadd02f5ed052159c187b6670231`
- License: Apache-2.0
- Local inspection path: `%TEMP%/myhhub-stock-inspect`

## README Feature Map

- Comprehensive stock selection across stock scope, fundamentals, technicals, news/events, popularity, and market data.
- Daily stock and ETF data jobs.
- Technical indicators via pandas, numpy, and TA-Lib.
- Buy/sell heuristic screens.
- 61 K-line pattern recognitions.
- Chip distribution / CYQ.
- Built-in strategy selection.
- Backtest validation.
- Automatic trading examples.
- Watchlist/follow features.
- Batch jobs by current date, explicit dates, or date ranges.
- Proxy and Cookie support for data fetching.
- Database-backed storage and Tornado web visualization.

## Dependency / Architecture Differences

- InStock targets Python 3.11; this project targets Python >=3.12.
- InStock requires TA-Lib, PyMySQL, Tornado, Bokeh, easytrader, py_mini_racer/mini-racer, and other dependencies not currently in this project.
- InStock uses MySQL/MariaDB oriented configuration; this project uses SQLAlchemy with PostgreSQL default and SQLite test fixtures.
- InStock has its own web UI and scheduled jobs; this project already has FastAPI, Celery, and Next.js.

## Candidate Reuse Modules

- `instock/core/indicator/calculate_indicator.py`: broad TA-Lib indicator calculation.
- `instock/core/pattern/pattern_recognitions.py`: K-line pattern application using configured functions.
- `instock/core/strategy/*.py`: individual screening heuristics.
- `instock/core/backtest/rate_stats.py`: simple return-path stats.
- `instock/core/kline/cyq.py`: chip distribution candidate, likely needs deeper review before porting.

## Risky / Excluded By Default

- `instock/trade/**`: automatic trading, broker login, strategy execution.
- Proxy and cookie scraping setup.
- Tornado web UI and static assets.
- Direct database schema import.
- Bulk scheduler replacement.

## Recommended Integration Shape

1. Do not vendor the whole repository.
2. Pick one analysis module family and port/adapt it into this project's service layer with attribution.
3. Add test fixtures over local OHLCV rows and compare deterministic output.
4. Surface results as research signals, not trading instructions.
5. Keep auto trading out unless the user explicitly opens a separate risk-reviewed task.
