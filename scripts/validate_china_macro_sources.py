"""Validate China macro source candidates without writing market observations."""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.services.source_capabilities import CHINA_MACRO_SOURCE_CAPABILITIES  # noqa: E402
from packages.services.source_capabilities import SourceCapability  # noqa: E402
from packages.services.source_capabilities import get_source_capability_by_id  # noqa: E402


DEFAULT_SOURCE = "all"
DEFAULT_TIMEOUT_SECONDS = 10.0
PROBE_NAME = "China macro source validation"


class ValidationResultStatus(str, Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ProbeHttpResponse:
    status_code: int
    text: str


@dataclass(frozen=True)
class SourceValidationResult:
    status: ValidationResultStatus
    name: str
    message: str
    details: list[str]
    suggestions: list[str]


class ProbeFetcher(Protocol):
    def __call__(self, url: str, timeout_seconds: float) -> ProbeHttpResponse: ...


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate China macro source candidates without database writes.",
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Source capability ID to validate, or 'all'. Defaults to 'all'.",
    )
    parser.add_argument(
        "--live-network",
        action="store_true",
        help="Opt in to shallow live reachability/schema probes.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Live probe timeout in seconds. Defaults to {DEFAULT_TIMEOUT_SECONDS:g}.",
    )
    return parser


def validate_china_macro_sources(
    *,
    source: str = DEFAULT_SOURCE,
    live_network: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    fetcher: ProbeFetcher | None = None,
) -> list[SourceValidationResult]:
    capabilities = _select_capabilities(source)
    if isinstance(capabilities, SourceValidationResult):
        return [capabilities]

    probe_fetcher = fetcher or fetch_probe_url
    return [
        validate_source_capability(
            capability,
            live_network=live_network,
            timeout_seconds=timeout_seconds,
            fetcher=probe_fetcher,
        )
        for capability in capabilities
    ]


def validate_source_capability(
    capability: SourceCapability,
    *,
    live_network: bool,
    timeout_seconds: float,
    fetcher: ProbeFetcher,
) -> SourceValidationResult:
    if not live_network:
        return SourceValidationResult(
            status=ValidationResultStatus.WARN,
            name=PROBE_NAME,
            message=f"{capability.id} live probe skipped; capability status is {capability.adapter_status}.",
            details=_base_details(capability)
            + [
                "validation_status=skipped",
                "reason=live probe skipped because --live-network was not provided",
            ],
            suggestions=[_live_probe_suggestion(capability.id)],
        )

    if capability.live_probe_url is None:
        return SourceValidationResult(
            status=ValidationResultStatus.WARN,
            name=PROBE_NAME,
            message=f"{capability.id} has no live probe URL; manual/license validation is required.",
            details=_base_details(capability)
            + [
                "validation_status=skipped",
                "reason=no_live_probe_url",
            ],
            suggestions=[capability.recommended_next_action],
        )

    try:
        response = fetcher(capability.live_probe_url, timeout_seconds)
    except Exception as exc:
        return SourceValidationResult(
            status=ValidationResultStatus.FAIL,
            name=PROBE_NAME,
            message=f"{capability.id} live probe failed with {type(exc).__name__}.",
            details=_base_details(capability)
            + [
                f"exception_type={type(exc).__name__}",
                "validation_status=failed",
            ],
            suggestions=["Verify source reachability, endpoint shape, and usage terms before adding an adapter."],
        )

    details = _base_details(capability) + [
        f"http_status={response.status_code}",
        "validation_status=checked",
    ]
    if not 200 <= response.status_code < 300:
        return SourceValidationResult(
            status=ValidationResultStatus.FAIL,
            name=PROBE_NAME,
            message=f"{capability.id} live probe returned HTTP {response.status_code}.",
            details=details,
            suggestions=["Treat this source as candidate/manual until access and schema are validated."],
        )

    missing_markers = [
        marker
        for marker in capability.live_probe_markers
        if marker not in response.text
    ]
    if missing_markers:
        return SourceValidationResult(
            status=ValidationResultStatus.WARN,
            name=PROBE_NAME,
            message=f"{capability.id} live probe schema marker was not found.",
            details=details
            + [
                f"missing_markers={','.join(missing_markers)}",
            ],
            suggestions=["Inspect the response schema before promoting this source to adapter-ready."],
        )

    return SourceValidationResult(
        status=ValidationResultStatus.OK,
        name=PROBE_NAME,
        message=f"{capability.id} live probe returned expected marker.",
        details=details,
        suggestions=[],
    )


def fetch_probe_url(url: str, timeout_seconds: float) -> ProbeHttpResponse:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "stock-analysis-platform-source-validation/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_body = response.read(64_000)
            charset = response.headers.get_content_charset() or "utf-8"
            return ProbeHttpResponse(
                status_code=response.status,
                text=raw_body.decode(charset, errors="replace"),
            )
    except urllib.error.HTTPError as error:
        return ProbeHttpResponse(status_code=error.code, text="")


def _select_capabilities(source: str) -> tuple[SourceCapability, ...] | SourceValidationResult:
    normalized_source = source.strip().lower()
    if normalized_source == DEFAULT_SOURCE:
        return CHINA_MACRO_SOURCE_CAPABILITIES

    capability = get_source_capability_by_id(normalized_source)
    if capability is None:
        supported = ", ".join(
            [DEFAULT_SOURCE, *(capability.id for capability in CHINA_MACRO_SOURCE_CAPABILITIES)]
        )
        return SourceValidationResult(
            status=ValidationResultStatus.FAIL,
            name=PROBE_NAME,
            message=f"unknown source: {source}",
            details=[f"Supported sources: {supported}."],
            suggestions=[f"Use one of: {supported}."],
        )
    return (capability,)


def _base_details(capability: SourceCapability) -> list[str]:
    return [
        f"source_id={capability.id}",
        f"access_mode={capability.access_mode}",
        f"adapter_status={capability.adapter_status}",
        f"credential_required={capability.credential_required}",
        "database_writes=none",
        "is_ai_citable=false",
    ]


def _live_probe_suggestion(source_id: str) -> str:
    return (
        "Run with explicit opt-in: "
        f"python scripts/validate_china_macro_sources.py --source {source_id} --live-network"
    )


def render_results(
    results: Sequence[SourceValidationResult],
    output: TextIO | None = None,
) -> None:
    output_stream = output if output is not None else sys.stdout
    for result in results:
        print(f"{result.status.value} {result.name}: {result.message}", file=output_stream)
        for detail in result.details:
            print(f"  - {detail}", file=output_stream)
        for suggestion in result.suggestions:
            print(f"  suggestion: {suggestion}", file=output_stream)

    status_counts = {
        ValidationResultStatus.OK: 0,
        ValidationResultStatus.WARN: 0,
        ValidationResultStatus.FAIL: 0,
    }
    for result in results:
        status_counts[result.status] += 1

    print(
        "Summary: "
        f"OK={status_counts[ValidationResultStatus.OK]} "
        f"WARN={status_counts[ValidationResultStatus.WARN]} "
        f"FAIL={status_counts[ValidationResultStatus.FAIL]}",
        file=output_stream,
    )


def has_failures(results: Sequence[SourceValidationResult]) -> bool:
    return any(result.status == ValidationResultStatus.FAIL for result in results)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    results = validate_china_macro_sources(
        source=args.source,
        live_network=args.live_network,
        timeout_seconds=args.timeout,
    )
    render_results(results)
    return 1 if has_failures(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
