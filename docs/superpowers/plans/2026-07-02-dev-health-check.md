# Dev Health Check Implementation Plan

> **Status: completed.** This plan was implemented and committed in `94a4e74 feat: add local dev health check`. The unchecked boxes below are preserved as the original TDD execution plan, not as the current backlog. Implemented artifacts include `scripts/dev_health_check.py`, `tests/scripts/test_dev_health_check.py`, README quick-start guidance, and local development runbook troubleshooting notes.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a non-mutating local development health check command that diagnoses frontend, API, Redis, and Celery readiness before a developer opens the web app.

**Architecture:** Add a focused Python CLI at `scripts/dev_health_check.py` with small check functions that return structured `HealthCheckResult` values. Keep the script diagnostic-only: it reads environment variables, probes ports/HTTP/brokers, renders human-readable suggestions, and exits nonzero only when a frontend `FAIL` occurs.

**Tech Stack:** Python standard library (`dataclasses`, `enum`, `os`, `socket`, `subprocess`, `urllib`, `json`), existing `redis` dependency, existing Celery app at `apps.worker.celery_app`, pytest monkeypatch tests.

---

## File Structure

- Create: `scripts/dev_health_check.py`
  - Owns all local health check logic and CLI rendering.
  - Does not start services, stop services, or modify files.
- Create: `tests/scripts/test_dev_health_check.py`
  - Tests script behavior through public functions using monkeypatches; does not depend on real ports, Redis, or Celery.
- Modify: `README.md`
  - Adds a quick-start self-check command and frontend troubleshooting hint.
- Modify: `docs/runbooks/local-development.md`
  - Adds a local health check and “frontend cannot open” troubleshooting section.

## Domain Decisions

- Frontend health is critical because the user-facing failure is “web page cannot open”; frontend failures return `FAIL`.
- API, Redis, and Celery are supporting dependencies for data and async tasks; failures return `WARN` so UI-only work is not blocked.
- The script reports suggested commands but never executes them automatically.
- The default frontend URL is `http://127.0.0.1:3000/zh`; the default API health URL is `http://127.0.0.1:8000/health`.
- The script supports Windows process-owner diagnostics through PowerShell, with a socket-only fallback on other platforms.

### Task 1: Core Result Model and Rendering

**Files:**
- Create: `tests/scripts/test_dev_health_check.py`
- Create: `scripts/dev_health_check.py`

- [ ] **Step 1: Write the failing tests for result rendering and exit codes**

Create `tests/scripts/test_dev_health_check.py` with the following initial content:

```python
from __future__ import annotations

import io

from scripts import dev_health_check


def test_render_results_summarizes_ok_warn_and_fail():
    output = io.StringIO()
    results = [
        dev_health_check.HealthCheckResult(
            status=dev_health_check.HealthStatus.OK,
            name="frontend port",
            message="frontend port 3000 is listening",
            details=["node.exe pid=140076"],
            suggestions=[],
        ),
        dev_health_check.HealthCheckResult(
            status=dev_health_check.HealthStatus.WARN,
            name="api health",
            message="api health unavailable",
            details=["http://127.0.0.1:8000/health"],
            suggestions=["uvicorn apps.api.main:app --reload --port 8000"],
        ),
        dev_health_check.HealthCheckResult(
            status=dev_health_check.HealthStatus.FAIL,
            name="frontend page",
            message="frontend page timed out",
            details=["Port 3000 is listening but did not return HTTP within 5s."],
            suggestions=["npm run dev:web"],
        ),
    ]

    exit_code = dev_health_check.render_results(results, output=output)

    rendered = output.getvalue()
    assert exit_code == 1
    assert "Stock Analysis Platform Dev Health Check" in rendered
    assert "[OK] frontend port: frontend port 3000 is listening" in rendered
    assert "node.exe pid=140076" in rendered
    assert "[WARN] api health: api health unavailable" in rendered
    assert "Suggested fix:" in rendered
    assert "uvicorn apps.api.main:app --reload --port 8000" in rendered
    assert "[FAIL] frontend page: frontend page timed out" in rendered
    assert "Summary: 1 OK, 1 WARN, 1 FAIL" in rendered


def test_render_results_returns_zero_when_only_ok_and_warn():
    output = io.StringIO()
    results = [
        dev_health_check.HealthCheckResult(
            status=dev_health_check.HealthStatus.OK,
            name="frontend page",
            message="frontend page responds",
            details=[],
            suggestions=[],
        ),
        dev_health_check.HealthCheckResult(
            status=dev_health_check.HealthStatus.WARN,
            name="redis broker",
            message="redis broker unavailable",
            details=[],
            suggestions=["docker compose up -d redis"],
        ),
    ]

    exit_code = dev_health_check.render_results(results, output=output)

    assert exit_code == 0
    assert "Summary: 1 OK, 1 WARN, 0 FAIL" in output.getvalue()
```

- [ ] **Step 2: Run tests to verify they fail before implementation**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: fail during import because `scripts/dev_health_check.py` does not exist yet.

- [ ] **Step 3: Implement the minimal core model and renderer**

Create `scripts/dev_health_check.py` with this initial content:

```python
"""Diagnose local development services for the stock analysis platform."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from typing import TextIO


class HealthStatus(str, Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class HealthCheckResult:
    status: HealthStatus
    name: str
    message: str
    details: list[str]
    suggestions: list[str]


def render_results(results: list[HealthCheckResult], output: TextIO = sys.stdout) -> int:
    print("Stock Analysis Platform Dev Health Check", file=output)
    print("", file=output)

    counts = {
        HealthStatus.OK: 0,
        HealthStatus.WARN: 0,
        HealthStatus.FAIL: 0,
    }
    for result in results:
        counts[result.status] += 1
        print(f"[{result.status.value}] {result.name}: {result.message}", file=output)
        for detail in result.details:
            print(f"       {detail}", file=output)
        if result.suggestions:
            print("       Suggested fix:", file=output)
            for suggestion in result.suggestions:
                print(f"       {suggestion}", file=output)

    print("", file=output)
    print(
        "Summary: "
        f"{counts[HealthStatus.OK]} OK, "
        f"{counts[HealthStatus.WARN]} WARN, "
        f"{counts[HealthStatus.FAIL]} FAIL",
        file=output,
    )
    return 1 if counts[HealthStatus.FAIL] else 0
```

- [ ] **Step 4: Run tests to verify core rendering passes**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Checkpoint**

Do not commit unless the user has explicitly requested commits in the implementation session. If commits are requested, use:

```bash
git add scripts/dev_health_check.py tests/scripts/test_dev_health_check.py
git commit -m "feat: add dev health check renderer"
```

### Task 2: Frontend Port and HTTP Checks

**Files:**
- Modify: `tests/scripts/test_dev_health_check.py`
- Modify: `scripts/dev_health_check.py`

- [ ] **Step 1: Add failing tests for frontend checks**

Append these tests to `tests/scripts/test_dev_health_check.py`:

```python
import socket
import urllib.error


class FakeResponse:
    def __init__(self, status: int, body: bytes = b"<html></html>") -> None:
        self.status = status
        self.body = body
        self.headers = {"content-type": "text/html; charset=utf-8"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self.body


def test_run_frontend_checks_reports_ok_when_port_and_page_are_healthy(monkeypatch):
    owner = dev_health_check.PortOwner(
        process_id=140076,
        process_name="node.exe",
        command_line="node next dev",
    )
    monkeypatch.setattr(dev_health_check, "find_port_owner", lambda port: owner)
    monkeypatch.setattr(dev_health_check, "is_tcp_port_open", lambda host, port, timeout_seconds: True)
    monkeypatch.setattr(
        dev_health_check.urllib.request,
        "urlopen",
        lambda request, timeout: FakeResponse(200),
    )

    results = dev_health_check.run_frontend_checks(
        frontend_base_url="http://127.0.0.1:3000",
        frontend_health_path="/zh",
        timeout_seconds=5,
    )

    assert [result.status for result in results] == [
        dev_health_check.HealthStatus.OK,
        dev_health_check.HealthStatus.OK,
    ]
    assert "node.exe pid=140076" in results[0].details[0]
    assert "status=200" in results[1].message


def test_run_frontend_checks_reports_fail_when_port_is_closed(monkeypatch):
    monkeypatch.setattr(dev_health_check, "find_port_owner", lambda port: None)
    monkeypatch.setattr(dev_health_check, "is_tcp_port_open", lambda host, port, timeout_seconds: False)

    results = dev_health_check.run_frontend_checks(
        frontend_base_url="http://127.0.0.1:3000",
        frontend_health_path="/zh",
        timeout_seconds=5,
    )

    assert len(results) == 1
    assert results[0].status == dev_health_check.HealthStatus.FAIL
    assert "not listening" in results[0].message
    assert "npm run dev:web" in results[0].suggestions


def test_run_frontend_checks_reports_fail_when_http_times_out(monkeypatch):
    owner = dev_health_check.PortOwner(
        process_id=140076,
        process_name="node.exe",
        command_line="node next dev",
    )
    monkeypatch.setattr(dev_health_check, "find_port_owner", lambda port: owner)
    monkeypatch.setattr(dev_health_check, "is_tcp_port_open", lambda host, port, timeout_seconds: True)

    def raise_timeout(request, timeout):
        raise TimeoutError("timed out")

    monkeypatch.setattr(dev_health_check.urllib.request, "urlopen", raise_timeout)

    results = dev_health_check.run_frontend_checks(
        frontend_base_url="http://127.0.0.1:3000",
        frontend_health_path="/zh",
        timeout_seconds=5,
    )

    assert len(results) == 2
    assert results[1].status == dev_health_check.HealthStatus.FAIL
    assert "timed out" in results[1].message
    assert "Port 3000 is listening" in results[1].details[0]
    assert 'Stop-Process -Id 140076 -Force' in results[1].suggestions[0]
    assert "npm run dev:web" in results[1].suggestions[1]


def test_run_frontend_checks_reports_fail_for_http_error(monkeypatch):
    owner = dev_health_check.PortOwner(
        process_id=140076,
        process_name="node.exe",
        command_line="node next dev",
    )
    monkeypatch.setattr(dev_health_check, "find_port_owner", lambda port: owner)
    monkeypatch.setattr(dev_health_check, "is_tcp_port_open", lambda host, port, timeout_seconds: True)

    def raise_http_error(request, timeout):
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:3000/zh",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )

    monkeypatch.setattr(dev_health_check.urllib.request, "urlopen", raise_http_error)

    results = dev_health_check.run_frontend_checks(
        frontend_base_url="http://127.0.0.1:3000",
        frontend_health_path="/zh",
        timeout_seconds=5,
    )

    assert results[1].status == dev_health_check.HealthStatus.FAIL
    assert "HTTP 500" in results[1].message
```

- [ ] **Step 2: Run frontend tests to verify they fail**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: frontend tests fail because `PortOwner`, `run_frontend_checks`, `find_port_owner`, and `is_tcp_port_open` are not implemented.

- [ ] **Step 3: Implement frontend port and HTTP checks**

Extend `scripts/dev_health_check.py` with these imports near the top:

```python
import json
import os
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
```

Add this dataclass after `HealthCheckResult`:

```python
@dataclass(frozen=True)
class PortOwner:
    process_id: int
    process_name: str
    command_line: str

    def describe(self) -> str:
        return f"{self.process_name} pid={self.process_id}"
```

Add these functions before `render_results`:

```python
def get_timeout_seconds() -> float:
    raw_timeout = os.environ.get("DEV_HEALTH_TIMEOUT_SECONDS", "5")
    try:
        timeout_seconds = float(raw_timeout)
    except ValueError:
        return 5.0
    return timeout_seconds if timeout_seconds > 0 else 5.0


def build_url(base_url: str, path: str) -> str:
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{normalized_base}{normalized_path}"


def parse_host_and_port(base_url: str) -> tuple[str, int]:
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    if parsed.port is not None:
        return host, parsed.port
    if parsed.scheme == "https":
        return host, 443
    return host, 80


def is_tcp_port_open(host: str, port: int, timeout_seconds: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def find_port_owner(port: int) -> PortOwner | None:
    if os.name != "nt":
        return None

    try:
        pid_process = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-NetTCPConnection "
                    f"-LocalPort {port} "
                    "-State Listen "
                    "-ErrorAction SilentlyContinue | "
                    "Select-Object -First 1 -ExpandProperty OwningProcess"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None

    raw_pid = pid_process.stdout.strip()
    if not raw_pid.isdigit():
        return None

    process_id = int(raw_pid)

    try:
        process_info = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process "
                    f"-Filter 'ProcessId={process_id}' | "
                    "Select-Object -First 1 ProcessId,Name,CommandLine | "
                    "ConvertTo-Json -Compress"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return PortOwner(process_id=process_id, process_name="unknown", command_line="")

    try:
        payload = json.loads(process_info.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return PortOwner(process_id=process_id, process_name="unknown", command_line="")

    return PortOwner(
        process_id=process_id,
        process_name=str(payload.get("Name") or "unknown"),
        command_line=str(payload.get("CommandLine") or ""),
    )


def build_restart_suggestions(port_owner: PortOwner | None) -> list[str]:
    suggestions: list[str] = []
    if port_owner is not None:
        suggestions.append(
            f'powershell -NoProfile -Command "Stop-Process -Id {port_owner.process_id} -Force"'
        )
    suggestions.append("npm run dev:web")
    return suggestions


def check_frontend_port(
    frontend_base_url: str,
    timeout_seconds: float,
) -> tuple[HealthCheckResult, PortOwner | None, bool, int]:
    host, port = parse_host_and_port(frontend_base_url)
    port_owner = find_port_owner(port)
    port_is_open = is_tcp_port_open(host, port, timeout_seconds)

    if not port_is_open:
        return (
            HealthCheckResult(
                status=HealthStatus.FAIL,
                name="frontend port",
                message=f"frontend port {port} is not listening",
                details=[f"Checked {host}:{port}."],
                suggestions=["npm run dev:web"],
            ),
            port_owner,
            False,
            port,
        )

    details = [f"Checked {host}:{port}."]
    if port_owner is not None:
        details.insert(0, port_owner.describe())

    return (
        HealthCheckResult(
            status=HealthStatus.OK,
            name="frontend port",
            message=f"frontend port {port} is listening",
            details=details,
            suggestions=[],
        ),
        port_owner,
        True,
        port,
    )


def check_frontend_page(
    frontend_url: str,
    timeout_seconds: float,
    port: int,
    port_owner: PortOwner | None,
) -> HealthCheckResult:
    request = urllib.request.Request(frontend_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response.read(300)
            if response.status == 200:
                return HealthCheckResult(
                    status=HealthStatus.OK,
                    name="frontend page",
                    message=f"frontend page responds: {frontend_url} status=200",
                    details=[f"content-type={response.headers.get('content-type', 'unknown')}"],
                    suggestions=[],
                )
            return HealthCheckResult(
                status=HealthStatus.FAIL,
                name="frontend page",
                message=f"frontend page returned HTTP {response.status}: {frontend_url}",
                details=["Next.js responded, but not with the expected 200 status."],
                suggestions=build_restart_suggestions(port_owner),
            )
    except TimeoutError:
        return HealthCheckResult(
            status=HealthStatus.FAIL,
            name="frontend page",
            message=f"frontend page timed out: {frontend_url}",
            details=[f"Port {port} is listening but did not return HTTP within {timeout_seconds:g}s."],
            suggestions=build_restart_suggestions(port_owner),
        )
    except urllib.error.HTTPError as exc:
        return HealthCheckResult(
            status=HealthStatus.FAIL,
            name="frontend page",
            message=f"frontend page returned HTTP {exc.code}: {frontend_url}",
            details=[str(exc)],
            suggestions=build_restart_suggestions(port_owner),
        )
    except Exception as exc:
        return HealthCheckResult(
            status=HealthStatus.FAIL,
            name="frontend page",
            message=f"frontend page unavailable: {frontend_url}",
            details=[str(exc)],
            suggestions=build_restart_suggestions(port_owner),
        )


def run_frontend_checks(
    frontend_base_url: str,
    frontend_health_path: str,
    timeout_seconds: float,
) -> list[HealthCheckResult]:
    frontend_url = build_url(frontend_base_url, frontend_health_path)
    port_result, port_owner, port_is_open, port = check_frontend_port(
        frontend_base_url,
        timeout_seconds,
    )
    if not port_is_open:
        return [port_result]
    return [
        port_result,
        check_frontend_page(frontend_url, timeout_seconds, port, port_owner),
    ]
```

- [ ] **Step 4: Run frontend check tests**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Checkpoint**

Do not commit unless the user has explicitly requested commits in the implementation session. If commits are requested, use:

```bash
git add scripts/dev_health_check.py tests/scripts/test_dev_health_check.py
git commit -m "feat: diagnose frontend dev server health"
```

### Task 3: API, Redis, and Celery Checks

**Files:**
- Modify: `tests/scripts/test_dev_health_check.py`
- Modify: `scripts/dev_health_check.py`

- [ ] **Step 1: Add failing tests for API, Redis, and Celery warnings**

Append these tests to `tests/scripts/test_dev_health_check.py`:

```python
def test_check_api_health_returns_ok_for_healthy_api(monkeypatch):
    monkeypatch.setattr(
        dev_health_check.urllib.request,
        "urlopen",
        lambda request, timeout: FakeResponse(200, b'{"status":"ok"}'),
    )

    result = dev_health_check.check_api_health(
        api_base_url="http://127.0.0.1:8000",
        timeout_seconds=5,
    )

    assert result.status == dev_health_check.HealthStatus.OK
    assert "status=200" in result.message


def test_check_api_health_returns_warn_when_unavailable(monkeypatch):
    def raise_connection_error(request, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(dev_health_check.urllib.request, "urlopen", raise_connection_error)

    result = dev_health_check.check_api_health(
        api_base_url="http://127.0.0.1:8000",
        timeout_seconds=5,
    )

    assert result.status == dev_health_check.HealthStatus.WARN
    assert "api health unavailable" in result.message
    assert "uvicorn apps.api.main:app --reload --port 8000" in result.suggestions


class FailingRedisClient:
    def ping(self):
        raise OSError("redis unavailable")


class PassingRedisClient:
    def ping(self):
        return True


def test_check_redis_connection_returns_ok_when_ping_succeeds(monkeypatch):
    monkeypatch.setattr(dev_health_check, "resolve_redis_url", lambda: "redis://localhost:6379/0")
    monkeypatch.setattr(dev_health_check, "create_redis_client", lambda redis_url, timeout_seconds: PassingRedisClient())

    result = dev_health_check.check_redis_connection(timeout_seconds=5)

    assert result.status == dev_health_check.HealthStatus.OK
    assert "redis://localhost:6379/0" in result.message


def test_check_redis_connection_returns_warn_when_ping_fails(monkeypatch):
    monkeypatch.setattr(dev_health_check, "resolve_redis_url", lambda: "redis://localhost:6379/0")
    monkeypatch.setattr(dev_health_check, "create_redis_client", lambda redis_url, timeout_seconds: FailingRedisClient())

    result = dev_health_check.check_redis_connection(timeout_seconds=5)

    assert result.status == dev_health_check.HealthStatus.WARN
    assert "redis broker unavailable" in result.message
    assert "docker compose up -d redis" in result.suggestions


class FakeCeleryConnection:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def ensure_connection(self, max_retries: int):
        if self.should_fail:
            raise OSError("broker unavailable")

    def release(self):
        return None



class FakeCeleryApp:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def connection(self):
        return FakeCeleryConnection(should_fail=self.should_fail)


def test_check_celery_connection_returns_ok_when_broker_opens(monkeypatch):
    monkeypatch.setattr(dev_health_check, "load_celery_app", lambda: FakeCeleryApp())

    result = dev_health_check.check_celery_connection()

    assert result.status == dev_health_check.HealthStatus.OK
    assert "celery app imports" in result.message


def test_check_celery_connection_returns_warn_for_import_failure(monkeypatch):
    def raise_import_error():
        raise ImportError("missing dependency")

    monkeypatch.setattr(dev_health_check, "load_celery_app", raise_import_error)

    result = dev_health_check.check_celery_connection()

    assert result.status == dev_health_check.HealthStatus.WARN
    assert "cannot import celery app" in result.message
    assert "python -m pip install -e ." in result.suggestions


def test_check_celery_connection_returns_warn_for_broker_failure(monkeypatch):
    monkeypatch.setattr(dev_health_check, "load_celery_app", lambda: FakeCeleryApp(should_fail=True))

    result = dev_health_check.check_celery_connection()

    assert result.status == dev_health_check.HealthStatus.WARN
    assert "celery broker unavailable" in result.message
    assert "docker compose up -d redis" in result.suggestions
```

- [ ] **Step 2: Run tests to verify dependency checks fail**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: new tests fail because API, Redis, and Celery check functions are not implemented.

- [ ] **Step 3: Implement API, Redis, and Celery checks**

Add these imports to `scripts/dev_health_check.py`:

```python
import importlib
```

Add these functions before `render_results`:

```python
def check_api_health(api_base_url: str, timeout_seconds: float) -> HealthCheckResult:
    health_url = build_url(api_base_url, "/health")
    request = urllib.request.Request(health_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response.read(300)
            if response.status == 200:
                return HealthCheckResult(
                    status=HealthStatus.OK,
                    name="api health",
                    message=f"api health responds: {health_url} status=200",
                    details=[],
                    suggestions=[],
                )
            return HealthCheckResult(
                status=HealthStatus.WARN,
                name="api health",
                message=f"api health returned HTTP {response.status}: {health_url}",
                details=["The frontend can render, but data-backed pages may be incomplete."],
                suggestions=["uvicorn apps.api.main:app --reload --port 8000"],
            )
    except urllib.error.HTTPError as exc:
        return HealthCheckResult(
            status=HealthStatus.WARN,
            name="api health",
            message=f"api health returned HTTP {exc.code}: {health_url}",
            details=[str(exc)],
            suggestions=["uvicorn apps.api.main:app --reload --port 8000"],
        )
    except Exception as exc:
        return HealthCheckResult(
            status=HealthStatus.WARN,
            name="api health",
            message=f"api health unavailable: {health_url}",
            details=[str(exc)],
            suggestions=["uvicorn apps.api.main:app --reload --port 8000"],
        )


def resolve_redis_url() -> str:
    environment_value = os.environ.get("REDIS_URL")
    if environment_value:
        return environment_value
    try:
        from packages.shared.config import settings

        return str(settings.redis_url)
    except Exception:
        return "redis://localhost:6379/0"


def create_redis_client(redis_url: str, timeout_seconds: float):
    import redis

    return redis.Redis.from_url(
        redis_url,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
    )


def check_redis_connection(timeout_seconds: float) -> HealthCheckResult:
    redis_url = resolve_redis_url()
    try:
        client = create_redis_client(redis_url, timeout_seconds)
        client.ping()
        return HealthCheckResult(
            status=HealthStatus.OK,
            name="redis broker",
            message=f"redis broker reachable: {redis_url}",
            details=[],
            suggestions=[],
        )
    except Exception as exc:
        return HealthCheckResult(
            status=HealthStatus.WARN,
            name="redis broker",
            message=f"redis broker unavailable: {redis_url}",
            details=[str(exc)],
            suggestions=["docker compose up -d redis"],
        )


def load_celery_app():
    importlib.import_module("apps.worker.tasks.ingestion")
    importlib.import_module("apps.worker.tasks.reports")
    importlib.import_module("apps.worker.tasks.alerts")
    celery_module = importlib.import_module("apps.worker.celery_app")
    return celery_module.celery_app


def check_celery_connection() -> HealthCheckResult:
    try:
        celery_app = load_celery_app()
    except Exception as exc:
        return HealthCheckResult(
            status=HealthStatus.WARN,
            name="celery app",
            message="cannot import celery app",
            details=[str(exc)],
            suggestions=["python -m pip install -e ."],
        )

    connection = None
    try:
        connection = celery_app.connection()
        connection.ensure_connection(max_retries=1)
        return HealthCheckResult(
            status=HealthStatus.OK,
            name="celery broker",
            message="celery app imports and broker connection opens",
            details=[],
            suggestions=[],
        )
    except Exception as exc:
        return HealthCheckResult(
            status=HealthStatus.WARN,
            name="celery broker",
            message="celery broker unavailable",
            details=[str(exc)],
            suggestions=[
                "docker compose up -d redis",
                "celery -A apps.worker.celery_app.celery_app worker --loglevel=info",
            ],
        )
    finally:
        if connection is not None and hasattr(connection, "release"):
            connection.release()
```

- [ ] **Step 4: Run all health-check unit tests**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Checkpoint**

Do not commit unless the user has explicitly requested commits in the implementation session. If commits are requested, use:

```bash
git add scripts/dev_health_check.py tests/scripts/test_dev_health_check.py
git commit -m "feat: add backend dependency health checks"
```

### Task 4: CLI Orchestration and Environment Configuration

**Files:**
- Modify: `tests/scripts/test_dev_health_check.py`
- Modify: `scripts/dev_health_check.py`

- [ ] **Step 1: Add failing tests for environment defaults and CLI orchestration**

Append these tests to `tests/scripts/test_dev_health_check.py`:

```python
def test_build_runtime_config_uses_defaults(monkeypatch):
    monkeypatch.delenv("FRONTEND_BASE_URL", raising=False)
    monkeypatch.delenv("FRONTEND_HEALTH_PATH", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("DEV_HEALTH_TIMEOUT_SECONDS", raising=False)

    config = dev_health_check.build_runtime_config()

    assert config.frontend_base_url == "http://127.0.0.1:3000"
    assert config.frontend_health_path == "/zh"
    assert config.api_base_url == "http://127.0.0.1:8000"
    assert config.timeout_seconds == 5.0


def test_build_runtime_config_uses_environment(monkeypatch):
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3001")
    monkeypatch.setenv("FRONTEND_HEALTH_PATH", "/en")
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:8001")
    monkeypatch.setenv("DEV_HEALTH_TIMEOUT_SECONDS", "2.5")

    config = dev_health_check.build_runtime_config()

    assert config.frontend_base_url == "http://localhost:3001"
    assert config.frontend_health_path == "/en"
    assert config.api_base_url == "http://127.0.0.1:8001"
    assert config.timeout_seconds == 2.5


def test_run_all_checks_orders_frontend_api_redis_and_celery(monkeypatch):
    calls: list[str] = []
    config = dev_health_check.RuntimeConfig(
        frontend_base_url="http://127.0.0.1:3000",
        frontend_health_path="/zh",
        api_base_url="http://127.0.0.1:8000",
        timeout_seconds=5,
    )

    def fake_frontend_checks(frontend_base_url, frontend_health_path, timeout_seconds):
        calls.append("frontend")
        return [
            dev_health_check.HealthCheckResult(
                status=dev_health_check.HealthStatus.OK,
                name="frontend page",
                message="frontend page responds",
                details=[],
                suggestions=[],
            )
        ]

    def fake_api_health(api_base_url, timeout_seconds):
        calls.append("api")
        return dev_health_check.HealthCheckResult(
            status=dev_health_check.HealthStatus.WARN,
            name="api health",
            message="api unavailable",
            details=[],
            suggestions=[],
        )

    def fake_redis_connection(timeout_seconds):
        calls.append("redis")
        return dev_health_check.HealthCheckResult(
            status=dev_health_check.HealthStatus.WARN,
            name="redis broker",
            message="redis unavailable",
            details=[],
            suggestions=[],
        )

    def fake_celery_connection():
        calls.append("celery")
        return dev_health_check.HealthCheckResult(
            status=dev_health_check.HealthStatus.WARN,
            name="celery broker",
            message="celery unavailable",
            details=[],
            suggestions=[],
        )

    monkeypatch.setattr(dev_health_check, "run_frontend_checks", fake_frontend_checks)
    monkeypatch.setattr(dev_health_check, "check_api_health", fake_api_health)
    monkeypatch.setattr(dev_health_check, "check_redis_connection", fake_redis_connection)
    monkeypatch.setattr(dev_health_check, "check_celery_connection", fake_celery_connection)

    results = dev_health_check.run_all_checks(config)

    assert calls == ["frontend", "api", "redis", "celery"]
    assert len(results) == 4
    assert results[0].status == dev_health_check.HealthStatus.OK
    assert results[1].status == dev_health_check.HealthStatus.WARN


def test_main_returns_renderer_exit_code(monkeypatch):
    config = dev_health_check.RuntimeConfig(
        frontend_base_url="http://127.0.0.1:3000",
        frontend_health_path="/zh",
        api_base_url="http://127.0.0.1:8000",
        timeout_seconds=5,
    )
    result = dev_health_check.HealthCheckResult(
        status=dev_health_check.HealthStatus.FAIL,
        name="frontend page",
        message="frontend unavailable",
        details=[],
        suggestions=[],
    )

    monkeypatch.setattr(dev_health_check, "build_runtime_config", lambda: config)
    monkeypatch.setattr(dev_health_check, "run_all_checks", lambda runtime_config: [result])
    monkeypatch.setattr(dev_health_check, "render_results", lambda results: 1)

    assert dev_health_check.main() == 1
```

- [ ] **Step 2: Run tests to verify orchestration tests fail**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: new tests fail because `RuntimeConfig`, `build_runtime_config`, `run_all_checks`, and `main` are not implemented.

- [ ] **Step 3: Implement runtime configuration and CLI orchestration**

Add this dataclass after `PortOwner`:

```python
@dataclass(frozen=True)
class RuntimeConfig:
    frontend_base_url: str
    frontend_health_path: str
    api_base_url: str
    timeout_seconds: float
```

Add these functions before `render_results`:

```python
def build_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        frontend_base_url=os.environ.get("FRONTEND_BASE_URL", "http://127.0.0.1:3000").rstrip("/"),
        frontend_health_path=os.environ.get("FRONTEND_HEALTH_PATH", "/zh"),
        api_base_url=os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        timeout_seconds=get_timeout_seconds(),
    )


def run_all_checks(config: RuntimeConfig) -> list[HealthCheckResult]:
    results: list[HealthCheckResult] = []
    results.extend(
        run_frontend_checks(
            frontend_base_url=config.frontend_base_url,
            frontend_health_path=config.frontend_health_path,
            timeout_seconds=config.timeout_seconds,
        )
    )
    results.append(check_api_health(config.api_base_url, config.timeout_seconds))
    results.append(check_redis_connection(config.timeout_seconds))
    results.append(check_celery_connection())
    return results


def main() -> int:
    config = build_runtime_config()
    return render_results(run_all_checks(config))
```

Add this block at the end of `scripts/dev_health_check.py`:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI orchestration tests**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Run the real diagnostic script in the current environment**

Run:

```bash
python scripts/dev_health_check.py
```

Expected when frontend is running and API/Redis/Celery are unavailable:

```text
Stock Analysis Platform Dev Health Check

[OK] frontend port: frontend port 3000 is listening
[OK] frontend page: frontend page responds: http://127.0.0.1:3000/zh status=200
[WARN] api health: api health unavailable: http://127.0.0.1:8000/health
[WARN] redis broker: redis broker unavailable: redis://localhost:6379/0
[WARN] celery broker: celery broker unavailable

Summary: 2 OK, 3 WARN, 0 FAIL
```

The command exits with `0` when there are no `FAIL` results. It can print `WARN` for API, Redis, or Celery without failing.

- [ ] **Step 6: Checkpoint**

Do not commit unless the user has explicitly requested commits in the implementation session. If commits are requested, use:

```bash
git add scripts/dev_health_check.py tests/scripts/test_dev_health_check.py
git commit -m "feat: add dev health check CLI"
```

### Task 5: Documentation Updates

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/local-development.md`

- [ ] **Step 1: Update README quick start with self-check command**

In `README.md`, after the “Start the web app” command block and before the “Open” sentence, insert this section:

```markdown
If the frontend does not open, run the local health check before restarting services:

```bash
python scripts/dev_health_check.py
```

The check reports whether port 3000 is listening, whether `/zh` responds, and whether API/Redis/Celery dependencies are reachable.
```

- [ ] **Step 2: Update local development runbook with troubleshooting section**

In `docs/runbooks/local-development.md`, after the “前端开发服务” section, insert this section:

```markdown
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
```

- [ ] **Step 3: Run documentation-related smoke commands**

Run:

```bash
python scripts/dev_health_check.py
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: script executes and tests pass.

- [ ] **Step 4: Checkpoint**

Do not commit unless the user has explicitly requested commits in the implementation session. If commits are requested, use:

```bash
git add README.md docs/runbooks/local-development.md
git commit -m "docs: document local health checks"
```

### Task 6: Final Verification

**Files:**
- Verify: `scripts/dev_health_check.py`
- Verify: `tests/scripts/test_dev_health_check.py`
- Verify: `README.md`
- Verify: `docs/runbooks/local-development.md`

- [ ] **Step 1: Run focused tests**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py -v
```

Expected: all tests in `tests/scripts/test_dev_health_check.py` pass.

- [ ] **Step 2: Run the diagnostic script against the current machine state**

Run:

```bash
python scripts/dev_health_check.py
```

Expected: the command prints a `Summary:` line. It exits `0` if frontend has no `FAIL`; it exits `1` if frontend port/page checks fail.

- [ ] **Step 3: Run adjacent existing checks**

Run:

```bash
python scripts/verify_celery.py
```

Expected: passes when Redis is running; if Redis is intentionally stopped, it may fail with a clear Redis connection error. Do not treat intentional local Redis absence as a code regression if `tests/scripts/test_dev_health_check.py` passes.

- [ ] **Step 4: Run full Python regression if time allows**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py tests/api/test_health.py tests/services/test_task_dispatch.py -v
```

Expected: all selected tests pass.

- [ ] **Step 5: Review git diff**

Run:

```bash
git diff --stat
git diff -- scripts/dev_health_check.py tests/scripts/test_dev_health_check.py README.md docs/runbooks/local-development.md
```

Expected: diff only contains the health check script, tests, and documentation updates described in this plan.

## Plan Self-Review

- Spec coverage: The plan implements frontend port checks, frontend HTTP checks, API `/health`, Redis broker ping, Celery import/broker connection, human-readable rendering, exit codes, configuration environment variables, tests, and docs.
- Unfinished-marker scan: The plan contains no unfinished implementation markers and no deferred behavior.
- Type consistency: `HealthStatus`, `HealthCheckResult`, `PortOwner`, and `RuntimeConfig` names are consistent across tasks and tests.
- Scope check: The plan does not add auto-repair, service startup, full MVP acceptance, or real provider smoke checks.
