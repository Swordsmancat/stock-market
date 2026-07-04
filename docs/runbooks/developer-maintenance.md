# 开发者维护手册

本手册面向维护者，集中说明 Phase 2 / Phase 3 功能、API 入口、降级数据契约、provider 能力和验证命令。基础本地启动流程仍以 [local-development.md](./local-development.md) 为准。

## 快速验证命令

常规回归：

```bash
python -m pytest -v
npm run test:web
```

近期 Phase 3 degraded-safe contract 的聚焦检查：

```bash
python -m pytest tests/api/test_market_depth_api.py tests/api/test_market_data_intraday_api.py tests/api/test_market_data_api.py
npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/market-depth-card.test.tsx" "apps/web/components/intraday-price-chart.test.tsx"
```

本地服务自检：

```bash
python scripts/dev_health_check.py
python scripts/provider_readiness.py --provider mock --market US
python scripts/task_run_health.py
```

## API Endpoint Catalog

### Core market data

| Endpoint | 用途 | 状态 |
|---|---|---:|
| `GET /market-data/latest?symbols=AAPL,MSFT` | 批量最新行情 | 已实现 |
| `GET /market-data/{symbol}/latest` | 单标的最新行情 | 已实现 |
| `GET /market-data/{symbol}/bars?timeframe=1d&start=YYYY-MM-DD&end=YYYY-MM-DD` | 日线 OHLCV | 已实现 |
| `GET /market-data/{symbol}/indicators?start=...&end=...&ma_window=20` | 基础指标 payload | 已实现 |
| `GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m` | 分时图 contract | 已实现，当前 provider 多数返回 degraded |
| `GET /market-data/{symbol}/depth?depth_levels=5&large_order_threshold_amount=1000000` | 深度数据 contract | 已实现，当前 provider 返回 degraded |

### Analysis, recommendations, reports, and dashboard

| Endpoint | 用途 | 状态 |
|---|---|---:|
| `POST /ingestion/snapshot` | 行情采集入口 | 已实现 |
| `POST /analysis/refresh` | 刷新单标的分析 | 已实现 |
| `GET /recommendations` | 智能推荐 | 已实现 |
| `GET /reports/{symbol}/daily/latest` | 最新日报 | 已实现 |
| `GET /news/{symbol}` | 新闻舆情 | 已实现 |
| `GET /fundamentals/{symbol}` | 基本面 | 已实现 |
| Hot sectors route | 热点板块/资金流展示 | 部分完成，真实资金流 provider 待补 |
| AI assistant route | 聊天式市场助手 | 未上线 |

### Portfolio, watchlist, alerts, and task runs

| Endpoint | 用途 | 状态 |
|---|---|---:|
| `GET /watchlist` | 关注列表 | 已实现 |
| `GET /alerts/triggers/recent` | 告警触发历史 | 已实现 |
| `GET /portfolios` | 组合列表 | 已实现 |
| `GET /task-runs/recent` | 最近异步任务 | 已实现 |

## Degraded-safe Provider Data Contract

当 provider 不支持某项能力、网络不可用、权限不足或数据没有经过验证时，后端和前端必须遵守 degraded-safe 原则。

### 后端原则

- 不得用 mock、日线或估算值伪造真实分时、Level-2、逐笔、大单或资金流数据。
- 对预期不可用状态返回 HTTP 200 + typed degraded payload，而不是 500。
- payload 应包含：
  - `status`: `ok` / `no_data` / `degraded`
  - `provider`, `requested_provider`, `effective_provider`
  - `availability.status`
  - `availability.reason`
  - `as_of`, `is_realtime`, `is_delayed`, `delay_minutes`（适用时）
- 不支持的参数仍通过 FastAPI 校验或 `ValueError` 映射为 HTTP 400/422。

### 前端原则

- 不要把 empty state 当作成功实时数据。
- 必须向用户显示 unavailable/degraded 文案。
- 在详情页中，日线数据仍是主要依赖；分时图和深度数据是非致命增强，失败时不应导致整页失败。
- 文案必须明确“当前数据源不支持/暂无已验证数据”。

## Provider Capability Matrix

| Provider | 日线 | 分时 | 深度 / Level-2 | 逐笔 / 大单 | 资金流 | 新闻 / 基本面 | 备注 |
|---|---:|---:|---:|---:|---:|---:|---|
| `mock` | 支持测试数据 | 不作为真实分钟线 | 不支持真实深度 | 不支持 | 不支持 | mock/demo | 不能把 mock 当真实市场数据。 |
| `yfinance` | 支持部分市场日线 | 当前后端未验证接入 | 不支持当前深度 contract | 不支持 | 不支持 | 支持部分新闻/基本面 | 适合默认开发和 US/HK/CN 基础行情。 |
| `akshare` | 未来/部分支持 | 待验证 | 未来候选 | 未来候选 | 未来候选 | 取决于接口 | 需要标准化字段和限流策略。 |
| `tushare` | 未来/部分支持 | 待验证 | 权限依赖 | 权限依赖 | 权限依赖 | 取决于 token 权限 | 需要 token、权限和配额治理。 |

## Phase 2 / Phase 3 Completion Matrix

| Phase | 功能 | 状态 | 关键证据 | 维护建议 |
|---|---|---:|---|---|
| Phase 2 | K 线图交互增强 | Complete | `apps/web/components/advanced-candlestick-chart.tsx`, `apps/web/lib/chart-indicators.ts`, chart tests | 可继续增强显式缩放按钮、多周期联动、图表布局保存。 |
| Phase 2 | 智能推荐 | Complete | `apps/api/routers/recommendations.py`, `packages/services/smart_recommendations.py`, `apps/web/components/smart-recommendations.tsx` | 增加推荐回测、命中率、策略解释和筛选器。 |
| Phase 2 | 热点板块轮动 | Partial | `apps/web/components/hot-sectors.tsx`, hot-sector route/tests | 需要真实资金流 provider、板块分类和成分股聚合。 |
| Phase 2 | 对比分析 | Complete | `apps/web/components/comparison-tool.tsx`, `apps/web/lib/comparison-utils.ts`, tests | 增加 beta、波动率、最大回撤和保存对比组合。 |
| Phase 3 | 分时图 | Partial | `apps/api/routers/market_data.py`, `get_intraday_bars_payload`, `apps/web/components/intraday-price-chart.tsx` | 需要真实分钟线 provider、交易时段处理和缓存/存储策略。 |
| Phase 3 | 深度数据 | Partial | `GET /market-data/{symbol}/depth`, `get_market_depth_payload`, `MarketDepthCard` | 需要真实 Level-2、逐笔、大单和资金流 provider。 |
| Phase 3 | 技术指标库 | Complete | `calculateMacdSeries`, `calculateKdjSeries`, `computeRsiSeries`, backend MACD/KDJ persistence | 可补更多指标、参数持久化和指标解释。 |
| Phase 3 | AI 助手 | Missing | 仅有 Trellis PRD，未见稳定 API/UI/tests | 应单独实现 Assistant API、上下文聚合、聊天 UI 和安全边界。 |

## Professional Benchmark Gap Summary

专业金融平台通常具备以下能力：

- TradingView 类：强交互图表、自定义指标脚本、告警、多周期联动、社区脚本。
- Bloomberg/Koyfin/AlphaSense 类：深度研究数据、新闻/研报检索、引用、监控、组合视图。
- 券商终端/Bookmap 类：实时行情、Level-2、订单流、逐笔成交、低延迟执行入口。
- CN 零售终端：分时图、五档盘口、主力资金流、热点板块、涨跌家数、龙虎榜/公告等本地市场功能。

当前平台优势：

- 已有 provider-neutral 架构、Celery 任务、TaskRun 监控和 degraded-safe 状态。
- 已有日线、指标、推荐、报告、组合、关注列表和告警基础。
- 已有 Phase 3 分时/深度 UI 和 API contract，可在真实 provider 接入后平滑升级。

主要差距：

- 真实分钟线、Level-2、逐笔和资金流数据尚未接入。
- AI 助手未上线。
- 策略/推荐缺少回测、解释和筛选器。
- 专业图表缺少多周期联动、自定义脚本、图表布局保存和告警联动。
- 缺少生产级权限、数据 SLA、审计日志和 provider 配额治理。

## Follow-up Roadmap

| 优先级 | Roadmap Item | 建议 Trellis 任务 | 验收方向 |
|---:|---|---|---|
| P0 | AI 市场助手 | `07-04-ai-market-assistant` | API/UI/tests、上下文引用、安全免责声明、degraded 数据不编造。 |
| P0 | 真实分时数据管线 | `real-intraday-minute-data-pipeline` | 至少一个 provider 的分钟线、缓存/存储、交易时段和前端真实渲染。 |
| P0 | 真实深度/大单/资金流管线 | `real-market-depth-provider-pipeline` | Level-2/逐笔/大单/资金流 provider 能力矩阵和真实 payload。 |
| P1 | 热点板块真实资金流 | `hot-sector-fund-flow-provider` | 板块分类、成分股映射、资金流排序和降级测试。 |
| P1 | Trellis 状态治理 | `trellis-phase2-phase3-state-reconciliation` | 已实现任务归档，planning/in_progress 状态与代码一致。 |
| P2 | 专业图表增强 | future task | 多周期联动、显式缩放按钮、图表布局保存、指标参数持久化。 |
| P2 | 推荐回测与策略评价 | future task | 历史回测、命中率、回撤、风险统计和解释增强。 |

## Change Safety Checklist

- 修改 endpoint contract 时同步更新本手册、用户手册和相关测试。
- 接入新 provider 能力时先扩展 capability matrix，再接入 UI。
- 任何真实行情能力上线前必须有 unavailable/degraded 回归测试。
- 不要把 AI 报告、AI 摘要和聊天式 AI 助手混为同一功能。
