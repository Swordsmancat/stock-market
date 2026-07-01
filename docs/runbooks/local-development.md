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
curl -X POST "http://localhost:8000/ingestion/mock-snapshot?market=US&provider=yfinance&start=2026-01-01&end=2026-01-20"
```

分析刷新会同时 ingest 新闻（yfinance headlines）与基本面（yfinance `.info`），并写入 DB。

Mock 仍可用于离线测试：

```bash
curl -X POST "http://localhost:8000/ingestion/mock-snapshot?market=US&provider=mock&start=2026-01-01&end=2026-01-20"
```

## 异步任务（Dashboard 按钮）

Dashboard「采集 / 刷新分析」通过 Celery 异步执行，并在任务监控页可查看状态：

```bash
curl -X POST "http://localhost:8000/analysis/refresh?symbol=AAPL&market=US&provider=yfinance"
curl -X POST "http://localhost:8000/ingestion/mock-snapshot?market=US&provider=yfinance"
curl "http://localhost:8000/task-runs/recent"
```

需同时运行 **Worker** 与 **Beat**（见上文）。

Beat 定时任务包括：关注列表分析、默认个股分析、US/HK/CN 市场日线采集。

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
