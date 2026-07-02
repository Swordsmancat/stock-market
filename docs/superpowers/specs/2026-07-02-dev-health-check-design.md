# Dev Health Check Design

## 背景

本地开发过程中已经多次遇到“前端打不开 / 启动失败”的问题。最近一次根因不是页面代码 500，也不是编译失败，而是旧 Next.js dev server 子进程仍监听 `3000` 端口但 HTTP 请求超时。当前项目已有：

- `scripts/verify_celery.py`：验证 Celery app 与 Redis broker。
- `scripts/mvp_acceptance.py`：在 API 已启动时跑 MVP 接口验收。
- `README.md` 与 `docs/runbooks/local-development.md`：记录本地启动步骤。

但缺少一个面向本地开发者的统一自检入口，用来快速判断前端、API、Redis、Celery 当前是否健康，并在失败时给出下一步命令建议。

## 目标

新增一个本地开发自检脚本：

```bash
python scripts/dev_health_check.py
```

它应该在不打开浏览器、不启动新服务、不修改运行状态的前提下，检查当前本地开发栈是否可用，并输出清晰诊断。

## 非目标

- 不自动杀进程。脚本只诊断并给出建议命令，避免误杀用户正在使用的服务。
- 不自动启动 API、前端、Redis、Celery。
- 不默认运行完整测试套件或 `scripts/mvp_acceptance.py`。
- 不把真实 provider smoke 作为默认检查项，避免网络波动影响“前端打不开”排障。

## 检查范围

默认检查本地全栈关键依赖：

| 检查项 | 默认目标 | 失败级别 | 说明 |
| --- | --- | --- | --- |
| Frontend port | `3000` | `FAIL` | 端口未监听时提示运行 `npm run dev:web`。 |
| Frontend HTTP | `http://127.0.0.1:3000/zh` | `FAIL` | 端口监听但请求超时时提示旧 Next 进程可能卡住。 |
| API health | `http://127.0.0.1:8000/health` 或 `API_BASE_URL` | `WARN` | API 未启动时前端仍可渲染部分页面，但会影响数据。 |
| Redis broker | `REDIS_URL` 或默认 `redis://localhost:6379/0` | `WARN` | Redis 不可达会影响异步任务。 |
| Celery app/broker | `apps.worker.celery_app.celery_app` | `WARN` | Celery app import 或 broker 连接失败时给出 worker/Redis 建议。 |

## 配置规则

脚本读取以下环境变量：

- `FRONTEND_BASE_URL`：默认 `http://127.0.0.1:3000`。
- `FRONTEND_HEALTH_PATH`：默认 `/zh`。
- `API_BASE_URL`：默认 `http://127.0.0.1:8000`。
- `REDIS_URL`：默认由项目 settings 解析，兜底为 `redis://localhost:6379/0`。
- `DEV_HEALTH_TIMEOUT_SECONDS`：默认 `5`。

这些配置只影响检查目标，不写回 `.env` 或其他配置文件。

## 输出格式

脚本输出人类可读文本，分为 `OK`、`WARN`、`FAIL` 三类：

```text
Stock Analysis Platform Dev Health Check

[OK] frontend port 3000 is listening: node.exe pid=140076
[OK] frontend page responds: http://127.0.0.1:3000/zh status=200
[WARN] api health unavailable: http://127.0.0.1:8000/health
       Suggested fix: uvicorn apps.api.main:app --reload --port 8000
[OK] redis broker reachable: redis://localhost:6379/0
[OK] celery app imports and broker connection opens

Summary: 4 OK, 1 WARN, 0 FAIL
```

当前端端口监听但 HTTP 超时时，输出必须明确区分“端口存在”和“页面无响应”：

```text
[FAIL] frontend page timed out: http://127.0.0.1:3000/zh
       Port 3000 is listening but did not return HTTP within 5s.
       Suggested fix:
       powershell -NoProfile -Command "Stop-Process -Id <pid> -Force"
       npm run dev:web
```

## 退出码

- `0`：没有 `FAIL`。
- `1`：存在至少一个 `FAIL`。

`WARN` 不导致非零退出码，因为 API、Redis、Celery 可能在只调试前端 UI 时暂时不需要。

## 架构

实现集中在 `scripts/dev_health_check.py`，使用小型函数分解每类检查，避免和现有业务服务耦合。脚本通过标准库完成 HTTP 与进程/端口检查；Redis 和 Celery 检查复用项目依赖与 settings。

建议的内部结构：

- `HealthStatus`：字符串枚举值 `OK`、`WARN`、`FAIL`。
- `HealthCheckResult`：包含 `status`、`name`、`message`、`details`、`suggestions`。
- `run_frontend_checks()`：组合端口检查与 HTTP 检查。
- `check_api_health()`：请求 `/health`。
- `check_redis_connection()`：读取 Redis URL 并执行 ping。
- `check_celery_connection()`：import Celery app 并尝试打开 broker connection。
- `render_results()`：统一打印输出与汇总。

端口 owner 检查在 Windows 上优先使用 PowerShell `Get-NetTCPConnection` 和 `Get-CimInstance`，失败时降级为“无法识别 owner，但端口监听存在”。这样可以支持当前开发环境，同时避免脚本在非 Windows 环境直接崩溃。

## 错误处理

- HTTP timeout：前端视为 `FAIL`，API 视为 `WARN`。
- HTTP 4xx/5xx：前端视为 `FAIL`，API 视为 `WARN`。
- 端口未监听：前端视为 `FAIL`，并建议 `npm run dev:web`。
- Redis 连接失败：`WARN`，并建议 `docker compose up -d redis`。
- Celery import 失败：`WARN`，并建议先运行 `python -m pip install -e .`。
- Celery broker 失败：`WARN`，并建议检查 Redis 与 worker 启动命令。

## 测试策略

新增 `tests/scripts/test_dev_health_check.py`，通过 monkeypatch/mock 覆盖脚本公共函数行为，不依赖真实端口或真实 Redis：

- 前端 HTTP 200 时返回 `OK`。
- 端口监听但 HTTP timeout 时返回 `FAIL`，且输出包含 `Stop-Process` 与 `npm run dev:web`。
- API `/health` 不可达时返回 `WARN`。
- Redis ping 失败时返回 `WARN`。
- Celery app import 或 broker 失败时返回 `WARN`。
- 汇总函数在存在 `FAIL` 时返回退出码 `1`，只有 `OK/WARN` 时返回 `0`。

## 文档更新

更新：

- `README.md`：Quick start 增加“前端打不开 / 本地自检”命令。
- `docs/runbooks/local-development.md`：增加故障排查小节，说明常见输出与建议动作。

## 验收标准

完成后以下命令应可运行：

```bash
python scripts/dev_health_check.py
python -m pytest tests/scripts/test_dev_health_check.py -v
```

当当前前端服务正常时，脚本至少应显示 frontend port 与 frontend page 为 `OK`。当 API、Redis、Celery 未启动时，脚本应以 `WARN` 提示，而不是阻止开发者继续查看前端页面。

## 自检结论

- 无占位符：本文档没有 `TBD`、`TODO` 或未定义的后续实现项。
- 范围聚焦：只覆盖本地开发健康检查，不自动修复、不跑完整 MVP。
- 术语一致：使用项目已有的 frontend、API、Redis、Celery、TaskRun、MVP acceptance 等术语。
- 可实现性明确：列出了脚本路径、配置环境变量、输出格式、退出码、测试文件与验收命令。
