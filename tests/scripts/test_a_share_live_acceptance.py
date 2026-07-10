import json
from pathlib import Path

import pytest

from scripts import a_share_live_acceptance as acceptance
from scripts.provider_readiness import ProviderReadinessResult, ReadinessStatus


def test_write_guards_reject_normal_database_and_missing_flags() -> None:
    with pytest.raises(acceptance.AcceptanceFailure, match="--real-network"):
        acceptance.require_write_guards(
            real_network=False,
            confirm_acceptance_writes=True,
            database_url="postgresql+psycopg://stock:stock@localhost/stock_acceptance",
        )

    with pytest.raises(acceptance.AcceptanceFailure, match="confirm-acceptance-writes"):
        acceptance.require_write_guards(
            real_network=True,
            confirm_acceptance_writes=False,
            database_url="postgresql+psycopg://stock:stock@localhost/stock_acceptance",
        )

    with pytest.raises(acceptance.AcceptanceFailure, match="refusing target stock"):
        acceptance.require_write_guards(
            real_network=True,
            confirm_acceptance_writes=True,
            database_url="postgresql+psycopg://stock:stock@localhost/stock",
        )


def test_runtime_identity_requires_acceptance_environment_and_database(monkeypatch) -> None:
    monkeypatch.setattr(
        acceptance,
        "request_json",
        lambda *_args, **_kwargs: {
            "status": "ok",
            "app_env": "local",
            "database_name": "stock_acceptance",
            "celery_timezone": "Asia/Shanghai",
        },
    )

    with pytest.raises(acceptance.AcceptanceFailure, match="not the isolated"):
        acceptance.verify_runtime_identity("http://api.test")


def test_poll_task_run_unwraps_and_sanitizes_terminal_payload(monkeypatch) -> None:
    responses = iter(
        [
            {"item": {"id": "task-1", "status": "running"}},
            {
                "item": {
                    "id": "task-1",
                    "task_name": "ingestion.test",
                    "status": "succeeded",
                    "result_json": {"provider": "akshare"},
                    "error_message": None,
                }
            },
        ]
    )
    monkeypatch.setattr(acceptance, "request_json", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(acceptance.time, "sleep", lambda _seconds: None)

    result = acceptance.poll_task_run(
        "http://api.test", "task-1", timeout_seconds=2, poll_seconds=0.01
    )

    assert result["status"] == "succeeded"
    assert result["result_json"] == {"provider": "akshare"}


def test_sanitized_artifact_redacts_urls_headers_and_secret_keys(tmp_path) -> None:
    path = acceptance.write_artifact(
        tmp_path,
        "canary",
        {
            "database_url": "postgresql://user:password@db/stock_acceptance",
            "authorization": "Bearer abc.def",
            "message": "call redis://stock:secret@redis:6379/0 with Bearer token-value cookie=private",
        },
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["database_url"] == "[REDACTED]"
    assert payload["authorization"] == "[REDACTED]"
    assert payload["message"] == (
        "call redis://[REDACTED]@redis:6379/0 with Bearer [REDACTED] cookie=[REDACTED]"
    )
    serialized = path.read_text(encoding="utf-8")
    assert "password" not in serialized
    assert "abc.def" not in serialized
    assert "token-value" not in serialized
    assert "private" not in serialized


def test_failed_readiness_record_drops_raw_exception_message() -> None:
    result = ProviderReadinessResult(
        status=ReadinessStatus.FAIL,
        name="provider readiness",
        message="connection failed with private upstream body and cookie=secret",
        details=["provider=akshare", "exception_type=ConnectionError"],
        suggestions=["Retry later."],
    )

    record = acceptance.readiness_record(result, attempt=2)

    assert record["message"] == "provider readiness failed; see classified details and suggestions."
    assert record["attempt"] == 2
    assert "private upstream" not in json.dumps(record)


def test_acceptance_build_context_recursively_ignores_generated_dependencies() -> None:
    patterns = set(Path(".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {"**/.next", "**/node_modules", "**/.env*"}.issubset(patterns)


def test_web_acceptance_image_uses_the_locked_package_manager_version() -> None:
    package_manager = json.loads(Path("package.json").read_text(encoding="utf-8"))[
        "packageManager"
    ]
    npm_version = package_manager.removeprefix("npm@")
    dockerfile = Path("Dockerfile.web.acceptance").read_text(encoding="utf-8")

    assert f"ARG NPM_VERSION={npm_version}" in dockerfile
    assert 'npm install --global "npm@${NPM_VERSION}"' in dockerfile
