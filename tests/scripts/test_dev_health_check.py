from __future__ import annotations

import io
import urllib.error

import pytest

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


def test_run_frontend_checks_reports_fail_when_urllib_wraps_timeout(monkeypatch):
    owner = dev_health_check.PortOwner(
        process_id=140076,
        process_name="node.exe",
        command_line="node next dev",
    )
    monkeypatch.setattr(dev_health_check, "find_port_owner", lambda port: owner)
    monkeypatch.setattr(dev_health_check, "is_tcp_port_open", lambda host, port, timeout_seconds: True)

    def raise_wrapped_timeout(request, timeout):
        raise urllib.error.URLError(TimeoutError("timed out"))

    monkeypatch.setattr(dev_health_check.urllib.request, "urlopen", raise_wrapped_timeout)

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


def test_parse_host_and_port_supports_common_frontend_base_urls():
    assert dev_health_check.parse_host_and_port("http://127.0.0.1") == ("127.0.0.1", 80)
    assert dev_health_check.parse_host_and_port("https://example.com") == ("example.com", 443)
    assert dev_health_check.parse_host_and_port("http://127.0.0.1:3000") == ("127.0.0.1", 3000)
    assert dev_health_check.parse_host_and_port("localhost:3000") == ("localhost", 3000)


def test_build_url_supports_scheme_less_frontend_base_url():
    assert dev_health_check.build_url("localhost:3000", "/zh") == "http://localhost:3000/zh"


def test_check_frontend_port_reports_fail_for_invalid_port():
    result, port_owner, port_is_open, port = dev_health_check.check_frontend_port(
        "http://127.0.0.1:not-a-port",
        timeout_seconds=5,
    )

    assert result.status == dev_health_check.HealthStatus.FAIL
    assert "invalid frontend URL" in result.message
    assert "FRONTEND_BASE_URL" in result.details[0]
    assert port_owner is None
    assert port_is_open is False
    assert port == 0


def test_parse_host_and_port_raises_clear_error_for_invalid_port():
    with pytest.raises(ValueError, match="Invalid port in frontend URL"):
        dev_health_check.parse_host_and_port("http://127.0.0.1:not-a-port")


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
    def __init__(self, should_fail: bool = False, release_should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.release_should_fail = release_should_fail

    def ensure_connection(self, max_retries: int):
        if self.should_fail:
            raise OSError("broker unavailable")

    def release(self):
        if self.release_should_fail:
            raise OSError("release failed")
        return None


class FakeCeleryApp:
    def __init__(self, should_fail: bool = False, release_should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.release_should_fail = release_should_fail

    def connection(self):
        return FakeCeleryConnection(
            should_fail=self.should_fail,
            release_should_fail=self.release_should_fail,
        )


def test_check_celery_connection_returns_ok_when_broker_opens(monkeypatch):
    monkeypatch.setattr(dev_health_check, "load_celery_app", lambda: FakeCeleryApp())

    result = dev_health_check.check_celery_connection()

    assert result.status == dev_health_check.HealthStatus.OK
    assert "celery app imports" in result.message


def test_check_celery_connection_returns_ok_when_release_fails_after_broker_opens(monkeypatch):
    monkeypatch.setattr(
        dev_health_check,
        "load_celery_app",
        lambda: FakeCeleryApp(release_should_fail=True),
    )

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


def test_check_celery_connection_returns_warn_when_broker_and_release_fail(monkeypatch):
    monkeypatch.setattr(
        dev_health_check,
        "load_celery_app",
        lambda: FakeCeleryApp(should_fail=True, release_should_fail=True),
    )

    result = dev_health_check.check_celery_connection()

    assert result.status == dev_health_check.HealthStatus.WARN
    assert "celery broker unavailable" in result.message
    assert "broker unavailable" in result.details[0]
    assert "docker compose up -d redis" in result.suggestions


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
    monkeypatch.setenv("FRONTEND_BASE_URL", "  http://localhost:3001/  ")
    monkeypatch.setenv("FRONTEND_HEALTH_PATH", "  /en  ")
    monkeypatch.setenv("API_BASE_URL", "  http://127.0.0.1:8001/  ")
    monkeypatch.setenv("DEV_HEALTH_TIMEOUT_SECONDS", "2.5")

    config = dev_health_check.build_runtime_config()

    assert config.frontend_base_url == "http://localhost:3001"
    assert config.frontend_health_path == "/en"
    assert config.api_base_url == "http://127.0.0.1:8001"
    assert config.timeout_seconds == 2.5


@pytest.mark.parametrize(
    ("frontend_base_url", "frontend_health_path", "api_base_url"),
    [
        ("", "", ""),
        ("   ", "\t", "\n"),
    ],
)
def test_build_runtime_config_uses_defaults_for_empty_or_blank_environment(
    monkeypatch,
    frontend_base_url,
    frontend_health_path,
    api_base_url,
):
    monkeypatch.setenv("FRONTEND_BASE_URL", frontend_base_url)
    monkeypatch.setenv("FRONTEND_HEALTH_PATH", frontend_health_path)
    monkeypatch.setenv("API_BASE_URL", api_base_url)
    monkeypatch.delenv("DEV_HEALTH_TIMEOUT_SECONDS", raising=False)

    config = dev_health_check.build_runtime_config()

    assert config.frontend_base_url == "http://127.0.0.1:3000"
    assert config.frontend_health_path == "/zh"
    assert config.api_base_url == "http://127.0.0.1:8000"
    assert config.timeout_seconds == 5.0


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
