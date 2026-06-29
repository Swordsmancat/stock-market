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
