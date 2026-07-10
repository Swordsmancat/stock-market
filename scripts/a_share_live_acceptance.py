"""Run guarded, sanitized acceptance checks against the isolated A-share stack."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.provider_readiness import ReadinessStatus  # noqa: E402
from scripts.provider_readiness import check_provider_readiness  # noqa: E402
from packages.services.daily_bar_sources import (  # noqa: E402
    CN_RESILIENT_POLICY,
    STRICT_POLICY,
)
from packages.services.ingestion import build_daily_bar_fetch_coordinator  # noqa: E402

ACCEPTANCE_DATABASE_NAME = "stock_acceptance"
TERMINAL_TASK_STATUSES = {"succeeded", "failed"}
BASELINE_RUN_KINDS = ("baseline", "fundamental_shard")
EVIDENCE_KINDS = ("daily_bars", "fundamentals", "technical_indicators")
SECRET_KEY_PATTERN = re.compile(
    r"(authorization|cookie|password|secret|token|api[_-]?key|database[_-]?url|redis[_-]?url)",
    re.I,
)
URL_CREDENTIAL_PATTERN = re.compile(r"([a-z][a-z0-9+.-]*://)([^/@\s:]+):([^/@\s]+)@", re.I)
BEARER_PATTERN = re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]+")
INLINE_SECRET_PATTERN = re.compile(
    r"(?i)\b(token|api[_-]?key|password|secret|cookie|authorization)=([^\s,&;]+)"
)


class AcceptanceFailure(RuntimeError):
    """A classified acceptance failure safe to display without a traceback."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("preflight", "canary", "baseline"), default="preflight")
    parser.add_argument("--api-base-url", default=os.getenv("ACCEPTANCE_API_BASE_URL", "http://127.0.0.1:18000"))
    parser.add_argument("--database-url", default=os.getenv("ACCEPTANCE_DATABASE_URL", ""))
    parser.add_argument("--artifact-dir", type=Path, default=PROJECT_ROOT / ".trellis" / "tasks" / "07-10-a-share-live-acceptance" / "evidence")
    parser.add_argument("--real-network", action="store_true")
    parser.add_argument(
        "--daily-bar-policy",
        choices=(STRICT_POLICY, CN_RESILIENT_POLICY),
        default=STRICT_POLICY,
    )
    parser.add_argument("--confirm-acceptance-writes", action="store_true")
    parser.add_argument(
        "--baseline-run-kind",
        choices=BASELINE_RUN_KINDS,
        default="baseline",
        help="Backfill run kind used by --phase baseline.",
    )
    parser.add_argument(
        "--evidence-kinds",
        nargs="+",
        choices=EVIDENCE_KINDS,
        default=list(EVIDENCE_KINDS),
        help="Evidence phases used by a baseline run.",
    )
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--shard-count", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=7_200)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--report-period", type=date.fromisoformat, default=date(2026, 6, 30))
    return parser


def require_write_guards(*, real_network: bool, confirm_acceptance_writes: bool, database_url: str) -> None:
    if not real_network:
        raise AcceptanceFailure("FAIL safety: --real-network is required before acceptance writes.")
    if not confirm_acceptance_writes:
        raise AcceptanceFailure("FAIL safety: --confirm-acceptance-writes is required before acceptance writes.")
    require_acceptance_database(database_url)


def require_acceptance_database(database_url: str) -> None:
    if not database_url:
        raise AcceptanceFailure("FAIL safety: ACCEPTANCE_DATABASE_URL/--database-url is required.")
    normalized_url = database_url.replace("postgresql+psycopg", "postgresql", 1)
    database_name = urlsplit(normalized_url).path.lstrip("/")
    if database_name != ACCEPTANCE_DATABASE_NAME:
        raise AcceptanceFailure(
            f"FAIL safety: database must be {ACCEPTANCE_DATABASE_NAME}; refusing target {database_name or '<empty>'}."
        )


def run_preflight(
    *,
    real_network: bool,
    daily_bar_policy: str = STRICT_POLICY,
) -> dict[str, object]:
    if not real_network:
        raise AcceptanceFailure("FAIL preflight: --real-network is required for live AkShare checks.")
    universe_results = check_provider_readiness(
        provider_name="akshare",
        market="CN",
        symbol=None,
        real_network=True,
        check_universe=True,
    )
    if daily_bar_policy == CN_RESILIENT_POLICY:
        bar_attempts, bars_ok = _run_resilient_bar_preflight()
    else:
        bar_attempts = []
        for attempt in range(1, 4):
            bar_results = check_provider_readiness(
                provider_name="akshare",
                market="CN",
                symbol="600519",
                real_network=True,
            )
            bar_attempts.extend(readiness_record(item, attempt=attempt) for item in bar_results)
            if all(item.status == ReadinessStatus.OK for item in bar_results):
                break
            if attempt < 3:
                time.sleep(2 ** (attempt - 1))
        bars_ok = all(item.status == ReadinessStatus.OK for item in bar_results)
    universe_ok = all(item.status == ReadinessStatus.OK for item in universe_results)
    payload = {
        "status": "passed" if universe_ok and bars_ok else "failed",
        "daily_bar_policy": daily_bar_policy,
        "database_writes": "none",
        "checks": [*(readiness_record(item) for item in universe_results), *bar_attempts],
    }
    return payload


def _run_resilient_bar_preflight() -> tuple[list[dict[str, object]], bool]:
    try:
        result = build_daily_bar_fetch_coordinator("akshare").fetch(
            "600519",
            "1d",
            date.today().fromordinal(date.today().toordinal() - 14),
            date.today(),
            policy=CN_RESILIENT_POLICY,
        )
    except Exception as exc:
        return ([{
            "status": "FAIL",
            "name": "akshare CN resilient daily bars",
            "message": "Resilient daily-bar preflight failed; see classified details.",
            "details": [f"exception_type={type(exc).__name__}"],
            "suggestions": ["Inspect the explicit source-attempt diagnostics and retry later."],
        }], False)
    record = {
        "status": "OK" if result.status == "ok" else "FAIL",
        "name": "akshare CN resilient daily bars",
        "message": "Explicit daily-bar source policy returned usable rows."
        if result.status == "ok"
        else "Explicit daily-bar sources returned no usable rows.",
        "details": [
            f"effective_provider={result.effective_provider or 'none'}",
            f"source={result.source or 'none'}",
            f"row_count={len(result.bars)}",
            f"fallback_used={str(result.fallback_used).lower()}",
            *[
                f"attempt={attempt.get('source')}:{attempt.get('status')}"
                for attempt in result.attempts
            ],
        ],
        "suggestions": [],
    }
    return [record], result.status == "ok"


def readiness_record(item: Any, *, attempt: int | None = None) -> dict[str, object]:
    message = str(item.message)
    if item.status == ReadinessStatus.FAIL:
        message = f"{item.name} failed; see classified details and suggestions."
    record: dict[str, object] = {
        "status": item.status.value,
        "name": item.name,
        "message": message,
        "details": item.details,
        "suggestions": item.suggestions,
    }
    if attempt is not None:
        record["attempt"] = attempt
    return record


def classify_preflight_findings(preflight: Mapping[str, object]) -> list[dict[str, object]]:
    failed_names = [
        str(check.get("name"))
        for check in preflight.get("checks", [])
        if isinstance(check, Mapping) and check.get("status") == "FAIL"
    ]
    if not failed_names:
        return []
    return [
        {
            "classification": "provider_limitation_or_environment_configuration",
            "code": "AKSHARE_PREFLIGHT_FAILED",
            "failed_checks": sorted(set(failed_names)),
            "database_writes": "none",
            "message": "Live provider preflight failed; acceptance writes were not started.",
        }
    ]


def request_json(
    api_base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, object] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{api_base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"content-type": "application/json"} if body is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(2_000_000)
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AcceptanceFailure(f"FAIL API: {method} {path} returned HTTP {exc.code}.") from None
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        raise AcceptanceFailure(f"FAIL API: {method} {path} failed ({type(exc).__name__}).") from None


def verify_runtime_identity(api_base_url: str) -> dict[str, str]:
    runtime = request_json(api_base_url, "/health/runtime")
    if runtime.get("app_env") != "acceptance" or runtime.get("database_name") != ACCEPTANCE_DATABASE_NAME:
        raise AcceptanceFailure("FAIL safety: API is not the isolated stock_acceptance runtime.")
    if runtime.get("celery_timezone") != "Asia/Shanghai":
        raise AcceptanceFailure("FAIL runtime: Celery timezone is not Asia/Shanghai.")
    return {key: str(runtime.get(key) or "") for key in ("status", "app_env", "database_name", "celery_timezone")}


def poll_task_run(
    api_base_url: str,
    task_run_id: str,
    *,
    timeout_seconds: int,
    poll_seconds: float,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        payload = request_json(api_base_url, f"/task-runs/{task_run_id}")
        item = payload.get("item") if isinstance(payload.get("item"), dict) else payload
        status = str(item.get("status") or "")
        if status in TERMINAL_TASK_STATUSES:
            return summarize_task_run(item)
        time.sleep(max(0.05, poll_seconds))
    raise AcceptanceFailure(f"FAIL timeout: TaskRun {task_run_id} did not reach a terminal state.")


def dispatch_and_poll(
    api_base_url: str,
    path: str,
    *,
    payload: Mapping[str, object] | None,
    timeout_seconds: int,
    poll_seconds: float,
) -> tuple[dict[str, Any], dict[str, object]]:
    dispatched = request_json(api_base_url, path, method="POST", payload=payload)
    task_run = dispatched.get("task_run")
    if not isinstance(task_run, dict) or not task_run.get("id"):
        raise AcceptanceFailure(f"FAIL dispatch: {path} did not return a TaskRun ID.")
    completed = poll_task_run(
        api_base_url,
        str(task_run["id"]),
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    return dispatched, completed


def run_canary(args: argparse.Namespace, preflight: dict[str, object]) -> dict[str, object]:
    runtime = verify_runtime_identity(args.api_base_url)
    _, universe_task = dispatch_and_poll(
        args.api_base_url,
        "/ingestion/instrument-universe?market=CN&provider=akshare",
        payload=None,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    if universe_task["status"] != "succeeded":
        raise AcceptanceFailure("FAIL universe: real API/worker universe synchronization failed.")
    universe = request_json(args.api_base_url, "/stock-selection/universe-status?market=CN&provider=akshare")
    universe_coverage = request_json(
        args.api_base_url,
        "/stock-selection/evidence-coverage?market=CN&provider=akshare",
    )
    universe_summary = universe_coverage.get("universe") or {}
    exchange_counts = (
        universe_summary.get("exchange_counts") if isinstance(universe_summary, Mapping) else {}
    ) or {}
    if not isinstance(exchange_counts, Mapping) or any(
        int(exchange_counts.get(exchange, 0)) <= 0 for exchange in ("SSE", "SZSE", "BSE")
    ):
        raise AcceptanceFailure("FAIL universe: stored SSE/SZSE/BSE distribution is incomplete.")

    dispatched, canary_task = dispatch_and_poll(
        args.api_base_url,
        "/ingestion/a-share-evidence-backfills",
        payload={
            "run_kind": "canary",
            "market": "CN",
            "provider": "akshare",
            "daily_bar_policy": args.daily_bar_policy,
            "evidence_kinds": ["daily_bars", "fundamentals", "technical_indicators"],
            "batch_size": 25,
            "cohort_size": 50,
        },
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    coverage = request_json(args.api_base_url, "/stock-selection/evidence-coverage?market=CN&provider=akshare")
    discoveries = run_discovery_replay(args.api_base_url)
    corporate_actions = run_corporate_action_slice(args)
    return {
        "status": "passed" if canary_task["status"] == "succeeded" else "needs_attention",
        "runtime": runtime,
        "preflight": preflight,
        "universe_task": universe_task,
        "universe": {**summarize_universe(universe), "exchange_counts": sanitize(exchange_counts)},
        "canary": {
            "backfill_run_id": ((dispatched.get("backfill") or {}).get("id") if isinstance(dispatched.get("backfill"), dict) else None),
            "task_run": canary_task,
        },
        "coverage": summarize_coverage(coverage),
        "discoveries": discoveries,
        "corporate_actions": corporate_actions,
    }


def run_baseline(args: argparse.Namespace, preflight: dict[str, object]) -> dict[str, object]:
    runtime = verify_runtime_identity(args.api_base_url)
    payload = build_baseline_payload(args)
    dispatched, task_run = dispatch_and_poll(
        args.api_base_url,
        "/ingestion/a-share-evidence-backfills",
        payload=payload,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    coverage = request_json(args.api_base_url, "/stock-selection/evidence-coverage?market=CN&provider=akshare")
    return {
        "status": "passed" if task_run["status"] == "succeeded" else "needs_attention",
        "runtime": runtime,
        "preflight": preflight,
        "baseline_run_id": ((dispatched.get("backfill") or {}).get("id") if isinstance(dispatched.get("backfill"), dict) else None),
        "task_run": task_run,
        "coverage": summarize_coverage(coverage),
    }


def build_baseline_payload(args: argparse.Namespace) -> dict[str, object]:
    if args.baseline_run_kind == "fundamental_shard":
        if args.shard_index is None:
            raise AcceptanceFailure(
                "FAIL baseline: --shard-index is required for a fundamental shard."
            )
        if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
            raise AcceptanceFailure(
                "FAIL baseline: --shard-index must be within --shard-count."
            )
        evidence_kinds = ["fundamentals"]
    else:
        if args.shard_index is not None:
            raise AcceptanceFailure(
                "FAIL baseline: --shard-index is only valid for a fundamental shard."
            )
        evidence_kinds = list(dict.fromkeys(args.evidence_kinds))

    payload: dict[str, object] = {
        "run_kind": args.baseline_run_kind,
        "market": "CN",
        "provider": "akshare",
        "daily_bar_policy": args.daily_bar_policy,
        "evidence_kinds": evidence_kinds,
        "batch_size": 25,
    }
    if args.baseline_run_kind == "fundamental_shard":
        payload.update(shard_index=args.shard_index, shard_count=args.shard_count)
    return payload


def run_discovery_replay(api_base_url: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for profile_id in ("balanced_research", "quality_value", "trend_liquidity"):
        attempts = [
            request_json(
                api_base_url,
                "/stock-selection/discover",
                method="POST",
                payload={"profile_id": profile_id, "market": "CN", "shortlist_limit": 10, "locale": "en", "use_llm": False},
                timeout=120,
            )
            for _ in range(2)
        ]
        symbols = [[str(item.get("symbol")) for item in attempt.get("shortlist", [])] for attempt in attempts]
        results.append(
            {
                "profile_id": profile_id,
                "stable": symbols[0] == symbols[1],
                "symbols": symbols[0],
                "coverage": attempts[0].get("coverage"),
                "model": attempts[0].get("model"),
            }
        )
    return results


def run_corporate_action_slice(args: argparse.Namespace) -> dict[str, object]:
    tasks: list[dict[str, object]] = []
    cursor = 0
    first_payload: dict[str, object] | None = None
    for batch_index in range(2):
        payload = {
            "report_period": args.report_period.isoformat(),
            "market": "CN",
            "provider": "akshare",
            "symbols": [],
            "event_types": ["dividend_bonus", "rights_allotment"],
            "cursor": cursor,
            "batch_size": 25,
        }
        if first_payload is None:
            first_payload = payload
        _, task = dispatch_and_poll(
            args.api_base_url,
            "/ingestion/corporate-actions",
            payload=payload,
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
        )
        tasks.append(task)
        result = task.get("result_json") if isinstance(task.get("result_json"), dict) else {}
        next_cursor = result.get("next_cursor")
        if next_cursor is None:
            break
        cursor = int(next_cursor)
    _, replay = dispatch_and_poll(
        args.api_base_url,
        "/ingestion/corporate-actions",
        payload=first_payload or {},
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    return {"report_period": args.report_period.isoformat(), "batches": tasks, "replay": replay}


def summarize_task_run(item: Mapping[str, object]) -> dict[str, object]:
    result = item.get("result_json") if isinstance(item.get("result_json"), dict) else None
    return sanitize(
        {
            "id": item.get("id"),
            "task_name": item.get("task_name"),
            "status": item.get("status"),
            "started_at": item.get("started_at"),
            "finished_at": item.get("finished_at"),
            "duration_ms": item.get("duration_ms"),
            "heartbeat_at": item.get("heartbeat_at"),
            "result_json": result,
            "error_type": "recorded" if item.get("error_message") else None,
        }
    )


def summarize_universe(payload: Mapping[str, object]) -> dict[str, object]:
    latest_sync = payload.get("latest_sync") if isinstance(payload.get("latest_sync"), dict) else None
    return sanitize(
        {
            "status": payload.get("status"),
            "active_instrument_count": payload.get("active_instrument_count"),
            "managed_instrument_count": payload.get("managed_instrument_count"),
            "exchange_counts": payload.get("exchange_counts"),
            "latest_sync": latest_sync,
        }
    )


def summarize_coverage(payload: Mapping[str, object]) -> dict[str, object]:
    return sanitize(
        {
            "status": payload.get("status"),
            "market": payload.get("market"),
            "provider": payload.get("provider"),
            "as_of": payload.get("as_of"),
            "universe": payload.get("universe"),
            "evidence": payload.get("evidence"),
            "latest_run": payload.get("latest_run"),
            "thresholds": payload.get("thresholds"),
        }
    )


def sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if SECRET_KEY_PATTERN.search(str(key)) else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [sanitize(item) for item in value[:100]]
    if isinstance(value, str):
        redacted = URL_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]@", value)
        redacted = BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
        return INLINE_SECRET_PATTERN.sub(r"\1=[REDACTED]", redacted)
    return value


def metadata() -> dict[str, object]:
    def command_output(command: list[str]) -> str:
        completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        return (completed.stdout or completed.stderr).strip().splitlines()[0] if (completed.stdout or completed.stderr).strip() else "unknown"

    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "commit": command_output(["git", "rev-parse", "HEAD"]),
        "git_status": "clean" if not git_status else "dirty",
        "python": sys.version.split()[0],
        "akshare": importlib.metadata.version("akshare"),
        "alembic_head": command_output([sys.executable, "-m", "alembic", "heads"]),
        "market": "CN",
        "provider": "akshare",
    }


def write_artifact(artifact_dir: Path, phase: str, payload: Mapping[str, object]) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = artifact_dir / f"{timestamp}-{phase}.json"
    sanitized = sanitize(payload)
    serialized = json.dumps(sanitized, ensure_ascii=False, indent=2, sort_keys=True)
    if SECRET_KEY_PATTERN.search(serialized) and "[REDACTED]" not in serialized:
        raise AcceptanceFailure("FAIL artifact: secret-like content survived sanitization.")
    path.write_text(serialized + "\n", encoding="utf-8")
    return path


def display_artifact_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        preflight = run_preflight(
            real_network=args.real_network,
            daily_bar_policy=args.daily_bar_policy,
        )
        if preflight["status"] != "passed":
            result = {
                "status": "failed",
                "metadata": metadata(),
                "preflight": preflight,
                "findings": classify_preflight_findings(preflight),
            }
            artifact_path = write_artifact(args.artifact_dir, args.phase, result)
            print(f"FAIL preflight: sanitized artifact {display_artifact_path(artifact_path)}")
            return 1
        if args.phase == "preflight":
            result: dict[str, object] = {"status": "passed", "metadata": metadata(), "preflight": preflight}
        else:
            require_write_guards(
                real_network=args.real_network,
                confirm_acceptance_writes=args.confirm_acceptance_writes,
                database_url=args.database_url,
            )
            phase_result = run_canary(args, preflight) if args.phase == "canary" else run_baseline(args, preflight)
            result = {"metadata": metadata(), **phase_result}
        artifact_path = write_artifact(args.artifact_dir, args.phase, result)
        print(f"PASS {args.phase}: sanitized artifact {display_artifact_path(artifact_path)}")
        return 0 if result.get("status") == "passed" else 2
    except AcceptanceFailure as exc:
        print(sanitize(str(exc)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
