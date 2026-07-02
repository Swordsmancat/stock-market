# 本地开发手册

## 启动依赖

```bash
docker compose up -d db redis
```

## 安装后端依赖

```bash
python -m pip install -e ".[dev]"
```

## 后端测试

```bash
python -m pytest -v
```

## 后端 API

```bash
uvicorn apps.api.main:app --reload
```

## Celery Worker

```bash
celery -A apps.worker.celery_app.celery_app worker --loglevel=info
```

## Celery Beat 定时调度

```bash
celery -A apps.worker.celery_app.celery_app beat --loglevel=info
```

## Docker 启动 Worker 和 Beat

```bash
docker compose up -d db redis worker beat
```

## Docker 启动完整栈（含 API）

```bash
docker compose up -d db redis api worker beat
```

API 将在 http://localhost:8000 可用（含 `/watchlist`、`/settings/platform` 等完整路由）。

## 验证 Celery 连接

```bash
python scripts/verify_celery.py
```

## TaskRun / Celery 可靠性诊断

```bash
python scripts/task_run_health.py
python scripts/verify_celery.py
```

`task_run_health.py` 是只读 TaskRun 检查：连接数据库后查询最近任务记录，报告超过 `TASK_RUN_STALE_MINUTES` 仍为 `running` 的任务，以及最近 24 小时内失败的任务；它不会修改任务状态，也不会写数据库。

`verify_celery.py` 检查 Celery app 是否可导入、Redis broker 是否可连接，以及预期任务是否已注册。

## A 股数据源（AkShare / Tushare）

```bash
python -m pip install -e ".[cn-market]"
```

在设置页选择 `akshare` 或 `tushare` 作为行情数据源。Tushare 需在设置页填写 Token。

## 数据库迁移

首次启动或拉取新代码后执行：

```bash
alembic upgrade head
```

当前迁移包含：`0006` task_run celery_id、`0007` portfolios、`0008` alert_triggers + report task_run_id。

## 环境变量

复制 `.env.example` 为 `.env`，常用项：

```bash
MARKET_DATA_PROVIDER=yfinance
NEXT_PUBLIC_MARKET_DATA_PROVIDER=yfinance
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://localhost:6379/0
```

## 行情数据源 Provider

默认推荐使用 `yfinance`（`.env.example` 已配置）。采集与分析刷新均会走该 provider：

```bash
curl -X POST "http://localhost:8000/ingestion/snapshot?market=US&provider=yfinance&start=2026-01-01&end=2026-01-20"
```

分析刷新会同时 ingest 新闻（yfinance headlines）与基本面（yfinance `.info`），并写入 DB。

Mock 仍可用于离线测试：

```bash
curl -X POST "http://localhost:8000/ingestion/snapshot?market=US&provider=mock&start=2026-01-01&end=2026-01-20"
```

兼容入口 `POST /ingestion/mock-snapshot` 暂时保留给旧脚本和旧前端代理，但新代码和文档应优先使用 `POST /ingestion/snapshot`。

## Provider readiness smoke

需要快速确认行情 provider 是否可读取基础标的与日线数据时，可运行只读 smoke CLI：

```bash
python scripts/provider_readiness.py --provider mock --market US
```

真实网络 provider 默认不会联网，必须显式 opt in：

```bash
python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL --real-network
```

未传 `--real-network` 时，`yfinance` 检查会返回 `WARN` 并跳过实时下载：

```bash
python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL
```

该 CLI 只直接调用 provider 的 instruments / bars 读取接口，不调用 ingestion 写库函数，也不会写数据库。

## Market data quality checks

`packages.services.data_quality.check_daily_bar_quality(...)` 是日线行情质量检查的纯服务第一版。调用方需要显式传入已序列化的 daily bars（每条至少包含 `timestamp` 或 `trade_date`、`open`、`high`、`low`、`close`、`volume`），服务本身不查询数据库、不写数据库，也不触发 ingestion。

检查结果包含：

- `checked_bars`：本次检查的 bar 数量。
- `missing_dates`：按 Monday-Friday 推导出的缺失 weekday session；第一版不接入交易日历，也不排除节假日。
- `invalid_ohlc`：违反 `high >= low/open/close` 或 `low <= open/close` 的行级明细，状态为 `FAIL`。
- `volume_warnings`：成交量异常明细；zero volume 返回 `WARN`，negative volume 返回 `FAIL`。
- `status`：`OK` / `WARN` / `FAIL`。

空输入当前返回 `FAIL`：没有任何 bar 时无法评估行情质量，通常也意味着 provider、ingestion 或上游任务没有产出数据；把它作为失败比静默告警更适合诊断。

后续可以把该纯服务接入 ingestion TaskRun result，将 provider/DB 已序列化的 bars 传入后，把 gap、OHLC 和 volume 诊断写入任务结果或告警报告。

## 异步任务（Dashboard 按钮）

Dashboard「采集 / 刷新分析」通过 Celery 异步执行，并在任务监控页可查看状态：

```bash
curl -X POST "http://localhost:8000/analysis/refresh?symbol=AAPL&market=US&provider=yfinance"
curl -X POST "http://localhost:8000/ingestion/snapshot?market=US&provider=yfinance&start=2026-01-01&end=2026-01-20"
curl "http://localhost:8000/task-runs/recent"
```

需同时运行 **Worker** 与 **Beat**（见上文）。

Beat 定时任务包括：关注列表分析、默认个股分析、US/HK/CN 市场日线采集、**关注列表告警评估**（每 15 分钟，`alerts.evaluate_watchlist_alerts`）。

## 组合与告警 API

```bash
curl "http://localhost:8000/portfolios"
curl "http://localhost:8000/portfolios/demo"
curl "http://localhost:8000/watchlist"
curl "http://localhost:8000/alerts/triggers/recent"
```

## 配置每日股票池

默认定时任务会读取：

```bash
DAILY_REPORT_WATCHLIST=AAPL:US
```

多个股票用英文逗号分隔，格式为 `SYMBOL:MARKET`：

```bash
DAILY_REPORT_WATCHLIST=AAPL:US,0700:HK,600519:CN
```

## 安装前端依赖

```bash
npm install
```

## 前端测试

```bash
npm run test:web
```

## 前端开发服务

```bash
npm run dev:web
```

## 本地一键自检

当前端打不开、页面请求超时，或不确定 API / Redis / Celery 是否可用时，先运行：

```bash
python scripts/dev_health_check.py
```

脚本只做诊断，不会自动杀进程或启动服务。检查结果分为：

- `OK`：该项可用。
- `WARN`：依赖不可用，但不一定阻止前端页面渲染。
- `FAIL`：核心前端可用性失败，需要优先处理。

如果输出显示 `frontend page timed out`，通常表示旧 Next.js dev server 仍占用 `3000` 端口但已经无响应。按脚本建议停止对应 PID 后重新运行：

```bash
npm run dev:web
```

如果输出显示 API 不可用，启动：

```bash
uvicorn apps.api.main:app --reload --port 8000
```

如果输出显示 Redis 或 Celery broker 不可用，启动：

```bash
docker compose up -d redis
celery -A apps.worker.celery_app.celery_app worker --loglevel=info
```

## CI 健康检查自动化

`.github/workflows/dev-health.yml` 定义了 `Dev Health` GitHub Actions workflow，可通过 `workflow_dispatch` 手动触发，也会每日 UTC 01:30（中国时间 09:30）定时运行。

该 workflow 会在干净 checkout 中启动临时 PostgreSQL/TimescaleDB 和 Redis，安装后端与前端依赖，执行数据库迁移，启动 API 与 web，并运行 `python scripts/dev_health_check.py` 和相关健康测试，用于验证 dev health check、API、web、Redis、Celery broker 是否可用。

该 workflow 只做诊断与测试，不修改代码、不连接生产数据、不自动修复问题。需要临时确认健康状态时，可在 GitHub Actions 页面选择 `Dev Health` 并手动触发；失败时查看上传的 API / web 日志 artifact。
