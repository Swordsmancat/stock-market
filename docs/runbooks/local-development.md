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

## 行情数据源 Provider

开发环境默认使用 Mock 数据源：

```bash
curl -X POST "http://localhost:8000/ingestion/mock-snapshot?market=US&provider=mock&start=2026-01-01&end=2026-01-20"
```

如需尝试真实行情数据源，可使用 `provider=yfinance`。该路径会通过 yfinance 拉取日线数据，并写入同一张 `bars_1d` 表：

```bash
curl -X POST "http://localhost:8000/ingestion/mock-snapshot?market=US&provider=yfinance&start=2026-01-01&end=2026-01-20"
```

Mock 仍然是默认 Provider，因此本地测试和演示流程不会依赖外部网络。

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
