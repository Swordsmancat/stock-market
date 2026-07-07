# 开发者维护手册

本手册面向维护者，集中说明 Phase 2 / Phase 3 功能、API 入口、降级数据契约、provider 能力和验证命令。基础本地启动流程仍以 [local-development.md](./local-development.md) 为准。

## 快速验证命令

常规回归：

```bash
python -m pytest -v
npm run test:web
```

证据中心聚焦检查：

```bash
python -m pytest tests/services/test_market_indicators_service.py tests/api/test_market_indicators_api.py -q
npx vitest run "apps/web/app/[locale]/evidence/page.test.tsx" "apps/web/components/evidence-seed-import-review.test.tsx" "apps/web/components/navigation-items.test.ts" "apps/web/app/api/market-indicators/seeds/preview/route.test.ts" "apps/web/app/api/market-indicators/seeds/import/route.test.ts" --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
```

证据中心读取态继续消费 `GET /dashboard/market-overview`；宏观/估值 seed 导入审阅通过 `POST /market-indicators/seeds/preview` 和 `POST /market-indicators/seeds/import` 写入本地 observation。维护时应确认：

- `macro_indicators.items` / `valuation_indicators.items` 继续包含全部宏观和估值指标代码，缺失观测值必须保持 `null`/`N/A`，不能显示为 0。
- `information_sources.items` 和 `groups` 继续保留 status、authority、coverage、freshness_policy、ai_usage、next_action、collection_links、seed_template、evidence_count 和 latest_as_of。
- source-readiness 链接和 seed 模板仍是 collection guidance，不是 AI citation。
- `dashboard_brief.narrative` 可以是 LLM 输出或 deterministic fallback，但 citations 必须来自 payload 中已有的本地证据 ID。
- seed preview 必须复用 `packages/services/market_indicators.py` 的审计规则，不写入数据库，并报告 row-level valid/invalid、metadata、insert/update 和错误。
- seed import 必须重新校验并保持 all-or-nothing；检测到 update 时，没有 `overwrite_acknowledged=true` 应返回 HTTP 409。
- 浏览器文件选择只读取文本内容用于 preview/import，不得把原始上传文件存成文档语料；成功 import 后应清理 market overview cache。

宏观/估值 seed 导入审阅的完整回归：

```bash
python -m pytest tests/services/test_market_indicators_service.py tests/api/test_market_indicators_api.py tests/scripts/test_import_market_indicator_seeds.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py -q
npx vitest run "apps/web/app/[locale]/evidence/page.test.tsx" "apps/web/components/evidence-seed-import-review.test.tsx" "apps/web/app/api/market-indicators/seeds/preview/route.test.ts" "apps/web/app/api/market-indicators/seeds/import/route.test.ts" --reporter=dot
npm run test:web -- --reporter=dot
```

近期 Phase 3 degraded-safe contract 的聚焦检查：

```bash
python -m pytest tests/api/test_market_depth_api.py tests/api/test_market_data_intraday_api.py tests/api/test_market_data_api.py
npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/market-depth-card.test.tsx" "apps/web/components/intraday-price-chart.test.tsx"
```

真实分时分钟线聚焦检查：

```bash
python -m pytest tests/providers/test_yfinance_provider.py tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py tests/domain/test_migrations.py
npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/intraday-price-chart.test.tsx"
```

yfinance 分时分钟线的可选 live smoke（默认不会访问外网，必须显式 opt-in；未传 `--trade-date` 时会尝试最近 5 个工作日，可用 `--intraday-lookback-days` 调整窗口）：

```bash
python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL --check-intraday --real-network
```

若需要固定某个交易日，显式传入 `--trade-date`，此时不会自动尝试 lookback 窗口：

```bash
python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL --check-intraday --trade-date 2026-07-03 --real-network
```

如果 `--trade-date` 是未来日期，readiness 会返回可解释的 `WARN` 并跳过 provider 分钟线调用，避免把尚未发生的市场 session 误判为 provider 故障。

真实深度 provider boundary 聚焦检查：

```bash
python -m pytest tests/providers/test_cn_market_providers.py tests/api/test_market_depth_api.py tests/services/test_market_data_service.py
npx vitest run "apps/web/components/market-depth-card.test.tsx" "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"
```

AkShare 深度候选路径的可选 live smoke（默认不会访问外网，必须显式 opt-in）：

```bash
python scripts/provider_readiness.py --provider akshare --market CN --symbol 600519 --check-depth --real-network
```

当 AkShare live endpoint 失败、为空或 schema 无法识别时，readiness 输出会透传安全诊断字段，例如 `availability_exception_type`、`availability_raw_shape`、`availability_raw_columns` 和 `availability_raw_fields_sample`。这些字段只用于后续 fixture-backed parser 适配，不应被当作已验证 Level-2 数据。

AI 市场助手聚焦检查：

```bash
python -m pytest tests/ai/test_market_assistant.py tests/api/test_assistant_api.py -q
npx vitest run "apps/web/app/api/assistant/market/route.test.ts" "apps/web/components/market-assistant-card.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" --reporter=dot
```

AI 市场助手现在在原有单标的问答 MVP 上增加了 service-local research evidence/citation 层。维护时应确认：

- `POST /assistant/market` 仍保持向后兼容，顶层 `answer_markdown` / `context` / `citations` / `diagnostics` / `safety` 不应被破坏。
- citation 必须继续包含 `id`、`label`、`source`、`url` 基础字段；新增的 `source_type`、`as_of`、`provider`、`retrieved_at`、`excerpt`、`metadata` 只能作为可选字段出现。
- 当前可引用来源包括日线 bars、stored technical indicators、fundamentals snapshot、news articles / sentiment payload、generated reports；filings、transcripts、exchange announcements、paid research feeds 和 vector search 仍不是生产能力。
- LLM 输出如果引用了 payload 中不存在的 citation ID，后端应降级到 deterministic fallback 或显式 `CITATION_UNKNOWN_ID` 诊断，不能把幻觉引用当作有效来源展示。
- diagnostics 可包含 `severity`、`code`、`citation_id`、`details`，但不得泄露 API key、prompt internals、原始 stack trace 或 provider 原始 payload。

推荐信号评估聚焦检查：

```bash
python -m pytest tests/services/test_recommendation_signal_evaluation.py tests/api/test_recommendations_api.py -q
```

推荐信号评估当前是 service-level deterministic research layer。维护时应确认：

- `evaluate_recommendation_signals` 只使用传入的 deterministic historical bars，不访问 live provider，也不写入数据库。
- 当前覆盖的信号类型保持与实时推荐一致：`breakout`、`volume_anomaly`、`oversold_rebound`、`strong_momentum`。
- 输出必须包含 `sample_size`、`forward_windows`、per-window hit rate、average/median forward return、max drawdown、可用时的 benchmark-relative return，以及 no-data / no-signal / invalid-window / insufficient-post-signal diagnostics。
- benchmark bars 缺失或无法安全对齐时应返回 `BENCHMARK_UNAVAILABLE` 等诊断，不要把缺失 benchmark-relative return 编码为 0。
- 缺失历史、样本不足、没有触发信号时应返回显式状态和 diagnostics，不能把“没有证据”展示成收益率、命中率或回撤为 0 的成功结果。
- 该能力是历史研究评估，不是投资建议、自动交易、组合回测或策略 tester；若未来暴露 API/UI，必须继续展示样本量、窗口、诊断和非建议声明。

热点板块资金流聚焦检查：

```bash
python -m pytest tests/services/test_hot_sectors_service.py tests/api/test_sectors_api.py
npx vitest run "apps/web/app/api/hot-sectors/route.test.ts" "apps/web/components/hot-sectors.test.tsx" "apps/web/app/[locale]/page.test.tsx"
```

FRED 官方宏观刷新聚焦检查：

```bash
python -m pytest tests/providers/test_fred_provider.py tests/services/test_market_indicators_fred_refresh.py tests/scripts/test_refresh_fred_macro_indicators.py tests/services/test_market_indicators_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
ruff check packages/providers/fred_provider.py packages/services/market_indicators.py scripts/refresh_fred_macro_indicators.py tests/providers/test_fred_provider.py tests/services/test_market_indicators_fred_refresh.py tests/scripts/test_refresh_fred_macro_indicators.py
```

FRED refresh 是显式 opt-in 的维护命令，不会自动调度。运行前需要配置 `FRED_API_KEY`，也可以用 `--dry-run` 先验证 provider payload 和审计字段：

```powershell
$env:FRED_API_KEY="..."
python scripts/refresh_fred_macro_indicators.py --series rates --latest-only --dry-run
python scripts/refresh_fred_macro_indicators.py --series all --start 2025-01-01 --end 2026-07-06
```

维护规则：

- 缺少 `FRED_API_KEY` 时脚本输出 `WARN` 并退出 0，不会尝试匿名请求。
- HTTP、JSON shape、provider 和 seed validation 失败输出 `FAIL` 并退出 1。
- FRED 缺失值 `"."`、空值或非法 decimal 会被跳过，不得写成 0。
- CPI/M2 YoY 只在当前值和同月去年值都存在且去年值非 0 时派生。
- 入库仍走 `MarketIndicatorObservation`，components 必须保留 `source_series_id`、`source_url`、`retrieved_at`、`methodology` 或 `calculation`。
- Source readiness 链接和 seed 模板不是 citation；dashboard/AI 只能引用成功入库的本地 observations。

World Bank 巴菲特指标刷新聚焦检查：

```bash
python -m pytest tests/providers/test_world_bank_provider.py tests/services/test_market_indicators_world_bank_refresh.py tests/scripts/test_refresh_world_bank_macro_indicators.py tests/services/test_information_sources_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
ruff check packages/providers/world_bank_provider.py packages/services/market_indicators.py packages/services/information_sources.py scripts/refresh_world_bank_macro_indicators.py tests/providers/test_world_bank_provider.py tests/services/test_market_indicators_world_bank_refresh.py tests/scripts/test_refresh_world_bank_macro_indicators.py
```

World Bank refresh 是显式 opt-in 的维护命令，不需要 API key。建议先用 `--dry-run` 验证年度 observation 和 diagnostics：

```powershell
python scripts/refresh_world_bank_macro_indicators.py --target USA --dry-run
python scripts/refresh_world_bank_macro_indicators.py --target all
python scripts/refresh_world_bank_macro_indicators.py --target buffett_indicator_us --start-year 2020 --end-year 2024 --no-latest-only
```

维护规则：

- 主值来自 World Bank `CM.MKT.LCAP.GD.ZS`，含义是上市公司市值占 GDP 百分比；不要二次计算后覆盖该值，除非同时记录清楚计算方法和组件。
- GDP context 来自 `NY.GDP.MKTP.CD`，只是 components 中的上下文，不是当前宏观指标库里的独立指标。
- World Bank 年度数据通常滞后；当前年份缺失应以 diagnostics/source gap 表达，不要写成 0 或视为市场结论。
- 入库仍走 `MarketIndicatorObservation`，components 必须保留 `provider=world_bank`、`country_code`、`source_indicator_id`、`source_url`、`retrieved_at` 和 `methodology` 或 `calculation`。
- Source readiness、World Bank 链接、adapter ID 和 diagnostics 不是 citation；dashboard/AI 只能引用成功入库的本地 observations。
- 测试必须 mock HTTP，不得默认访问真实 World Bank 网络。

本地服务自检：

```bash
python scripts/dev_health_check.py
python scripts/provider_readiness.py --provider mock --market US
python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL --check-intraday --real-network
python scripts/provider_readiness.py --provider akshare --market CN --symbol 600519 --check-depth --real-network
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
| `GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m` | 分时图 minute-bar contract，返回 `ok` / `no_data` / `degraded`、provider、previous_close、分钟点位、freshness/session 和缓存状态 | Provider-backed + closed-session cache MVP；yfinance 可返回 verified `1m` 分钟线并对历史闭市请求复用持久缓存，mock/AkShare/Tushare 仍 degraded |
| `GET /market-data/{symbol}/depth?depth_levels=5&large_order_threshold_amount=1000000` | 深度数据 provider contract，返回 order_book / recent_trades / large_orders / fund_flow 分区状态和可验证行 | Provider-boundary MVP；只调用显式 `fetch_market_depth`；AkShare 已有 fixture-tested 盘口候选路径，生产 verified 状态仍需 live smoke、schema 监控和权限验证 |

### Analysis, recommendations, reports, and dashboard

| Endpoint | 用途 | 状态 |
|---|---|---:|
| `POST /ingestion/snapshot` | 行情采集入口 | 已实现 |
| `POST /analysis/refresh` | 刷新单标的分析 | 已实现 |
| `GET /recommendations` | 智能推荐 | 已实现 |
| `GET /reports/{symbol}/daily/latest` | 最新日报 | 已实现 |
| `GET /news/{symbol}` | 新闻舆情 | 已实现 |
| `GET /fundamentals/{symbol}` | 基本面 | 已实现 |
| `GET /sectors/hot?limit=5&provider=static_fixture` | 热点板块/资金流 provider contract，返回板块 taxonomy、资金流口径、数据模式、provider/as-of、延迟和成分股元数据 | Provider-backed MVP；默认 `static_fixture` 明确为 `degraded + mock`，可选 `provider=akshare` 在环境支持时尝试延迟板块资金流 |
| `POST /assistant/market` | 聊天式市场助手，聚合单标的日线、指标、基本面、新闻和已生成报告上下文，返回 answer/citations/diagnostics/safety | Research-citation MVP；已有统一 evidence/citation 层、可选 citation metadata、diagnostic severity/code 和 LLM citation validation；缺失上下文时返回 `no_data` / `degraded` |
| `GET /dashboard/market-overview?provider=...` | 首页和证据中心共享的市场/宏观/估值/来源就绪度/AI brief 聚合 payload | Evidence Center source；保持 backward compatible，不要把 source links 或 seed templates 升级为 citations |
| `POST /market-indicators/seeds/preview` | 预览粘贴或浏览器文件读取出来的 JSON/CSV seed 内容，返回 row-level 校验、metadata 和 insert/update 意图 | Preview-only；HTTP 200 可承载 invalid preview；不得写入 observation |
| `POST /market-indicators/seeds/import` | 确认导入已复核宏观/估值 seed 内容，写入本地 `MarketIndicatorObservation` | All-or-nothing import；invalid 返回 422，缺少覆盖确认返回 409，成功后清理 market overview cache |

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
  - `status`: `ok` / `no_data` / `degraded` / `unavailable`（具体 endpoint 可选子集）
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

### Frontend provider trust visibility MVP

前端新增了共享 trust normalizer 和 badge/summary 组件，用来统一展示 provider、source、freshness、延迟、缓存、session 和 no-data/degraded 原因。

关键文件：

- `apps/web/lib/data-trust.ts`：纯前端 normalizer；缺失 metadata 时必须返回 `unknown`，不能默认 fresh/live。
- `apps/web/components/data-trust-badge.tsx`：compact / summary 两种展示模式；颜色是语义状态色，不是市场涨跌色。
- `apps/web/components/market-overview-client.tsx`、`market-ticker.tsx`：首页 market overview 和黑底 ticker 的来源/状态可见性。
- `apps/web/components/smart-recommendations.tsx`：推荐卡片不再默认宣称 realtime，显示 payload diagnostics。
- `apps/web/components/instrument-detail-client.tsx`、`intraday-price-chart.tsx`：最新价、K 线、分时图展示 provider/source/freshness/session/cache。
- `apps/web/app/[locale]/reports/**`、`generate-daily-report-button.tsx`：报告列表/详情展示 `source_summary`，生成报告时透传显式 provider 或提示使用后端默认。

维护规则：

- 如果 payload 没有 `is_realtime=true`，不要显示“实时”或 Level-2 等强声明。
- mock/demo/fixture/provider_error 应优先显示为 mock/degraded/unavailable，而不是成功状态。
- `provider` 和 `effective_provider` 不一致时，UI 应优先暴露 effective provider，并保留 requested provider 供排查。
- `freshness.cache_status` 和 `session.status` 是数据解释 metadata，不代表完整生产 SLA 或低延迟 market-data plant。
- 新增行情相关组件时，优先复用 `createDataTrustSignal` 和 `DataTrustBadge`，不要在组件内手写另一套状态映射。

P0 provider trust 聚焦检查：

```bash
npx vitest run "apps/web/lib/data-trust.test.ts" "apps/web/components/data-trust-badge.test.tsx" "apps/web/components/market-ticker.test.tsx" "apps/web/app/[locale]/page.test.tsx" "apps/web/components/smart-recommendations.test.tsx" "apps/web/components/intraday-price-chart.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/app/[locale]/reports/page.test.tsx" "apps/web/app/[locale]/reports/[reportId]/page.test.tsx" "apps/web/components/generate-daily-report-button.test.tsx" --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
```

### Hot sector fund-flow contract

`GET /sectors/hot` 是首页热点板块的后端源。它保留旧字段以兼容现有 dashboard，同时新增 provider-backed 元数据。

常用 query：

- `limit`: `1..10`，FastAPI 仍负责校验。
- `provider`: 可选。当前支持 `static_fixture` / `mock` / `static` fallback，以及环境可用时的 `akshare` 候选 provider。未知 provider 返回 typed `unavailable` payload，而不是 500。

顶层 payload 重点字段：

- `status`: `ok` / `degraded` / `unavailable`。
- `data_mode`: `live` / `delayed` / `demo` / `mock` / `none`。
- `source`, `provider`, `requested_provider`, `effective_provider`。
- `as_of`, `generated_at`, `is_realtime`, `is_delayed`, `delay_minutes`。
- `taxonomy_version`: 当前为 `sector-taxonomy-v1`。
- `flow_definition`: `{ metric, window, currency, unit, methodology }`，用于解释资金流口径。
- `availability`: performance/fund_flow/constituents/breadth/constituent_contribution/rotation_history/taxonomy 的可用性说明。
- `provider_capabilities`: provider section-level capability matrix，说明 sector ranking、fund flow、constituents、breadth、contribution、rotation history 和 taxonomy 当前是 verified/delayed/mock/unavailable 中的哪一种状态。
- `items`: normalized sector rows。

单个 sector item 同时保留 legacy dashboard 字段和 normalized 字段：

- Legacy: `name`, `name_en`, `change_percent`, `fund_flow`, `fund_flow_amount`, `leader_symbol`, `leader_name`, `leader_change_percent`, `symbols_count`。
- Normalized: `sector_id`, `market`, `rank`, `flow_direction`, `net_flow_amount`, `net_flow_currency`, `net_flow_unit`, `flow_window`, `flow_metric`, `leader`, `top_constituents`, `breadth`, `constituent_contribution`, `taxonomy`, `history`, `as_of`, `provider`, `is_verified`, `availability`。

新增 section 规则：

- `breadth` 只能由 provider 明确返回的成分股表现或已验证成分股列表派生；缺失时返回 `status=unavailable`，不要编码为 0。
- `constituent_contribution` 可展示正贡献和负贡献成分股，但不能从日线价格或静态 fixture 推断生产级资金贡献。
- `taxonomy` 必须带 `taxonomy_version` 和 normalized sector id，以防不同 provider 分类混用。
- `history` 只有存在真实快照存储或明确 provider 历史数据时才可标为 available；当前无快照时保持 `status=unavailable`。

维护规则：

- 不要把 `static_sector_fixture`、demo 或 mock payload 标成 `live` / `is_verified=true`。
- provider 失败时用 `source=provider_error` + `status=unavailable`，并过滤 secret/token 值。
- 若新增 provider，应先补 service/API/component/proxy tests，再更新本手册的 capability matrix。
- 若新增 rotation-history 持久化，应通过显式 schema/migration 和 deterministic tests 实现，不要把不透明 JSON 写进无关表来模拟历史能力。

### Intraday minute-bar contract

`GET /market-data/{symbol}/intraday` 是个股详情页分时图的后端源。它现在支持 yfinance `1m` verified minute-bar MVP，同时保留 unsupported provider 的 degraded-safe 行为。

常用 query：

- `date`: 目标交易日期，格式 `YYYY-MM-DD`。
- `timeframe`: 当前仅支持 `1m`；其他值通过 FastAPI/service 映射为 HTTP 400。
- `provider`: 可选。当前 yfinance 支持显式 intraday method；mock/AkShare/Tushare 不会复用 daily API 来伪造分钟线。

顶层 payload 重点字段：

- `status`: `ok` / `no_data` / `degraded`。
- `source`: yfinance real minute rows 首次 provider fetch 使用 `provider`；历史闭市缓存命中使用 `cache`；unsupported provider 或 session-policy skip 使用 `none`。
- `provider`, `requested_provider`, `effective_provider`。
- `previous_close`: 昨收参考线，可通过日线 lookback 获取；缺失时为 `null`。
- `items`: minute rows，仅 verified provider 返回或由 verified historical closed-session cache 复用真实分钟点位。
- `availability`: `{ status, reason, is_realtime, is_delayed, delay_minutes }`。
- `freshness`: additive metadata，包含 `status`, `reason`, `data_as_of`, `checked_at`, `fetched_at`, `cached_at`, `cache_status`, `max_age_seconds`。`cache_status` 当前含义为 `hit`（历史闭市持久缓存命中）、`miss`（缓存未命中并执行 provider path）、`skipped`（session/provider policy 明确跳过缓存或 provider 调用）、`unavailable`（没有可用数据库 session 或缓存读写失败后返回 provider 数据）。
- `session`: additive metadata，包含 `market`, `timezone`, `trading_date`, `status`, `reason`。当前覆盖 yfinance US-like symbol 的 future / weekend / known holiday / closed/current session / unsupported provider 判断，不代表完整全球交易日历。

单个 minute item：

- `timestamp`: ISO datetime，保留分钟级时间。
- `open`, `high`, `low`, `close`, `price`。
- `average_price`: provider 未验证时为 `null`。
- `volume`, `amount`。

维护规则：

- 只允许显式 provider intraday method 生成 `items`。
- 不要调用 mock/AkShare/Tushare 当前 daily `fetch_bars("1m")` 来生成分钟线。
- yfinance 空结果、历史窗口外日期、周末/节假日应返回 `no_data`，不是伪造点位。
- 对周末日期，服务层会直接返回可解释的 `no_data`，并且不会调用 provider 的日线或分钟线接口；如数据库已有日线，`previous_close` 可从本地读取，否则为 `null`。
- 对未来日期，服务层会直接返回可解释的 `no_data`，并且不会调用 provider 的日线或分钟线接口；这避免把尚未发生的市场 session 当作 provider 故障。
- 对 yfinance + US-like symbol 的已知美股休市日，服务层会直接返回可解释的 `no_data`，并跳过 provider 日线/分钟线接口；readiness 窗口模式也会跳过这些休市日继续尝试最近有效工作日。当前覆盖固定/顺延休市日和常见移动休市日（MLK Day、Presidents Day、Good Friday、Memorial Day、Labor Day、Thanksgiving）。
- 日线数据只可用于 `previous_close` 参考线，不可生成 minute rows。
- 历史闭市 session 会先查 `intraday_minute_cache_entries` 元数据和 `bars_1m` 分钟事实表；命中时返回 `source="cache"` 并且不调用 provider。当前 session 保持 provider-first，不从缓存冒充实时行情。
- 缓存只写 verified provider 返回的 minute rows。不要为 future/weekend/holiday、unsupported provider、provider empty response 或 daily fallback 写入 fake minute rows。

### Market depth provider contract

`GET /market-data/{symbol}/depth` 是个股详情页深度数据卡片的后端源。它现在使用显式 `fetch_market_depth` provider boundary，允许真实 provider 返回五档盘口、逐笔成交、资金流中的任意子集，同时保持未验证分区 degraded。

常用 query：

- `depth_levels`: 返回买卖盘层数，默认 `5`。
- `large_order_threshold_amount`: 大单金额阈值，默认 `1000000`。
- `provider`: 可选。只有暴露 `fetch_market_depth(symbol, depth_levels)` 的 provider 才会被视为深度候选；mock/yfinance/Tushare 当前生产路径仍 degraded。AkShare 已有显式 `fetch_market_depth` 候选解析路径，但 production-verified Level-2 状态仍必须等待 opt-in live smoke、schema 监控和 provider 权限验证。

顶层 payload 重点字段：

- `status`: `ok` 表示至少一个分区有已验证数据；`degraded` 表示没有可验证深度分区。
- `source`, `provider`, `requested_provider`, `effective_provider`。
- `as_of`, `is_realtime`, `is_delayed`, `delay_minutes`。
- `availability.capabilities`: `{ order_book, recent_trades, large_orders, fund_flow }`，逐项说明可用性。

分区 payload：

- `order_book`: `status`, `reason`, `depth_levels`, `bids`, `asks`；每档包含 `price`, `volume`, `amount`, `order_count`。
- `recent_trades`: `status`, `reason`, `items`；每笔包含 `timestamp`, `price`, `volume`, `amount`, `side`。
- `large_orders`: `status`, `reason`, `threshold_amount`, `threshold_volume`, `currency`, `items`；只从已验证逐笔成交按金额阈值派生。
- `fund_flow`: `status`, `reason`, `currency`, `net_inflow`, `main_net_inflow`, `retail_net_inflow`, `source_definition`。

维护规则：

- 不要从日线、分钟线、mock fixture 或估算分布生成 order book、recent trades、large orders 或 fund-flow。
- 可以出现局部可用：例如 `order_book.status="ok"`，但 `recent_trades.status="degraded"`。前端必须展示各分区原因，不能因为顶层 `ok` 隐藏 degraded 分区。
- 大单只能从已验证 `recent_trades` 派生；如果没有逐笔成交，即使 provider 有盘口，也必须保持 `large_orders.status="degraded"`。
- AkShare depth candidate 必须保持 fixture-backed parser tests；若 live endpoint 为空、schema 变化、依赖缺失或权限不足，应返回 degraded availability，而不是 fallback 到日线或 mock。
- provider runtime failure 应通过 typed provider error/degraded path 处理，不能泄露 token、URL secret 或完整异常上下文。

## Provider Capability Matrix

| Provider | 日线 | 分时 | 深度 / Level-2 | 逐笔 / 大单 | 资金流 | 新闻 / 基本面 | 备注 |
|---|---:|---:|---:|---:|---:|---:|---|
| `mock` / `static_fixture` | 支持测试数据 | 不作为真实分钟线；intraday endpoint 返回 degraded | 不支持真实深度；不会伪造 order book | 不支持；不会伪造逐笔/大单 | 热点板块仅 `degraded + mock` 静态 contract 展示 | mock/demo | 不能把 mock 当真实市场数据；热点板块默认 fallback 明确标记 `source=static_sector_fixture`。 |
| `yfinance` | 支持部分市场日线 | 支持 verified `1m` MVP，受 yfinance 历史留存和市场时段限制；空结果返回 `no_data` | 不支持当前深度 contract；depth endpoint 返回 degraded | 不支持 | 不支持 | 支持部分新闻/基本面 | 适合默认开发和 US/HK/CN 基础行情；minute bars 通过显式 `fetch_intraday_bars`，不是 daily `fetch_bars("1m")`。 |
| `akshare` | 未来/部分支持 | 待验证 | 已有显式 `fetch_market_depth` 盘口候选路径和 fixture parser tests；production verified 仍待 live smoke、schema 监控和权限验证 | 逐笔/大单仍是候选；大单只可从 verified recent trades 派生 | 热点板块资金流候选 provider；可返回 delayed sector ranking，环境/接口可用性需验证 | 取决于接口 | 盘口候选路径使用 AkShare order-book endpoint 解析；运行时失败、空响应或 schema 变化必须 degraded，不能复用日线/分钟线/mock 伪造。 |
| `tushare` | 未来/部分支持 | 待验证 | 权限依赖；当前 degraded | 权限依赖；当前 degraded | 权限依赖 | 取决于 token 权限 | 需要 token、权限、配额治理和按字段验证后的显式 provider method。 |

## Phase 2 / Phase 3 Completion Matrix

| Phase | 功能 | 状态 | 关键证据 | 维护建议 |
|---|---|---:|---|---|
| Phase 2 | K 线图交互增强 | Complete | `apps/web/components/advanced-candlestick-chart.tsx`, `apps/web/lib/chart-indicators.ts`, chart tests | 可继续增强显式缩放按钮、多周期联动、图表布局保存。 |
| Phase 2 | 智能推荐 | Complete | `apps/api/routers/recommendations.py`, `packages/services/smart_recommendations.py`, `apps/web/components/smart-recommendations.tsx` | 增加推荐回测、命中率、策略解释和筛选器。 |
| Phase 2 | 热点板块轮动 | Partial / provider-backed MVP | `packages/services/hot_sectors.py`, `apps/api/routers/sectors.py`, `apps/web/components/hot-sectors.tsx`, hot-sector service/API/proxy/component/page tests | 已有 normalized provider contract、MVP taxonomy、flow definition、top constituents 和 degraded-safe UI；后续需要生产级真实资金流 provider、涨跌家数、成分股贡献和历史轮动。 |
| Phase 2 | 对比分析 | Complete | `apps/web/components/comparison-tool.tsx`, `apps/web/lib/comparison-utils.ts`, tests | 增加 beta、波动率、最大回撤和保存对比组合。 |
| Phase 3 | 分时图 | Partial / provider-backed + closed-session cache MVP | `ProviderIntradayBar`, `YFinanceProvider.fetch_intraday_bars`, `IntradayMinuteCacheEntry`, `bars_1m`, `get_intraday_bars_payload`, `IntradayPriceChart`, intraday provider/service/API/proxy/page tests | yfinance `1m` verified minute path 已可返回 `ok`；历史闭市请求可持久缓存并复用；unsupported provider 继续 degraded。后续需要更多 provider、完整交易日历、半日市、盘前盘后、实时推送和更长历史窗口。 |
| Phase 3 | 深度数据 | Partial / provider-boundary MVP | `ProviderMarketDepthSnapshot`, `ProviderOrderBookLevel`, `ProviderRecentTrade`, `ProviderFundFlow`, `AkShareProvider.fetch_market_depth`, `get_market_depth_payload`, `MarketDepthCard`, market-depth provider/service/API/proxy/page/component tests | 已有显式 `fetch_market_depth` boundary、AkShare fixture-tested 盘口候选路径、局部分区状态、真实行渲染和大单从已验证逐笔派生；后续需要生产级 Level-2 live smoke、逐笔和资金流 provider 验证。 |
| Phase 3 | 技术指标库 | Complete | `calculateMacdSeries`, `calculateKdjSeries`, `computeRsiSeries`, backend MACD/KDJ persistence | 可补更多指标、参数持久化和指标解释。 |
| Phase 3 | AI 助手 | Partial / MVP | `apps/api/routers/assistant.py`, `packages/services/market_assistant.py`, `apps/web/components/market-assistant-card.tsx`, assistant tests | 继续增强多轮上下文、报告/新闻检索、实时数据联动和更丰富引用。 |

## Professional Benchmark Gap Summary

专业金融平台通常具备以下能力：

- TradingView 类：强交互图表、自定义指标脚本、告警、多周期联动、社区脚本。
- Bloomberg/Koyfin/AlphaSense 类：深度研究数据、新闻/研报检索、引用、监控、组合视图。
- 券商终端/Bookmap 类：实时行情、Level-2、订单流、逐笔成交、低延迟执行入口。
- CN 零售终端：分时图、五档盘口、主力资金流、热点板块、涨跌家数、龙虎榜/公告等本地市场功能。

当前平台优势：

- 已有 provider-neutral 架构、Celery 任务、TaskRun 监控和 degraded-safe 状态。
- 已有日线、指标、推荐、报告、组合、关注列表和告警基础。
- 已有 Phase 3 分时 provider-backed + closed-session cache MVP，以及深度数据 provider-boundary MVP，可在真实 provider 接入后平滑升级。

主要差距：

- 真实分钟线已有 yfinance `1m` + 历史闭市缓存 MVP；Level-2、逐笔和资金流仍缺少已验证生产 provider。
- AI 助手 MVP 已上线，但仍需增强多轮上下文、检索引用、实时行情联动和更完整的投资研究工作流。
- 策略/推荐缺少回测、解释和筛选器。
- 专业图表已具备浏览器本地工作区保存/恢复和轻量研究注释；仍缺少多周期联动、自定义脚本、账号级图表布局同步和告警联动。
- 缺少生产级权限、数据 SLA、审计日志和 provider 配额治理。

## Follow-up Roadmap

| 优先级 | Roadmap Item | 建议 Trellis 任务 | 验收方向 |
|---:|---|---|---|
| P0 | AI 市场助手 MVP | `07-04-ai-market-assistant` | 已实现 API/UI/tests、上下文引用、安全免责声明和 degraded/no-data fallback；后续应拆分增强任务。 |
| P0 | 真实分时数据管线 | `real-intraday-minute-data-pipeline` | yfinance `1m` MVP 已支持 verified minute payload、no_data/degraded fallback、前端真实渲染和历史闭市持久缓存；下一步是多 provider、完整交易日历、半日市、盘前盘后、实时推送和历史窗口治理。 |
| P0 | 真实深度/大单/资金流管线 | `real-market-depth-provider-pipeline` | Provider-boundary MVP 已支持显式 `fetch_market_depth`、局部分区状态、真实 payload 渲染和大单派生；下一步是接入并验证生产 Level-2/逐笔/资金流 provider。 |
| P1 | 热点板块真实资金流 | `hot-sector-fund-flow-provider` | Provider-backed MVP 已建立 contract、taxonomy、flow definitions、AkShare 候选路径和 degraded-safe UI；下一步是生产 provider 验证、涨跌家数/成分股贡献和历史轮动。 |
| P1 | Trellis 状态治理 | `trellis-phase2-phase3-state-reconciliation` | 已实现任务归档，planning/in_progress 状态与代码一致。 |
| P2 | 专业图表增强 | active slice | 本地工作区保存/恢复和研究注释已作为第一切片；后续仍需多周期联动、显式缩放按钮、账号同步、指标参数持久化和 chart-linked alerts。 |
| P2 | 推荐信号评估 | active slice | Service-level deterministic evaluation 已覆盖样本数、前瞻窗口、命中率、回撤、benchmark-relative return 和诊断；后续仍需 API/UI、持久化历史、交易成本和 walk-forward 验证。 |
| P2 | 推荐回测与策略评价 | future task | 历史回测、命中率、回撤、风险统计和解释增强。 |

## Change Safety Checklist

- 修改 endpoint contract 时同步更新本手册、用户手册和相关测试。
- 接入新 provider 能力时先扩展 capability matrix，再接入 UI。
- 任何真实行情能力上线前必须有 unavailable/degraded 回归测试。
- 不要把 AI 报告、AI 摘要和聊天式 AI 助手混为同一功能；助手回答必须保留引用、诊断和安全边界。
