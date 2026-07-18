"""Run automated MVP acceptance checks against a running API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def base_url() -> str:
    return os.environ.get("API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def probe_base(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/openapi.json", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            paths = payload.get("paths", {})
            return "/watchlist" in paths and "/settings/platform" in paths
    except Exception:
        return False


def resolve_api_base() -> str:
    explicit = os.environ.get("API_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    for candidate in ("http://127.0.0.1:8001", "http://127.0.0.1:8000"):
        if probe_base(candidate):
            return candidate
    return base_url()


def check(name: str, path: str, method: str = "GET", expect_status: int = 200) -> bool:
    url = f"{base_url()}{path}"
    request = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            ok = response.status == expect_status
            body = response.read().decode("utf-8", errors="replace")
            print(f"{'PASS' if ok else 'FAIL'} {name}: {response.status} {path}")
            if not ok:
                print(f"  body: {body[:200]}")
            return ok
    except urllib.error.HTTPError as exc:
        print(f"FAIL {name}: HTTP {exc.code} {path}")
        return False
    except Exception as exc:
        print(f"FAIL {name}: {exc}")
        return False


def check_json(name: str, path: str, predicate) -> bool:
    url = f"{base_url()}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            ok = predicate(payload)
            print(f"{'PASS' if ok else 'FAIL'} {name}: {path}")
            return ok
    except Exception as exc:
        print(f"FAIL {name}: {exc}")
        return False


def main() -> int:
    api = resolve_api_base()
    os.environ["API_BASE_URL"] = api
    print(f"MVP acceptance against {api}\n")
    results = [
        check("health", "/health"),
        check_json(
            "instruments multi-market",
            "/instruments",
            lambda p: len(p.get("items", [])) >= 1,
        ),
        check_json(
            "watchlist endpoint",
            "/watchlist",
            lambda p: "items" in p,
        ),
        check_json(
            "portfolios endpoint",
            "/portfolios",
            lambda p: "items" in p,
        ),
        check_json(
            "settings endpoint",
            "/settings/platform",
            lambda p: "market_data_provider" in p,
        ),
        check_json(
            "task runs endpoint",
            "/task-runs/recent?limit=5",
            lambda p: "items" in p,
        ),
        check_json(
            "alert triggers endpoint",
            "/alerts/triggers/recent?limit=5",
            lambda p: "items" in p,
        ),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
