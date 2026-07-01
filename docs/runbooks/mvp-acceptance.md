# MVP 验收手册

## 验收项

1. `/health` 返回 `{ "status": "ok" }`。
2. `/instruments` 返回 A股、港股、美股样例标的。
3. 技术指标测试覆盖 MA、RSI、BOLL 和 ATR。
4. 新闻舆情测试覆盖去重和情绪分类。
5. AI 报告测试确认报告包含数据截止时间和引用。
6. Web 首页展示“股票分析平台”和三类市场样例标的。
7. 后台任务可以调度 mock 行情采集、指标计算和报告生成。
8. AI 组合建议和报告内容保持研究辅助边界，不连接实盘交易，也不自动下单。
9. AI 个股报告包含基本面指标摘要，并在引用中标明 `fundamental_metrics` 来源。
10. `/fundamentals/{symbol}` DB 优先返回 PE、营收增速、净利率和资产负债率，DB 无数据时回退 mock fixture。
11. Web 首页单独展示 AI 报告和每日报告的引用来源，并将包含 URL 的新闻引用渲染为可点击链接。
12. Web 报告中心展示最新日报、历史日报和引用来源。
13. Web 模拟组合页展示持仓、市值、风险摘要和 AI 调仓建议。
14. Web 个股详情页展示行情快照、MA/RSI/BOLL/ATR、基本面指标、新闻舆情和 AI 摘要。
15. Web 任务监控页展示每日关注列表报告任务状态和最近任务运行记录。
16. Web 关注列表页从 `/watchlist` 读取持久化默认关注标的，并链接到对应个股详情页。
17. `/watchlist` 支持持久化关注标的，并为后续价格/指标提醒保留 `alert_rules` 字段。
18. AI 个股报告包含综合研判，汇总行情、BOLL/ATR、基本面和新闻情绪。

## 验收追踪矩阵

| # | 验收项 | 后端测试 | 前端测试 | 手动/API 检查 | 状态 |
|---:|---|---|---|---|---|
| 1 | `/health` 返回 `{ "status": "ok" }` | `tests/api/test_health.py` | 不适用 | `curl http://localhost:8000/health` | 已覆盖 |
| 2 | `/instruments` 返回 A股、港股、美股样例标的 | `tests/api/test_instruments_api.py` | `apps/web/app/[locale]/page.test.tsx` | `curl http://localhost:8000/instruments` | 已覆盖，需定期核对样例池 |
| 3 | 技术指标测试覆盖 MA、RSI、BOLL 和 ATR | `tests/analytics/test_indicators.py`, `tests/services/test_indicator_persistence_service.py`, `tests/api/test_indicators_db_api.py` | `apps/web/app/[locale]/instruments/[symbol]/page.test.tsx` | `curl http://localhost:8000/indicators/AAPL` | 已覆盖 |
| 4 | 新闻舆情测试覆盖去重和情绪分类 | `tests/services/test_news_service.py`, `tests/analytics/test_sentiment.py`, `tests/api/test_news_api.py` | `apps/web/app/[locale]/page.test.tsx`, `apps/web/app/[locale]/reports/page.test.tsx` | `curl http://localhost:8000/news/AAPL` | 已覆盖，真实新闻源另需 smoke |
| 5 | AI 报告包含数据截止时间和引用 | `tests/ai/test_report_builder.py`, `tests/ai/test_llm_report.py`, `tests/services/test_report_service.py`, `tests/api/test_reports_api.py` | `apps/web/app/[locale]/reports/page.test.tsx` | `curl http://localhost:8000/reports/AAPL/daily/latest` | 已覆盖 |
| 6 | Web 首页展示平台名称和三类市场样例标的 | `tests/api/test_instruments_api.py` | `apps/web/app/[locale]/page.test.tsx` | 打开 `http://localhost:3000/en` 或 `/zh` | 已覆盖 |
| 7 | 后台任务可以调度行情采集、指标计算和报告生成 | `tests/api/test_ingestion_api.py`, `tests/api/test_analysis_api.py`, `tests/worker/test_tasks.py`, `tests/services/test_task_dispatch.py` | `apps/web/app/[locale]/page.test.tsx`, `apps/web/app/[locale]/task-runs/page.test.tsx` | `curl -X POST http://localhost:8000/ingestion/snapshot?...` | 已覆盖，新入口为 `/ingestion/snapshot` |
| 8 | AI 组合建议和报告保持研究辅助边界 | `tests/api/test_report_portfolio_db_api.py`, `tests/services/test_portfolio_service.py`, `tests/api/test_portfolios_api.py` | `apps/web/app/[locale]/portfolios/page.test.tsx` | 打开 `/portfolios` 并检查文案 | 已覆盖 |
| 9 | AI 个股报告包含基本面摘要并引用 `fundamental_metrics` | `tests/api/test_reports_api.py`, `tests/services/test_report_service.py`, `tests/services/test_fundamentals_service.py` | `apps/web/app/[locale]/page.test.tsx`, `apps/web/app/[locale]/instruments/[symbol]/page.test.tsx` | 查看报告 citations | 已覆盖 |
| 10 | `/fundamentals/{symbol}` DB 优先，缺失时回退 mock fixture | `tests/api/test_fundamentals_api.py`, `tests/services/test_fundamentals_service.py`, `tests/services/test_fundamentals_yfinance.py` | `apps/web/app/[locale]/instruments/[symbol]/page.test.tsx` | `curl http://localhost:8000/fundamentals/AAPL` | 已覆盖 |
| 11 | Web 首页展示报告引用来源并渲染新闻 URL 链接 | `tests/api/test_reports_api.py` | `apps/web/app/[locale]/page.test.tsx` | 打开首页并检查 citations | 已覆盖 |
| 12 | Web 报告中心展示最新日报、历史日报和引用来源 | `tests/api/test_reports_api.py` | `apps/web/app/[locale]/reports/page.test.tsx` | 打开 `/reports` | 已覆盖 |
| 13 | Web 模拟组合页展示持仓、市值、风险摘要和 AI 调仓建议 | `tests/api/test_portfolios_api.py`, `tests/services/test_portfolio_service.py` | `apps/web/app/[locale]/portfolios/page.test.tsx` | 打开 `/portfolios` | 已覆盖 |
| 14 | Web 个股详情页展示行情、指标、基本面、新闻舆情和 AI 摘要 | `tests/api/test_market_data_db_api.py`, `tests/api/test_indicators_db_api.py`, `tests/api/test_fundamentals_api.py`, `tests/api/test_news_api.py` | `apps/web/app/[locale]/instruments/[symbol]/page.test.tsx` | 打开 `/instruments/AAPL` | 已覆盖 |
| 15 | Web 任务监控页展示每日关注列表任务状态和最近任务 | `tests/api/test_task_runs_api.py`, `tests/services/test_task_runs_service.py` | `apps/web/app/[locale]/task-runs/page.test.tsx` | 打开 `/task-runs` 或 `curl /task-runs/recent` | 已覆盖 |
| 16 | Web 关注列表页从 `/watchlist` 读取持久化默认关注标的并链接详情 | `tests/api/test_watchlists_api.py`, `tests/services/test_watchlists_service.py` | `apps/web/app/[locale]/watchlist/page.test.tsx` | 打开 `/watchlist` | 已覆盖 |
| 17 | `/watchlist` 支持持久化关注标的并保留 `alert_rules` | `tests/api/test_watchlists_api.py`, `tests/services/test_watchlists_service.py`, `tests/services/test_watchlist_alert_evaluation.py` | `apps/web/app/[locale]/watchlist/page.test.tsx` | `curl http://localhost:8000/watchlist` | 已覆盖，规则 UX 仍需持续验收 |
| 18 | AI 个股报告汇总行情、BOLL/ATR、基本面和新闻情绪 | `tests/ai/test_report_builder.py`, `tests/services/test_report_service.py`, `tests/api/test_analysis_api.py` | `apps/web/app/[locale]/instruments/[symbol]/page.test.tsx`, `apps/web/app/[locale]/reports/page.test.tsx` | 生成或查看个股日报 | 已覆盖 |

## 验收命令

```bash
python -m pytest -v
npm run test:web
```

## 通过标准

- 后端 pytest 全部通过。
- 前端 Vitest 全部通过。
- API、任务、指标、基本面、舆情、AI 报告和 Web Dashboard MVP 骨架均可被测试覆盖。
