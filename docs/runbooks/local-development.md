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
