"""Diagnose local development services for the stock analysis platform."""

from __future__ import annotations

import importlib
import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
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


@dataclass(frozen=True)
class PortOwner:
    process_id: int
    process_name: str
    command_line: str

    def describe(self) -> str:
        return f"{self.process_name} pid={self.process_id}"


@dataclass(frozen=True)
class RuntimeConfig:
    frontend_base_url: str
    frontend_health_path: str
    api_base_url: str
    timeout_seconds: float


def get_timeout_seconds() -> float:
    raw_timeout = os.environ.get("DEV_HEALTH_TIMEOUT_SECONDS", "5")
    try:
        timeout_seconds = float(raw_timeout)
    except ValueError:
        return 5.0
    return timeout_seconds if timeout_seconds > 0 else 5.0


def get_environment_value(name: str, default_value: str) -> str:
    environment_value = os.environ.get(name)
    if environment_value is None:
        return default_value

    stripped_environment_value = environment_value.strip()
    if not stripped_environment_value:
        return default_value

    return stripped_environment_value


def normalize_base_url(base_url: str) -> str:
    stripped_base_url = base_url.strip().rstrip("/")
    parsed = urllib.parse.urlparse(stripped_base_url)
    if parsed.scheme in {"http", "https"}:
        return stripped_base_url
    return f"http://{stripped_base_url}"


def build_url(base_url: str, path: str) -> str:
    normalized_base = normalize_base_url(base_url)
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{normalized_base}{normalized_path}"


def parse_host_and_port(base_url: str) -> tuple[str, int]:
    normalized_base_url = normalize_base_url(base_url)
    parsed = urllib.parse.urlparse(normalized_base_url)
    host = parsed.hostname or "127.0.0.1"
    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise ValueError(f"Invalid port in frontend URL: {base_url}") from exc
    if parsed_port is not None:
        return host, parsed_port
    if parsed.scheme == "https":
        return host, 443
    return host, 80


def is_timeout_error(error: BaseException) -> bool:
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, urllib.error.URLError):
        reason = getattr(error, "reason", None)
        return isinstance(reason, TimeoutError)
    return False


def build_frontend_timeout_result(
    frontend_url: str,
    timeout_seconds: float,
    port: int,
    port_owner: PortOwner | None,
) -> HealthCheckResult:
    return HealthCheckResult(
        status=HealthStatus.FAIL,
        name="frontend page",
        message=f"frontend page timed out: {frontend_url}",
        details=[f"Port {port} is listening but did not return HTTP within {timeout_seconds:g}s."],
        suggestions=build_restart_suggestions(port_owner),
    )


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
    try:
        host, port = parse_host_and_port(frontend_base_url)
    except ValueError as exc:
        return (
            HealthCheckResult(
                status=HealthStatus.FAIL,
                name="frontend port",
                message=f"invalid frontend URL: {frontend_base_url}",
                details=[f"Set FRONTEND_BASE_URL to a valid URL with a numeric port. {exc}"],
                suggestions=["set FRONTEND_BASE_URL=http://127.0.0.1:3000"],
            ),
            None,
            False,
            0,
        )
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
            response.read()
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
    except urllib.error.HTTPError as exc:
        return HealthCheckResult(
            status=HealthStatus.FAIL,
            name="frontend page",
            message=f"frontend page returned HTTP {exc.code}: {frontend_url}",
            details=[str(exc)],
            suggestions=build_restart_suggestions(port_owner),
        )
    except (TimeoutError, urllib.error.URLError) as exc:
        if is_timeout_error(exc):
            return build_frontend_timeout_result(frontend_url, timeout_seconds, port, port_owner)
        return HealthCheckResult(
            status=HealthStatus.FAIL,
            name="frontend page",
            message=f"frontend page unavailable: {frontend_url}",
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


def check_api_health(api_base_url: str, timeout_seconds: float) -> HealthCheckResult:
    health_url = build_url(api_base_url, "/health")
    request = urllib.request.Request(health_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response.read()
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
            try:
                connection.release()
            except Exception:
                pass


def build_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        frontend_base_url=get_environment_value(
            "FRONTEND_BASE_URL",
            "http://127.0.0.1:3000",
        ).rstrip("/"),
        frontend_health_path=get_environment_value("FRONTEND_HEALTH_PATH", "/zh"),
        api_base_url=get_environment_value("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
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


if __name__ == "__main__":
    raise SystemExit(main())
