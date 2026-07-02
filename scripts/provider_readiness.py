"""Smoke-check market data providers without writing to the database."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from pathlib import Path
from typing import Protocol, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.providers.base import ProviderBar, ProviderInstrument  # noqa: E402
from packages.providers.mock_provider import MockProvider  # noqa: E402
from packages.providers.yfinance_provider import YFinanceProvider  # noqa: E402


DEFAULT_PROVIDER = "mock"
DEFAULT_MARKET = "US"
DEFAULT_TIMEFRAME = "1d"
LOOKBACK_DAYS = 10


class ReadinessStatus(str, Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ProviderReadinessResult:
    status: ReadinessStatus
    name: str
    message: str
    details: list[str]
    suggestions: list[str]


class Provider(Protocol):
    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]: ...

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]: ...


ProviderFactory = Callable[[], Provider]


PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "mock": MockProvider,
    "yfinance": YFinanceProvider,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke-check a market data provider without database writes.",
    )
    parser.add_argument(
        "--provider",
        default=DEFAULT_PROVIDER,
        help=f"Provider to check. Defaults to {DEFAULT_PROVIDER!r}.",
    )
    parser.add_argument(
        "--market",
        default=DEFAULT_MARKET,
        help=f"Market used when selecting a default instrument. Defaults to {DEFAULT_MARKET!r}.",
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="Symbol to fetch. Defaults to the provider's first instrument for the market.",
    )
    parser.add_argument(
        "--real-network",
        action="store_true",
        help="Opt in to real network access for live providers such as yfinance.",
    )
    return parser


def check_provider_readiness(
    provider_name: str,
    market: str,
    symbol: str | None,
    real_network: bool,
) -> list[ProviderReadinessResult]:
    normalized_provider_name = provider_name.strip().lower()
    normalized_market = market.strip().upper()
    normalized_symbol = symbol.strip().upper() if symbol is not None and symbol.strip() else None

    if normalized_provider_name not in PROVIDER_FACTORIES:
        supported_providers = ", ".join(sorted(PROVIDER_FACTORIES))
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.FAIL,
                name="provider readiness",
                message=f"unknown provider: {provider_name}",
                details=[f"Supported providers: {supported_providers}."],
                suggestions=["Use --provider mock or --provider yfinance."],
            )
        ]

    if normalized_provider_name == "yfinance" and not real_network:
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.WARN,
                name="provider readiness",
                message="yfinance readiness requires explicit real-network opt-in.",
                details=[
                    "Skipped live yfinance fetch because --real-network was not provided.",
                    "This smoke check is non-destructive and performs no database writes.",
                ],
                suggestions=[
                    "python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL --real-network"
                ],
            )
        ]

    try:
        provider = PROVIDER_FACTORIES[normalized_provider_name]()
    except Exception as exc:
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.FAIL,
                name="provider readiness",
                message=f"failed to create provider {normalized_provider_name}: {exc}",
                details=[type(exc).__name__],
                suggestions=["Check provider dependencies and local environment configuration."],
            )
        ]

    selected_symbol = normalized_symbol
    if selected_symbol is None:
        symbol_result = select_default_symbol(provider, normalized_market, normalized_provider_name)
        if isinstance(symbol_result, ProviderReadinessResult):
            return [symbol_result]
        selected_symbol = symbol_result

    end_date = date.today()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)

    try:
        bars = provider.fetch_bars(selected_symbol, DEFAULT_TIMEFRAME, start_date, end_date)
    except Exception as exc:
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.FAIL,
                name="provider readiness",
                message=f"{normalized_provider_name} failed to fetch bars for {selected_symbol}: {exc}",
                details=[
                    f"provider={normalized_provider_name}",
                    f"market={normalized_market}",
                    f"symbol={selected_symbol}",
                    f"date_range={start_date.isoformat()}..{end_date.isoformat()}",
                    type(exc).__name__,
                ],
                suggestions=["Verify provider credentials, dependencies, and symbol mapping."],
            )
        ]

    if not bars:
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.FAIL,
                name="provider readiness",
                message=f"{normalized_provider_name} returned no bars for {selected_symbol}.",
                details=[
                    f"provider={normalized_provider_name}",
                    f"market={normalized_market}",
                    f"symbol={selected_symbol}",
                    f"timeframe={DEFAULT_TIMEFRAME}",
                    f"date_range={start_date.isoformat()}..{end_date.isoformat()}",
                ],
                suggestions=["Try an explicit --symbol or a wider provider-specific smoke later."],
            )
        ]

    return [
        ProviderReadinessResult(
            status=ReadinessStatus.OK,
            name="provider readiness",
            message=f"{normalized_provider_name} returned {len(bars)} bars for {selected_symbol}.",
            details=[
                f"provider={normalized_provider_name}",
                f"market={normalized_market}",
                f"symbol={selected_symbol}",
                f"timeframe={DEFAULT_TIMEFRAME}",
                f"date_range={start_date.isoformat()}..{end_date.isoformat()}",
                "database_writes=none",
            ],
            suggestions=[],
        )
    ]


def select_default_symbol(
    provider: Provider,
    market: str,
    provider_name: str,
) -> str | ProviderReadinessResult:
    try:
        instruments = provider.fetch_instruments(market)
    except Exception as exc:
        return ProviderReadinessResult(
            status=ReadinessStatus.FAIL,
            name="provider readiness",
            message=f"{provider_name} failed to fetch instruments for market {market}: {exc}",
            details=[f"provider={provider_name}", f"market={market}", type(exc).__name__],
            suggestions=["Pass --symbol explicitly or verify provider instrument support."],
        )

    if not instruments:
        return ProviderReadinessResult(
            status=ReadinessStatus.FAIL,
            name="provider readiness",
            message=f"{provider_name} has no instruments for market {market}.",
            details=[f"provider={provider_name}", f"market={market}"],
            suggestions=["Pass --symbol explicitly or choose a supported market."],
        )

    return instruments[0].symbol


def render_results(
    results: Sequence[ProviderReadinessResult],
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
        ReadinessStatus.OK: 0,
        ReadinessStatus.WARN: 0,
        ReadinessStatus.FAIL: 0,
    }
    for result in results:
        status_counts[result.status] += 1

    print(
        "Summary: "
        f"OK={status_counts[ReadinessStatus.OK]} "
        f"WARN={status_counts[ReadinessStatus.WARN]} "
        f"FAIL={status_counts[ReadinessStatus.FAIL]}",
        file=output_stream,
    )


def has_failures(results: Sequence[ProviderReadinessResult]) -> bool:
    return any(result.status == ReadinessStatus.FAIL for result in results)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    results = check_provider_readiness(
        provider_name=args.provider,
        market=args.market,
        symbol=args.symbol,
        real_network=args.real_network,
    )
    render_results(results)
    return 1 if has_failures(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
